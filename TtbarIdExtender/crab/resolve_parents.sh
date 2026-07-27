#!/usr/bin/env bash
# =============================================================================
# resolve_parents.sh
# =============================================================================
# Confirm the true MiniAODv2 parent of each NanoAODv9 child in datasets.yaml
# using DAS, so the `dataset:` field (and its -v1/-v2 suffix) is grid-accurate.
#
# Run on cms01 (or any machine with dasgoclient + a valid grid proxy):
#
#   voms-proxy-init -voms cms
#   bash resolve_parents.sh [ERA]        # ERA = 2017 (default) | 2018
#
# 2026-07-26: made era-aware (was 2017-hardcoded). The 2018 NanoAODv9 children
# below are the exact datasets found by NtupleForge/script/das_ul18_scan.sh
# (log: NtupleForge/script/das_ul18_scan_20260726_1657.log) -- standard campaign
# RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-vN, i.e. the
# same 7 stitching samples that config_ttHH2018UL.yaml uses. Their MiniAODv2
# parents (and the -vN suffixes) are what this script resolves; do NOT guess them.
#
# For each ttbar stitching sample it:
#   1. prints the NanoAODv9 child (from this script's list),
#   2. asks DAS for that child's parent dataset,
#   3. prints the parent so you can paste it into datasets.yaml `dataset:`.
#
# It also cross-checks by querying the MiniAODv2 dataset directly (sometimes a
# child has no parent link in DAS; the direct query is the fallback).
# =============================================================================
set -u

# logical name  ->  NanoAODv9 child  (the known-good reference)
# (order matches datasets.yaml)
NAMES=(
  "TT4b"
  "TTbar_SemiLep"
  "TTbar_Hadronic"
  "TTbar_DiLep"
  "TTbb_SemiLep"
  "TTbb_Hadronic"
  "TTbb_DiLep"
)
ERA="${1:-2017}"

case "$ERA" in
  2017)
    NANO_CAMPAIGN="RunIISummer20UL17NanoAODv9"
    MINI_CAMPAIGN="RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9"
    NANO=(
      "/TT4b_TuneCP5_13TeV_madgraph_pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v2/NANOAODSIM"
      "/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
      "/TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
      "/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
      "/TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
      "/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
      "/TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
    )
    ;;
  2018)
    NANO_CAMPAIGN="RunIISummer20UL18NanoAODv9"
    MINI_CAMPAIGN="RunIISummer20UL18MiniAODv2-106X_upgrade2018_realistic_v16_L1v1"
    NANO=(
      "/TT4b_TuneCP5_13TeV_madgraph_pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v2/NANOAODSIM"
      "/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v1/NANOAODSIM"
      "/TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v1/NANOAODSIM"
      "/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v1/NANOAODSIM"
      "/TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v1/NANOAODSIM"
      "/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v1/NANOAODSIM"
      "/TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-v1/NANOAODSIM"
    )
    ;;
  *)
    echo "ERROR: unsupported ERA '$ERA' (expected 2017 or 2018)" >&2
    exit 2
    ;;
esac
echo "### resolve_parents.sh -- ERA=$ERA (nano campaign: $NANO_CAMPAIGN)"

if ! command -v dasgoclient >/dev/null 2>&1; then
  echo "ERROR: dasgoclient not found. Source a CMSSW environment (cmsenv) first." >&2
  exit 1
fi

# Warn if no proxy (non-fatal; dasgoclient will error per-query if truly absent)
if command -v voms-proxy-info >/dev/null 2>&1; then
  voms-proxy-info -exists >/dev/null 2>&1 || \
    echo "WARNING: no valid grid proxy detected; run 'voms-proxy-init -voms cms'." >&2
fi

n=${#NAMES[@]}
for ((i=0; i<n; i++)); do
  name="${NAMES[$i]}"
  nano="${NANO[$i]}"
  echo "============================================================"
  echo "[$name]"
  echo "  nano_child : $nano"

  # 1) parent of the NanoAODv9 child
  parent="$(dasgoclient -query="parent dataset=${nano}" 2>/dev/null | grep MINIAODSIM | head -n1)"
  if [[ -n "$parent" ]]; then
    echo "  PARENT (from DAS) : $parent"
  else
    echo "  PARENT (from DAS) : <none returned> -- trying direct MiniAODv2 search"
    # 2) fallback: search the MiniAODv2 dataset by the base name + campaign
    base="$(echo "$nano" | sed "s#/${NANO_CAMPAIGN}.*##")"
    hits="$(dasgoclient -query="dataset=${base}/${MINI_CAMPAIGN}-*/MINIAODSIM" 2>/dev/null)"
    if [[ -n "$hits" ]]; then
      echo "  MiniAODv2 candidates:"
      echo "$hits" | sed 's/^/    /'
    else
      echo "  (no MiniAODv2 found by direct search either; check the name by hand)"
    fi
  fi
done
echo "============================================================"
echo "Paste each PARENT string into the matching 'dataset:' field in"
echo "datasets.yaml, then set 'verified: true' for that entry."
