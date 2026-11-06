#!/usr/bin/env python3
# =============================================================================
# check_sidecar_lumimask.py -- did a lumi-masked CRAB task stay inside its mask?
# =============================================================================
# The MiniAODv3 tasks of 2022 / 2022EE (datasets.yaml, miniaod_version v3) must
# process ONLY the lumis of their lumi mask (Data.lumiMask; TTHHAnalyzer STEP 47,
# docs/04_decisions.md D25). They run with FileBased splitting; this check reads
# the finished sidecars and verifies that every (run, luminosityBlock) in them is
# inside the mask. A lumi outside the mask means CRAB processed whole files
# instead of the masked lumis (2026-11-06, CEO decision D: then the v3 tasks go
# to LumiBased splitting).
#
# Run on lxplus after the task finished, inside cmssw-el8 after cmsenv in the
# CMSSW_15_0_X area (PyROOT of the release):
#   find /eos/user/j/junghyun/TTHHGenCategoryTools/ttbarIdExtend_v2/2022/<primary>/<request_name> \
#        -name 'ttbarIDExtend_*.root' | sort > /tmp/$USER/<request_name>.txt
#   python3 crab/check_sidecar_lumimask.py --filelist /tmp/$USER/<request_name>.txt \
#        --mask crab/lumimasks/crab_lumimask_<era>_<sample>_v3.json
# A filelist line is a local path (EOS FUSE) or a root:// URL; blank lines and
# lines starting with '#' are skipped.
#
# Output: one line per file ([i/N], entries, distinct lumis, outside the mask,
# elapsed, ETA), the totals (entries, distinct (run, lumi), inside, outside,
# mask lumis seen of all) and a last line
#   RESULT OK check_sidecar_lumimask: ...           (exit 0)
#   RESULT FAIL check_sidecar_lumimask: ... (exit N)
# Exit codes: 0 every (run, lumi) inside the mask; 1 some outside (listed);
#   2 bad arguments, filelist or mask (unreadable, 0 lumis); 3 a file not
#   readable / no tree / no run or luminosityBlock branch / read error;
#   4 --require-full-mask and some mask lumis never seen; 5 no entries at all.
#
# Python 3.6 syntax, ASCII only (the crab/ rules). Needs PyROOT (CMSSW_15_0_X
# or any ROOT >= 6.22 with python3); the event loop runs in C++ (declared below).
# Author: TTHHAnalyzer STEP 47 (2026-11-06)
# =============================================================================

import argparse
import bisect
import json
import os
import sys
import time

_CPP = r"""
#include "TTree.h"
#include <set>
#include <vector>
struct TthhLumiScan {
  Long64_t entries;
  int status;   // 0 ok, -2 no branch, -3 address, -4 read error
  std::vector<ULong64_t> keys;   // distinct (run << 32 | lumi)
};
TthhLumiScan tthh_scan_lumis(TTree* t) {
  TthhLumiScan out;
  out.entries = 0;
  out.status = 0;
  if (!t->GetBranch("run") || !t->GetBranch("luminosityBlock")) { out.status = -2; return out; }
  UInt_t run = 0, lumi = 0;
  t->SetBranchStatus("*", 0);
  t->SetBranchStatus("run", 1);
  t->SetBranchStatus("luminosityBlock", 1);
  if (t->SetBranchAddress("run", &run) < 0 || t->SetBranchAddress("luminosityBlock", &lumi) < 0) {
    t->ResetBranchAddresses();
    out.status = -3;
    return out;
  }
  std::set<ULong64_t> seen;
  const Long64_t n = t->GetEntries();
  for (Long64_t i = 0; i < n; ++i) {
    if (t->GetEntry(i) <= 0) { out.status = -4; out.entries = i; t->ResetBranchAddresses(); return out; }
    seen.insert((static_cast<ULong64_t>(run) << 32) | static_cast<ULong64_t>(lumi));
  }
  t->ResetBranchAddresses();
  out.entries = n;
  out.keys.assign(seen.begin(), seen.end());
  return out;
}
"""

_STATUS_TXT = {-2: "no 'run' or 'luminosityBlock' branch", -3: "cannot bind run / luminosityBlock",
               -4: "read error (GetEntry <= 0)"}


def log(msg):
    print("[check_sidecar_lumimask] %s" % msg)
    sys.stdout.flush()


def finish(ok, code, text):
    print("RESULT %s check_sidecar_lumimask: %s%s" % ("OK" if ok else "FAIL", text,
                                                    "" if ok else " (exit %d)" % code))
    sys.stdout.flush()
    sys.exit(code)


def read_mask(path):
    """{run: sorted [(first, last), ...]} and the lumi count. ValueError if bad."""
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    if not isinstance(d, dict):
        raise ValueError("not a JSON object of runs")
    mask, n = {}, 0
    for run, ranges in d.items():
        r = int(run)
        if not isinstance(ranges, list):
            raise ValueError("run %s: not a list of [first, last]" % run)
        rr = []
        for x in ranges:
            if not isinstance(x, list) or len(x) != 2:
                raise ValueError("run %s: range %r is not [first, last]" % (run, x))
            a, b = int(x[0]), int(x[1])
            if a < 1 or b < a:
                raise ValueError("run %s: range [%d, %d]" % (run, a, b))
            rr.append((a, b))
            n += b - a + 1
        mask[r] = sorted(rr)
    return mask, n


