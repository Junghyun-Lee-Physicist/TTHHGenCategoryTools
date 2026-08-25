#!/usr/bin/env bash
# =============================================================================
#  resolve_nano_children.sh -- which NanoAOD versions descend from the MiniAOD
#                              parents we have ALREADY produced ttbarId-extend on?
# =============================================================================
#  Created 2026-08-17.  Companion to resolve_parents.sh, opposite direction.
#
#  THE QUESTION THIS ANSWERS
#  -------------------------
#  Moving the analysis from NanoAODv9 to a newer NanoAOD only costs a re-nano IF
#  the new NanoAOD descends from the SAME MiniAOD we already ran the extender on.
#  If it descends from a different MiniAOD (a MiniAODv1/v3/v4, or a different
#  -vN of MiniAODv2), then:
#      * the ttbarId-extend CRAB production must be RE-RUN for that parent,
#      * the sort + patch extraction must be redone (7 more patch files per
#        parent, so 28 instead of 14 across two years),
#      * and the `genTtbarId` byte-identity argument has to be rebuilt from
#        scratch, because a different MiniAOD can carry a different pruned/packed
#        gen record.
#  That is the difference between "re-nano is nearly free" and "the plan doubles",
#  so it is not something to assume in either direction.
#
#  WHY 'child' AND NOT 'parent'
#  ----------------------------
#  resolve_parents.sh asks "what is this nano's parent?" -- which requires you to
#  already know the nano dataset, and its hand-copied NANO=() array only holds
#  the v9 paths, so it cannot answer the question for a version you have not
#  wired in yet.
#  This script asks the inverse: "given the MiniAOD parent that datasets.yaml has
#  already DAS-verified and that we already produced extend output from, what
#  NanoAOD datasets exist downstream of it?" One query per sample answers the
#  whole question, and the answer is authoritative by construction -- if the new
#  nano appears in the child list, the parent is identical, full stop.
#
#  It also reads the MiniAOD paths straight out of crab/datasets.yaml, so unlike
#  resolve_parents.sh it holds no duplicate copy of anything.
#
# -----------------------------------------------------------------------------
#  USAGE
#      bash crab/resolve_nano_children.sh <ERA> [--want vN] [--yaml PATH]
#
#      bash crab/resolve_nano_children.sh 2018
#      bash crab/resolve_nano_children.sh 2018 --want v15
#      bash crab/resolve_nano_children.sh 2017 --want v15 --yaml crab/datasets.yaml
#
#  ERA      an era key present in datasets.yaml (2017 | 2018 | ...)
#  --want   a NanoAOD version token to render a verdict on (e.g. v15). Without
#           it the script only enumerates what exists.
#  --yaml   datasets.yaml path (default: alongside this script)
#
#  Needs only bash + awk + dasgoclient. No python, no PyROOT -- so it runs in
#  CMSSW_10_6_32_patch1 (ROOT 6.14 / python 3.6) as well as in 14_X.
#
#  OUTPUT (machine-readable lines)
#      MINI|<era>|<name>|<miniaod dataset>
#      CHILD|<era>|<name>|<nanoVersionToken>|<nano dataset>
#      RECORDED|<era>|<name>|<IN_CHILD_LIST|NOT_IN_CHILD_LIST>|<datasets.yaml nano_child>
#      VERDICT|<era>|<name>|<SAME_PARENT|DIFFERENT_PARENT|VERSION_ABSENT>|<detail>
#
#  EXIT CODES
#      0  every sample resolved, and (with --want) every one is SAME_PARENT
#      1  dasgoclient missing
#      2  no valid VOMS proxy
#      3  bad arguments / era not found in the yaml
#      4  --want given and at least one sample is DIFFERENT_PARENT
#         ("the plan doubles" -- stop and re-plan)
#      5  --want given and at least one sample is VERSION_ABSENT, none DIFFERENT
#         (that version does not exist for some samples)
# =============================================================================

set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ERA=""; WANT=""; YAML="${HERE}/datasets.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --want) WANT="${2:-}"; shift 2 ;;
    --yaml) YAML="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,/^# ====/p' "${BASH_SOURCE[0]}" | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    -*) echo "FATAL: unknown option '$1' (try --help)" >&2; exit 3 ;;
    *)  if [[ -z "$ERA" ]]; then ERA="$1"; shift; else
          echo "FATAL: unexpected extra argument '$1'" >&2; exit 3; fi ;;
  esac
done

[[ -z "$ERA" ]] && { echo "FATAL: ERA is required (e.g. 2018). See --help" >&2; exit 3; }
[[ -r "$YAML" ]] || { echo "FATAL: cannot read '$YAML'" >&2; exit 3; }

command -v dasgoclient >/dev/null 2>&1 || {
  echo "FATAL: dasgoclient not found (run on lxplus with the CMS environment)" >&2; exit 1; }
