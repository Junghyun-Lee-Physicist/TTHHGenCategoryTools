#!/usr/bin/env python
"""judge_compare.py -- turn a compare_v9_v15.py --json summary into PASS/FAIL.

compare_v9_v15.py (NtupleForge) writes: branches_only_v9, branches_only_v15,
events_common, events_mismatched, per_branch_mismatch {branch: n}, nan_agree.

Options say what the comparison is supposed to show:
  --only-v15 a,b,c   the exact set of branches allowed to exist only in the
                     --v15 file (our three columns); "" = none allowed
  --only-v9  a,b     same for the --v9 file (default: none)
  --min-common N     at least N common events
  --zero             no mismatch at all (bit identity)
  --allow REGEX      mismatches allowed only in branches matching REGEX
                     (e.g. '(_area$|^HTXS_)' for the reproduction artifacts)
Exit 0 = PASS, 1 = FAIL, 4 = cannot read the JSON. python2/3.
"""
from __future__ import print_function
import argparse
import json
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--label", default="")
    ap.add_argument("--only-v15", default="")
    ap.add_argument("--only-v9", default="")
    ap.add_argument("--min-common", type=int, default=1)
    ap.add_argument("--zero", action="store_true")
    ap.add_argument("--allow", default="")
    a = ap.parse_args()

    try:
        with open(a.json_file) as fh:
            s = json.load(fh)
    except Exception as e:  # noqa: BLE001
        print("[judge] FAIL %s: cannot read %s (%s)" % (a.label, a.json_file, e))
        return 4

    want15 = set(x for x in a.only_v15.split(",") if x)
    want9 = set(x for x in a.only_v9.split(",") if x)
    got15 = set(s.get("branches_only_v15", []))
    got9 = set(s.get("branches_only_v9", []))
    common = int(s.get("events_common", 0))
    per = dict(s.get("per_branch_mismatch", {}))
    ev_bad = int(s.get("events_mismatched", 0))

    problems = []
    if got15 != want15:
        problems.append("only-in-v15 branches %s != expected %s" % (sorted(got15), sorted(want15)))
    if got9 != want9:
        problems.append("only-in-v9 branches %s != expected %s" % (sorted(got9), sorted(want9)))
    if common < a.min_common:
        problems.append("common events %d < %d" % (common, a.min_common))
    if a.zero and per:
        problems.append("expected bit identity but %d branch(es) disagree: %s" % (
            len(per), ", ".join("%s(%d)" % kv for kv in sorted(per.items()))))
    if a.allow and per:
        rx = re.compile(a.allow)
        outside = sorted(b for b in per if not rx.search(b))
        if outside:
            problems.append("mismatches outside the allowed class %s: %s" % (
                a.allow, ", ".join("%s(%d)" % (b, per[b]) for b in outside)))

    print("[judge] %s: branches compared=%s common events=%d mismatched events=%d (%.2f%%) "
          "disagreeing branches=%d" % (a.label, s.get("branches_compared"), common, ev_bad,
                                       100.0 * ev_bad / common if common else 0.0, len(per)))
    if per:
        print("[judge]   per-branch: %s" % ", ".join(
            "%s=%d" % kv for kv in sorted(per.items(), key=lambda kv: -kv[1])))
    if problems:
        for p in problems:
            print("[judge]   !! %s" % p)
        print("[judge] FAIL %s" % a.label)
        return 1
    print("[judge] PASS %s" % a.label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
