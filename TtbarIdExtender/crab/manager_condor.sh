#!/usr/bin/env bash
# =============================================================================
# manager_condor.sh -- run extend_manager.py as a condor job (lxplus batch)
# =============================================================================
# Run on the lxplus HOST shell (EL9), NOT inside cmssw-el7/-el8: condor_submit
# exists only on the host. Your ssh session is needed for about a minute; the
# job does the rest on a batch node and survives logout:
#   (with --launch) local cmsRun + invariants, resolve + --apply, preflight,
#   dry-run, CRAB submit, report  -> then every 30 min crab status, resubmit of
#   failed jobs, ALERTs  -> completion checks and REPORT.txt.
#
# Usage (from TtbarIdExtender/, after git pull --ff-only):
#   voms-proxy-init -voms cms -rfc -valid 192:00 --out $PWD/proxy.cert
#   bash crab/manager_condor.sh --era 2016APV,2016 --name extend2016 --launch
# Era 2024 (Run 3): the same command from the TtbarIdExtender/ of the CMSSW_15_0_X
# area (~/TTHHGenCategoryTools_v15/CMSSW_15_0_18): the job then runs in
# cmssw-el8. The area must fit the eras (10_6 for Run 2, 15_0 for 2024).
# Its datasets.yaml entries start with dataset: "" -- run
# bash crab/resolve_parents.sh 2024 --fill (inside cmssw-el8, after cmsenv)
# first; this script refuses an era that still has such an entry.
# Options:
#   --launch          let the job submit the campaign first (skipped when any
#                     task of these eras already has a crab_projects dir)
#   --proxy PATH      proxy file (default: ./proxy.cert, else $X509_USER_PROXY);
#                     must be on AFS, not /tmp (the schedd cannot read /tmp)
#   --flavour F       condor JobFlavour (default tomorrow = 24 h; the manager
#                     exits 75 after 22 h and condor re-queues it -- it resumes)
#   --interval-min M  minutes between checks (default 30)
#   --launch-args "A" extra arguments for launch_extend.sh (e.g. "--skip-local")
#   --dry-run         write the job files, do not submit
#
# Job layout: crab/manager/<name>/  (git-ignored)
#   manager.log   everything the manager and the launch print (tail -f this)
#   state.json, manager.lock, launch.done, REPORT.txt, check/  (manager files)
#   condor/       job.sh, job.sub, x509up.proxy, job.<cluster>.{out,err,log}
# How the job runs: native el9 slot (MY.WantOS = "el9"); job.sh re-executes
# itself inside /cvmfs/cms.cern.ch/common/cmssw-el<N> (the condor/runTask.sh
# pattern; N = 7 for a slc7 area, 8 for an el8 area, none for el9 -- read from
# the area's .SCRAM/<arch>), then cmsenv in this CMSSW area, crab-setup.sh, and
#   python3 -u crab/extend_manager.py --era .. --name .. --lock-owner condor:<id> [--launch]
# Exit codes of job.sh before the manager: 90 cmsset_default, 91 CMSSW dir,
# 92 scram runtime, 93 package dir, 94 crab-setup (all logged to manager.log;
# 94 with the tail of crab-setup's output and of the CRABClient import error).
# ASCII-only.
# =============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../TtbarIdExtender/crab
PKG="$(dirname "$HERE")"
REPO="$(dirname "$PKG")"
CMSSW_AREA="$(cd "$REPO/../.." 2>/dev/null && pwd)"     # .../CMSSW_10_6_32_patch1

ERAS=""; NAME=""; LAUNCH=0; PROXY=""; FLAVOUR="tomorrow"; INTERVAL=30; DRY=0; LAUNCH_ARGS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --era)          ERAS="${2:-}"; shift 2 ;;
    --name)         NAME="${2:-}"; shift 2 ;;
    --launch)       LAUNCH=1; shift ;;
    --proxy)        PROXY="${2:-}"; shift 2 ;;
    --flavour)      FLAVOUR="${2:-}"; shift 2 ;;
    --interval-min) INTERVAL="${2:-}"; shift 2 ;;
    --launch-args)  LAUNCH_ARGS="${2:-}"; shift 2 ;;
    --dry-run)      DRY=1; shift ;;
    -h|--help)      awk 'NR>=2 && /^set -u/ {exit} NR>=2' "${BASH_SOURCE[0]}" | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    *) echo "ERROR: unknown argument '$1' (try --help)" >&2; exit 2 ;;
  esac
