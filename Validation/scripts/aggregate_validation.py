#!/usr/bin/env python3
# =============================================================================
# aggregate_validation.py
# =============================================================================
# Sum the per-chunk JSON counters written by matchTtbarIdSorted (--json) into
# ONE verdict per sample, and cross-check the summed nano event count against
# the DAS nevents recorded in tempTTHH/data/samples_<era>UL.json.
#
# WHY THE CROSS-CHECK MATTERS (docs/08_troubleshooting.md T-21)
#   `unmatched` is the number of nano events NOT found in the extend files.
#   It is monotonically DECREASING in data loss: drop nano input and unmatched
#   can only get smaller, so "unmatched 0" alone is NOT evidence of
#   completeness -- on 2026-07-27 it reported a clean pass over 13% of a sample
#   because 5 of 6 nano files had failed to open. The only honest completeness
#   statement is
#        sum(nano_entries over all chunks) == DAS nevents for that sample
#   so that comparison is a first-class PASS/FAIL criterion here, not a note.
#
# Missing chunks are a FAILURE, not a gap to be silently averaged over: if the
# expected chunk list and the JSON files on disk disagree, this prints which
# chunk indices are absent and marks the sample INCOMPLETE.
#
# USAGE
#   python3 scripts/aggregate_validation.py --era 2018
#   python3 scripts/aggregate_validation.py --era 2018 --samples ttbb_2L2Nu
#   python3 scripts/aggregate_validation.py --era 2018 --json-out summary.json
#
# Exit 0 only if every requested sample passes every criterion.
# =============================================================================

import argparse
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
VAL_ROOT = THIS_DIR.parent

SHORTS = ["tt4b", "ttbb_Hadronic", "ttbb_SemiLeptonic", "ttbb_2L2Nu",
          "TTToHadronic", "TTToSemiLeptonic", "TTTo2L2Nu"]

# short name (validation tooling) -> sample key in samples_<era>UL.json
# These two naming schemes are historical and both are load-bearing, so the
# mapping is explicit rather than guessed.
SHORT_TO_XSECKEY = {
    "tt4b":              "TT4b",
    "ttbb_Hadronic":     "TTbb_Hadronic",
    "ttbb_SemiLeptonic": "TTbb_SemiLep",
    "ttbb_2L2Nu":        "TTbb_DiLep",
    "TTToHadronic":      "TTbar_Hadronic",
    "TTToSemiLeptonic":  "TTbar_SemiLep",
    "TTTo2L2Nu":         "TTbar_DiLep",
}

DEFAULT_EOS = "/eos/user/j/junghyun/TTHHGenCategoryTools"

VIOL_KEYS = ["viol_ext_but_lt3", "viol_ge3_not_ext",
             "viol_prefix_changed", "viol_le2_changed"]
SUM_KEYS = (["nano_entries", "nano_entries_opencheck", "matched", "unmatched",
             "agree", "disagree", "nAddBJets_ge3", "expanded_sub_in_set"]
            + VIOL_KEYS)
MAP_KEYS = ["expanded_sub_counts", "orig_sub_of_reclassified",
            "disagree_by_nano_sub"]


def parse_args():
    p = argparse.ArgumentParser(
        description="Aggregate per-chunk validation JSON into one verdict "
                    "per sample.")
    p.add_argument("--era", required=True)
    p.add_argument("--samples", default=None,
                   help="Comma-separated short names; default = all 7.")
    p.add_argument("--out-base", default=None,
                   help="Default: %s/valout<era>" % DEFAULT_EOS)
    p.add_argument("--nano-filelist-dir", default=None,
                   help="Used to know how many chunks were EXPECTED. "
                        "Default: <Validation>/filelists/nano<era>")
    p.add_argument("--xsec-db", default=None,
                   help="samples_<era>UL.json for the DAS nevents cross-check. "
                        "Default: ../../tempTTHH/data/samples_<era>UL.json")
    p.add_argument("--json-out", default=None,
                   help="Also write the aggregated summary as JSON.")
    p.add_argument("--no-das-check", action="store_true",
                   help="Skip the nano-total vs DAS nevents comparison. "
                        "DISCOURAGED: that comparison is the only real "
                        "completeness proof (see header).")
    return p.parse_args()


