#!/bin/bash
# =============================================================================
#  runTask.sh -- HTCondor worker for the enriched-NanoAOD validation tasks
#  (TTHHGenCategoryTools docs/11, D17 gates 3 / 4 / 5).
#
#  usage (set by submit.sh):   runTask.sh <task> <tag> [tt4b_miniaod_lfn]
#
#  tasks
#    control_v15_200  negative control: the CENTRAL v15 cfg (no customise) on the
#                     same 200 TTbb events -> (a) vs central v15  (b) vs our smoke
#    timing_v15_2k    our v15 cfg, 2000 TTbb events, timed (gate 4 input)
#                     -> vs our 2026-09-02 2k file (machine independence)
#                     -> vs central v15 (gate 5 at 2000 events)
#    tt4b_v9_2k       our v9  cfg on a TT4b MiniAOD, 2000 events -> 71/72 (gate 3)
#    tt4b_v15_2k      our v15 cfg on the same TT4b file            -> 71/72 on 15_0_X
#
#  Everything is staged into the Condor scratch directory, run there, and the
#  results (root, json, cfg, cmsRun log, this log, a summary) are copied to
#  $TTHH_EOS/{enriched,json,logs}/<tag>/. Nothing is written to AFS.
#
#  OS: a task that needs a different OS than the worker re-executes itself inside
#  /cvmfs/cms.cern.ch/common/cmssw-el<N> (same wrapper as on lxplus).
#  Exit code: 0 = every check PASS, 1 = a check FAILED, 2 = infrastructure error.
# =============================================================================
set -u
set -o pipefail

TASK="${1:?usage: runTask.sh <task> <tag> [tt4b_lfn]}"
TAG="${2:?usage: runTask.sh <task> <tag> [tt4b_lfn]}"
TT4B_LFN="${3:-}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="$HERE/$(basename "${BASH_SOURCE[0]}")"   # Condor renames the executable to condor_exec.exe
# shellcheck source=config.sh
source "$HERE/config.sh"
WORK="${_CONDOR_SCRATCH_DIR:-$PWD}"
cd "$WORK" || exit 2
LOG="$WORK/${TASK}.log"

# ----------------------------------------------------------------------------- task table
case "$TASK" in
  control_v15_200) NEED_OS=8; AREA="$V15_AREA"; COND="$CONDITIONS_V15"; NEV="$N_CONTROL"
                   CUSTOMISE="$CUSTOMISE_CENTRAL";                  OUT="plain_v15_${N_CONTROL}.root"   ;;
  timing_v15_2k)   NEED_OS=8; AREA="$V15_AREA"; COND="$CONDITIONS_V15"; NEV="$N_TIMING"
                   CUSTOMISE="$CUSTOMISE_CENTRAL,$CUSTOMISE_OURS";  OUT="enriched_v15_${N_TIMING}_timed.root" ;;
  tt4b_v9_2k)      NEED_OS=7; AREA="$V9_AREA";  COND="$CONDITIONS_V9";  NEV="$N_TT4B"
                   CUSTOMISE="$CUSTOMISE_CENTRAL,$CUSTOMISE_OURS";  OUT="tt4b_v9_${N_TT4B}.root"        ;;
  tt4b_v15_2k)     NEED_OS=8; AREA="$V15_AREA"; COND="$CONDITIONS_V15"; NEV="$N_TT4B"
                   CUSTOMISE="$CUSTOMISE_CENTRAL,$CUSTOMISE_OURS";  OUT="tt4b_v15_${N_TT4B}.root"       ;;
  *) echo "[FATAL] unknown task '$TASK'"; exit 2 ;;
esac

# ----------------------------------------------------------------------------- OS re-exec
. /etc/os-release
HOST_MAJOR="${VERSION_ID%%.*}"
if [[ "$HOST_MAJOR" != "$NEED_OS" && -z "${TTHH_INNER:-}" ]]; then
  WRAP="/cvmfs/cms.cern.ch/common/cmssw-el${NEED_OS}"
  {
    echo "[env] $(date -u +%FT%TZ) worker OS is el${HOST_MAJOR} ($PRETTY_NAME); task '$TASK' needs el${NEED_OS}"
    echo "[env] re-executing inside $WRAP"
  } | tee -a "$LOG"
  [[ -x "$WRAP" ]] || { echo "[FATAL] $WRAP not found" | tee -a "$LOG"; exit 2; }
  export TTHH_INNER=1
  printf 'cd %q && exec bash %q %q %q %q\n' "$WORK" "$SELF" "$TASK" "$TAG" "$TT4B_LFN" > "$WORK/inner.sh"
  exec "$WRAP" --command-to-run bash "$WORK/inner.sh"