voms-proxy-info -exists 2>/dev/null || {
  echo "FATAL: no valid VOMS proxy (voms-proxy-init -voms cms -rfc --valid 72:00)" >&2; exit 2; }

# --- pull (name, MiniAOD dataset, recorded nano_child) out of the era block ---
# Indentation in datasets.yaml: era key at 2 spaces, '- name:' at 6, the
# 'dataset:'/'nano_child:' keys at 8. Matching on [[:space:]]+ rather than a
# fixed count so a reindent does not silently produce zero rows.
ROWS=$(ERA="$ERA" awk '
  $0 ~ "^  \"" ENVIRON["ERA"] "\":"  { inera=1; next }
  inera && /^  "[0-9]/               { inera=0 }
  !inera                             { next }
  /^[[:space:]]+- name:/             { if (name!="") print name "\t" ds "\t" nc;
                                       name=$3; gsub(/"/,"",name); ds=""; nc="" }
  /^[[:space:]]+dataset:/            { ds=$2; gsub(/"/,"",ds) }
  /^[[:space:]]+nano_child:/         { nc=$2; gsub(/"/,"",nc) }
  END                                { if (name!="") print name "\t" ds "\t" nc }
' "$YAML")

if [[ -z "$ROWS" ]]; then
  echo "FATAL: era '$ERA' yielded 0 samples from $YAML." >&2
  echo "       Era keys present:" >&2
  grep -nE '^  "[0-9]+":' "$YAML" >&2
  exit 3
fi

echo "========================================================================="
echo "resolve_nano_children.sh   era=${ERA}   want=${WANT:-<enumerate only>}"
echo "  yaml : ${YAML}"
echo "  utc  : $(date -u +%FT%TZ)"
echo "  NOTE : the MiniAOD paths below are the ones datasets.yaml has already"
echo "         DAS-verified and that the extend production actually ran on."
echo "========================================================================="

n_same=0; n_diff=0; n_absent=0; n_tot=0

while IFS=$'\t' read -r NAME MINI REC; do
  [[ -z "${NAME:-}" ]] && continue
  n_tot=$((n_tot+1))
  echo ""
  echo "### ${NAME}"
  echo "MINI|${ERA}|${NAME}|${MINI}"

  mapfile -t kids < <(dasgoclient -query="child dataset=${MINI}" 2>/dev/null \
                      | grep -E '/NANOAODSIM$' | sort -u)

  if [[ ${#kids[@]} -eq 0 || -z "${kids[0]:-}" ]]; then
    echo "  (no NANOAODSIM children returned -- DAS lineage may be incomplete for"
    echo "   this dataset; fall back to 'parent dataset=<nano>' for this sample)"
  fi

  # Campaign substrings that mark a special reprocessing rather than the
  # standard nano. Real UL18 v15 example: alongside the plain
  #   RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v2
  # DAS also carries
  #   RunIISummer20UL18NanoAODv15-BTVNanoV15_150X_mc2018_realistic_v1-v3
  #   RunIISummer20UL18NanoAODv15-20UL18JMENano_150X_mc2018_realistic_v1-v1
  # Those are POG-specific extended formats with different content. The verdict
  # is the same either way (same parent), but the dataset path we PRINT gets
  # copied into configs, so it must be the plain one.
  FLAVOUR='JMENano|BTVNano|PFNano|MuonNano|TauNano|EGMNano|HIGNano|PUFor|PU35For|FSUL|BPH_'

  found_want=""; found_plain=""; best_v=-1
  for k in "${kids[@]}"; do
    [[ -z "$k" ]] && continue
    camp=$(echo "$k" | cut -d/ -f3)
    vtok=$(echo "$camp" | grep -oE 'NanoAOD[A-Za-z]*v[0-9]+' | head -1)
    vtok=${vtok:-UNKNOWN}
    flav=""
    echo "$camp" | grep -qE "$FLAVOUR" && flav=" [flavour: $(echo "$camp" | grep -oE "$FLAVOUR" | head -1)]"
    echo "CHILD|${ERA}|${NAME}|${vtok}|${k}${flav}"
    # exact version-token match, not a suffix glob
    if [[ -n "$WANT" && "$vtok" == "NanoAOD${WANT}" || ( -n "$WANT" && "$vtok" == "NanoAODAPV${WANT}" ) ]]; then
      found_want="${found_want:-$k}"
      if [[ -z "$flav" ]]; then
        vn=$(echo "$camp" | grep -oE -- '-v[0-9]+$' | tr -dc '0-9')
        vn=${vn:-0}
        if (( vn > best_v )); then best_v=$vn; found_plain="$k"; fi
      fi
    fi
  done
  # prefer the plain standard campaign as the representative
  [[ -n "$found_plain" ]] && found_want="$found_plain"

  # consistency check on datasets.yaml itself: is the recorded nano_child really
  # a child of the recorded parent?
  if [[ -n "${REC:-}" ]]; then
    if printf '%s\n' "${kids[@]}" | grep -qxF "$REC"; then
      echo "RECORDED|${ERA}|${NAME}|IN_CHILD_LIST|${REC}"
    else
      echo "RECORDED|${ERA}|${NAME}|NOT_IN_CHILD_LIST|${REC}"
      echo "  !! datasets.yaml's nano_child is NOT a DAS child of its own dataset:."
      echo "  !! One of the two fields is wrong -- resolve before trusting anything below."
    fi
  fi

  [[ -z "$WANT" ]] && continue

  if [[ -n "$found_want" ]]; then
    n_same=$((n_same+1))
    echo "VERDICT|${ERA}|${NAME}|SAME_PARENT|${found_want}"
    echo "  -> ${WANT} descends from the SAME MiniAOD. No extend re-run needed."
  else
    # Does the wanted version exist at all for this primary, just from elsewhere?
    #
    # The query MUST anchor both the era and the version token. A loose
    # '*NanoAOD*v15*' matched
    #   RunIISummer20UL16NanoAODv2-106X_mcRun2_asymptotic_v15-v1
    #   RunIISummer20UL18NanoAODv2-106X_upgrade2018_realistic_v15_L1v1-v1
    # because the GLOBAL TAG contains "_v15" -- those are NanoAODv2, from a
    # different era, and reporting them as "v15 from a different parent" was a
    # false DIFFERENT_PARENT (observed on TT4b, 2026-08-25). The era prefix is
    # taken from the MiniAOD campaign itself, so it cannot drift.
    prim=$(echo "$MINI" | cut -d/ -f2)
    mini_camp=$(echo "$MINI" | cut -d/ -f3)
    era_prefix="${mini_camp%%MiniAOD*}"        # e.g. RunIISummer20UL18
    mapfile -t alt < <(dasgoclient -query="dataset=/${prim}/${era_prefix}NanoAOD${WANT}*/NANOAODSIM" 2>/dev/null \
                       | grep -E '/NANOAODSIM$' | sort -u)
    # 2016preVFP uses the NanoAODAPV flavour of the same era prefix
    if [[ ${#alt[@]} -eq 0 || -z "${alt[0]:-}" ]]; then
      mapfile -t alt < <(dasgoclient -query="dataset=/${prim}/${era_prefix}NanoAODAPV${WANT}*/NANOAODSIM" 2>/dev/null \
                         | grep -E '/NANOAODSIM$' | sort -u)
    fi
    if [[ ${#alt[@]} -eq 0 || -z "${alt[0]:-}" ]]; then
      n_absent=$((n_absent+1))
      echo "VERDICT|${ERA}|${NAME}|VERSION_ABSENT|no ${era_prefix}NanoAOD${WANT} NANOAODSIM for primary ${prim}"
      echo "  -> ${WANT} does not exist for this sample in era ${era_prefix}."
      echo "     (queried /${prim}/${era_prefix}NanoAOD${WANT}*/NANOAODSIM -- zero hits)"
    else
      n_diff=$((n_diff+1))
      echo "VERDICT|${ERA}|${NAME}|DIFFERENT_PARENT|${alt[0]}"
      echo "  !! ${WANT} EXISTS but is NOT a child of the parent we produced extend on."
      echo "  !! Its actual parent:"
      for a in "${alt[@]}"; do
        [[ -z "$a" ]] && continue
        p=$(dasgoclient -query="parent dataset=${a}" 2>/dev/null | grep -E '/MINIAOD(SIM)?$' | head -1)
        echo "  !!   ${a}"
        echo "  !!     parent: ${p:-<none returned>}"
      done
      echo "  !! CONSEQUENCE: extend must be re-run for this parent; patch files"
      echo "  !! must be re-extracted; the genTtbarId byte-identity argument does"
      echo "  !! not carry over."
    fi
  fi
done <<< "$ROWS"

echo ""
echo "========================================================================="
echo "SUMMARY  era=${ERA}  samples=${n_tot}"
if [[ -n "$WANT" ]]; then
  echo "  want=${WANT}   SAME_PARENT=${n_same}   DIFFERENT_PARENT=${n_diff}   VERSION_ABSENT=${n_absent}"
  if   [[ $n_diff  -gt 0 ]]; then
    echo "  >>> STOP. At least one sample's ${WANT} comes from a different MiniAOD."
    echo "  >>> The ttbarId-extend work does NOT carry over. Re-plan before running."
    echo "========================================================================="; exit 4
  elif [[ $n_absent -gt 0 ]]; then
    echo "  >>> ${WANT} is missing for ${n_absent} sample(s). Decide per sample."
    echo "========================================================================="; exit 5
  else
    echo "  >>> All ${n_tot} samples: ${WANT} descends from the same MiniAOD parent."
    echo "  >>> extend CRAB production and the patch files carry over unchanged."
    echo "  >>> Only the nano-side filelists and the match runs need the new version."
  fi
else
  echo "  (enumeration only -- pass --want vN for a verdict)"
fi
echo "========================================================================="
exit 0
