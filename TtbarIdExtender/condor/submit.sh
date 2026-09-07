#!/bin/bash
# =============================================================================
#  submit.sh -- submit the enriched-NanoAOD validation tasks to HTCondor
#  (TTHHGenCategoryTools docs/11, D17 gates 3 / 4 / 5). Run on the lxplus HOST
#  shell, not inside cmssw-el*: condor_submit exists only on the host.
#
#    ./submit.sh                      all tasks in TASKS_DEFAULT (config.sh)
#    ./submit.sh -T "tt4b_v9_2k"      a subset
#    ./submit.sh -t mytag             choose the tag (default: UTC time stamp)
#    ./submit.sh -n                   dry run: resolve inputs, render, do not submit
#    ./submit.sh -P                   skip pre-staging the MiniAOD files to EOS
#
#  What it does
#    1. proxy      needs >= PROXY_MIN_HOURS left; copies it next to the JDL
#    2. inputs     resolves the TT4b MiniAOD file from DAS (parent of the v9
#                  dataset, smallest file with >= N_TT4B events) unless
#                  TT4B_MINIAOD_LFN is set; checks the EOS reference files
#    3. prestage   copies the MiniAOD files to $TTHH_EOS/miniaod/ once, so the
#                  jobs read from EOS instead of racing each other on the grid
#    4. render     submissions/<TAG>/{tasks_el8.jdl, tasks_el9.jdl, logs/}
#    5. submit     one cluster per OS group; prints how to follow the jobs
#
#  Reading results: $TTHH_EOS/logs/<TAG>/<task>.summary.txt (PASS/FAIL lines),
#  <task>.log (full worker log), <task>.cmsRun.log, <task>_cfg.py;
#  $TTHH_EOS/json/<TAG>/*.json (comparator output); $TTHH_EOS/enriched/<TAG>/*.root.
# =============================================================================
set -u
set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
# shellcheck source=config.sh
source "$SCRIPT_DIR/config.sh"

TAG=""; DRYRUN=0; PRESTAGE=1; TASKS="$TASKS_DEFAULT"
while getopts "t:T:nPh" opt; do
  case $opt in
    t) TAG="$OPTARG" ;;
    T) TASKS="$OPTARG" ;;
    n) DRYRUN=1 ;;
    P) PRESTAGE=0 ;;
    h) sed -n '2,/^# ====/p' "$0" | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    *) echo "bad option (try -h)"; exit 64 ;;
  esac
done
[[ -z "$TAG" ]] && TAG="$(date -u +%Y%m%d_%H%M)"
SUBDIR="$SCRIPT_DIR/$SUBMIT_ROOT/$TAG"
DAS=/cvmfs/cms.cern.ch/common/dasgoclient      # static binary; needs only a proxy

echo "=== enriched-NanoAOD validation submission  tag=$TAG"
echo "    tasks : $TASKS"
echo "    eos   : $TTHH_EOS"

# ----------------------------------------------------------------------------- 1. proxy
PROXY_SRC="${X509_USER_PROXY:-/tmp/x509up_u$(id -u)}"
[[ -r "$PROXY_SRC" ]] || { echo "FATAL: no proxy at $PROXY_SRC -- voms-proxy-init --voms cms --valid 72:00"; exit 2; }
if command -v voms-proxy-info >/dev/null 2>&1; then
  LEFT=$(voms-proxy-info -file "$PROXY_SRC" -timeleft 2>/dev/null || echo 0)
  echo "    proxy : $PROXY_SRC  ($((LEFT/3600)) h left)"
  [[ $LEFT -ge $((PROXY_MIN_HOURS*3600)) ]] || { echo "FATAL: proxy has < ${PROXY_MIN_HOURS} h left -- renew it first"; exit 2; }
else
  echo "    proxy : $PROXY_SRC  (voms-proxy-info not on PATH, validity not checked)"
fi
export X509_USER_PROXY="$PROXY_SRC"