fi

# ----------------------------------------------------------------------------- logging
exec > >(tee -a "$LOG") 2>&1

EOS_OUT="$TTHH_EOS/enriched/$TAG"
EOS_JSON="$TTHH_EOS/json/$TAG"
EOS_LOGS="$TTHH_EOS/logs/$TAG"
declare -a RESULTS=()
FAILED=0

log()  { echo "[$(date -u +%T)] $*"; }
pass() { RESULTS+=("PASS  $*"); log "PASS  $*"; }
fail() { RESULTS+=("FAIL  $*"); log "FAIL  $*"; FAILED=1; }
die()  { log "FATAL $*"; RESULTS+=("FATAL $*"); FAILED=2; exit 2; }

# step <name> <command...>  -- echoes the command, times it, records the exit code
step() {
  local name="$1"; shift
  echo
  echo "---- [$name] $(date -u +%FT%TZ)"
  echo "     \$ $*"
  local t0; t0=$(date +%s)
  "$@"
  local rc=$? dt=$(( $(date +%s) - t0 ))
  echo "---- [$name] exit=$rc (${dt}s)"
  return $rc
}

# eos_put <local> <eos path>   -- xrdcp through eosuser, fall back to the fuse mount
eos_put() {
  local src="$1" dst="$2"
  xrdfs eosuser.cern.ch mkdir -p "$(dirname "$dst")" >/dev/null 2>&1 || mkdir -p "$(dirname "$dst")" 2>/dev/null
  if xrdcp -f -s "$src" "$EOS_XRD/$dst" 2>/dev/null; then log "eos_put $src -> $dst (xrdcp)"; return 0; fi
  if cp -f "$src" "$dst" 2>/dev/null;          then log "eos_put $src -> $dst (fuse)";  return 0; fi
  log "eos_put FAILED: $src -> $dst"; return 1
}
eos_exists() { xrdfs eosuser.cern.ch stat "$1" >/dev/null 2>&1 || [[ -e "$1" ]]; }
eos_get()    { xrdcp -f -s "$EOS_XRD/$1" "$2" 2>/dev/null || cp -f "$1" "$2"; }

# stage_lfn <lfn> <cache dir on EOS> <local name>
#   Use the EOS copy if it is there, else fetch from the grid and leave a copy on
#   EOS for the next job (the "temporary files live on EOS, not /tmp" rule).
stage_lfn() {
  local lfn="$1" cache_dir="$2" dst="$3" base; base="$(basename "$lfn")"
  if eos_exists "$cache_dir/$base"; then
    log "stage $base from EOS cache $cache_dir"
    eos_get "$cache_dir/$base" "$dst" || return 1
  else
    log "stage $base from the grid ($GRID_XRD) -- not yet cached on EOS"
    xrdcp -f "$GRID_XRD$lfn" "$dst" || return 1
    eos_put "$dst" "$cache_dir/$base" || log "WARN could not cache $base on EOS (continuing)"
  fi
  ls -la "$dst"
}

