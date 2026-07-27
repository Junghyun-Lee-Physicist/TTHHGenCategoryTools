#!/usr/bin/env python3
# =============================================================================
# CRAB status checker for extend production
# =============================================================================
# Walks every crab_* project under workArea and prints a one-line summary
# per project.
#
# Usage:
#   python3 crab/status.py
#   python3 crab/status.py --filter TTToHadronic_2017
#
# WHEN TO USE THIS vs `submit_ttbarIdExtend.py --report`
#   this script : discovers projects by SCANNING workArea. Use it when you do not
#                 know (or do not care) which era/process a project belongs to,
#                 or when datasets.yaml has moved on since submission (entries
#                 toggled off, renamed, request_name_tag bumped) -- the scan
#                 still finds the tasks.
#   --report    : drives off datasets.yaml (--process/--era aware) and prints an
#                 ALIGNED TABLE with a TOTAL row, same columns as NtupleForge's
#                 submit_crab.py --report. Use it for the campaign-wide picture.
#
# 2026-07-27 fix: this script used to print only done/run/idle/fail next to
# tot=sum(all states), so `transferring` (huge here -- ~21k jobs staging out to
# T3_CH_CERNBOX), plus cooloff/held/unsubmitted, were INVISIBLE and the four
# printed numbers did not add up to tot. It now uses the same buckets as
# --report, so every job is accounted for in a printed column.
# =============================================================================

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent

# The bucket rules live in ONE place (submit_ttbarIdExtend.py) so this script and
# `--report` can never disagree about what counts as "other". Both files sit in
# crab/, so a sys.path entry is enough -- there is no package __init__ here.
# Importing that module is side-effect free: its CRAB imports are inside
# functions and main() only runs under __main__.
sys.path.insert(0, str(THIS_DIR))
try:
    from submit_ttbarIdExtend import summarize_status
except ImportError as _exc:  # pragma: no cover - keeps the scan usable
    sys.exit("ERROR: cannot import summarize_status from "
             "submit_ttbarIdExtend.py (%s).\n"
             "       Both files must stay in the same crab/ directory." % _exc)


def load_site_cfg(path):
    try:
        import yaml
    except ImportError:
        return {}
    if not path.exists():
        return {}
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def main():
    p = argparse.ArgumentParser(description="Bulk CRAB status check.")
    p.add_argument("--site-config", type=Path,
                   default=THIS_DIR / "site_config.yaml")
    p.add_argument("--work-area",   type=Path, default=None)
    p.add_argument("--filter",      default=None,
                   help="Substring match against project dir names.")
    args = p.parse_args()

    work = args.work_area or Path(
        load_site_cfg(args.site_config).get("work_area", "crab_projects"))
    if not work.exists():
        sys.exit(f"ERROR: workArea {work} not found.")

    try:
        from CRABAPI.RawCommand import crabCommand
    except ImportError as exc:
        sys.exit(f"ERROR: CRAB client missing ({exc}).  "
                 f"source /cvmfs/cms.cern.ch/common/crab-setup.sh")

    projs = sorted(p for p in work.iterdir()
                   if p.is_dir() and p.name.startswith("crab_"))
    if args.filter:
        projs = [p for p in projs if args.filter in p.name]
    if not projs:
        print(f"  no crab_* projects under {work}"
              f"{f' matching {args.filter!r}' if args.filter else ''}")
        return

    print(f"  scanning {len(projs)} project(s) under {work}")
    print("=" * 80)
    unknown_all = set()
    for pr in projs:
        try:
            r = crabCommand("status", dir=str(pr))
        except Exception as exc:  # noqa: BLE001
            print(f"  {pr.name:60s}  ERROR: {exc}")
            continue
        row, unknown = summarize_status(r.get("jobsPerStatus", {}))
        unknown_all |= unknown
        # Every job lands in exactly one printed column, so the numbers add up
        # to tot by construction (see the 2026-07-27 note in the header).
        print(f"  {pr.name:60s}  status={r.get('status', '?'):14s}  "
              f"done={row['finished']} run={row['running']} "
              f"idle={row['idle']} transf={row['transferring']} "
              f"fail={row['failed']} other={row['others']} "
              f"tot={row['total']}")
    if unknown_all:
        print()
        print(f"  [WARN] unknown CRAB job state(s) folded into 'other': "
              f"{sorted(unknown_all)}")
        print( "         Add them to REPORT_COLUMNS / KNOWN_OTHER_STATES in "
               "submit_ttbarIdExtend.py (and keep NtupleForge/crab/submit_crab.py "
               "in sync).")


if __name__ == "__main__":
    main()
