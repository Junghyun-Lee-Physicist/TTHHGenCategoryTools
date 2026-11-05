#!/bin/bash
# =============================================================================
#  test_extract_format2.sh -- extractTtbarIdPatch format 2 (--input: the key holds the NanoAOD dataset) on
#  synthetic extend files, and format 1 (--filelist) against the tool before format 2.
#  (2026-11-05, TTHHAnalyzer STEP 45; docs/07_analyzer_integration.md section 5)
#
#    /bin/bash Validation/tests/test_extract_format2.sh <extractTtbarIdPatch> [--old <the tool before format 2>] [--keep]
#
#  Needs ROOT ('root' on PATH: the macros make_sidecar.C and dump_lookup.C next to this script); no PyROOT.
#  <the tool before format 2> (for the byte-for-byte check of format 1), e.g. from git:
#      git show 25c07a7:Validation/tools/extractTtbarIdPatch.cc > /tmp/extract_old.cc
#      g++ -std=c++17 -O2 $(root-config --cflags) /tmp/extract_old.cc -o /tmp/extract_old $(root-config --libs)
#  Without --old that part says SKIP; the rest runs.
#  What it holds:
#   1. two inputs of one dataset (MiniAODv4 priority 0, MiniAODv3 priority 1) with keys in both: the v4 row is kept
#      (its nAddBJetsMulti), a key only in v3 is kept from v3, a non-tt+nb key in both is not written; the same when
#      v4 is the smaller input (held in memory) and when v3 comes first on the command line
#   2. two datasets with the same key and different categories: both rows, each with its datasetIdx
#   3. a dataset with no tt+nb row is in nano_datasets; nano_datasets sorted; lookup_format; the sources table (the
#      entries per input and per dataset); rows sorted by (datasetIdx, run, lumi, event); the tree, its 8 leaves
#   4. a disagreement between two inputs (Expanded_genTtbarId; genTtbarId; a v4 row that is not tt+nb against a v3 row
#      that is) stops with exit 8 and writes nothing; --on-conflict report: exit 0, RESULT WARN, the v4 row kept
#   5. one key twice in ONE input, the input STREAMED (the largest of its dataset) and HELD (a larger input of the
#      dataset is streamed): two tt+nb rows of different categories, a tt+nb row against a non-tt+nb row, and two
#      non-tt+nb rows of different genTtbarId -> exit 8 in both places; equal rows -> one row (WARN) in both places
#   6. the entries: an input with 0 entries -> exit 6; --expect right -> OK, wrong -> exit 6, of a dataset no --input
#      names or given twice -> exit 2
#   7. the output: an existing --out without --replace -> exit 4, the file untouched; with --replace -> replaced; with
#      --replace and a failure (a conflict) -> exit 8, the old file untouched, no temporary file left
#   8. one sidecar file twice: in two inputs through other spellings ('..', '//', a symlink) and twice in one input ->
#      exit 2; a filelist named '<name>:<digits>' when '<name>' is no file -> exit 2
#   9. bad usage (exit 2), an empty or missing filelist (3), a missing file / no tree / no branch (5), a selection
#      inconsistency (7) -- every failing run ends with 'RESULT FAIL ... (exit N)' of its own code, and writes nothing
#  10. format 1 (--filelist): md5 of the output (ROOT's ?reproducible= mode: no time stamps, a fixed UUID), stdout
#      and exit code = the tool before format 2 (exit 0, exit 7 on a selection inconsistency, exit 3); a control:
#      the old tool twice gives one md5 (else the md5 part is SKIP and the files are compared by their dump)
#  Lines: CHECK <name> PASS|FAIL; the last line RESULT OK|FAIL <n> PASS, <m> FAIL. Exit 0 all pass, 1 a FAIL, 2 bad usage.
# =============================================================================
set -u
NEW=""; OLD=""; KEEP=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --old) OLD="$2"; shift ;;
    --keep) KEEP=1 ;;
    -h|--help) sed -n '3,40p' "$0" | sed 's/^# \{0,2\}//'; exit 0 ;;
    *) [[ -z "$NEW" ]] && NEW="$1" || { echo "ERROR unknown argument $1"; exit 2; } ;;
  esac
  shift