finish() {
  local rc=$?
  echo
  echo "================================================================ SUMMARY $TASK ($TAG)"
  printf '%s\n' "${RESULTS[@]:-"(no checks recorded)"}"
  local verdict
  if   [[ ${#RESULTS[@]} -eq 0 && $rc -ne 0 ]]; then verdict="INFRASTRUCTURE ERROR (died before any check, rc=$rc)"; rc=2
  elif [[ $FAILED -eq 0 && $rc -eq 0 ]]; then verdict="ALL PASS";         rc=0
  elif [[ $FAILED -eq 2 || $rc -ge 2 ]];  then verdict="INFRASTRUCTURE ERROR (rc=$rc)"; rc=2
  else                                         verdict="CHECK FAILED";     rc=1
  fi
  echo "verdict: $verdict"
  echo "outputs: $EOS_OUT/   json: $EOS_JSON/   logs: $EOS_LOGS/"
  echo "finished $(date -u +%FT%TZ)"
  echo "================================================================"
  { printf '%s\n' "$TASK $TAG"; printf '%s\n' "${RESULTS[@]:-}"; echo "verdict: $verdict"; } > "$WORK/${TASK}.summary.txt"
  eos_put "$WORK/${TASK}.summary.txt" "$EOS_LOGS/${TASK}.summary.txt"
  sleep 2   # let tee flush the last lines before the log is copied
  eos_put "$LOG" "$EOS_LOGS/${TASK}.log"
  exit $rc
}
trap finish EXIT

# ----------------------------------------------------------------------------- 0. environment
echo "================================================================ $TASK ($TAG)"
log "started      $(date -u +%FT%TZ)"
log "host         $(hostname)   OS: ${PRETTY_NAME:-?}   inner=${TTHH_INNER:-0}"
log "cpu          $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ //')  x$(nproc)"
log "scratch      $WORK   ($(df -h "$WORK" | awk 'NR==2{print $4" free"}'))"
log "area         $AREA"
log "cmsDriver    conditions=$COND era=$ERA nev=$NEV"
log "customise    $CUSTOMISE"
log "output       $OUT"
[[ -n "$TT4B_LFN" ]] && log "tt4b lfn     $TT4B_LFN"
if [[ -n "${X509_USER_PROXY:-}" ]]; then
  log "proxy        $X509_USER_PROXY  timeleft=$(voms-proxy-info -file "$X509_USER_PROXY" -timeleft 2>/dev/null || echo '?')s"
else
  log "WARN         X509_USER_PROXY not set -- xrootd reads will fail"
fi

set +u   # CMS site scripts read unset variables (CVS_RSH) -- docs/08 T-34
source /cvmfs/cms.cern.ch/cmsset_default.sh
pushd "$AREA/src" >/dev/null || die "cannot cd to $AREA/src"
eval "$(scramv1 runtime -sh)" || die "cmsenv failed in $AREA"
popd >/dev/null
set -u
log "CMSSW        $CMSSW_VERSION  SCRAM_ARCH=$SCRAM_ARCH"
log "python       $(python3 --version 2>&1 || python --version 2>&1)"
log "ROOT         $(root-config --version 2>/dev/null || echo '?')"
REPO="$AREA/src/TTHHGenCategoryTools"
log "repo commit  $(git --no-optional-locks -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo '?')  $(git --no-optional-locks -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
DIRTY="$(git --no-optional-locks -C "$REPO" status --porcelain --untracked-files=no 2>/dev/null | head -5)"
[[ -n "$DIRTY" ]] && log "WARN repo has uncommitted changes:" && echo "$DIRTY"
log "customise    $(python3 -c "import TTHHGenCategoryTools.TtbarIdExtender.ttbarIdTable_cff as m; print(m.__file__)" 2>/dev/null || python -c "import TTHHGenCategoryTools.TtbarIdExtender.ttbarIdTable_cff as m; print(m.__file__)" 2>/dev/null || echo 'import FAILED')"

# a python with PyROOT for the small checks (10_6_X: python3 may lack ROOT)
PY=python3; python3 -c 'import ROOT' >/dev/null 2>&1 || PY=python
log "pyroot via   $PY"

# ----------------------------------------------------------------------------- 1. inputs
case "$TASK" in
  tt4b_*)
    [[ -n "$TT4B_LFN" ]] || die "tt4b task without a MiniAOD LFN (submit.sh resolves it)"
    step stage_miniaod stage_lfn "$TT4B_LFN" "$TTHH_EOS/miniaod" "$WORK/mini.root" || die "MiniAOD staging failed" ;;
  *)
    step stage_miniaod stage_lfn "$TTBB_MINIAOD_LFN" "$TTHH_EOS/miniaod" "$WORK/mini.root" || die "MiniAOD staging failed" ;;
esac
case "$TASK" in
  control_v15_200|timing_v15_2k)
    if eos_exists "$TTHH_EOS/central/$TTBB_CENTRAL_V15_NAME"; then
      step stage_central eos_get "$TTHH_EOS/central/$TTBB_CENTRAL_V15_NAME" "$WORK/central.root" || die "central staging failed"
    else
      step stage_central stage_lfn "$TTBB_CENTRAL_V15_LFN" "$TTHH_EOS/central" "$WORK/central.root" || die "central staging failed"
      log "NOTE central file cached on EOS under its LFN basename; config expects $TTBB_CENTRAL_V15_NAME"
    fi
    ls -la "$WORK/central.root" ;;
