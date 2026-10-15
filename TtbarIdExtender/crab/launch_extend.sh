#!/usr/bin/env bash
# =============================================================================
# launch_extend.sh -- one command for a whole extend (ttbarIdExtend) launch
# =============================================================================
# Runs every step of TtbarIdExtender/README.md sec.2.2d for the given era(s),
# in order, and STOPS at the first step whose pass condition fails:
#
#   1 env        CMSSW_10_6_X after cmsenv, cmsRun/root/dasgoclient on PATH,
#                CRABClient (sources crab-setup.sh if needed), VOMS proxy with
#                >= 24 h left, the era blocks exist in datasets.yaml
#   2 local      per era: cmsRun year=<ERA> on one MiniAOD file of the smallest
#                sample (TTbb_DiLep); needs exit 0, the expected era-modifier
#                line, the output file, and 0 "missing" in the endJob summary
#   3 invariants per era: check_extend_invariants.C -> ALL INVARIANTS PASS
#   4 resolve    per era: resolve_parents.sh <ERA>          -> MATCH 7/7, exit 0
#   5 apply      per era: resolve_parents.sh <ERA> --apply  -> exit 0
#   6 preflight  submit_ttbarIdExtend.py --preflight --check-das -> 0 FAIL, 0 WARN
#   7 dryrun     submit_ttbarIdExtend.py --dry-run -> attempted == entries, skipped 0
#   8 submit     (only with --submit) -> submitted == entries, no [FAILED]/[skip]
#   9 report     (only with --submit) wait, then --report -> no DEAD TASK
#
# The only interactive part stays with you: voms-proxy-init (grid pass phrase).
#
# Usage (lxplus, inside cmssw-el7, after cmsenv and voms-proxy-init):
#   bash crab/launch_extend.sh --era 2016APV,2016            # steps 1-7, no submit
#   bash crab/launch_extend.sh --era 2016APV,2016 --submit   # steps 1-9
# Options:
#   --skip-local      skip steps 2-3 (only after they passed for these eras)
#   --max-events N    local test size per era (default 20000)
#   --report-wait S   seconds between submit and --report (default 300)
#
# Logs: crab/launch_logs/<UTC>_<eras>/ (git-ignored) holds launch.log (all
# output, with a header and a final "=== END launch_extend.sh ... EXIT=" line;
# a log without that line means the run was killed or is still running), one
# log per step, and the local test outputs. The read-only resolve logs are also
# copied to crab/resolve_parents_<ERA>_<YYYYmmdd_HHMM>.log (tracked, like the
# 2018 one) so they can be committed together with datasets.yaml.
#
# Exit codes: 0 every requested step passed; 2 bad arguments; 10 env;
#   11 local cmsRun; 12 invariants; 13 resolve (not every sample MATCH);
#   14 apply; 15 preflight; 16 dry-run; 17 submit; 18 report (DEAD TASK);
#   130 interrupted (SIGINT/SIGTERM).
#
# ASCII-only, bash 4.2 (cmssw-el7) compatible.
# =============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../TtbarIdExtender/crab
PKG="$(dirname "$HERE")"                                # .../TtbarIdExtender
REPO="$(dirname "$PKG")"                                # .../TTHHGenCategoryTools
YAML="$HERE/datasets.yaml"
SUBMIT="$HERE/submit_ttbarIdExtend.py"
RESOLVE="$HERE/resolve_parents.sh"
PSET="$PKG/test/run_ttbarIdExtend_cfg.py"
MACRO="$REPO/Validation/scripts/check_extend_invariants.C"
LOCAL_SAMPLE="TTbb_DiLep"
XRD="root://cms-xrd-global.cern.ch/"
CRAB_SETUP="/cvmfs/cms.cern.ch/common/crab-setup.sh"

declare -A ERA_MOD=( ["2016APV"]="Run2_2016_HIPM" ["2016"]="Run2_2016"
                     ["2017"]="Run2_2017"         ["2018"]="Run2_2018" )

usage() { awk 'NR>=2 && /^set -u/ {exit} NR>=2' "${BASH_SOURCE[0]}" | sed 's/^#\{0,1\} \{0,1\}//'; }