def in_mask(mask, run, lumi):
    rr = mask.get(run)
    if not rr:
        return False
    i = bisect.bisect_right(rr, (lumi, float("inf"))) - 1
    return i >= 0 and rr[i][0] <= lumi <= rr[i][1]


def main():
    p = argparse.ArgumentParser(description="Check that every (run, luminosityBlock) of "
                                "lumi-masked sidecars is inside the lumi mask.")
    p.add_argument("--filelist", required=True, help="one sidecar path or root:// URL per line")
    p.add_argument("--mask", required=True, help="the task's CRAB lumi-mask JSON")
    p.add_argument("--tree", default="Events")
    p.add_argument("--require-full-mask", action="store_true",
                   help="also FAIL (exit 4) when some mask lumis never appear in the sidecars")
    p.add_argument("--max-list", type=int, default=20, help="outside lumis listed (default 20)")
    a = p.parse_args()

    try:
        with open(a.filelist, encoding="utf-8") as fh:
            files = [l.strip() for l in fh if l.strip() and not l.strip().startswith("#")]
    except OSError as e:
        finish(False, 2, "cannot read the filelist %s (%s)" % (a.filelist, e))
    if not files:
        finish(False, 2, "the filelist %s has no file" % a.filelist)
    try:
        mask, n_mask = read_mask(a.mask)
    except (OSError, ValueError, TypeError) as e:
        finish(False, 2, "the mask %s is not a CRAB lumi mask (%s)" % (a.mask, e))
    if n_mask == 0:
        finish(False, 2, "the mask %s holds 0 lumis" % a.mask)

    try:
        import ROOT  # noqa: E402  (PyROOT: CMSSW_15_0_X after cmsenv)
    except ImportError as e:
        finish(False, 2, "PyROOT not importable (%s) -- run inside cmssw-el8 after cmsenv" % e)
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kError
    ROOT.gInterpreter.Declare(_CPP)

    log("%d file(s), mask %s (%s lumis in %d run(s)), tree %s"
        % (len(files), a.mask, format(n_mask, ","), len(mask), a.tree))
    t0 = time.time()
    keys_all = set()
    outside_first = {}            # (run, lumi) -> the first file it was seen in
    n_entries = 0
    for i, path in enumerate(files, 1):
        try:
            tf = ROOT.TFile.Open(path)    # newer PyROOT raises OSError, older returns null
        except OSError as e:
            finish(False, 3, "file %d/%d cannot be opened: %s (%s)" % (i, len(files), path, e))
        if not tf or tf.IsZombie():
            finish(False, 3, "file %d/%d cannot be opened: %s" % (i, len(files), path))
        t = tf.Get(a.tree)
        if not t or not t.InheritsFrom("TTree"):
            tf.Close()
            finish(False, 3, "file %d/%d has no TTree %s: %s" % (i, len(files), a.tree, path))
        r = ROOT.tthh_scan_lumis(t)
        status, entries = int(r.status), int(r.entries)
        keys = [int(k) for k in r.keys]
        tf.Close()
        if status != 0:
            finish(False, 3, "file %d/%d: %s after %d entries: %s"
                   % (i, len(files), _STATUS_TXT.get(status, "status %d" % status), entries, path))
        n_out = 0
        for k in keys:
            run, lumi = k >> 32, k & 0xFFFFFFFF
            if not in_mask(mask, run, lumi):
                n_out += 1
                outside_first.setdefault((run, lumi), path)
        keys_all.update(keys)
        n_entries += entries
        el = time.time() - t0
        eta = el / i * (len(files) - i)
        log("[%d/%d] %s: entries %s, lumis %d, outside the mask %d | elapsed %.0f s, ETA %.0f s%s"
            % (i, len(files), os.path.basename(path), format(entries, ","), len(keys), n_out, el,
               eta, "" if entries else "  (NOTE: empty file)"))

    n_lumis = len(keys_all)
    n_outside = len(outside_first)
    n_inside = n_lumis - n_outside
    log("totals: entries %s, distinct (run, lumi) %s, inside the mask %s, outside %s; mask lumis "
        "seen %s of %s" % (format(n_entries, ","), format(n_lumis, ","), format(n_inside, ","),
                           format(n_outside, ","), format(n_inside, ","), format(n_mask, ",")))
    counts = ("%d file(s), %s entries, %s distinct (run, lumi): %s inside, %s outside the mask; "
              "mask lumis seen %s of %s; %.0f s"
              % (len(files), format(n_entries, ","), format(n_lumis, ","), format(n_inside, ","),
                 format(n_outside, ","), format(n_inside, ","), format(n_mask, ","),
                 time.time() - t0))
    if n_outside:
        for (run, lumi), path in sorted(outside_first.items())[:a.max_list]:
            log("OUTSIDE the mask: run %d lumi %d (first in %s)" % (run, lumi, path))
        if n_outside > a.max_list:
            log("... and %d more" % (n_outside - a.max_list))
        finish(False, 1, counts + " -- the task processed lumis outside its mask")
    if n_entries == 0:
        finish(False, 5, counts + " -- no entries at all")
    if a.require_full_mask and n_inside < n_mask:
        finish(False, 4, counts + " -- %s mask lumi(s) never seen (--require-full-mask)"
               % format(n_mask - n_inside, ","))
    finish(True, 0, counts)


if __name__ == "__main__":
    main()