esac
case "$TASK" in
  control_v15_200) step stage_ref eos_get "$TTHH_EOS/enriched/$OURS_V15_SMOKE" "$WORK/ours_ref.root" || die "reference (smoke) staging failed" ;;
  timing_v15_2k)   step stage_ref eos_get "$TTHH_EOS/enriched/$OURS_V15_2K"    "$WORK/ours_ref.root" || die "reference (2k) staging failed" ;;
esac
[[ -f "$WORK/ours_ref.root" ]] && ls -la "$WORK/ours_ref.root"

# ----------------------------------------------------------------------------- 2. cmsDriver + cmsRun
CFG="${TASK}_cfg.py"
step cmsDriver cmsDriver.py nano --python_filename "$CFG" \
  --eventcontent NANOAODSIM --datatier NANOAODSIM \
  --conditions "$COND" --step NANO --era "$ERA" \
  --customise "$CUSTOMISE" \
  --filein "file:$WORK/mini.root" --fileout "file:$WORK/$OUT" --no_exec --mc -n "$NEV" \
  || die "cmsDriver failed"
log "cfg threads  $(grep -E 'numberOfThreads|numberOfStreams' "$CFG" | tr -s ' ' | tr '\n' ' ')"

CMSRUN_LOG="$WORK/${TASK}.cmsRun.log"
T0=$(date +%s)
step cmsRun bash -c "cmsRun '$CFG' > '$CMSRUN_LOG' 2>&1"
RC=$?
WALL=$(( $(date +%s) - T0 ))
log "cmsRun exit=$RC wall=${WALL}s  (log: $(wc -l < "$CMSRUN_LOG") lines)"
echo "---- cmsRun log: table style / errors / warnings"
grep -n 'ttbarIdTable_cff\|Updating process to run' "$CMSRUN_LOG" | head -5
NERR=$(grep -c '%MSG-e' "$CMSRUN_LOG"); NWARN=$(grep -c '%MSG-w' "$CMSRUN_LOG")
log "messages     %MSG-e=$NERR  %MSG-w=$NWARN"
grep '%MSG-w' "$CMSRUN_LOG" | awk '{print $2}' | sort | uniq -c | sort -rn | head -10
[[ $NERR -gt 0 ]] && { echo "---- first %MSG-e blocks:"; grep -n -A3 '%MSG-e' "$CMSRUN_LOG" | head -40; }
echo "---- cmsRun log: tail"
tail -n 25 "$CMSRUN_LOG"
if [[ $RC -ne 0 ]]; then fail "cmsRun exit=$RC"; eos_put "$CMSRUN_LOG" "$EOS_LOGS/${TASK}.cmsRun.log"; eos_put "$CFG" "$EOS_LOGS/$CFG"; exit 1; fi
pass "cmsRun exit=0 (${WALL}s wall, %MSG-e=$NERR)"

# timing (gate 4 input): the Timing service summary + our wall clock
echo "---- timing"
grep -E 'Event Throughput|Total loop|Total init|Total job|Avg event' "$CMSRUN_LOG" | head -12
NOUT=$($PY - "$WORK/$OUT" <<'EOF'
import sys, ROOT
f = ROOT.TFile.Open(sys.argv[1]); t = f.Get("Events")
print(t.GetEntries() if t else -1)
EOF
)
log "events out   $NOUT (requested $NEV)   wall-clock rate $(awk -v n="$NOUT" -v w="$WALL" 'BEGIN{printf "%.2f", (w>0? n/w : 0)}') ev/s incl. startup"
LOOP=$(grep -m1 -E '^ *- Total loop:' "$CMSRUN_LOG" | awk '{print $NF}')
[[ -n "$LOOP" ]] && log "loop rate    $(awk -v n="$NOUT" -v l="$LOOP" 'BEGIN{printf "%.2f", (l>0? n/l : 0)}') ev/s (Timing service, event loop only)"
[[ "$NOUT" == "$NEV" ]] && pass "output has $NOUT events" || fail "output has $NOUT events, expected $NEV"

