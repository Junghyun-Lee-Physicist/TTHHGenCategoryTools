#!/usr/bin/env bash
# =============================================================================
# merge_hists.sh
# =============================================================================
# Merge per-job histogram (or extend) ROOT files into one file per process.
#
# This is a thin wrapper around ROOT's `hadd`.  It expects a directory holding
# per-job files named like  <prefix>_<process>_<jobN>.root  and produces one
# <prefix>_<process>.root  per process.
#
# Usage:
#   merge_hists.sh <indir> <outdir> <prefix>
#
#   indir   directory containing the per-job files
#   outdir  where to write the merged per-process files
#   prefix  filename prefix, e.g. 'hist_extend' or 'hist_nano'
#
# Example:
#   # per-job files: hists/hist_extend_TTHHto4b_0.root, ..._1.root, ...
#   merge_hists.sh hists merged hist_extend
#   # -> merged/hist_extend_TTHHto4b.root  (and one per other process)
#
# Process name is taken as the token between "<prefix>_" and the trailing
# "_<jobN>.root".  Files without a trailing _<number> are treated as already
# per-process and merged on their own (harmless single-input hadd).
# =============================================================================

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <indir> <outdir> <prefix>" >&2
  exit 1
fi

INDIR="$1"
OUTDIR="$2"
PREFIX="$3"

if ! command -v hadd >/dev/null 2>&1; then
  echo "ERROR: hadd not on PATH (run cmsenv or source a ROOT environment)." >&2
  exit 1
fi
if [[ ! -d "$INDIR" ]]; then
  echo "ERROR: input dir not found: $INDIR" >&2
  exit 1
fi
mkdir -p "$OUTDIR"

# Collect the set of process names by stripping the prefix and the trailing
# _<jobN>.root from each matching file.
declare -A PROCS
shopt -s nullglob
for f in "$INDIR"/${PREFIX}_*.root; do
  base="$(basename "$f" .root)"           # e.g. hist_extend_TTHHto4b_3
  rest="${base#${PREFIX}_}"               # e.g. TTHHto4b_3   (or TTHHto4b)
  # strip a trailing _<digits> if present
  if [[ "$rest" =~ ^(.*)_[0-9]+$ ]]; then
    proc="${BASH_REMATCH[1]}"
  else
    proc="$rest"
  fi
  PROCS["$proc"]=1
done
shopt -u nullglob

if [[ ${#PROCS[@]} -eq 0 ]]; then
  echo "ERROR: no files matching ${INDIR}/${PREFIX}_*.root" >&2
  exit 2
fi

echo "[merge_hists] prefix=${PREFIX}  processes found: ${!PROCS[*]}"

for proc in "${!PROCS[@]}"; do
  # inputs for this process: prefix_proc_<jobN>.root and/or prefix_proc.root
  inputs=( "$INDIR/${PREFIX}_${proc}"_*.root )
  # also include an exact prefix_proc.root if it exists (no jobN)
  if [[ -f "$INDIR/${PREFIX}_${proc}.root" ]]; then
    inputs+=( "$INDIR/${PREFIX}_${proc}.root" )
  fi
  # filter out non-existent globs
  real_inputs=()
  for x in "${inputs[@]}"; do [[ -f "$x" ]] && real_inputs+=( "$x" ); done
  if [[ ${#real_inputs[@]} -eq 0 ]]; then
    echo "[merge_hists]   ${proc}: no input files, skipping"
    continue
  fi
  out="$OUTDIR/${PREFIX}_${proc}.root"
  echo "[merge_hists]   ${proc}: ${#real_inputs[@]} file(s) -> ${out}"
  hadd -f "$out" "${real_inputs[@]}" >/dev/null
done

echo "[merge_hists] done.  Merged files in: $OUTDIR"