done
[[ -n "$ERAS" && -n "$NAME" ]] || { echo "ERROR: --era and --name are required" >&2; exit 2; }
[[ "$NAME" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "ERROR: --name may contain only A-Z a-z 0-9 _ . -" >&2; exit 2; }
[[ "$INTERVAL" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "ERROR: --interval-min must be a number" >&2; exit 2; }
[[ "$LAUNCH_ARGS" =~ ^[A-Za-z0-9\ ._=-]*$ ]] || { echo "ERROR: --launch-args may contain only letters, digits, space . _ = -" >&2; exit 2; }
case "$FLAVOUR" in espresso|microcentury|longlunch|workday|tomorrow|testmatch|nextweek) ;;
  *) echo "ERROR: unknown JobFlavour '$FLAVOUR'" >&2; exit 2 ;; esac

echo "=== manager_condor.sh  $(date -u +%FT%TZ)  host=$(hostname 2>/dev/null || echo '?')"
echo "    eras=$ERAS  name=$NAME  launch=$LAUNCH${LAUNCH_ARGS:+ ($LAUNCH_ARGS)}  flavour=$FLAVOUR  interval=${INTERVAL} min"
echo "    package=$PKG"
echo "    CMSSW area=$CMSSW_AREA"

fail() { echo "FATAL: $*" >&2; exit 2; }
# read VERSION_ID in a subshell: sourcing /etc/os-release here would overwrite NAME (and ID)
OS_MAJOR="$( (. /etc/os-release 2>/dev/null; echo "${VERSION_ID:-}") )"; OS_MAJOR="${OS_MAJOR%%.*}"
[[ "$OS_MAJOR" == "7" || "$OS_MAJOR" == "8" ]] && fail "this shell is el$OS_MAJOR (cmssw-el$OS_MAJOR?) -- run on the lxplus host shell, where condor_submit exists"
[[ $DRY -eq 1 ]] || command -v condor_submit >/dev/null 2>&1 || fail "condor_submit not found -- run on the lxplus host shell"
AREA_NAME="$(basename "$CMSSW_AREA")"
case "$AREA_NAME" in
  CMSSW_10_6_*) AREA_FAMILY="CMSSW_10_6_" ;;
  CMSSW_15_0_*) AREA_FAMILY="CMSSW_15_0_" ;;
  *) fail "expected the package inside CMSSW_10_6_X/src/TTHHGenCategoryTools (Run 2) or CMSSW_15_0_X/src/... (2024) (got CMSSW area '$CMSSW_AREA')" ;;
esac
[[ -d "$CMSSW_AREA/src" ]] || fail "no $CMSSW_AREA/src"
# 2026-10-15: each era needs its release family (Run 2: 10_6; 2024: 15_0)
IFS=',' read -r -a ERA_ARR <<< "$ERAS"
for E in "${ERA_ARR[@]}"; do
  case "$E" in
    2016APV|2016|2017|2018) NEED="CMSSW_10_6_" ;;
    2024)                   NEED="CMSSW_15_0_" ;;
    *) fail "unknown era '$E' (2016APV, 2016, 2017, 2018, 2024)" ;;
  esac
  [[ "$NEED" == "$AREA_FAMILY" ]] || fail "era $E needs a ${NEED}X area, this package sits in $AREA_NAME (2024: ~/TTHHGenCategoryTools_v15/CMSSW_15_0_18; Run 2: ~/TTHHGenCategoryTools/CMSSW_10_6_32_patch1)"
done
# container of the job = the OS of the area's SCRAM arch (.SCRAM/<arch>, else lib/<arch>)
ARCH="$( { ls -1 "$CMSSW_AREA/.SCRAM"; ls -1 "$CMSSW_AREA/lib"; } 2>/dev/null | grep -E '^(slc7|cc7|el8|el9)_' | head -n1)"
case "$ARCH" in
  slc7_*|cc7_*) CONT_OS=7 ;;
  el8_*)        CONT_OS=8 ;;
  el9_*)        CONT_OS=9 ;;
  *) fail "cannot tell the SCRAM arch of $CMSSW_AREA (no slc7_/el8_/el9_ dir in .SCRAM or lib)" ;;
esac
echo "    SCRAM arch=$ARCH  -> job runs in $( [[ $CONT_OS == 9 ]] && echo 'the native el9 slot' || echo "cmssw-el$CONT_OS" )"
for f in "$HERE/extend_manager.py" "$HERE/launch_extend.sh" "$HERE/submit_ttbarIdExtend.py" "$HERE/datasets.yaml"; do
  [[ -f "$f" ]] || fail "missing $f (git pull --ff-only?)"