# schema: branch count and our three columns
echo "---- schema"
$PY - "$WORK/$OUT" "$OUR_COLUMNS" "$CUSTOMISE" <<'EOF'
import sys, ROOT
f = ROOT.TFile.Open(sys.argv[1]); t = f.Get("Events")
names = set(b.GetName() for b in t.GetListOfBranches())
ours = sys.argv[2].split(","); expect_ours = "ttbarIdTable_cff" in sys.argv[3]
present = [c for c in ours if c in names]
print("branches = %d ; our columns present: %s" % (len(names), present or "none"))
for c in present:
    b = t.GetBranch(c); print("  %-22s %s" % (c, b.GetLeaf(c).GetTypeName()))
ok = (len(present) == len(ours)) if expect_ours else (len(present) == 0)
print("SCHEMA_OK" if ok else "SCHEMA_BAD")
sys.exit(0 if ok else 1)
EOF
if [[ $? -eq 0 ]]; then pass "schema (our columns $([[ "$CUSTOMISE" == *ttbarIdTable_cff* ]] && echo present || echo absent) as intended)"; else fail "schema check"; fi

eos_put "$CFG" "$EOS_LOGS/$CFG"
eos_put "$CMSRUN_LOG" "$EOS_LOGS/${TASK}.cmsRun.log"
eos_put "$WORK/$OUT" "$EOS_OUT/$OUT" || fail "could not copy $OUT to EOS"

# ----------------------------------------------------------------------------- 3. checks per task
compare() {  # compare <label> <fileA(--v9)> <fileB(--v15)> <json> <judge args...>
  local label="$1" a="$2" b="$3" js="$4"; shift 4
  echo
  echo "======== compare: $label"
  step "compare_$label" $PY "$NF_COMPARE" --v9 "$a" --v15 "$b" --prefix "" --ftol 0 --json "$WORK/$js" --max-print 12
  local crc=$?
  log "compare exit=$crc (1 = some disagreement; the judge decides whether that is allowed)"
  eos_put "$WORK/$js" "$EOS_JSON/$js"
  if step "judge_$label" $PY "$HERE/judge_compare.py" "$WORK/$js" --label "$label" "$@"; then pass "$label"; else fail "$label"; fi
}

case "$TASK" in
  control_v15_200)
    # (a) the central cfg re-run vs the central file: identical schema; value
    #     differences may appear only in the reproduction-artifact classes
    #     (jet ghost-area RNG, HTXS float residuals) -- the same classes seen
    #     between OUR output and central on 2026-09-03.
    compare plain_vs_central "$WORK/central.root" "$WORK/$OUT" "control_plain_vs_central.json" \
            --only-v15 "" --only-v9 "" --min-common "$NEV" --allow '(_area$|^HTXS_)'
    # (b) plain re-run vs our customised run of the same events: bit identity
    #     except our three extra columns -> the customise changes nothing else.
    compare plain_vs_ours "$WORK/$OUT" "$WORK/ours_ref.root" "control_plain_vs_ours.json" \
            --only-v15 "$OUR_COLUMNS" --only-v9 "" --min-common "$NEV" --zero
    ;;
  timing_v15_2k)
    # machine independence: same cfg, same events, different node -> bit identity
    compare ours2k_vs_ref2k "$WORK/ours_ref.root" "$WORK/$OUT" "timing_ours2k_vs_ref2k.json" \
            --only-v15 "" --only-v9 "" --min-common "$NEV" --zero
    # gate 5 at 2000 events against central v15
    compare ours2k_vs_central "$WORK/central.root" "$WORK/$OUT" "gate5_values_2k.json" \
            --only-v15 "$OUR_COLUMNS" --only-v9 "" --min-common "$NEV" --allow '(_area$|^HTXS_)'
    ;;
  tt4b_v9_2k|tt4b_v15_2k)
    echo
    echo "======== gate 3: expanded rule and 71/72 on TT4b"
    if step check_expanded $PY "$HERE/check_expanded.py" "$WORK/$OUT" --expect-4b; then
      pass "expanded rule holds and 71/72 present (gate 3, ${TASK#tt4b_})"
    else
      fail "check_expanded (gate 3, ${TASK#tt4b_})"
    fi
    ;;
esac

[[ $FAILED -eq 0 ]] && exit 0 || exit 1
