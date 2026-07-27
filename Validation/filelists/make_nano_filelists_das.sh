#!/usr/bin/env bash
# =============================================================================
# make_nano_filelists_das.sh — build the nano-side filelists straight from DAS
# =============================================================================
# WHY
#   matchTtbarId / matchTtbarIdSorted read only run/luminosityBlock/event/
#   genTtbarId from the nano side, so CENTRAL NanoAODv9 works directly — no
#   local ntuple production is needed to validate a new era. make_filelists.py
#   walks a local directory; this script is its DAS equivalent for eras where
#   no local copy exists (e.g. 2018 before the ttHH2018UL production lands).
#
# USAGE (lxplus / any node with dasgoclient + a valid proxy)
#   voms-proxy-init -voms cms -rfc --valid 168:00
#   ./make_nano_filelists_das.sh 2018            # -> nano2018/filelist_<short>.txt
#   ./make_nano_filelists_das.sh 2017            # -> nano2017das/ (2017 local lists untouched)
#   ./make_nano_filelists_das.sh 2018 xrootd     # force root:// prefix (default)
#   ./make_nano_filelists_das.sh 2018 lfn        # bare /store/... paths instead
#
# OUTPUT
#   <outdir>/filelist_<short>.txt        one ROOT path per line (master list)
#   <outdir>/<short>/file_<short>_<i>.txt  per-condor-job splits (SPLIT_SIZE)
#   <outdir>/summary_<era>.log           per-sample file counts + the DAS query
#                                        used (paste this back for review)
#
# The 7 short names match Validation/README.md and make_filelists.py exactly:
#   tt4b ttbb_Hadronic ttbb_SemiLeptonic ttbb_2L2Nu
#   TTToHadronic TTToSemiLeptonic TTTo2L2Nu
# =============================================================================
set -u

ERA="${1:-}"
MODE="${2:-xrootd}"
SPLIT_SIZE="${SPLIT_SIZE:-20}"          # files per split list; override via env

if [[ -z "$ERA" ]]; then
    echo "usage: $0 <era: 2017|2018> [xrootd|lfn]" >&2
    exit 2
fi

case "$ERA" in
  2017) CAMPAIGN="RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9"          ; OUTDIR="nano2017das" ;;
  2018) CAMPAIGN="RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1"; OUTDIR="nano2018"    ;;
  *)    echo "ERROR: unsupported era '$ERA' (expected 2017 or 2018)" >&2; exit 2 ;;
esac

case "$MODE" in
  xrootd) PREFIX="root://cms-xrd-global.cern.ch/" ;;
  lfn)    PREFIX="" ;;
  *)      echo "ERROR: unsupported mode '$MODE' (expected xrootd or lfn)" >&2; exit 2 ;;
esac

command -v dasgoclient >/dev/null 2>&1 || {
    echo "ERROR: dasgoclient not found. Source a CMSSW environment (cmsenv) first." >&2; exit 1; }
voms-proxy-info -exists >/dev/null 2>&1 || {
    echo "ERROR: no valid grid proxy. Run: voms-proxy-init -voms cms -rfc --valid 168:00" >&2; exit 1; }

# short name  <-->  DAS primary dataset (same 7 stitching samples as datasets.yaml)
SHORT=(tt4b ttbb_Hadronic ttbb_SemiLeptonic ttbb_2L2Nu TTToHadronic TTToSemiLeptonic TTTo2L2Nu)
PRIMARY=(
  "TT4b_TuneCP5_13TeV_madgraph_pythia8"
  "TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8"
  "TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8"
  "TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8"
  "TTToHadronic_TuneCP5_13TeV-powheg-pythia8"
  "TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8"
  "TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8"
)

mkdir -p "$OUTDIR"
LOG="${OUTDIR}/summary_${ERA}.log"
: > "$LOG"

log() { echo "$*" | tee -a "$LOG"; }

log "=============================================================="
log " make_nano_filelists_das.sh  era=${ERA}  mode=${MODE}"
log " campaign : ${CAMPAIGN}"
log " outdir   : ${OUTDIR}   (split size ${SPLIT_SIZE})"
log " started  : $(date -u +%FT%TZ)"
log "=============================================================="

rc=0
for i in "${!SHORT[@]}"; do
    short="${SHORT[$i]}"; prim="${PRIMARY[$i]}"
    ds="/${prim}/${CAMPAIGN}-*/NANOAODSIM"
    log ""
    log "### ${short}"
    log "  query: file dataset=${ds}"

    # Resolve the concrete dataset(s) first so an ambiguous -vN is visible.
    mapfile -t hits < <(dasgoclient -query "dataset=${ds}" 2>/dev/null)
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        log "  ERROR: no dataset found -> SKIPPED"
        rc=1
        continue
    fi
    if [[ ${#hits[@]} -gt 1 ]]; then
        log "  WARNING: ${#hits[@]} datasets match; using ALL of them:"
        for h in "${hits[@]}"; do log "     $h"; done
    else
        log "  dataset: ${hits[0]}"
    fi

    master="${OUTDIR}/filelist_${short}.txt"
    : > "$master"
    for h in "${hits[@]}"; do
        [[ -z "$h" ]] && continue
        dasgoclient -query "file dataset=${h}" 2>/dev/null \
            | sed "s#^#${PREFIX}#" >> "$master"
    done
    n=$(wc -l < "$master")
    if [[ "$n" -eq 0 ]]; then
        log "  ERROR: 0 files listed -> check the dataset/proxy"
        rc=1
        continue
    fi
    log "  files : ${n}  -> ${master}"

    # per-job splits (mirrors make_filelists.py layout)
    split_dir="${OUTDIR}/${short}"
    rm -rf "$split_dir"; mkdir -p "$split_dir"
    split -l "$SPLIT_SIZE" -d -a 4 "$master" "${split_dir}/part_"
    j=0
    for p in "${split_dir}"/part_*; do
        mv "$p" "${split_dir}/file_${short}_${j}.txt"
        j=$((j+1))
    done
    log "  splits: ${j} file(s) in ${split_dir}/ (${SPLIT_SIZE} paths each)"
done

log ""
log "=============================================================="
log " done: $(date -u +%FT%TZ)   overall rc=${rc}"
log " summary log: ${LOG}"
log "=============================================================="
exit "$rc"
