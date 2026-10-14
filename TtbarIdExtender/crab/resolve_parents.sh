#!/usr/bin/env bash
# =============================================================================
# resolve_parents.sh
# =============================================================================
# Confirm the true MiniAODv2 parent of each NanoAODv9 child in datasets.yaml
# using DAS, so the `dataset:` field (and its -v1/-v2 suffix) is grid-accurate.
#
# Run on lxplus (cmssw-el7 + cmsenv, so dasgoclient is on PATH) with a valid
# grid proxy:
#
#   voms-proxy-init -voms cms
#   bash resolve_parents.sh [ERA] [--apply]
#        ERA = 2017 (default) | 2018 | 2016APV | 2016
#
# 2026-07-26: made era-aware (was 2017-hardcoded). The 2018 NanoAODv9 children
# below are the exact datasets found by NtupleForge/script/das_ul18_scan.sh
# (log: NtupleForge/script/das_ul18_scan_20260726_1657.log) -- standard campaign
# RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1-vN, i.e. the
# same 7 stitching samples that config_ttHH2018UL.yaml uses. Their MiniAODv2
# parents (and the -vN suffixes) are what this script resolves; do NOT guess them.
#
# 2026-10-14: eras 2016APV (UL16 preVFP) and 2016 (UL16 postVFP). The NanoAODv9
# children are the VALID standard-campaign datasets of the NtupleForge DAS
# inventories script/das/inventory_dumps/das_inventory_ul16{pre,post}_v9_*.tsv.
#
# For each ttbar stitching sample it:
#   1. prints the NanoAODv9 child (from this script's list),
#   2. asks DAS for that child's parent dataset,
#   3. prints the parent, and compares it with the `dataset:` value that
#      datasets.yaml holds for the entry with that nano_child:
#        MATCH     identical strings
#        MISMATCH  different -> paste the DAS parent into `dataset:` by hand
#        ABSENT    no datasets.yaml entry has this nano_child
#
# It also cross-checks by querying the MiniAODv2 dataset directly when DAS
# returns no parent (sometimes a child has no parent link in DAS; the direct
# query is the fallback). A sample without a parent link is never MATCH.
#
# --apply (2026-10-14): after the read-only pass, and ONLY if every sample of
#   the era is MATCH, rewrite datasets.yaml in place. Inside the era block, in
#   the entries whose nano_child is a MATCH child (and nowhere else):
#       enabled: false  -> enabled: true
#       verified: false -> verified: true
#   The diff is printed and checked (only those flag lines may change). This is
#   exactly the manual step "paste the parent, flip verified/enabled" of
#   docs/05_architecture.md sec.5, done only when the pasted value would be
#   identical to the DAS answer. If any sample is not MATCH nothing is written.
#   Undo: git checkout -- crab/datasets.yaml
#
# Exit codes:
#   0  every sample MATCH (and, with --apply, datasets.yaml updated or already open)
#   1  dasgoclient not found
#   2  bad arguments / unsupported ERA / datasets.yaml unreadable
#   3  at least one sample is not MATCH (MISMATCH, ABSENT, or no parent)
#   4  --apply refused by its own post-check (datasets.yaml left unchanged)
#
# Keep it ASCII-only (docs/09_environment.md: LANG=C inside CMSSW_10_6_X).
# =============================================================================
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# RESOLVE_PARENTS_YAML exists for offline tests only; leave it unset.
YAML="${RESOLVE_PARENTS_YAML:-${HERE}/datasets.yaml}"

APPLY=0
ERA=""
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    -h|--help) sed -n '2,/^# ====/p' "${BASH_SOURCE[0]}" | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    -*) echo "ERROR: unknown option '$arg' (try --help)" >&2; exit 2 ;;
    *)  if [[ -z "$ERA" ]]; then ERA="$arg"; else
          echo "ERROR: unexpected extra argument '$arg'" >&2; exit 2; fi ;;
  esac
done
ERA="${ERA:-2017}"

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
  2016APV)
    NANO_CAMPAIGN="RunIISummer20UL16NanoAODAPVv9"
    MINI_CAMPAIGN="RunIISummer20UL16MiniAODAPVv2-106X_mcRun2_asymptotic_preVFP_v11"
    NANO=(
      "/TT4b_TuneCP5_13TeV_madgraph_pythia8/RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v2/NANOAODSIM"
      "/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v1/NANOAODSIM"
      "/TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v1/NANOAODSIM"
      "/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v1/NANOAODSIM"
      "/TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v1/NANOAODSIM"
      "/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v1/NANOAODSIM"
      "/TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11-v1/NANOAODSIM"
    )
    ;;
  2016)
    NANO_CAMPAIGN="RunIISummer20UL16NanoAODv9"
    MINI_CAMPAIGN="RunIISummer20UL16MiniAODv2-106X_mcRun2_asymptotic_v17"
    NANO=(
      "/TT4b_TuneCP5_13TeV_madgraph_pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v2/NANOAODSIM"
      "/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"
      "/TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"
      "/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"
      "/TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"
      "/TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"
      "/TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM"
    )
    ;;
  *)
    echo "ERROR: unsupported ERA '$ERA' (expected 2017, 2018, 2016APV or 2016)" >&2
    exit 2
    ;;
