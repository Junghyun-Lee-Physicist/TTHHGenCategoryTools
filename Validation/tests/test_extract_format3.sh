#!/bin/bash
# =============================================================================
#  test_extract_format3.sh -- extractTtbarIdPatch format 3 (--input whose sidecars have the event fingerprint:
#  Generator_x1/F Generator_x2/F Generator_id1/I Generator_id2/I) on synthetic extend files; format 2 and format 1 of
#  the same tool against the tool before format 3. (2026-11-05, TTHHAnalyzer STEP 46; docs/07_analyzer_integration.md
#  section 5)
#
#    /bin/bash Validation/tests/test_extract_format3.sh <extractTtbarIdPatch> [--old <the tool before format 3>] [--keep]
#
#  Needs ROOT ('root' on PATH: make_sidecar.C and dump_lookup.C next to this script); no PyROOT. <the tool before format
#  3> = the STEP 45 tool (git 12e8011), for the comparison of format 2 (and format 1) runs; without --old that part says
#  SKIP. test_extract_format2.sh keeps testing format 2 and format 1 in full (run it too).
#  What it holds:
#   1. one dataset, v4 (priority 0) and v3 (priority 1), plus ext1: two DIFFERENT events of one key in ONE input (a tt+nb
#      and a non-tt+nb one) -> the tt+nb one written; two different events of one key ACROSS the inputs (both tt+nb) ->
#      both rows; the same event (key and fingerprint) in v4 and v3 -> v4's row (priority); a key with one event held
#      and two others streamed -> counted once among the keys with two or more events; the same key and fingerprint in
#      ext1 -> its own row (its dataset); rows sorted by (datasetIdx, key, fingerprint); the fingerprint as read
#   2. the same rows when v4 is the smaller input (held) and when v3 comes first on the command line
#   3. lookup_format tthh-ttnb/3, the 12 leaves, the sources table with the keys of two or more events per dataset, the
#      log's format and counts, the RESULT line
#   4. the same fingerprint and another genTtbarId / Expanded_genTtbarId: between v4 and v3, and twice in one input
#      (streamed alone, and held next to a larger streamed input) -> exit 8, nothing written
#   5. two different events of one key, one tt+nb, too close for NanoAOD (the same ids, x1 and x2 within 2^-10): in one
#      streamed input, in one held input, between the streamed and the held input -> exit 9, nothing written; just
#      outside (x1 2^-10 apart), other ids, or both not tt+nb -> written (exit 0); --on-conflict report -> exit 0,
#      RESULT WARN, both kept
#   6. two tt+nb events of one key with other categories in one input (streamed and held) -> both rows
#   7. mixed inputs: one input with the fingerprint and one without, a filelist mixing them, a file with only
#      Generator_x1 -> exit 5, nothing written; --expect holds in format 3
#   8. (--old) format 2 runs of this tool = the tool before format 3: the dump (rows, TNamed) and stdout (the elapsed
#      seconds masked); format 1: stdout, exit and the output's md5 (ROOT's ?reproducible= mode)
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
[[ -n "$NEW" && -x "$NEW" ]] || { echo "ERROR usage: $0 <extractTtbarIdPatch> [--old <tool before format 3>] [--keep]"; exit 2; }
[[ -z "$OLD" || -x "$OLD" ]] || { echo "ERROR --old $OLD is not an executable"; exit 2; }
command -v root > /dev/null 2>&1 || { echo "ERROR no 'root' on PATH (set up ROOT first)"; exit 2; }
NEW="$(cd "$(dirname "$NEW")" && pwd -P)/$(basename "$NEW")"
[[ -n "$OLD" ]] && OLD="$(cd "$(dirname "$OLD")" && pwd -P)/$(basename "$OLD")"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
W="$(mktemp -d "${TMPDIR:-/tmp}/extract_format3.XXXXXX")" || exit 2
W="$(cd "$W" && pwd -P)"
echo "WORK $W"
[[ $KEEP -eq 1 ]] || trap 'rm -rf "$W"' EXIT
NPASS=0; NFAIL=0
check() { if [[ "$2" == 1 ]]; then echo "CHECK $1 PASS"; NPASS=$((NPASS+1)); else echo "CHECK $1 FAIL ${3:-}"; NFAIL=$((NFAIL+1)); fi; }
mk() {     # name fpmode, then the rows: $W/<name>.root (fpmode 1: the four branches, 2: only Generator_x1, 0: none)
  local name="$1" fpm="$2"; shift 2
  if [[ $# -gt 0 ]]; then printf '%s\n' "$@" > "$W/$name.tsv"; else : > "$W/$name.tsv"; fi
  root -l -b -q "$HERE/make_sidecar.C(\"$W/$name.tsv\",\"$W/$name.root\",\"Events\",0,$fpm)" > "$W/$name.mk.log" 2>&1 \
    || { echo "ERROR make_sidecar.C $name"; cat "$W/$name.mk.log"; exit 2; }
}
fl() {     # filelist name, then the sidecar names
  local name="$1"; shift
  : > "$W/$name"
  for s in "$@"; do echo "$W/$s.root" >> "$W/$name"; done
}
dump() { root -l -b -q "$HERE/dump_lookup.C(\"$1\",\"${2:-TtNb}\")" 2>/dev/null | grep -E '^(NAMED|NONAMED|LINE|END|TREE|LEAF|ROW|DUMPFAIL) ?'; }
rows() { dump "$@" | grep '^ROW '; }
run3() {   # tag, then the tool's arguments: $W/<tag>.log, $W/<tag>.rc
  local tag="$1"; shift
  ( cd "$W" && "$NEW" "$@" ) > "$W/$tag.log" 2>&1
  echo $? > "$W/$tag.rc"
}
failed() {  # tag code [format]: exit <code>, the last line 'RESULT FAIL ... format <n>: ... (exit <code>)', no out_<tag>.root, no tmp
  local rc last
  rc="$(cat "$W/$1.rc")"; last="$(tail -n 1 "$W/$1.log")"
  [[ "$rc" == "$2" && "$last" == "RESULT FAIL extractTtbarIdPatch format ${3:-3}: "*" (exit $2)" && ! -e "$W/out_$1.root" ]] && \
    ! ls "$W"/*.tmp.* > /dev/null 2>&1
}

DA=/TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6-v2/NANOAODSIM
DB=/TTto2L2Nu_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22EENanoAODv12-130X_mcRun3_2022_realistic_postEE_v6_ext1-v2/NANOAODSIM

# ---- the synthetic sidecars: run lumi event genTtbarId Expanded_genTtbarId nAddBJets nAddBJetsMulti x1 x2 id1 id2 ----
#   key 101: P (tt+nb 61) and Q (not tt+nb) in v4 -- two events, one input; ext1 has P's key and fingerprint (category 62)
#   key 102: R in v4 and v3 with one fingerprint (v4: nAddBJetsMulti 4, v3: 5) -- one event, v4 wins
#   key 202: S (71) in v4, T (72) in v3 -- two tt+nb events across the inputs
#   key 301: only in v3; key 401: A (61) in v3, B and C (not tt+nb) in v4 -- one key, three events
mk v4 1 "1 1 101 53 61 3 3 0.25 0.5 21 21" "1 1 101 53 53 2 2 0.375 0.0625 2 -2" "1 1 102 53 62 3 4 0.125 0.75 1 -1" \
        "1 2 201 0 0 0 0 0.5 0.5 21 21" "1 2 202 54 71 4 4 0.0625 0.25 21 2" "1 4 401 53 53 2 2 0.5 0.5 2 2" \
        "1 4 401 53 54 2 2 0.75 0.75 3 3"
mk v3 1 "1 1 102 53 62 3 5 0.125 0.75 1 -1" "1 2 202 54 72 4 5 0.75 0.125 -1 1" "1 3 301 54 71 4 4 0.5 0.25 21 21" \
        "1 4 401 53 61 3 3 0.25 0.25 1 1"
mk ext1 1 "1 1 101 53 62 3 3 0.25 0.5 21 21" "1 5 501 0 0 0 0 0.5 0.5 21 21"
mk v4s 1 "1 1 101 53 61 3 3 0.25 0.5 21 21" "1 1 102 53 62 3 4 0.125 0.75 1 -1"          # v4 smaller than v3
mk v3big 1 "1 1 101 53 53 2 2 0.375 0.0625 2 -2" "1 1 102 53 62 3 5 0.125 0.75 1 -1" "1 2 202 54 72 4 5 0.75 0.125 -1 1" \
           "1 3 301 54 71 4 4 0.5 0.25 21 21" "1 6 601 0 0 0 0 0.5 0.5 21 21"
mk v3conf 1 "1 1 102 53 61 3 5 0.125 0.75 1 -1"                                            # R's fingerprint, Expanded 61
mk v3gen 1 "1 1 102 54 62 3 5 0.125 0.75 1 -1"                                             # R's fingerprint, genTtbarId 54
mk dupx 1 "1 1 101 53 61 3 3 0.25 0.5 21 21" "1 1 101 53 62 3 3 0.25 0.5 21 21"            # one event twice, two categories
mk two 1 "1 1 101 53 61 3 3 0.25 0.5 21 21" "1 1 101 53 72 4 4 0.75 0.125 21 21"           # two tt+nb events, one key
mk big 1 "1 9 901 0 0 0 0 0.5 0.5 21 21" "1 9 902 0 0 0 0 0.5 0.5 21 21" "1 9 903 0 0 0 0 0.5 0.5 21 21" \
         "1 9 904 0 0 0 0 0.5 0.5 21 21" "1 9 905 53 61 3 3 0.5 0.5 21 21" "1 9 906 0 0 0 0 0.5 0.5 21 21"
#   too close: the same ids, x1 2^-11 apart (0.5 and 0.50048828125), x2 the same; 1 ulp apart; just outside 2^-10
mk close 1 "1 1 101 53 61 3 3 0.5 0.25 21 21" "1 1 101 53 53 2 2 0.50048828125 0.25 21 21"
mk closev4 1 "1 1 101 53 61 3 3 0.5 0.25 21 21" "1 1 102 0 0 0 0 0.5 0.5 21 21" "1 1 103 0 0 0 0 0.5 0.5 21 21"
mk closev3 1 "1 1 101 53 53 2 2 0.50000006 0.25 21 21"
mk apart 1 "1 1 101 53 61 3 3 0.5 0.25 21 21" "1 1 101 53 53 2 2 0.5009765625 0.25 21 21"
mk ids 1 "1 1 101 53 61 3 3 0.5 0.25 21 21" "1 1 101 53 53 2 2 0.5 0.25 21 1"
mk closenn 1 "1 1 101 53 53 2 2 0.5 0.25 21 21" "1 1 101 53 54 2 2 0.50048828125 0.25 21 21"
mk close2 1 "1 1 101 53 61 3 3 0.5 0.25 21 21" "1 1 101 53 71 4 4 0.50048828125 0.25 21 21"
#   mixed: a format-2 sidecar (no fingerprint), a file with only Generator_x1
mk nofp 0 "1 7 701 53 61 3 3"
mk part 2 "1 7 702 53 61 3 3 0.5 0.5 21 21"
fl v4.txt v4; fl v3.txt v3; fl ext1.txt ext1; fl v4s.txt v4s; fl v3big.txt v3big; fl v3conf.txt v3conf
fl v3gen.txt v3gen; fl dupx.txt dupx; fl two.txt two; fl big.txt big; fl close.txt close; fl closev4.txt closev4
fl closev3.txt closev3; fl apart.txt apart; fl ids.txt ids; fl closenn.txt closenn; fl close2.txt close2
fl nofp.txt nofp; fl part.txt part; fl mixfl.txt v4 nofp

# ---- 1-3: the main case --------------------------------------------------------------------------------------------
run3 main --input "$DA=v4.txt:0" --input "$DA=v3.txt:1" --input "$DB=ext1.txt" --expect "$DA=11" --expect "$DB=2" \
  --out ttnb_main.root --out-tree TtNb --label TTbar_DiLep_2022EE_A
printf '%s\n' "ROW 0 1 1 101 53 61 3 3 0.25 0.5 21 21" "ROW 0 1 1 102 53 62 3 4 0.125 0.75 1 -1" \
  "ROW 0 1 2 202 54 71 4 4 0.0625 0.25 21 2" "ROW 0 1 2 202 54 72 4 5 0.75 0.125 -1 1" "ROW 0 1 3 301 54 71 4 4 0.5 0.25 21 21" \
  "ROW 0 1 4 401 53 61 3 3 0.25 0.25 1 1" "ROW 1 1 1 101 53 62 3 3 0.25 0.5 21 21" > "$W/main.want"
dump "$W/ttnb_main.root" > "$W/main.dump"
grep '^ROW ' "$W/main.dump" > "$W/main.rows"
check "format 3: exit 0 and 'RESULT OK ... format 3: 7 rows, 2 dataset(s), 3 input(s), 13 entries, 1 shared event(s), 0 repeated row(s) in one input, 3 key(s) with two or more events, 0 conflict(s), 0 too-close pair(s)' (two --expect right)" \
  "$([[ $(cat "$W/main.rc") == 0 ]] && grep -q '^RESULT OK extractTtbarIdPatch format 3: 7 rows, 2 dataset(s), 3 input(s), 13 entries, 1 shared event(s), 0 repeated row(s) in one input, 3 key(s) with two or more events, 0 conflict(s), 0 too-close pair(s)' "$W/main.log" && echo 1)" "($W/main.log)"
check "format 3: the rows = the expected seven (key 101: P written, Q -- another event of the key in the same input, not tt+nb -- not; 102: v4's row (nAddBJetsMulti 4) over v3's; 202: S of v4 AND T of v3 -- two events; 301 from v3; 401: v3's A, v4's B and C not tt+nb; ext1's 101 with its own datasetIdx; sorted by (dataset, key, fingerprint); the fingerprints as read)" \
  "$(diff -q "$W/main.want" "$W/main.rows" > /dev/null && echo 1)" "($(tr '\n' ';' < "$W/main.rows"))"
check "format 3: TNamed lookup_format = tthh-ttnb/3; nano_datasets the two datasets sorted" \
  "$(awk '/^NAMED lookup_format/{f=1;next} f&&/^LINE /{print;f=0}' "$W/main.dump" | grep -qx 'LINE tthh-ttnb/3' && [[ "$(awk '/^NAMED nano_datasets/{f=1;next} /^END/{f=0} f' "$W/main.dump" | tr '\n' '|')" == "LINE $DA|LINE $DB|" ]] && echo 1)"
check "format 3: the tree TtNb with the 8 branches of format 2 and Generator_x1/F Generator_x2/F Generator_id1/I Generator_id2/I" \
  "$([[ "$(grep -E '^(TREE|LEAF) ' "$W/main.dump" | tr '\n' '|')" == "TREE TtNb 7|LEAF run UInt_t|LEAF luminosityBlock UInt_t|LEAF event ULong64_t|LEAF genTtbarId Int_t|LEAF Expanded_genTtbarId Int_t|LEAF nAddBJets Int_t|LEAF nAddBJetsMulti Int_t|LEAF datasetIdx Int_t|LEAF Generator_x1 Float_t|LEAF Generator_x2 Float_t|LEAF Generator_id1 Int_t|LEAF Generator_id2 Int_t|" ]] && echo 1)"
check "format 3: TNamed sources: one line per input (v3: 1 row superseded, 3 written; v4: 3 written), the keys with two or more events per dataset ([0] 3, [1] 0), the counts" \
  "$(grep -q "^LINE 0	$DA	0	v4.txt	1	7	0	3$" "$W/main.dump" && grep -q "^LINE 0	$DA	1	v3.txt	1	4	1	3$" "$W/main.dump" && grep -q "^LINE 1	$DB	0	ext1.txt	1	2	0	1$" "$W/main.dump" && grep -q '^LINE # keys with two or more distinct events per dataset: \[0\] 3, \[1\] 0$' "$W/main.dump" && grep -q '^LINE # events in two or more inputs of one dataset 1, repeated rows of an event in one input 0, conflicts 0, pairs of events of one key too close 0 (of [0-9]* checked), keys with two or more tt+nb rows 1$' "$W/main.dump" && echo 1)" "($W/main.dump)"
check "format 3: the log names format 3, the second pass of v4 (key 101 twice, 401 twice), the per-dataset line, the summary" \
  "$(grep -q '^\[extractTtbarIdPatch\] start: format 3 (tthh-ttnb/3)' "$W/main.log" && grep -q "may repeat in v4.txt (Bloom filter): reading it again" "$W/main.log" && grep -q "^\[extractTtbarIdPatch\] dataset \[0\] done: 1 event(s) in two or more of its inputs .*; 3 key(s) with two or more distinct events" "$W/main.log" && grep -q '^\[extractTtbarIdPatch\]   keys with two or more distinct events (fingerprints): 3 (\[0\] 3, \[1\] 0); pairs of distinct events of one key (one tt+nb) checked for NanoAOD.s precision: [1-9][0-9]*, too close: 0; keys with two or more tt+nb events written: 1' "$W/main.log" && echo 1)" "($W/main.log)"
run3 small --input "$DA=v4s.txt:0" --input "$DA=v3big.txt:1" --out ttnb_small.root --out-tree TtNb
check "format 3: v4 held (the smaller input), v3 streamed: 101 (P) from v4, Q of v3 another event (not written), 102 v4's row, 202 T, 301 -- and the key 101 counted once" \
  "$([[ $(cat "$W/small.rc") == 0 && "$(rows "$W/ttnb_small.root" | tr '\n' '|')" == "ROW 0 1 1 101 53 61 3 3 0.25 0.5 21 21|ROW 0 1 1 102 53 62 3 4 0.125 0.75 1 -1|ROW 0 1 2 202 54 72 4 5 0.75 0.125 -1 1|ROW 0 1 3 301 54 71 4 4 0.5 0.25 21 21|" ]] && grep -q 'streamed: v3big.txt (5 entries' "$W/small.log" && grep -q ', 1 key(s) with two or more events, 0 conflict' "$W/small.log" && echo 1)" "($W/small.log)"
run3 order --input "$DB=ext1.txt" --input "$DA=v3.txt:1" --input "$DA=v4.txt:0" --out ttnb_order.root --out-tree TtNb
check "format 3: the priority decides, not the order of --input (v3 first): the same rows" \
  "$([[ $(cat "$W/order.rc") == 0 ]] && rows "$W/ttnb_order.root" | diff -q - "$W/main.want" > /dev/null && echo 1)" "($W/order.log)"

# ---- 4: the same event, another category: exit 8 ---------------------------------------------------------------
for c in conf gen; do run3 c8_$c --input "$DA=v4.txt:0" --input "$DA=v3$c.txt:1" --out out_c8_$c.root --out-tree TtNb; done
run3 c8_s --input "$DA=dupx.txt" --out out_c8_s.root --out-tree TtNb
run3 c8_h --input "$DA=dupx.txt:0" --input "$DA=big.txt:1" --out out_c8_h.root --out-tree TtNb
check "format 3: the same key and fingerprint with another Expanded_genTtbarId or genTtbarId -- between v4 and v3, and twice in one input streamed and held: exit 8, a CONFLICT line, RESULT FAIL format 3, nothing written" \
  "$(failed c8_conf 8 && failed c8_gen 8 && failed c8_s 8 && failed c8_h 8 && grep -q 'CONFLICT .* twice in one input' "$W/c8_s.log" && grep -q 'CONFLICT .* twice in one input' "$W/c8_h.log" && grep -q 'streamed: big.txt' "$W/c8_h.log" && echo 1)" \
  "(exits $(cat "$W/c8_conf.rc") $(cat "$W/c8_gen.rc") $(cat "$W/c8_s.rc") $(cat "$W/c8_h.rc"))"

# ---- 5: two events of one key too close for NanoAOD: exit 9 --------------------------------------------------------
run3 c9_s --input "$DA=close.txt" --out out_c9_s.root --out-tree TtNb                                # streamed
run3 c9_h --input "$DA=close.txt:0" --input "$DA=big.txt:1" --out out_c9_h.root --out-tree TtNb      # held
run3 c9_x --input "$DA=closev4.txt:0" --input "$DA=closev3.txt:1" --out out_c9_x.root --out-tree TtNb # streamed vs held (1 ulp)
check "format 3: two events of one key, one tt+nb, the same ids and x1 2^-11 (or 1 ulp) apart -- in one streamed input, in one held input, between the streamed and the held input: exit 9, a TOO CLOSE line, nothing written" \
  "$(failed c9_s 9 && failed c9_h 9 && failed c9_x 9 && grep -q 'TOO CLOSE dataset .* key (run 1, lumi 1, event 101): x1 0.5 x2 0.25 id1 21 id2 21' "$W/c9_s.log" && grep -q 'TOO CLOSE' "$W/c9_h.log" && grep -q 'TOO CLOSE .*x1 0.50000006' "$W/c9_x.log" && echo 1)" \
  "(exits $(cat "$W/c9_s.rc") $(cat "$W/c9_h.rc") $(cat "$W/c9_x.rc"))"
for c in apart ids closenn; do run3 ok_$c --input "$DA=$c.txt" --out ttnb_$c.root --out-tree TtNb; done
check "format 3: x1 2^-10 apart (0.5 / 0.5009765625), other id2, or two close events neither tt+nb: written (exit 0, 1 / 1 / 0 rows)" \
  "$([[ $(cat "$W/ok_apart.rc") == 0 && $(cat "$W/ok_ids.rc") == 0 && $(cat "$W/ok_closenn.rc") == 0 && $(rows "$W/ttnb_apart.root" | wc -l | tr -d ' ') == 1 && $(rows "$W/ttnb_ids.root" | wc -l | tr -d ' ') == 1 && $(rows "$W/ttnb_closenn.root" | wc -l | tr -d ' ') == 0 ]] && echo 1)" \
  "(exits $(cat "$W/ok_apart.rc") $(cat "$W/ok_ids.rc") $(cat "$W/ok_closenn.rc"))"
run3 rep9 --input "$DA=close2.txt" --on-conflict report --out ttnb_rep9.root --out-tree TtNb
check "format 3: --on-conflict report with two close tt+nb events: exit 0, RESULT WARN with 1 too-close pair, both rows" \
  "$([[ $(cat "$W/rep9.rc") == 0 && $(rows "$W/ttnb_rep9.root" | wc -l | tr -d ' ') == 2 ]] && grep -q '^RESULT WARN extractTtbarIdPatch format 3: .* 0 conflict(s), 1 too-close pair(s) (--on-conflict report' "$W/rep9.log" && echo 1)" "($W/rep9.log)"

# ---- 6: two tt+nb events of one key, other categories, one input ---------------------------------------------------
run3 two_s --input "$DA=two.txt" --out ttnb_two_s.root --out-tree TtNb
run3 two_h --input "$DA=two.txt:0" --input "$DA=big.txt:1" --out ttnb_two_h.root --out-tree TtNb
check "format 3: two tt+nb events of one key with other fingerprints and categories (61, 72) in one input, streamed and held: both rows" \
  "$([[ $(cat "$W/two_s.rc") == 0 && $(cat "$W/two_h.rc") == 0 && "$(rows "$W/ttnb_two_s.root" | tr '\n' '|')" == "ROW 0 1 1 101 53 61 3 3 0.25 0.5 21 21|ROW 0 1 1 101 53 72 4 4 0.75 0.125 21 21|" && "$(rows "$W/ttnb_two_h.root" | grep -c ' 1 1 101 ')" == 2 ]] && echo 1)" "($W/two_s.log $W/two_h.log)"

# ---- 7: mixed inputs: exit 5 ----------------------------------------------------------------------------------------
run3 mix --input "$DA=v4.txt" --input "$DB=nofp.txt" --out out_mix.root --out-tree TtNb
run3 mixfl --input "$DA=mixfl.txt" --out out_mixfl.root --out-tree TtNb
run3 part --input "$DA=v4.txt" --input "$DB=part.txt" --out out_part.root --out-tree TtNb
check "format 3: an input with the fingerprint and one without, a filelist mixing them, a file with only Generator_x1: exit 5 ('mix' / 'only some'), nothing written" \
  "$(failed mix 5 2 && failed mixfl 5 2 && failed part 5 2 && grep -q 'mix files with the fingerprint branches' "$W/mix.log" && grep -q 'mix files with the fingerprint branches' "$W/mixfl.log" && grep -q 'only some of the fingerprint branches' "$W/part.log" && echo 1)" \
  "(exits $(cat "$W/mix.rc") $(cat "$W/mixfl.rc") $(cat "$W/part.rc"))"
run3 xbad --input "$DA=v4.txt" --input "$DA=v3.txt:1" --expect "$DA=12" --out out_xbad.root --out-tree TtNb
check "format 3: --expect: a dataset's entries not its --expect (11 against 12): exit 6, RESULT FAIL format 3" "$(failed xbad 6 && echo 1)" "($W/xbad.log)"

# ---- 8: format 2 and format 1 = the tool before format 3 -------------------------------------------------------
if [[ -z "$OLD" ]]; then
  echo "CHECK format 2 and format 1 = the tool before format 3 SKIP (no --old)"
else
  DA2=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5-v2/NANOAODSIM
  DB2=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/Run3Summer22NanoAODv12-130X_mcRun3_2022_realistic_v5_ext1-v2/NANOAODSIM
  mk f2a 0 "1 1 101 53 61 3 3" "1 1 102 55 55 2 2" "1 1 103 54 72 4 5" "1 2 202 53 62 3 4"
  mk f2b 0 "1 1 101 53 61 3 4" "1 3 301 54 71 4 4" "1 1 101 53 61 3 4"
  mk f2c 0 "1 2 202 54 71 4 4" "1 1 101 53 62 3 3"
  mk f2x 0 "1 1 101 53 62 3 3"
  fl f2a.txt f2a; fl f2b.txt f2b; fl f2c.txt f2c; fl f2x.txt f2x
  mkdir -p "$W/o2" "$W/n2"
  for d in o2 n2; do cp "$W"/f2*.txt "$W/$d/"; done
  mask() { sed -E 's/elapsed [0-9]+ s/elapsed N s/g; s/ETA [0-9]+ s/ETA N s/g; s/; [0-9]+ s$/; N s/'; }
  f2_ok=1
  for spec in "a:--input $DA2=f2a.txt:0 --input $DA2=f2b.txt:1 --input $DB2=f2c.txt --expect $DA2=7 --out ttnb_a.root --out-tree TtNb --label a" \
              "b:--input $DA2=f2b.txt --on-conflict report --out ttnb_b.root --out-tree TtNb" \
              "c:--input $DA2=f2a.txt:0 --input $DA2=f2x.txt:1 --out ttnb_c.root --out-tree TtNb" \
              "d:--input $DA2=f2a.txt:0 --input $DA2=f2x.txt:1 --on-conflict report --out ttnb_d.root" \
              "e:--input $DA2=f2a.txt --expect $DA2=5 --out ttnb_e.root"; do
    tag="${spec%%:*}"; args="${spec#*:}"
    # shellcheck disable=SC2086
    ( cd "$W/o2" && "$OLD" $args ) > "$W/o2/$tag.out" 2>&1; echo $? > "$W/o2/$tag.rc"
    # shellcheck disable=SC2086
    ( cd "$W/n2" && "$NEW" $args ) > "$W/n2/$tag.out" 2>&1; echo $? > "$W/n2/$tag.rc"
    out="$(sed -E 's/^.*--out ([^ ]*).*$/\1/' <<< "$args")"
    tr="TtNb"; [[ "$args" == *"--out-tree TtNb"* ]] || tr="TtbarIdPatch"
    s_out=1; [[ "$(mask < "$W/o2/$tag.out")" == "$(mask < "$W/n2/$tag.out")" ]] || s_out=0
    s_rc=1; [[ "$(cat "$W/o2/$tag.rc")" == "$(cat "$W/n2/$tag.rc")" ]] || s_rc=0
    s_f=1
    if [[ -e "$W/o2/$out" || -e "$W/n2/$out" ]]; then
      [[ "$(dump "$W/o2/$out" "$tr")" == "$(dump "$W/n2/$out" "$tr")" ]] || s_f=0
    fi
    echo "  format 2 case $tag (exit $(cat "$W/n2/$tag.rc")): stdout same $s_out, exit same $s_rc, output dump same $s_f"
    [[ $s_out == 1 && $s_rc == 1 && $s_f == 1 ]] || f2_ok=0
  done
  check "format 2 (no fingerprint branches) = the tool before format 3: stdout + stderr (elapsed seconds masked), exit (0 with a repeated row, 0, 8, 0 with RESULT WARN, 6) and the output's dump (rows, TNamed lookup_format / nano_datasets / sources, leaves)" "$f2_ok"
  mkdir -p "$W/o1" "$W/n1"
  for d in o1 n1; do cp "$W"/f2*.txt "$W/$d/"; done
  f1_ok=1
  for spec in "a:--filelist f2a.txt --out ttnb_a.root?reproducible=ttnb --out-tree TtNb --label a" "b:--filelist f2b.txt --out ttnb_b.root?reproducible=ttnb"; do
    tag="${spec%%:*}"; args="${spec#*:}"
    set -f
    # shellcheck disable=SC2086
    ( cd "$W/o1" && "$OLD" $args ) > "$W/o1/$tag.out" 2>&1; echo $? > "$W/o1/$tag.rc"
    # shellcheck disable=SC2086
    ( cd "$W/n1" && "$NEW" $args ) > "$W/n1/$tag.out" 2>&1; echo $? > "$W/n1/$tag.rc"
    set +f
    out="$(sed -E 's/^.*--out ([^ ?]*).*$/\1/' <<< "$args")"
    md5of() { if command -v md5sum > /dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }
    s_all=0
    cmp -s "$W/o1/$tag.out" "$W/n1/$tag.out" && [[ "$(cat "$W/o1/$tag.rc")" == "$(cat "$W/n1/$tag.rc")" ]] && \
      [[ "$(md5of "$W/o1/$out")" == "$(md5of "$W/n1/$out")" ]] && s_all=1
    echo "  format 1 case $tag (exit $(cat "$W/n1/$tag.rc")): stdout, exit and md5 the same: $s_all"
    [[ $s_all == 1 ]] || f1_ok=0
  done
  check "format 1 (--filelist) = the tool before format 3: stdout + stderr, exit and the output's md5 (ROOT ?reproducible=)" "$f1_ok"
fi

echo "RESULT $([[ $NFAIL -eq 0 ]] && echo OK || echo FAIL) test_extract_format3: $NPASS PASS, $NFAIL FAIL"
[[ $NFAIL -eq 0 ]]