done
[[ -n "$NEW" && -x "$NEW" ]] || { echo "ERROR usage: $0 <extractTtbarIdPatch> [--old <tool before format 2>] [--keep]"; exit 2; }
[[ -z "$OLD" || -x "$OLD" ]] || { echo "ERROR --old $OLD is not an executable"; exit 2; }
command -v root > /dev/null 2>&1 || { echo "ERROR no 'root' on PATH (set up ROOT first)"; exit 2; }
NEW="$(cd "$(dirname "$NEW")" && pwd -P)/$(basename "$NEW")"
[[ -n "$OLD" ]] && OLD="$(cd "$(dirname "$OLD")" && pwd -P)/$(basename "$OLD")"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
W="$(mktemp -d "${TMPDIR:-/tmp}/extract_format2.XXXXXX")" || exit 2
W="$(cd "$W" && pwd -P)"
echo "WORK $W"
[[ $KEEP -eq 1 ]] || trap 'rm -rf "$W"' EXIT
NPASS=0; NFAIL=0
check() { if [[ "$2" == 1 ]]; then echo "CHECK $1 PASS"; NPASS=$((NPASS+1)); else echo "CHECK $1 FAIL ${3:-}"; NFAIL=$((NFAIL+1)); fi; }
mk() {     # name, then the rows (one argument per row): $W/<name>.root, tree Events
  local name="$1"; shift
  if [[ $# -gt 0 ]]; then printf '%s\n' "$@" > "$W/$name.tsv"; else : > "$W/$name.tsv"; fi
  root -l -b -q "$HERE/make_sidecar.C(\"$W/$name.tsv\",\"$W/$name.root\",\"Events\",${DROPMULTI:-0})" > "$W/$name.mk.log" 2>&1 \
    || { echo "ERROR make_sidecar.C $name"; cat "$W/$name.mk.log"; exit 2; }
}
fl() {     # filelist name, then the sidecar names
  local name="$1"; shift
  : > "$W/$name"
  for s in "$@"; do echo "$W/$s.root" >> "$W/$name"; done
}
dump() {   # file [tree]: the dump lines
  root -l -b -q "$HERE/dump_lookup.C(\"$1\",\"${2:-TtNb}\")" 2>/dev/null | grep -E '^(NAMED|NONAMED|LINE|END|TREE|LEAF|ROW|DUMPFAIL) ?'
}
rows() { dump "$@" | grep '^ROW '; }
run2() {   # tag, then the tool's arguments: $W/<tag>.log, $W/<tag>.rc (format 2 runs write $W/<tag>.root)
  local tag="$1"; shift
  ( cd "$W" && "$NEW" "$@" ) > "$W/$tag.log" 2>&1
  echo $? > "$W/$tag.rc"
}
failed() {  # tag code: exit <code>, the last line 'RESULT FAIL ... (exit <code>)', no file out_<tag>.root, no temporary file
  local rc last
  rc="$(cat "$W/$1.rc")"; last="$(tail -n 1 "$W/$1.log")"
  [[ "$rc" == "$2" && "$last" == "RESULT FAIL extractTtbarIdPatch format 2: "*" (exit $2)" && ! -e "$W/out_$1.root" ]] && \
    ! ls "$W"/*.tmp.* > /dev/null 2>&1
}

DA=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM
DB=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2/NANOAODSIM
DC=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext2-v1/NANOAODSIM

# ---- the synthetic extend files: run lumi event genTtbarId Expanded_genTtbarId nAddBJets nAddBJetsMulti ----------
mk a_v4_1 "1 1 101 53 61 3 3" "1 1 102 55 55 2 2" "1 1 103 54 72 4 5"
mk a_v4_2 "1 2 201 0 0 0 0" "1 2 202 53 62 3 4"
mk a_v3_1 "1 1 101 53 61 3 4" "1 1 102 55 55 2 2" "1 3 301 54 71 4 4" "1 3 302 51 51 0 0"
mk b_v4_1 "1 2 202 54 71 4 4" "1 1 101 53 62 3 3" "1 4 401 0 0 0 0"
mk c_v4_1 "1 5 501 0 0 0 0" "1 5 502 41 41 0 0"
mk a_v4s "1 1 101 53 61 3 3" "1 1 102 55 55 2 2"                        # v4 smaller than v3 (held in memory)
mk a_v3_exp "1 1 101 53 62 3 3" "1 3 301 54 71 4 4"                     # 101: Expanded 62, v4 says 61
mk a_v3_gen "1 1 101 54 61 3 3" "1 3 301 54 71 4 4"                     # 101: genTtbarId 54, v4 says 53
mk a_v3_cat "1 1 102 55 61 3 3" "1 3 301 54 71 4 4"                     # 102: tt+nb in v3, 55 (not tt+nb) in v4
mk d_dup "1 1 101 53 61 3 3" "1 1 101 53 61 3 3" "1 1 105 53 62 3 3"     # one key twice, equal
mk d_dupx "1 1 101 53 61 3 3" "1 1 101 53 62 3 3"                       # one key twice: two tt+nb categories
mk d_dupc "1 1 101 53 61 3 3" "1 1 101 53 53 2 2"                       # one key twice: tt+nb and not tt+nb
mk d_dupn "1 1 101 53 53 2 2" "1 1 101 54 54 2 2"                       # one key twice: two non-tt+nb genTtbarId
mk big6 "1 9 901 0 0 0 0" "1 9 902 0 0 0 0" "1 9 903 0 0 0 0" "1 9 904 0 0 0 0" "1 9 905 53 61 3 3" "1 9 906 0 0 0 0"
mk zero                                                                 # a file of 0 entries
mk bad7 "1 1 101 53 61 2 2" "1 1 102 55 55 2 2"                         # Expanded 61 with nAddBJets 2 (exit 7)
mk notree_src "1 1 101 53 61 3 3"
root -l -b -q -e "TFile f(\"$W/notree.root\",\"RECREATE\"); TNamed n(\"x\",\"y\"); n.Write(); f.Close();" > /dev/null 2>&1
DROPMULTI=1 mk nomulti "1 1 101 53 61 3 3"
fl a_v4.txt a_v4_1 a_v4_2; fl a_v3.txt a_v3_1; fl b_v4.txt b_v4_1; fl c_v4.txt c_v4_1; fl a_v4s.txt a_v4s
fl a_v3_exp.txt a_v3_exp; fl a_v3_gen.txt a_v3_gen; fl a_v3_cat.txt a_v3_cat; fl d_dup.txt d_dup; fl d_dupx.txt d_dupx
fl d_dupc.txt d_dupc; fl d_dupn.txt d_dupn; fl big6.txt big6; fl zero.txt zero
fl bad7.txt bad7; fl notree.txt notree; fl nomulti.txt nomulti; : > "$W/empty.txt"
echo "$W/does_not_exist.root" > "$W/missing.txt"

# ---- 1-3: the main case ----------------------------------------------------------------------------------------
run2 main --input "$DA=a_v4.txt:0" --input "$DA=a_v3.txt:1" --input "$DB=b_v4.txt" --input "$DC=c_v4.txt:0" \
  --expect "$DA=9" --expect "$DB=3" --out ttnb_main.root --out-tree TtNb --label TTbar_Hadronic_2022_A
printf '%s\n' "ROW 0 1 1 101 53 61 3 3" "ROW 0 1 1 103 54 72 4 5" "ROW 0 1 2 202 53 62 3 4" "ROW 0 1 3 301 54 71 4 4" \
  "ROW 1 1 1 101 53 62 3 3" "ROW 1 1 2 202 54 71 4 4" > "$W/main.want"
dump "$W/ttnb_main.root" > "$W/main.dump"
grep '^ROW ' "$W/main.dump" > "$W/main.rows"
check "format 2: exit 0 and 'RESULT OK ... format 2: 6 rows, 3 dataset(s), 4 input(s), 14 entries, 2 shared key(s), 0 repeated row(s) in one input, 0 conflict(s)' (two --expect right)" \
  "$([[ $(cat "$W/main.rc") == 0 ]] && grep -q '^RESULT OK extractTtbarIdPatch format 2: 6 rows, 3 dataset(s), 4 input(s), 14 entries, 2 shared key(s), 0 repeated row(s) in one input, 0 conflict(s)' "$W/main.log" && echo 1)" "($W/main.log)"
check "format 2: the rows = the expected six (v4's 101 with nAddBJetsMulti 3 over v3's 4; v3-only 301; 102 in both but not tt+nb: none; A's 202 = 62 and B's 202 = 71, A's 101 = 61 and B's 101 = 62: both, each with its datasetIdx; sorted)" \
  "$(diff -q "$W/main.want" "$W/main.rows" > /dev/null && echo 1)" "($(tr '\n' ';' < "$W/main.rows"))"
check "format 2: TNamed lookup_format = tthh-ttnb/2" \
  "$(awk '/^NAMED lookup_format/{f=1;next} f&&/^LINE /{print;f=0}' "$W/main.dump" | grep -qx 'LINE tthh-ttnb/2' && echo 1)"
check "format 2: TNamed nano_datasets = the three datasets sorted, the one without a tt+nb row (ext2) included" \
  "$([[ "$(awk '/^NAMED nano_datasets/{f=1;next} /^END/{f=0} f' "$W/main.dump" | tr '\n' '|')" == "LINE $DA|LINE $DB|LINE $DC|" ]] && echo 1)"
check "format 2: the tree TtNb with the 7 branches of format 1 and datasetIdx/I" \
  "$([[ "$(grep -E '^(TREE|LEAF) ' "$W/main.dump" | tr '\n' '|')" == "TREE TtNb 6|LEAF run UInt_t|LEAF luminosityBlock UInt_t|LEAF event ULong64_t|LEAF genTtbarId Int_t|LEAF Expanded_genTtbarId Int_t|LEAF nAddBJets Int_t|LEAF nAddBJetsMulti Int_t|LEAF datasetIdx Int_t|" ]] && echo 1)"
check "format 2: TNamed sources: one line per input (dataset index, priority, files, entries, rows superseded, tt+nb rows written), the entries per dataset with their --expect, the counts" \
  "$(grep -q "^LINE 0	$DA	0	a_v4.txt	2	5	0	3$" "$W/main.dump" && grep -q "^LINE 0	$DA	1	a_v3.txt	1	4	2	1$" "$W/main.dump" && grep -q "^LINE 1	$DB	0	b_v4.txt	1	3	0	2$" "$W/main.dump" && grep -q "^LINE 2	$DC	0	c_v4.txt	1	2	0	0$" "$W/main.dump" && grep -q '^LINE # entries per dataset: \[0\] 9 (--expect 9), \[1\] 3 (--expect 3), \[2\] 2 (no --expect)$' "$W/main.dump" && grep -q '^LINE # keys in two or more inputs of one dataset 2, repeated rows of a key in one input 0, conflicts 0' "$W/main.dump" && echo 1)"
check "format 2: the log has the input table with the entries (per dataset with --expect OK, per input) first, progress with elapsed / ETA, the per-dataset lines" \
  "$(grep -q '^\[extractTtbarIdPatch\]   3 NanoAOD dataset(s) (datasetIdx = the line in nano_datasets), 4 input(s), 14 entries in all' "$W/main.log" && grep -q "^\[extractTtbarIdPatch\]   \[0\] $DA: 9 entries, --expect 9: OK$" "$W/main.log" && grep -q '^\[extractTtbarIdPatch\]        priority 1  a_v3.txt: 1 file(s), 4 entries$' "$W/main.log" && grep -q 'scanned 14 / 14 (100.0 %), elapsed' "$W/main.log" && grep -q "^\[extractTtbarIdPatch\] dataset \[0\] $DA: 2 input(s); held in memory: 4 rows of 1 input(s)" "$W/main.log" && echo 1)" "($W/main.log)"
run2 small --input "$DA=a_v4s.txt:0" --input "$DA=a_v3.txt:1" --out ttnb_small.root --out-tree TtNb
check "format 2: v4 wins also when it is the smaller input (held in memory, v3 streamed): 101 with v4's nAddBJetsMulti 3, v3-only 301" \
  "$([[ $(cat "$W/small.rc") == 0 && "$(rows "$W/ttnb_small.root" | tr '\n' '|')" == "ROW 0 1 1 101 53 61 3 3|ROW 0 1 3 301 54 71 4 4|" ]] && grep -q 'streamed: a_v3.txt (4 entries' "$W/small.log" && echo 1)" "($W/small.log)"
run2 order --input "$DC=c_v4.txt" --input "$DA=a_v3.txt:1" --input "$DB=b_v4.txt:0" --input "$DA=a_v4.txt:0" \
  --out ttnb_order.root --out-tree TtNb
check "format 2: the priority decides, not the order of --input (v3 first on the command line): the same rows" \
  "$([[ $(cat "$W/order.rc") == 0 ]] && rows "$W/ttnb_order.root" | diff -q - "$W/main.want" > /dev/null && echo 1)" "($W/order.log)"

# ---- 4: conflicts between inputs ------------------------------------------------------------------------------------
for c in exp gen cat; do
  run2 conf_$c --input "$DA=a_v4.txt:0" --input "$DA=a_v3_$c.txt:1" --out out_conf_$c.root --out-tree TtNb
done
check "format 2: two inputs of one dataset disagree -- Expanded_genTtbarId (61 vs 62), genTtbarId (53 vs 54), or a non-tt+nb v4 row (55) against a tt+nb v3 row (61): exit 8, a CONFLICT line, RESULT FAIL, no output" \
  "$(for c in exp gen cat; do failed conf_$c 8 && grep -q '^\[extractTtbarIdPatch\]   CONFLICT dataset ' "$W/conf_$c.log" || exit 1; done; echo 1)" \
  "(exits $(cat "$W/conf_exp.rc") $(cat "$W/conf_gen.rc") $(cat "$W/conf_cat.rc"))"
run2 report --input "$DA=a_v4.txt:0" --input "$DA=a_v3_exp.txt:1" --on-conflict report --out ttnb_report.root --out-tree TtNb
check "format 2: --on-conflict report: exit 0, RESULT WARN with 1 conflict, v4's row (61) kept, the count in sources" \
  "$([[ $(cat "$W/report.rc") == 0 ]] && grep -q '^RESULT WARN extractTtbarIdPatch format 2: .* 1 conflict(s) (--on-conflict report' "$W/report.log" && rows "$W/ttnb_report.root" | grep -qx 'ROW 0 1 1 101 53 61 3 3' && dump "$W/ttnb_report.root" | grep -q '^LINE # keys in two or more inputs of one dataset 1, repeated rows of a key in one input 0, conflicts 1' && echo 1)" "($W/report.log)"

# ---- 5: one key twice in ONE input, streamed and held --------------------------------------------------------------
for c in dupx dupc dupn; do
  run2 s_$c --input "$DA=d_$c.txt" --out out_s_$c.root --out-tree TtNb                                   # streamed (alone)
  run2 h_$c --input "$DA=d_$c.txt:0" --input "$DA=big6.txt:1" --out out_h_$c.root --out-tree TtNb      # held (big6 streamed)
done
w5=1
for c in dupx dupc dupn; do
  failed s_$c 8 && grep -q 'CONFLICT .* twice in one input' "$W/s_$c.log" && grep -q 'may repeat in d_'"$c"'.txt (Bloom filter): reading it again' "$W/s_$c.log" || { w5=0; echo "  streamed $c: exit $(cat "$W/s_$c.rc")"; }
  failed h_$c 8 && grep -q 'CONFLICT .* twice in one input' "$W/h_$c.log" && grep -q 'streamed: big6.txt' "$W/h_$c.log" || { w5=0; echo "  held $c: exit $(cat "$W/h_$c.rc")"; }
done
check "format 2: one key twice in ONE input -- two tt+nb categories, tt+nb against not tt+nb, two non-tt+nb genTtbarId: exit 8 (a CONFLICT 'twice in one input' line, RESULT FAIL, no output) both when the input is STREAMED (the Bloom filter's second pass) and when it is HELD" "$w5"
run2 s_dup --input "$DA=d_dup.txt" --out s_dup.root --out-tree TtNb
run2 h_dup --input "$DA=d_dup.txt:0" --input "$DA=big6.txt:1" --out h_dup.root --out-tree TtNb
check "format 2: one key twice in one input with equal rows: one row and a WARN line, streamed and held" \
  "$([[ $(cat "$W/s_dup.rc") == 0 && $(cat "$W/h_dup.rc") == 0 && "$(rows "$W/s_dup.root" | tr '\n' '|')" == "ROW 0 1 1 101 53 61 3 3|ROW 0 1 1 105 53 62 3 3|" && "$(rows "$W/h_dup.root" | tr '\n' '|')" == "ROW 0 1 1 101 53 61 3 3|ROW 0 1 1 105 53 62 3 3|ROW 0 1 9 905 53 61 3 3|" ]] && grep -q 'WARN: 1 repeated row(s) of a key inside one input' "$W/s_dup.log" && grep -q 'WARN: 1 repeated row(s) of a key inside one input' "$W/h_dup.log" && echo 1)" "($W/s_dup.log $W/h_dup.log)"

# ---- 6: the entries -----------------------------------------------------------------------------------------------
run2 zero --input "$DA=a_v4.txt" --input "$DB=zero.txt" --out out_zero.root --out-tree TtNb
run2 xbad --input "$DA=a_v4.txt" --input "$DA=a_v3.txt:1" --expect "$DA=10" --out out_xbad.root --out-tree TtNb
check "format 2: an input with 0 entries (the table says NO ENTRY) and a dataset whose entries are not its --expect (9 against 10): exit 6, RESULT FAIL, no output" \
  "$(failed zero 6 && grep -q 'priority 0  zero.txt: 1 file(s), 0 entries  <- NO ENTRY' "$W/zero.log" && failed xbad 6 && grep -q -- "\[0\] $DA: 9 entries, --expect 10: DIFFERENT" "$W/xbad.log" && echo 1)" \
  "(exits $(cat "$W/zero.rc") $(cat "$W/xbad.rc"))"
run2 xunk --input "$DA=a_v4.txt" --expect "$DB=3" --out out_xunk.root
run2 xtwice --input "$DA=a_v4.txt" --expect "$DA=5" --expect "$DA=5" --out out_xtwice.root
check "format 2: --expect of a dataset no --input names, or given twice: exit 2" \
  "$(failed xunk 2 && failed xtwice 2 && echo 1)" "(exits $(cat "$W/xunk.rc") $(cat "$W/xtwice.rc"))"

# ---- 7: the output: --replace, the temporary file ----------------------------------------------------------------
cp "$W/ttnb_small.root" "$W/keep.root"
k0="$(cksum < "$W/keep.root")"
run2 nrep --input "$DA=a_v4.txt" --out keep.root --out-tree TtNb
o1=0; [[ "$(cat "$W/nrep.rc")" == 4 && "$(tail -n 1 "$W/nrep.log")" == *"keep.root exists: --replace to replace it"*"(exit 4)" && "$(cksum < "$W/keep.root")" == "$k0" ]] && o1=1
run2 yrepf --input "$DA=d_dupx.txt" --replace --out keep.root --out-tree TtNb
o2=0; [[ "$(cat "$W/yrepf.rc")" == 8 && "$(cksum < "$W/keep.root")" == "$k0" ]] && ! ls "$W"/keep.root.tmp.* > /dev/null 2>&1 && o2=1
run2 yrep --input "$DA=a_v4.txt" --replace --out keep.root --out-tree TtNb
o3=0; [[ "$(cat "$W/yrep.rc")" == 0 && "$(cksum < "$W/keep.root")" != "$k0" && "$(rows "$W/keep.root" | wc -l | tr -d ' ')" == 3 ]] && ! ls "$W"/keep.root.tmp.* > /dev/null 2>&1 && o3=1
run2 nodir --input "$DA=a_v4.txt" --out no_such_dir/x.root --out-tree TtNb
o4=0; [[ "$(cat "$W/nodir.rc")" == 4 && "$(tail -n 1 "$W/nodir.log")" == "RESULT FAIL"*"(exit 4)" ]] && o4=1
check "format 2: --out exists without --replace: exit 4, the file untouched; --replace and a failure (a conflict): exit 8, the old file untouched, no temporary file; --replace: replaced (3 rows), no temporary file; a directory that does not exist: exit 4 before any input is read ($o1 $o2 $o3 $o4)" \
  "$([[ "$o1$o2$o3$o4" == 1111 ]] && echo 1)"

# ---- 8: one sidecar file twice --------------------------------------------------------------------------------------
mkdir -p "$W/sub"; ln -s "$W/a_v4_1.root" "$W/sub/link.root"
echo "$W/sub/../a_v4_1.root" > "$W/sp_dotdot.txt"; echo "${W}//a_v4_1.root" > "$W/sp_slash.txt"; echo "$W/sub/link.root" > "$W/sp_link.txt"
printf '%s\n' "$W/a_v4_1.root" "$W/a_v4_2.root" "$W/a_v4_1.root" > "$W/sp_twice.txt"
for c in dotdot slash link; do run2 sp_$c --input "$DA=a_v4.txt" --input "$DB=sp_$c.txt" --out out_sp_$c.root; done
run2 sp_twice --input "$DA=sp_twice.txt" --out out_sp_twice.root
cp "$W/a_v4.txt" "$W/odd:12"
run2 colon --input "$DA=odd:12" --out out_colon.root
check "format 2: one sidecar file in two inputs through '..', '//' or a symlink, or twice in one input: exit 2 ('the sidecar file ... is in --input ... and --input ...' / 'twice in --input'); a filelist named 'odd:12' with no file 'odd': exit 2 (rename it)" \
  "$(failed sp_dotdot 2 && failed sp_slash 2 && failed sp_link 2 && failed sp_twice 2 && grep -q "the sidecar file $W/a_v4_1.root is in --input a_v4.txt and --input sp_link.txt" "$W/sp_link.log" && grep -q 'is twice in --input sp_twice.txt' "$W/sp_twice.log" && failed colon 2 && grep -q 'rename the filelist' "$W/colon.log" && echo 1)" \
  "(exits $(cat "$W/sp_dotdot.rc") $(cat "$W/sp_slash.rc") $(cat "$W/sp_link.rc") $(cat "$W/sp_twice.rc") $(cat "$W/colon.rc"))"

# ---- 9: usage and inputs: every failing run ends with its RESULT FAIL line ---------------------------------------
u_ok=1
for args in "--input a_v4.txt --out x.root" "--input /A/B/MINIAODSIM=a_v4.txt --out x.root" "--input $DA= --out x.root" \
            "--input $DA=a_v4.txt --input $DB=a_v4.txt --out x.root" "--filelist a_v4.txt --input $DA=a_v4.txt --out x.root" \
            "--input $DA=a_v4.txt --on-conflict maybe --out x.root" "--input $DA=a_v4.txt:1234567 --out x.root" \
            "--input $DA=a_v4.txt --bogus --out x.root" "--input $DA=a_v4.txt" "--input $DA=a_v4.txt --out root://h//x.root"; do
  # shellcheck disable=SC2086
  run2 usage $args
  failed usage 2 && [[ ! -e "$W/x.root" ]] || { u_ok=0; echo "  usage case '$args': exit $(cat "$W/usage.rc"): $(tail -n 1 "$W/usage.log")"; }
done
check "format 2: bad usage exits 2 with a RESULT FAIL line (no '=', not NANOAODSIM, no filelist, one filelist for two datasets, --filelist with --input, --on-conflict not stop|report, a priority of 7 digits, an unknown argument, no --out, a remote --out)" "$u_ok"
run2 empty --input "$DA=empty.txt" --out out_empty.root
run2 missing --input "$DA=missing.txt" --out out_missing.root
run2 notree --input "$DA=notree.txt" --out out_notree.root
run2 nomulti --input "$DA=nomulti.txt" --out out_nomulti.root
run2 nofl --input "$DA=no_such_filelist.txt" --out out_nofl.root
check "format 2: an empty filelist and a filelist that does not exist exit 3; a file that does not exist, a file without the tree, a file without nAddBJetsMulti exit 5 -- each with its RESULT FAIL line, no output" \
  "$(failed empty 3 && failed nofl 3 && failed missing 5 && failed notree 5 && failed nomulti 5 && echo 1)" \
  "(exits $(cat "$W/empty.rc") $(cat "$W/nofl.rc") $(cat "$W/missing.rc") $(cat "$W/notree.rc") $(cat "$W/nomulti.rc"))"
run2 bad7 --input "$DA=bad7.txt" --out out_bad7.root
check "format 2: a selection inconsistency (Expanded 61 with nAddBJets 2) exits 7 with its RESULT FAIL line and writes nothing" \
  "$(failed bad7 7 && echo 1)" "($W/bad7.log)"

# ---- 10: format 1 = the tool before format 2 ---------------------------------------------------------------------
if [[ -z "$OLD" ]]; then
  echo "CHECK format 1 = the tool before format 2 SKIP (no --old)"
else
  mkdir -p "$W/f1old" "$W/f1new" "$W/f1ctl"
  for d in f1old f1new f1ctl; do cp "$W"/*.txt "$W/$d/" 2>/dev/null; done
  f1() {   # dir tool tag, then the arguments: <dir>/<tag>.out (stdout and stderr), <dir>/<tag>.rc
    local d="$1" tool="$2" tag="$3"; shift 3
    ( cd "$W/$d" && "$tool" "$@" ) > "$W/$d/$tag.out" 2>&1; echo $? > "$W/$d/$tag.rc"
  }
  REPRO=1
  f1 f1old "$OLD" ctl1 --filelist a_v4.txt --out "ttnb_c.root?reproducible=ttnb" --out-tree TtNb --label c
  f1 f1ctl "$OLD" ctl2 --filelist a_v4.txt --out "ttnb_c.root?reproducible=ttnb" --out-tree TtNb --label c
  md5of() { if command -v md5sum > /dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }
  if [[ "$(md5of "$W/f1old/ttnb_c.root")" != "$(md5of "$W/f1ctl/ttnb_c.root")" ]]; then
    REPRO=0; echo "NOTE ROOT's ?reproducible= mode does not give one md5 here: the format-1 files are compared by their dump"
  fi
  f1_ok=1
  for spec in "a:--filelist a_v4.txt --out ttnb_a.root?reproducible=ttnb --out-tree TtNb --label TTbar_Hadronic" \
              "b:--filelist a_v3.txt --out ttbarIdPatch_b.root?reproducible=ttnb --label b" \
              "c:--label c --tree Events --filelist b_v4.txt --out ttnb_cc.root?reproducible=ttnb --out-tree TtNb" \
              "d:--filelist d_dup.txt --out ttnb_d.root?reproducible=ttnb --out-tree TtNb" \
              "e:--filelist bad7.txt --out ttnb_e.root?reproducible=ttnb --out-tree TtNb" \
              "f:--filelist empty.txt --out ttnb_f.root?reproducible=ttnb --out-tree TtNb"; do
    tag="${spec%%:*}"; args="${spec#*:}"
    set -f   # the '?' of ?reproducible= is not a glob here
    # shellcheck disable=SC2086
    f1 f1old "$OLD" "$tag" $args
    # shellcheck disable=SC2086
    f1 f1new "$NEW" "$tag" $args
    set +f
    out="$(sed -E 's/^.*--out ([^ ?]*).*$/\1/' <<< "$args")"
    same_out=1
    cmp -s "$W/f1old/$tag.out" "$W/f1new/$tag.out" || same_out=0
    same_rc=1; [[ "$(cat "$W/f1old/$tag.rc")" == "$(cat "$W/f1new/$tag.rc")" ]] || same_rc=0
    same_file=1
    if [[ -e "$W/f1old/$out" || -e "$W/f1new/$out" ]]; then
      if [[ $REPRO == 1 ]]; then
        [[ "$(md5of "$W/f1old/$out")" == "$(md5of "$W/f1new/$out")" ]] || same_file=0
      else
        tr="TtNb"; [[ "$args" == *"--out-tree TtNb"* ]] || tr="TtbarIdPatch"
        [[ "$(dump "$W/f1old/$out" "$tr")" == "$(dump "$W/f1new/$out" "$tr")" ]] || same_file=0
      fi
    fi
    echo "  format 1 case $tag (exit $(cat "$W/f1new/$tag.rc")): stdout same $same_out, exit same $same_rc, output same $same_file ($out)"
    [[ $same_out == 1 && $same_rc == 1 && $same_file == 1 ]] || f1_ok=0
  done
  check "format 1 (--filelist) = the tool before format 2: stdout + stderr, exit code (0, 0, 0, 0 with a key twice, 7, 3) and the output file ($([[ $REPRO == 1 ]] && echo "md5, ROOT reproducible mode" || echo "dump"))" "$f1_ok"
  check "format 1: no format-2 objects in its output (no lookup_format, no nano_datasets, no datasetIdx)" \
    "$(dump "$W/f1new/ttnb_a.root" | grep -q '^NONAMED lookup_format' && dump "$W/f1new/ttnb_a.root" | grep -q '^NONAMED nano_datasets' && ! dump "$W/f1new/ttnb_a.root" | grep -q '^LEAF datasetIdx' && echo 1)"
fi

echo "RESULT $([[ $NFAIL -eq 0 ]] && echo OK || echo FAIL) test_extract_format2: $NPASS PASS, $NFAIL FAIL"
[[ $NFAIL -eq 0 ]]
