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
#   bash resolve_parents.sh
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
NANO=(
  "/TT4b_TuneCP5_13TeV_madgraph_pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v2/NANOAODSIM"
  "/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
  "/TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
  "/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
  "/TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
  "/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
  "/TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM"
)

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
    base="$(echo "$nano" | sed 's#/RunIISummer20UL17NanoAODv9.*##')"
    hits="$(dasgoclient -query="dataset=${base}/RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-*/MINIAODSIM" 2>/dev/null)"
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