done
# 2026-10-15 review: a new era (2024) starts with dataset: "" in datasets.yaml
# until resolve_parents.sh <era> --fill; the job would only stop on the batch
# node (extend_manager.py), so refuse here. Era block = from '  "<era>":' to the
# next era key or top-level key.
for E in "${ERA_ARR[@]}"; do
  N_EMPTY="$(awk -v key="  \"$E\":" '
      index($0, key) == 1                                       { inb = 1; next }
      inb && (/^  "[^"]*":/ || /^[^ #]/)                         { inb = 0 }
      inb && /^[[:space:]]+dataset:[[:space:]]*""[[:space:]]*$/ { n++ }
      END { print n + 0 }' "$HERE/datasets.yaml")"
  [[ "$N_EMPTY" == "0" ]] || fail "era $E has $N_EMPTY entr(y/ies) with dataset: \"\" in crab/datasets.yaml -- first, after cmsenv in $AREA_NAME ($( [[ $CONT_OS == 9 ]] && echo 'on the el9 host' || echo "inside cmssw-el$CONT_OS" )): bash crab/resolve_parents.sh $E --fill (check its diff), then run this command again"
done

# --- proxy ---------------------------------------------------------------------
if [[ -z "$PROXY" ]]; then
  if [[ -f "$PKG/proxy.cert" ]]; then PROXY="$PKG/proxy.cert"; else PROXY="${X509_USER_PROXY:-}"; fi