def load_xsec_db(path):
    if not path or not Path(path).is_file():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print("[warn] cannot read xsec db %s: %s" % (path, exc))
        return None


def expected_chunks(nano_dir, short):
    split_dir = nano_dir / short
    if split_dir.is_dir():
        cs = sorted(split_dir.glob("file_%s_*.txt" % short))
        if cs:
            return [c.stem for c in cs]
    master = nano_dir / ("filelist_%s.txt" % short)
    return [master.stem] if master.is_file() else []


def aggregate_sample(short, jsondir, expected):
    """Return (agg, problems). agg has summed counters; problems is a list."""
    agg = {k: 0 for k in SUM_KEYS}
    agg.update({k: {} for k in MAP_KEYS})
    agg["chunks_found"] = 0
    agg["chunks_expected"] = len(expected)
    agg["missing_chunks"] = []
    agg["chunk_exit_codes"] = {}
    problems = []

    for tag in expected:
        jf = jsondir / ("%s.json" % tag)
        if not jf.is_file():
            agg["missing_chunks"].append(tag)
            continue
        try:
            with open(jf, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError) as exc:
            problems.append("chunk %s: unreadable JSON (%s)" % (tag, exc))
            agg["missing_chunks"].append(tag)
            continue
        agg["chunks_found"] += 1
        for k in SUM_KEYS:
            agg[k] += int(d.get(k, 0))
        for k in MAP_KEYS:
            for sub, n in (d.get(k) or {}).items():
                agg[k][str(sub)] = agg[k].get(str(sub), 0) + int(n)
        ec = int(d.get("exit_code", -1))
        agg["chunk_exit_codes"][tag] = ec
        # A chunk that opened fewer entries than its own open-check saw means the
        # chain lost a file between check and read; the C++ side aborts on that,
        # but if an older binary produced the JSON we still want to notice.
        if d.get("nano_entries") != d.get("nano_entries_opencheck"):
            problems.append(
                "chunk %s: nano_entries %s != open-check %s"
                % (tag, d.get("nano_entries"), d.get("nano_entries_opencheck")))
    return agg, problems


def verdict(short, agg, problems, das_nevents):
    """Build the ordered list of (name, ok, detail) criteria for one sample."""
    crit = []

    complete_chunks = (agg["chunks_found"] == agg["chunks_expected"]
                       and agg["chunks_expected"] > 0)
    crit.append(("all chunks present", complete_chunks,
                 "%d/%d%s" % (agg["chunks_found"], agg["chunks_expected"],
                              "" if complete_chunks
                              else "   MISSING: " + ", ".join(
                                  agg["missing_chunks"][:6])
                              + (" ..." if len(agg["missing_chunks"]) > 6 else ""))))

    if das_nevents is None:
        crit.append(("nano total == DAS nevents", None, "no DAS value available"))
    else:
        ok = agg["nano_entries"] == das_nevents
        crit.append(("nano total == DAS nevents", ok,
                     "%s vs %s%s" % (fmt(agg["nano_entries"]), fmt(das_nevents),
                                     "" if ok else "   DIFF %s"
                                     % fmt(das_nevents - agg["nano_entries"]))))

    crit.append(("matched > 0", agg["matched"] > 0, fmt(agg["matched"])))
    crit.append(("unmatched == 0", agg["unmatched"] == 0,
                 fmt(agg["unmatched"])))
    crit.append(("disagree == 0", agg["disagree"] == 0, fmt(agg["disagree"])))
    crit.append(("conservation ge3 == extended",
                 agg["nAddBJets_ge3"] == agg["expanded_sub_in_set"],
                 "%s vs %s" % (fmt(agg["nAddBJets_ge3"]),
                               fmt(agg["expanded_sub_in_set"]))))
    for k in VIOL_KEYS:
        crit.append((k + " == 0", agg[k] == 0, fmt(agg[k])))
    bad_exits = {t: e for t, e in agg["chunk_exit_codes"].items() if e != 0}
    crit.append(("every chunk exit 0", not bad_exits,
                 "ok" if not bad_exits
                 else ", ".join("%s->%d" % (t, e)
                                for t, e in list(bad_exits.items())[:6])))
    crit.append(("no per-chunk anomalies", not problems,
                 "ok" if not problems else problems[0]))
    return crit