ERAS=""; DO_SUBMIT=0; SKIP_LOCAL=0; MAXEV=20000; REPORT_WAIT=300
while [[ $# -gt 0 ]]; do
  case "$1" in
    --era)          ERAS="${2:-}"; shift 2 ;;
    --submit)       DO_SUBMIT=1; shift ;;
    --skip-local)   SKIP_LOCAL=1; shift ;;
    --max-events)   MAXEV="${2:-}"; shift 2 ;;
    --report-wait)  REPORT_WAIT="${2:-}"; shift 2 ;;
    -h|--help)      usage; exit 0 ;;
    *) echo "ERROR: unknown argument '$1' (try --help)" >&2; exit 2 ;;
  esac
done
[[ -n "$ERAS" ]] || { echo "ERROR: --era is required (e.g. --era 2016APV,2016)" >&2; exit 2; }
[[ "$MAXEV" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: --max-events must be a positive integer" >&2; exit 2; }
[[ "$REPORT_WAIT" =~ ^[0-9]+$ ]] || { echo "ERROR: --report-wait must be a non-negative integer" >&2; exit 2; }
IFS=',' read -r -a ERA_LIST <<< "$ERAS"
for E in "${ERA_LIST[@]}"; do
  [[ -n "${ERA_MOD[$E]:-}" ]] || { echo "ERROR: unsupported era '$E' (2016APV, 2016, 2017, 2018)" >&2; exit 2; }
done

TS="$(date -u +%Y%m%d_%H%M%S)"
TSL="$(date +%Y%m%d_%H%M)"
RUN="$HERE/launch_logs/${TS}_${ERAS//,/-}"
mkdir -p "$RUN" || { echo "ERROR: cannot create $RUN" >&2; exit 2; }
LOG="$RUN/launch.log"
NSTEPS=7; (( DO_SUBMIT )) && NSTEPS=9
export PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
# value of key $3 (dataset | nano_child) of entry $2 in era block $1
yaml_field() {
  ERA="$1" NAME="$2" KEY="$3" awk '
    $0 ~ "^  \"" ENVIRON["ERA"] "\":"  { inera=1; nm=""; next }
    inera && /^  "[0-9]/               { inera=0 }
    !inera                             { next }
    /^[[:space:]]+- name:/             { nm=$3; gsub(/"/,"",nm) }
    nm == ENVIRON["NAME"] && $1 == ENVIRON["KEY"] ":" { v=$2; gsub(/"/,"",v); print v; exit }
  ' "$YAML"
}
# number of entries in era block $1
yaml_count() {
  ERA="$1" awk '
    $0 ~ "^  \"" ENVIRON["ERA"] "\":"  { inera=1; next }
    inera && /^  "[0-9]/               { inera=0 }
    inera && /^[[:space:]]+- name:/    { n++ }
    END                                { print n+0 }
  ' "$YAML"
}

T_START=$(date +%s)
STEP_K=0; STEP_NAME="(start)"; STEP_T0=$T_START
RESULTS=()
step() {
  STEP_K=$1; STEP_NAME=$2; STEP_T0=$(date +%s)
  echo ""
  echo "[launch] ==== step $STEP_K/$NSTEPS $STEP_NAME -- start $(date -u +%FT%TZ)"
}
step_ok() {
  local extra="${1:-}"
  echo "[launch] ==== step $STEP_K/$NSTEPS $STEP_NAME -- OK ($(( $(date +%s) - STEP_T0 )) s)${extra:+ $extra}"
  RESULTS+=("step $STEP_K/$NSTEPS $STEP_NAME: OK${extra:+ $extra}")
}
die() {   # die <exit code> <reason> [<log to read>]
  echo "[launch] ==== step $STEP_K/$NSTEPS $STEP_NAME -- FAILED: $2"
  [[ -n "${3:-}" ]] && echo "[launch]      read: $3"
  RESULTS+=("step $STEP_K/$NSTEPS $STEP_NAME: FAILED ($2)")
  exit "$1"
}
on_exit() {
  local rc=$?
  echo ""
  echo "[launch] ------------------------------------------------------------"
  local r
  for r in ${RESULTS[@]+"${RESULTS[@]}"}; do echo "[launch]   $r"; done
  if [[ $rc -eq 0 ]]; then
    if (( DO_SUBMIT )); then
      echo "[launch] RESULT: SUBMITTED -- follow with: python3 crab/submit_ttbarIdExtend.py --era $ERAS --report"
      echo "[launch] then commit the opened entries and the resolve logs (from $REPO):"
      echo "[launch]   git add TtbarIdExtender/crab/datasets.yaml${RESOLVE_COPIES:-}"
      echo "[launch]   git commit -m \"extend: $ERAS parents MATCH, entries opened by resolve_parents --apply; resolve logs\""
      echo "[launch]   git push"
    else
      echo "[launch] RESULT: READY -- every check passed; nothing submitted. Re-run with --submit"
      echo "[launch]         (add --skip-local to skip the local tests that just passed)."
    fi
  else
    echo "[launch] RESULT: STOPPED at step $STEP_K/$NSTEPS ($STEP_NAME), nothing after it ran."
  fi
  echo "=== END launch_extend.sh  EXIT=$rc  $(date -u +%FT%TZ)  elapsed=$(( $(date +%s) - T_START ))s  log=$LOG"
}

# ---------------------------------------------------------------------------
# main runs in a subshell (main | tee below) and ends with `exit`, never `return`: bash 4.2 (cmssw-el7) does not
# run a subshell's EXIT trap when a function there just returns -- on 2026-10-15 a successful --submit on lxplus
# ended without the summary, the commit hints and the END line (docs/08 T-37). `exit` runs the trap in every bash.
main() {
  trap on_exit EXIT
  trap 'echo "[launch] INTERRUPTED (SIGINT) during step $STEP_K ($STEP_NAME)"; exit 130' INT
  trap 'echo "[launch] TERMINATED (SIGTERM) during step $STEP_K ($STEP_NAME)"; exit 130' TERM
  cd "$PKG" || exit 2     # CRAB work_area (crab_projects) is relative to here

  echo "=== START launch_extend.sh  $(date -u +%FT%TZ)  host=$(hostname 2>/dev/null || echo '?')  user=${USER:-?}"
  echo "    eras=$ERAS  submit=$DO_SUBMIT  skip_local=$SKIP_LOCAL  max_events=$MAXEV  report_wait=${REPORT_WAIT}s"
  echo "    repo=$REPO"
  echo "    commit=$(git -C "$REPO" --no-optional-locks rev-parse --short HEAD 2>/dev/null || echo '(not a git checkout)')"
  echo "    run dir=$RUN"
  echo "    steps: 1 env, 2 local, 3 invariants, 4 resolve, 5 apply, 6 preflight, 7 dryrun$( (( DO_SUBMIT )) && echo ', 8 submit, 9 report')"

  # ---- 1 env -----------------------------------------------------------------
  step 1 env
  [[ -n "${CMSSW_BASE:-}" ]] || die 10 "CMSSW_BASE unset -- run cmsenv in CMSSW_10_6_32_patch1/src (inside cmssw-el7)"
  [[ "${CMSSW_VERSION:-}" == CMSSW_10_6_* ]] || die 10 "CMSSW_VERSION=${CMSSW_VERSION:-unset}, this package needs CMSSW_10_6_32_patch1"
  local tool
  for tool in cmsRun root dasgoclient voms-proxy-info python3; do   # git is optional (header only)
    command -v "$tool" >/dev/null 2>&1 || die 10 "'$tool' not on PATH"
  done
  if ! python3 -c "import CRABClient" >/dev/null 2>&1; then
    echo "[launch] CRABClient not importable -> source $CRAB_SETUP"
    set +u
    # shellcheck disable=SC1090
    source "$CRAB_SETUP" >/dev/null 2>&1
    set -u
    python3 -c "import CRABClient" >/dev/null 2>&1 || die 10 "CRABClient still not importable after sourcing $CRAB_SETUP"
  fi
  local left
  left="$(voms-proxy-info -timeleft 2>/dev/null | tr -dc '0-9')"
  [[ -n "$left" && "$left" -ge 86400 ]] || die 10 "VOMS proxy has ${left:-no} s left (need >= 24 h): voms-proxy-init -voms cms -valid 192:00"
  local E n
  for E in "${ERA_LIST[@]}"; do
    n="$(yaml_count "$E")"
    [[ "$n" -gt 0 ]] || die 10 "era '$E' has no entries in $YAML (git pull --ff-only first?)"
    [[ -n "$(yaml_field "$E" "$LOCAL_SAMPLE" nano_child)" ]] || die 10 "era '$E' has no $LOCAL_SAMPLE entry"
    echo "[launch] era $E: $n entries in datasets.yaml, expected era modifier ${ERA_MOD[$E]}"
  done
  [[ -f "$PSET" && -f "$MACRO" && -f "$RESOLVE" && -f "$SUBMIT" ]] || die 10 "a package file is missing (pset, macro, resolve, submitter)"
  echo "[launch] CMSSW=$CMSSW_VERSION  proxy=$(( left / 3600 )) h left  CRABClient ok"
  step_ok

  # ---- 2 local / 3 invariants --------------------------------------------------
  local nano mini file out rc lines miss
  declare -A OUTFILE=()
  if (( SKIP_LOCAL )); then
    step 2 local;      step_ok "(skipped by --skip-local)"
    step 3 invariants; step_ok "(skipped by --skip-local)"
  else
    step 2 local
    local i=0
    for E in "${ERA_LIST[@]}"; do
      i=$((i+1))
      nano="$(yaml_field "$E" "$LOCAL_SAMPLE" nano_child)"
      mini="$(dasgoclient -query="parent dataset=${nano}" 2>/dev/null | grep MINIAODSIM | head -n1)"
      [[ -n "$mini" ]] || die 11 "DAS returned no MiniAOD parent for $nano (proxy? DAS?)"
      file="$(dasgoclient -query="file dataset=${mini}" 2>/dev/null | grep '\.root$' | head -n1)"
      [[ -n "$file" ]] || die 11 "DAS returned no file for $mini"
      echo "[launch] local $i/${#ERA_LIST[@]} era=$E  $file  (maxEvents=$MAXEV; progress = 'Begin processing' lines)"
      (cd "$RUN" && cmsRun "$PSET" year="$E" inputFiles="${XRD}${file}" maxEvents="$MAXEV" \
         outputFile="ttbarIDExtend_local${E}.root") 2>&1 | tee -i "$RUN/local_${E}.log"
      rc=${PIPESTATUS[0]}
      [[ $rc -eq 0 ]] || die 11 "cmsRun year=$E exited $rc" "$RUN/local_${E}.log"
      grep -q "era modifier = ${ERA_MOD[$E]} + run2_nanoAOD_106Xv2" "$RUN/local_${E}.log" \
        || die 11 "no 'era modifier = ${ERA_MOD[$E]} + run2_nanoAOD_106Xv2' line" "$RUN/local_${E}.log"
      out="$RUN/ttbarIDExtend_local${E}_numEvent${MAXEV}.root"
      [[ -s "$out" ]] || die 11 "output file missing or empty: $out" "$RUN/local_${E}.log"
      OUTFILE[$E]="$out"
      if grep -q "endJob summary" "$RUN/local_${E}.log"; then
        lines="$(grep -o 'missing [A-Za-z_]*=[0-9]*' "$RUN/local_${E}.log")"
        miss="$(printf '%s\n' "$lines" | grep -v '=0$' | grep -c .)"
        [[ "$miss" -eq 0 ]] || die 11 "endJob summary reports missing values: $(printf '%s ' $lines)" "$RUN/local_${E}.log"
        echo "[launch] era $E endJob summary: $(grep -o 'total rows=[0-9]*' "$RUN/local_${E}.log" | head -n1), missing all 0"
      else
        echo "[launch] WARNING: no 'endJob summary' line in the cmsRun log (MessageLogger); step 3 still checks the tree"
      fi
    done
    step_ok

    step 3 invariants
    for E in "${ERA_LIST[@]}"; do
      root -l -b -q "${MACRO}(\"${OUTFILE[$E]}\")" 2>&1 | tee -i "$RUN/invariants_${E}.log"
      grep -q "VERDICT: ALL INVARIANTS PASS" "$RUN/invariants_${E}.log" \
        || die 12 "era $E: no 'VERDICT: ALL INVARIANTS PASS'" "$RUN/invariants_${E}.log"
    done
    step_ok
  fi

  # ---- 4 resolve / 5 apply -------------------------------------------------------
  step 4 resolve
  RESOLVE_COPIES=""
  for E in "${ERA_LIST[@]}"; do
    bash "$RESOLVE" "$E" 2>&1 | tee -i "$RUN/resolve_${E}.log"
    rc=${PIPESTATUS[0]}
    [[ $rc -eq 0 ]] || die 13 "resolve_parents.sh $E exited $rc (3 = not every sample MATCH; paste the DAS parent by hand)" "$RUN/resolve_${E}.log"
    cp "$RUN/resolve_${E}.log" "$HERE/resolve_parents_${E}_${TSL}.log"
    RESOLVE_COPIES="$RESOLVE_COPIES TtbarIdExtender/crab/resolve_parents_${E}_${TSL}.log"
  done
  step_ok

  step 5 apply
  for E in "${ERA_LIST[@]}"; do
    bash "$RESOLVE" "$E" --apply 2>&1 | tee -i "$RUN/apply_${E}.log"
    rc=${PIPESTATUS[0]}
    [[ $rc -eq 0 ]] || die 14 "resolve_parents.sh $E --apply exited $rc" "$RUN/apply_${E}.log"
  done
  step_ok

  # ---- 6 preflight / 7 dry-run ------------------------------------------------------
  local expected=0
  for E in "${ERA_LIST[@]}"; do expected=$(( expected + $(yaml_count "$E") )); done

  step 6 preflight
  python3 "$SUBMIT" --era "$ERAS" --preflight --check-das 2>&1 | tee -i "$RUN/preflight.log"
  rc=${PIPESTATUS[0]}
  [[ $rc -eq 0 ]] || die 15 "preflight exited $rc (FAIL lines above)" "$RUN/preflight.log"
  grep -q "RESULT: READY TO SUBMIT" "$RUN/preflight.log" || die 15 "no 'RESULT: READY TO SUBMIT'" "$RUN/preflight.log"
  if grep -q '^\[WARN\]' "$RUN/preflight.log"; then
    grep '^\[WARN\]' "$RUN/preflight.log"
    die 15 "preflight has WARN lines (an existing project dir would be SKIPPED; a closed entry would not be submitted)" "$RUN/preflight.log"
  fi
  step_ok

  step 7 dryrun
  python3 "$SUBMIT" --era "$ERAS" --dry-run 2>&1 | tee -i "$RUN/dryrun.log"
  rc=${PIPESTATUS[0]}
  [[ $rc -eq 0 ]] || die 16 "dry-run exited $rc" "$RUN/dryrun.log"
  grep -Eq "attempted : +${expected}$" "$RUN/dryrun.log" || die 16 "dry-run did not attempt all $expected entries" "$RUN/dryrun.log"
  grep -Eq "skipped +: +0 " "$RUN/dryrun.log" || die 16 "dry-run skipped entries (enabled:false)" "$RUN/dryrun.log"
  step_ok "($expected tasks planned)"

  (( DO_SUBMIT )) || exit 0

  # ---- 8 submit / 9 report ---------------------------------------------------------
  step 8 submit
  python3 "$SUBMIT" --era "$ERAS" 2>&1 | tee -i "$RUN/submit.log"
  rc=${PIPESTATUS[0]}
  [[ $rc -eq 0 ]] || die 17 "submitter exited $rc" "$RUN/submit.log"
  if grep -q '\[FAILED\]\|\[skip\] project dir already exists' "$RUN/submit.log"; then
    grep '\[FAILED\]\|\[skip\] project dir already exists' "$RUN/submit.log"
    echo "[launch] the other tasks WERE submitted: python3 crab/submit_ttbarIdExtend.py --era $ERAS --report"
    echo "[launch] for a failed task: remove its empty crab_projects/crab_<request> (docs/08 T-16), then"
    echo "[launch]   python3 crab/submit_ttbarIdExtend.py --era <ERA> --process <name>"
    die 17 "some task was not submitted (lines above)" "$RUN/submit.log"
  fi
  grep -Eq "submitted : +${expected}$" "$RUN/submit.log" || die 17 "submitted count is not $expected" "$RUN/submit.log"
  step_ok "($expected tasks)"

  step 9 report
  local waited=0
  while (( waited < REPORT_WAIT )); do
    sleep $(( REPORT_WAIT - waited < 60 ? REPORT_WAIT - waited : 60 ))
    waited=$(( waited + (REPORT_WAIT - waited < 60 ? REPORT_WAIT - waited : 60) ))
    echo "[launch] waiting for the CRAB server before --report: ${waited}/${REPORT_WAIT} s"
  done
  python3 "$SUBMIT" --era "$ERAS" --report 2>&1 | tee -i "$RUN/report.log"
  rc=${PIPESTATUS[0]}
  [[ $rc -eq 0 ]] || die 18 "--report exited $rc" "$RUN/report.log"
  grep -q "DEAD TASK" "$RUN/report.log" && die 18 "DEAD task(s): they will never run (docs/08 T-19); see the block above" "$RUN/report.log"
  local nerr
  nerr="$(grep -c '\[status FAILED\]' "$RUN/report.log")"
  if [[ "$nerr" -gt 0 ]]; then
    step_ok "(but $nerr task(s) had no status yet -- run --report again in ~10 min)"
  else
    step_ok
  fi
  exit 0
}

main 2>&1 | tee -i -a "$LOG"
exit "${PIPESTATUS[0]}"
