#!/usr/bin/env bash
# =============================================================================
# manager_condor.sh -- run extend_manager.py as a condor job (lxplus batch)
# =============================================================================
# Run on the lxplus HOST shell (EL9), NOT inside cmssw-el7: condor_submit
# exists only on the host. Your ssh session is needed for about a minute; the
# job does the rest on a batch node and survives logout:
#   (with --launch) local cmsRun + invariants, resolve + --apply, preflight,
#   dry-run, CRAB submit, report  -> then every 30 min crab status, resubmit of
#   failed jobs, ALERTs  -> completion checks and REPORT.txt.
#
# Usage (from TtbarIdExtender/, after git pull --ff-only):
#   voms-proxy-init -voms cms -rfc -valid 192:00 --out $PWD/proxy.cert
#   bash crab/manager_condor.sh --era 2016APV,2016 --name extend2016 --launch
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
# itself inside /cvmfs/cms.cern.ch/common/cmssw-el7 (the condor/runTask.sh
# pattern), then cmsenv in this CMSSW area, crab-setup.sh, and
#   python3 -u crab/extend_manager.py --era .. --name .. --lock-owner condor:<id> [--launch]
# Exit codes of job.sh before the manager: 90 cmsset_default, 91 CMSSW dir,
# 92 scram runtime, 93 package dir, 94 crab-setup (all logged to manager.log).
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
[[ "$OS_MAJOR" == "7" ]] && fail "this shell is el7 (cmssw-el7?) -- run on the lxplus host shell, where condor_submit exists"
[[ $DRY -eq 1 ]] || command -v condor_submit >/dev/null 2>&1 || fail "condor_submit not found -- run on the lxplus host shell"
[[ -d "$CMSSW_AREA/src" && "$(basename "$CMSSW_AREA")" == CMSSW_10_6_* ]] \
  || fail "expected the package inside CMSSW_10_6_X/src/TTHHGenCategoryTools (got CMSSW area '$CMSSW_AREA')"
for f in "$HERE/extend_manager.py" "$HERE/launch_extend.sh" "$HERE/submit_ttbarIdExtend.py" "$HERE/datasets.yaml"; do
  [[ -f "$f" ]] || fail "missing $f (git pull --ff-only?)"
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
if [[ "\${OSV%%.*}" != "7" && -z "\${TTHH_INNER:-}" ]]; then
  jlog "condor job \$JOBID on \$(hostname) (\$OSV): re-executing inside cmssw-el7"
  export TTHH_INNER=1
  printf 'cd %q && exec bash %q %q\n' "\$WORK" "\$SELF" "\$JOBID" > "\$WORK/inner.sh"
  exec /cvmfs/cms.cern.ch/common/cmssw-el7 --command-to-run bash "\$WORK/inner.sh"
fi
jlog "inside el7 on \$(hostname): cmsenv in $CMSSW_AREA, crab-setup, X509_USER_PROXY=\${X509_USER_PROXY:-unset}"
source /cvmfs/cms.cern.ch/cmsset_default.sh || { jlog "FATAL cmsset_default.sh failed (exit 90)"; exit 90; }
cd "$CMSSW_AREA/src" || { jlog "FATAL cannot cd $CMSSW_AREA/src (AFS token?) (exit 91)"; exit 91; }
eval "\$(scramv1 runtime -sh)" || { jlog "FATAL scram runtime failed (exit 92)"; exit 92; }
cd "$PKG" || { jlog "FATAL cannot cd $PKG (exit 93)"; exit 93; }
set +u
source /cvmfs/cms.cern.ch/common/crab-setup.sh >/dev/null 2>&1
set -u
python3 -c "import CRABClient" >/dev/null 2>&1 || { jlog "FATAL CRABClient not importable after crab-setup.sh (exit 94)"; exit 94; }
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
