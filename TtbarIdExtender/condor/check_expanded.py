#!/usr/bin/env python
"""check_expanded.py -- verify the Expanded_genTtbarId rule on an enriched NanoAOD file.

Rule (TTHHGenCategoryTools docs/02_physics.md section 3; branch on nAddBJets only):

    expanded = genTtbarId                              if nAddBJets <= 2
             = (genTtbarId // 100) * 100 + newSub      if nAddBJets >= 3
    newSub   = 61 / 62   (nAddBJets == 3, nAddBJetsMulti == 0 / >= 1)   tt+bbb
             = 71 / 72   (nAddBJets >= 4, nAddBJetsMulti == 0 / >= 1)   tt+4b

Reads the top-level branches genTtbarId, expandedGenTtbarId, nAddBJets,
nAddBJetsMulti (the three we add are top-level in the enriched file, gate 1).

Prints: the per-event rule violations (first few), the nAddBJets distribution,
the genTtbarId%100 -> expanded%100 transition table, and a PASS/FAIL line.
Exit codes: 0 pass; 2 rule violated; 3 --expect-4b given but no 71/72 seen;
4 file/tree/branch problem. Works with python2 (10_6_X) and python3 (15_0_X).
"""
from __future__ import print_function
import argparse
import sys
from collections import Counter


def expected(gen, nadd, multi):
    if nadd <= 2:
        return gen
    sub = (61 if nadd == 3 else 71) + (1 if multi >= 1 else 0)
    return (gen // 100) * 100 + sub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--tree", default="Events")
    ap.add_argument("--expect-4b", action="store_true",
                    help="fail unless at least one 71/72 event is present (TT4b input)")
    ap.add_argument("--max-print", type=int, default=20)
    args = ap.parse_args()

    import ROOT  # noqa: E402  (after argparse so --help works without ROOT)
    ROOT.gROOT.SetBatch(True)
    f = ROOT.TFile.Open(args.file)
    if not f or f.IsZombie():
        print("[check_expanded] FAIL: cannot open %s" % args.file)
        return 4
    t = f.Get(args.tree)          # keep f alive: ROOT 6.14 GC trap (docs/08 T-26)
    if not t:
        print("[check_expanded] FAIL: no tree %s" % args.tree)
        return 4
    need = ["genTtbarId", "expandedGenTtbarId", "nAddBJets", "nAddBJetsMulti"]
    have = set(b.GetName() for b in t.GetListOfBranches())
    missing = [b for b in need if b not in have]
    if missing:
        print("[check_expanded] FAIL: missing branches: %s" % ", ".join(missing))
        return 4
    t.SetBranchStatus("*", 0)
    for b in need:
        t.SetBranchStatus(b, 1)

    n = t.GetEntries()
    bad = []
    n_add = Counter()
    trans = Counter()
    ext = Counter()
    for i in range(n):
        t.GetEntry(i)
        gen = int(t.genTtbarId)
        exp_ = int(t.expandedGenTtbarId)
        nadd = int(t.nAddBJets)
        multi = int(t.nAddBJetsMulti)
        n_add[nadd] += 1
        trans[(gen % 100, exp_ % 100)] += 1
        if exp_ % 100 in (61, 62, 71, 72):
            ext[exp_ % 100] += 1
        want = expected(gen, nadd, multi)
        if exp_ != want:
            bad.append((i, gen, nadd, multi, exp_, want))
        # the prefix (hundreds and above) must always survive
        if exp_ // 100 != gen // 100:
            bad.append((i, gen, nadd, multi, exp_, "prefix"))

    print("[check_expanded] %s  tree=%s  events=%d" % (args.file, args.tree, n))
    print("  nAddBJets distribution : %s" % ", ".join(
        "%d:%d" % (k, n_add[k]) for k in sorted(n_add)))
    print("  events with nAddBJets>=3: %d   >=4: %d" % (
        sum(v for k, v in n_add.items() if k >= 3), sum(v for k, v in n_add.items() if k >= 4)))
    print("  genTtbarId%100 -> expanded%100 (count):")
    for (a, b), c in sorted(trans.items()):
        mark = "" if a == b else "   <- extended"
        print("    %3d -> %3d : %6d%s" % (a, b, c, mark))
    print("  extended codes seen     : %s" % (", ".join(
        "%d:%d" % (k, ext[k]) for k in sorted(ext)) or "none"))
    if bad:
        print("  RULE VIOLATIONS: %d (showing up to %d)" % (len(bad), args.max_print))
        for row in bad[:args.max_print]:
            print("    entry %d  genTtbarId=%d nAddBJets=%d multi=%d expanded=%d expected=%s" % row)
        print("[check_expanded] FAIL")
        return 2
    print("  rule violations         : 0")
    if args.expect_4b and not (ext[71] or ext[72]):
        print("[check_expanded] FAIL: --expect-4b but no 71/72 event in %d events" % n)
        return 3
    print("[check_expanded] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