fi
[[ -n "$PROXY" && -r "$PROXY" ]] || fail "no proxy file -- voms-proxy-init -voms cms -rfc -valid 192:00 --out \$PWD/proxy.cert"
case "$PROXY" in /tmp/*) fail "proxy $PROXY is in /tmp, which the schedd cannot read -- use --out \$PWD/proxy.cert" ;; esac
LEFT=0
if command -v voms-proxy-info >/dev/null 2>&1; then
  LEFT="$(voms-proxy-info -file "$PROXY" -timeleft 2>/dev/null | tr -dc '0-9')"
  LEFT="${LEFT:-0}"
  [[ "$LEFT" -ge 86400 ]] || fail "proxy $PROXY has $(( LEFT / 3600 )) h left (need >= 24 h): voms-proxy-init -voms cms -rfc -valid 192:00 --out \$PWD/proxy.cert"
  echo "    proxy=$PROXY  ($(( LEFT / 3600 )) h left)"
else
  echo "    proxy=$PROXY  (voms-proxy-info not on PATH; lifetime not checked here, the job checks it)"
fi

# --- an already-running manager of this name? ------------------------------------
if [[ $DRY -eq 0 ]] && command -v condor_q >/dev/null 2>&1; then
  running="$(condor_q -constraint "JobBatchName == \"extend_manager_$NAME\"" -af ClusterId 2>/dev/null | head -n1)"
  [[ -z "$running" ]] || fail "a manager job '$NAME' is already in the queue (cluster $running): condor_rm $running first, or use another --name"
fi

# --- job files -------------------------------------------------------------------
STATE="$HERE/manager/$NAME"
JOBDIR="$STATE/condor"
mkdir -p "$JOBDIR" || fail "cannot create $JOBDIR"
cp -f "$PROXY" "$JOBDIR/x509up.proxy" && chmod 600 "$JOBDIR/x509up.proxy" || fail "cannot copy the proxy"
LAUNCH_ARG=""; [[ $LAUNCH -eq 1 ]] && LAUNCH_ARG="--launch"
[[ $LAUNCH -eq 1 && -n "$LAUNCH_ARGS" ]] && LAUNCH_ARG="--launch --launch-args '$LAUNCH_ARGS'"

cat > "$JOBDIR/job.sh" <<EOF
#!/bin/bash
# job.sh -- written by manager_condor.sh $(date -u +%FT%TZ); runs on a batch node
set -u
JOBID="\${1:-unknown}"
MLOG="$STATE/manager.log"
WORK="\${_CONDOR_SCRATCH_DIR:-\$PWD}"
SELF="\$WORK/\$(basename "\${BASH_SOURCE[0]}")"
jlog() { echo "[job] \$(date -u +%FT%TZ) \$*" | tee -a "\$MLOG"; }
# os-release read in a subshell: sourcing it would overwrite variables (NAME, ID, ...)
OSV="\$( (. /etc/os-release 2>/dev/null; echo "\${VERSION_ID:-?} \${PRETTY_NAME:-?}") )"
if [[ "\${OSV%%.*}" != "$CONT_OS" && -z "\${TTHH_INNER:-}" ]]; then
  jlog "condor job \$JOBID on \$(hostname) (\$OSV): re-executing inside cmssw-el$CONT_OS"
  export TTHH_INNER=1
  printf 'cd %q && exec bash %q %q\n' "\$WORK" "\$SELF" "\$JOBID" > "\$WORK/inner.sh"
  exec /cvmfs/cms.cern.ch/common/cmssw-el$CONT_OS --command-to-run bash "\$WORK/inner.sh"
fi
jlog "inside el$CONT_OS on \$(hostname): cmsenv in $CMSSW_AREA, crab-setup, X509_USER_PROXY=\${X509_USER_PROXY:-unset}"
source /cvmfs/cms.cern.ch/cmsset_default.sh || { jlog "FATAL cmsset_default.sh failed (exit 90)"; exit 90; }
cd "$CMSSW_AREA/src" || { jlog "FATAL cannot cd $CMSSW_AREA/src (AFS token?) (exit 91)"; exit 91; }
eval "\$(scramv1 runtime -sh)" || { jlog "FATAL scram runtime failed (exit 92)"; exit 92; }
cd "$PKG" || { jlog "FATAL cannot cd $PKG (exit 93)"; exit 93; }
# A sourced file sees the caller's positional parameters when it is given none. Sourced at
# the top level of this script, crab-setup.sh got \$1 = the condor job id, and CRABClient was
# not importable afterwards (exit 94 on 2026-10-15, T-38; crab-setup.sh takes an optional
# first argument, the client version). So source it from a function called without
# arguments, and keep its output (shown in manager.log on exit 94).
crab_setup() { source /cvmfs/cms.cern.ch/common/crab-setup.sh; }
set +u
crab_setup > "\$WORK/crab_setup.log" 2>&1
set -u
if ! python3 -c "import CRABClient" > "\$WORK/crab_import.log" 2>&1; then
  crabpp="\$(echo "\${PYTHONPATH:-}" | tr ':' '\n' | grep -i crab | head -n 3 | tr '\n' ' ')"
  jlog "FATAL CRABClient not importable after crab-setup.sh (exit 94): python3=\$(command -v python3) (\$(python3 -V 2>&1)), PYTHONPATH crab entries: \${crabpp:-none}"
  { echo "--- crab-setup.sh output (last 20 lines):"; tail -n 20 "\$WORK/crab_setup.log"
    echo "--- python3 -c 'import CRABClient' (last 20 lines):"; tail -n 20 "\$WORK/crab_import.log"; } | sed 's/^/[job]   /' | tee -a "\$MLOG"
  exit 94
fi
jlog "CRABClient from \$(python3 -c 'import os, CRABClient; print(os.path.dirname(CRABClient.__file__))' 2>&1 | tail -n 1)"
export PYTHONUNBUFFERED=1
jlog "starting extend_manager.py"
exec python3 -u crab/extend_manager.py --era "$ERAS" --name "$NAME" --interval-min "$INTERVAL" --lock-owner "condor:\$JOBID" $LAUNCH_ARG
EOF
chmod u+x "$JOBDIR/job.sh"

cat > "$JOBDIR/job.sub" <<EOF
# job.sub -- written by manager_condor.sh $(date -u +%FT%TZ)
universe                = vanilla
executable              = $JOBDIR/job.sh
arguments               = \$(ClusterId).\$(ProcId)
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_output_files   = ""
use_x509userproxy       = true
x509userproxy           = $JOBDIR/x509up.proxy
MY.WantOS               = "el9"
MY.JobBatchName         = "extend_manager_$NAME"
output                  = $JOBDIR/job.\$(ClusterId).out
error                   = $JOBDIR/job.\$(ClusterId).err
log                     = $JOBDIR/job.\$(ClusterId).log
request_cpus            = 1
request_memory          = 4 GB
request_disk            = 2 GB
+JobFlavour             = "$FLAVOUR"
# exit 75 = the manager used its time budget and wants to go on: back to the queue
on_exit_remove          = (ExitBySignal == False) && (ExitCode != 75)
notification            = never
queue
EOF
echo "--- written: $JOBDIR/job.sh, $JOBDIR/job.sub, $JOBDIR/x509up.proxy"

if [[ $DRY -eq 1 ]]; then
  echo "=== dry run: nothing submitted. Inspect $JOBDIR and re-run without --dry-run."
  exit 0
fi

out="$(condor_submit "$JOBDIR/job.sub" 2>&1)"; rc=$?
echo "$out"
[[ $rc -eq 0 ]] || fail "condor_submit failed (exit $rc)"
cluster="$(echo "$out" | grep -o 'submitted to cluster [0-9]*' | grep -o '[0-9]*$')"
echo "[submit] $(date -u +%FT%TZ) manager job cluster ${cluster:-?} submitted by $(hostname 2>/dev/null)" >> "$STATE/manager.log"
cat <<EOF

=== submitted: manager '$NAME', condor cluster ${cluster:-?}
  follow  : tail -f $STATE/manager.log
            condor_q -constraint 'JobBatchName == "extend_manager_$NAME"'
  healthy : a "check <n> | jobs done ..." line every ${INTERVAL} min (the first one right after the launch)
  stop    : condor_rm ${cluster:-<cluster>}     (the state is kept; resubmit this command to go on)
  done    : RESULT DONE / STOPPED / CHECK FAILED in manager.log; table in $STATE/REPORT.txt
EOF