esac
echo "### resolve_parents.sh -- ERA=$ERA (nano campaign: $NANO_CAMPAIGN)$( (( APPLY )) && echo '  [--apply]')"
echo "### datasets.yaml: $YAML"
echo "### utc: $(date -u +%FT%TZ)  host: $(hostname 2>/dev/null || echo '?')"

if [[ ! -r "$YAML" ]]; then
  echo "ERROR: cannot read datasets.yaml at '$YAML'" >&2
  exit 2
fi

if ! command -v dasgoclient >/dev/null 2>&1; then
  echo "ERROR: dasgoclient not found. Source a CMSSW environment (cmsenv) first." >&2
  exit 1
fi

# Warn if no proxy (non-fatal; dasgoclient will error per-query if truly absent)
if command -v voms-proxy-info >/dev/null 2>&1; then
  voms-proxy-info -exists >/dev/null 2>&1 || \
    echo "WARNING: no valid grid proxy detected; run 'voms-proxy-init -voms cms'." >&2
fi

# dataset: value of the datasets.yaml entry (inside the ERA block) whose
# nano_child equals $1; empty if there is none. Same parsing conventions as
# resolve_nano_children.sh: era key at 2 spaces, keys matched on [[:space:]]+.
yaml_dataset_for_nano() {
  ERA="$ERA" NANO_WANT="$1" awk '
    $0 ~ "^  \"" ENVIRON["ERA"] "\":"  { inera=1; next }
    inera && /^  "[0-9]/               { inera=0 }
    !inera                             { next }
    /^[[:space:]]+- name:/             { ds="" }
    /^[[:space:]]+dataset:/            { ds=$2; gsub(/"/,"",ds) }
    /^[[:space:]]+nano_child:/         { nc=$2; gsub(/"/,"",nc);
                                         if (nc == ENVIRON["NANO_WANT"]) { print ds; exit } }
  ' "$YAML"
}

n=${#NAMES[@]}
n_match=0
n_bad=0
MATCHED=()
for ((i=0; i<n; i++)); do
  name="${NAMES[$i]}"
  nano="${NANO[$i]}"
  echo "============================================================"
  echo "[$name]  ($((i+1))/$n)"
  echo "  nano_child : $nano"

  # 1) parent of the NanoAODv9 child
  parents="$(dasgoclient -query="parent dataset=${nano}" 2>/dev/null | grep MINIAODSIM)"
  parent="$(printf '%s\n' "$parents" | head -n1)"
  n_par="$(printf '%s\n' "$parents" | grep -c MINIAODSIM)"
  ymini="$(yaml_dataset_for_nano "$nano")"
  if [[ -n "$parent" ]]; then
    echo "  PARENT (from DAS) : $parent"
    if (( n_par > 1 )); then
      echo "  datasets.yaml     : NOT CHECKED -- DAS returned $n_par MINIAODSIM parents:"
      printf '%s\n' "$parents" | sed 's/^/    /'
      n_bad=$((n_bad+1))
    elif [[ -z "$ymini" ]]; then
      echo "  datasets.yaml     : ABSENT -- no entry of era $ERA has this nano_child"
      n_bad=$((n_bad+1))
    elif [[ "$parent" == "$ymini" ]]; then
      echo "  datasets.yaml     : MATCH"
      n_match=$((n_match+1))
      MATCHED+=("$nano")
    else
      echo "  datasets.yaml     : MISMATCH -- datasets.yaml has $ymini"
      n_bad=$((n_bad+1))
    fi
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
    echo "  datasets.yaml     : NOT CHECKED (no parent link; check proxy / DAS)"
    n_bad=$((n_bad+1))
  fi
done
echo "============================================================"
echo "RESULT: ERA=$ERA  MATCH $n_match/$n  not-MATCH $n_bad"

if (( n_bad > 0 )); then
  echo "Not every sample is MATCH. Paste each PARENT string into the matching"
  echo "'dataset:' field in datasets.yaml by hand, then set 'verified: true' (and"
  echo "'enabled: true') for that entry, and re-run this script."
  (( APPLY )) && echo "--apply: NOTHING WRITTEN (it needs MATCH for every sample)."
  exit 3
fi

if (( ! APPLY )); then
  echo "Every dataset: field already equals its DAS parent."
  echo "To open these entries (enabled/verified -> true) run:"
  echo "  bash crab/resolve_parents.sh $ERA --apply"
  exit 0
fi

# ---------------------------------------------------------------------------
# --apply: flip enabled/verified to true in the MATCH entries of the ERA block
# ---------------------------------------------------------------------------
tmp="$(mktemp "${YAML}.apply.XXXXXX")" || { echo "ERROR: mktemp failed" >&2; exit 4; }
# ${MATCHED[@]+...}: an empty array under set -u is an error in bash 4.2 (cmssw-el7)
MATCH_LIST="$(printf '%s\n' ${MATCHED[@]+"${MATCHED[@]}"})" ERA="$ERA" awk '
  BEGIN {
    nm = split(ENVIRON["MATCH_LIST"], arr, "\n")
    for (k = 1; k <= nm; k++) if (arr[k] != "") ok[arr[k]] = 1
  }
  { line[NR] = $0 }
  END {
    # pass 1: mark the line ranges of MATCH entries inside the ERA block
    inera = 0; start = 0
    for (i = 1; i <= NR; i++) {
      l = line[i]
      if (l ~ "^  \"" ENVIRON["ERA"] "\":") { inera = 1; start = 0; continue }
      if (inera && l ~ /^  "[0-9]/)         { close_entry(i - 1); inera = 0; continue }
      if (!inera) continue
      if (l ~ /^[[:space:]]+- name:/)       { close_entry(i - 1); start = i; nc = "" }
      if (l ~ /^[[:space:]]+nano_child:/)   { split(l, f, /[[:space:]]+/); nc = f[3]; gsub(/"/, "", nc) }
    }
    if (inera) close_entry(NR)
    # pass 2: print, flipping only the flag lines of marked entries
    for (i = 1; i <= NR; i++) {
      l = line[i]
      if (flip[i]) {
        if (l ~ /^[[:space:]]+enabled:[[:space:]]*false[[:space:]]*$/)  sub(/false/, "true", l)
        if (l ~ /^[[:space:]]+verified:[[:space:]]*false[[:space:]]*$/) sub(/false/, "true", l)
      }
      print l
    }
  }
  function close_entry(last,   j) {
    if (start > 0 && (nc in ok)) for (j = start; j <= last; j++) flip[j] = 1
    start = 0
  }
' "$YAML" > "$tmp"

# post-check: only enabled:/verified: lines may differ, false -> true, and every
# MATCH entry must now be open.
changed="$(diff "$YAML" "$tmp" | grep '^[<>]')"
bad_lines="$(printf '%s\n' "$changed" | grep -v '^$' \
  | grep -Ev '^< [[:space:]]+(enabled|verified):[[:space:]]*false[[:space:]]*$' \
  | grep -Ev '^> [[:space:]]+(enabled|verified):[[:space:]]*true[[:space:]]*$')"
n_minus="$(printf '%s\n' "$changed" | grep -c '^<')"
n_plus="$(printf '%s\n' "$changed" | grep -c '^>')"
not_open=0
for nano in ${MATCHED[@]+"${MATCHED[@]}"}; do
  st="$(ERA="$ERA" NANO_WANT="$nano" awk '
    $0 ~ "^  \"" ENVIRON["ERA"] "\":"  { inera=1; next }
    inera && /^  "[0-9]/               { inera=0 }
    !inera                             { next }
    /^[[:space:]]+- name:/             { if (hit) { print en "/" ve; done=1; exit }
                                         en="?"; ve="?" }
    /^[[:space:]]+enabled:/            { en=$2 }
    /^[[:space:]]+verified:/           { ve=$2 }
    /^[[:space:]]+nano_child:/         { nc=$2; gsub(/"/,"",nc); if (nc == ENVIRON["NANO_WANT"]) hit=1 }
    END                                { if (hit && !done) print en "/" ve }
  ' "$tmp")"
  [[ "$st" == "true/true" ]] || { echo "  post-check: $nano -> enabled/verified = ${st:-<not found>}"; not_open=$((not_open+1)); }
done
if [[ -n "$bad_lines" || "$n_minus" != "$n_plus" || "$not_open" -ne 0 ]]; then
  echo "ERROR: --apply post-check failed; datasets.yaml NOT modified." >&2
  [[ -n "$bad_lines" ]] && { echo "  unexpected changed lines:" >&2; printf '%s\n' "$bad_lines" | sed 's/^/    /' >&2; }
  echo "  removed=$n_minus added=$n_plus not_open=$not_open" >&2
  rm -f "$tmp"
  exit 4
fi
if [[ "$n_plus" -eq 0 ]]; then
  echo "--apply: nothing to change -- every MATCH entry of era $ERA was already enabled/verified."
  rm -f "$tmp"
  exit 0
fi
echo "--apply: the following flag lines change (diff datasets.yaml):"
diff -u "$YAML" "$tmp" | sed 's/^/  /'
cat "$tmp" > "$YAML" && rm -f "$tmp"
echo "--apply: datasets.yaml updated -- $n_match entries of era $ERA are now enabled/verified ($n_plus flag lines)."
echo "Next: python3 crab/submit_ttbarIdExtend.py --era $ERA --preflight --check-das"
exit 0