def fmt(n):
    try:
        return format(int(n), ",")
    except (TypeError, ValueError):
        return str(n)


def main():
    a = parse_args()
    era = a.era
    out_base = Path(a.out_base or ("%s/valout%s" % (DEFAULT_EOS, era)))
    # Condor's output_destination delivers every transferred output file into ONE
    # flat directory (it cannot fan out into json/ and root/ sub-dirs), so the
    # per-chunk JSON and ROOT files share results/. Fall back to the older
    # json/ layout so summaries produced before 2026-07-28 still aggregate.
    jsondir = out_base / "results"
    if not jsondir.is_dir() and (out_base / "json").is_dir():
        jsondir = out_base / "json"
    nano_dir = Path(a.nano_filelist_dir or
                    VAL_ROOT / "filelists" / ("nano%s" % era))
    xsec_path = a.xsec_db or (VAL_ROOT.parent.parent / "tempTTHH" / "data"
                              / ("samples_%sUL.json" % era))
    shorts = ([s.strip() for s in a.samples.split(",")] if a.samples
              else list(SHORTS))

    print("=" * 92)
    print("ttbarId-extend validation summary   era=%s" % era)
    print("  json dir  : %s" % jsondir)
    print("  nano lists: %s" % nano_dir)
    print("  xsec db   : %s" % xsec_path)
    print("=" * 92)
    if not jsondir.is_dir():
        sys.exit("FATAL: no results directory %s\n"
                 "  Did the condor jobs run? The condor .out/.err logs are on\n"
                 "  AFS under <Validation>/condor_val<era>/logs/ -- each job also\n"
                 "  echoes its JSON between 'BEGIN JSON'/'END JSON' there, so the\n"
                 "  numbers survive even a failed EOS transfer." % jsondir)

    db = None if a.no_das_check else load_xsec_db(xsec_path)
    summary, all_ok = {}, True

    for short in shorts:
        exp = expected_chunks(nano_dir, short)
        agg, problems = aggregate_sample(short, jsondir, exp)

        das = None
        if db is not None:
            key = SHORT_TO_XSECKEY.get(short)
            if key and key in db:
                das = db[key].get("nevents")
            else:
                problems.append("no xsec-db key for short name %r" % short)

        crit = verdict(short, agg, problems, das)
        ok = all(c[1] is not False for c in crit)
        all_ok = all_ok and ok
        summary[short] = {"pass": ok, "counters": agg,
                          "das_nevents": das,
                          "criteria": [(n, o, d) for n, o, d in crit]}

        print()
        print("### %-20s %s" % (short, "PASS" if ok else "**FAIL**"))
        for name, o, detail in crit:
            mark = "ok  " if o is True else ("SKIP" if o is None else "FAIL")
            print("    [%s] %-30s %s" % (mark, name, detail))
        if agg["chunks_found"]:
            print("    tt+bbb (61+62) : %s     tt+4b (71+72) : %s"
                  % (fmt(sum(v for k, v in agg["expanded_sub_counts"].items()
                             if k in ("61", "62"))),
                     fmt(sum(v for k, v in agg["expanded_sub_counts"].items()
                             if k in ("71", "72")))))
            print("    Expanded sub-code counts     : %s"
                  % dict(sorted(agg["expanded_sub_counts"].items())))
            print("    nano sub-code of reclassified: %s"
                  % dict(sorted(agg["orig_sub_of_reclassified"].items())))

    print()
    print("=" * 92)
    print("OVERALL: %s" % ("ALL SAMPLES PASS" if all_ok
                           else "AT LEAST ONE SAMPLE FAILED"))
    print("=" * 92)
    print("Reminder: 2017 reference numbers (tt+nb 1,882,170 = 1,585,810 + 296,360)")
    print("are NOT the 2018 acceptance criteria -- the event counts differ.")
    print("Record the numbers above in docs/06_validation_results.md (append).")

    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as fh:
            json.dump({"era": era, "all_pass": all_ok, "samples": summary},
                      fh, indent=1)
        print("wrote %s" % a.json_out)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