# ----------------------------------------------------------------------------- 2. inputs
need_tt4b=0; for t in $TASKS; do [[ $t == tt4b_* ]] && need_tt4b=1; done
if [[ $need_tt4b -eq 1 && -z "$TT4B_MINIAOD_LFN" ]]; then
  echo "--- resolving the TT4b MiniAOD file from DAS"
  [[ -x "$DAS" ]] || { echo "FATAL: $DAS not found"; exit 2; }
  PARENT=$("$DAS" -query="parent dataset=$TT4B_NANO_V9_DS" | head -1)
  [[ -n "$PARENT" ]] || { echo "FATAL: DAS returned no parent for $TT4B_NANO_V9_DS"; exit 2; }
  echo "    parent : $PARENT"
  TT4B_MINIAOD_LFN=$("$DAS" -query="file dataset=$PARENT" -json | python3 -c '
import sys, json
files = []
for rec in json.load(sys.stdin):
    for f in rec.get("file", []):
        if f.get("nevents") and f.get("size"):
            files.append((int(f["size"]), int(f["nevents"]), f["name"]))
need = int(sys.argv[1])
ok = sorted(f for f in files if f[1] >= need)
if not ok:
    sys.exit("no file with >= %d events" % need)
sz, nev, name = ok[0]
sys.stderr.write("    chosen : %s  (%d events, %.2f GB, smallest with >= %d)\n" % (name, nev, sz/1e9, need))
print(name)' "$N_TT4B")
  [[ -n "$TT4B_MINIAOD_LFN" ]] || { echo "FATAL: could not pick a TT4b MiniAOD file"; exit 2; }
fi
echo "    tt4b   : ${TT4B_MINIAOD_LFN:-<not needed>}"

echo "--- reference files on EOS"
miss=0
for f in "central/$TTBB_CENTRAL_V15_NAME" "enriched/$OURS_V15_SMOKE" "enriched/$OURS_V15_2K"; do
  if [[ -e "$TTHH_EOS/$f" ]]; then printf '    ok      %s (%s)\n' "$f" "$(du -h "$TTHH_EOS/$f" | cut -f1)"
  else printf '    MISSING %s\n' "$f"; miss=1; fi
done
[[ $miss -eq 1 ]] && echo "    (central is re-fetched by the job from its LFN; the enriched references must exist -- copy them from the CMSSW area)"

# ----------------------------------------------------------------------------- 3. prestage
if [[ $PRESTAGE -eq 1 ]]; then
  echo "--- pre-staging MiniAOD inputs to $TTHH_EOS/miniaod/"
  mkdir -p "$TTHH_EOS"/{miniaod,central,enriched,json,logs}
  for lfn in "$TTBB_MINIAOD_LFN" ${TT4B_MINIAOD_LFN:+"$TT4B_MINIAOD_LFN"}; do
    dst="$TTHH_EOS/miniaod/$(basename "$lfn")"
    if [[ -s "$dst" ]]; then echo "    cached  $(basename "$lfn") ($(du -h "$dst" | cut -f1))"; continue; fi
    [[ $DRYRUN -eq 1 ]] && { echo "    (dry)   would xrdcp $lfn"; continue; }
    echo "    xrdcp   $lfn"
    xrdcp -f "$GRID_XRD$lfn" "$EOS_XRD/$dst" || { echo "FATAL: prestage failed for $lfn"; exit 2; }
  done
fi

# ----------------------------------------------------------------------------- 4. render
mkdir -p "$SUBDIR/logs"
cp -f config.sh runTask.sh check_expanded.py judge_compare.py "$SUBDIR/"   # frozen copies = provenance
cp -f "$PROXY_SRC" "$SUBDIR/x509up.proxy" && chmod 600 "$SUBDIR/x509up.proxy"
echo "$TASKS" > "$SUBDIR/tasks.txt"
echo "tt4b_miniaod_lfn=$TT4B_MINIAOD_LFN" > "$SUBDIR/inputs.txt"

render_jdl() {  # render_jdl <wantos> <task list...>
  local wantos="$1"; shift
  local jdl="$SUBDIR/tasks_${wantos}.jdl"
  cat > "$jdl" <<JDL
# rendered by submit.sh  tag=$TAG  $(date -u +%FT%TZ)
universe                = vanilla
executable              = $SUBDIR/runTask.sh
arguments               = \$(task) $TAG $TT4B_MINIAOD_LFN
transfer_input_files    = $SUBDIR/config.sh, $SUBDIR/check_expanded.py, $SUBDIR/judge_compare.py
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_output_files   = ""

use_x509userproxy       = true
x509userproxy           = $SUBDIR/x509up.proxy

MY.WantOS               = "$wantos"
MY.JobBatchName         = "enriched_$TAG"

output                  = $SUBDIR/logs/\$(task).\$(ClusterId).\$(ProcId).out
error                   = $SUBDIR/logs/\$(task).\$(ClusterId).\$(ProcId).err
log                     = $SUBDIR/logs/\$(task).\$(ClusterId).\$(ProcId).log

request_cpus            = $REQUEST_CPUS
request_memory          = $REQUEST_MEMORY
request_disk            = $REQUEST_DISK
+JobFlavour             = "$JOB_FLAVOUR"
notification            = never
max_retries             = 0

queue task in ( $* )
JDL
  echo "$jdl"
}

el8=(); el9=()
for t in $TASKS; do
  case $t in
    tt4b_v9_2k) el9+=("$t") ;;
    control_v15_200|timing_v15_2k|tt4b_v15_2k) el8+=("$t") ;;
    *) echo "FATAL: unknown task '$t'"; exit 2 ;;
  esac
done
JDLS=()
[[ ${#el8[@]} -gt 0 ]] && JDLS+=("$(render_jdl "$WANTOS_V15" "${el8[@]}")")
[[ ${#el9[@]} -gt 0 ]] && JDLS+=("$(render_jdl "$WANTOS_V9"  "${el9[@]}")")
echo "--- rendered"
for j in "${JDLS[@]}"; do echo "    $j  ($(grep -c . "$j") lines; WantOS $(grep WantOS "$j" | awk '{print $3}'))"; done

# ----------------------------------------------------------------------------- 5. submit
if [[ $DRYRUN -eq 1 ]]; then
  echo "=== dry run: nothing submitted. Inspect $SUBDIR and re-run without -n."
  exit 0
fi
command -v condor_submit >/dev/null 2>&1 || { echo "FATAL: condor_submit not found -- run on the lxplus host, not inside cmssw-el*"; exit 2; }
for j in "${JDLS[@]}"; do
  echo "--- condor_submit $j"
  condor_submit "$j" | tee -a "$SUBDIR/submit.out" || { echo "FATAL: condor_submit failed for $j"; exit 2; }
done

cat <<EOF

=== submitted. tag=$TAG
  follow   : condor_q -constraint 'JobBatchName=="enriched_$TAG"' ; condor_q -nobatch
  condor   : $SUBDIR/logs/<task>.*.out  (written when a job ends -- CERN batch no longer streams stdout)
  results  : $TTHH_EOS/logs/$TAG/<task>.summary.txt   (PASS/FAIL per check)
             $TTHH_EOS/logs/$TAG/<task>.log            (full worker log)
             $TTHH_EOS/logs/$TAG/<task>.cmsRun.log, <task>_cfg.py
             $TTHH_EOS/json/$TAG/*.json                (compare_v9_v15.py summaries)
             $TTHH_EOS/enriched/$TAG/*.root
  when done: cat $TTHH_EOS/logs/$TAG/*.summary.txt
EOF
