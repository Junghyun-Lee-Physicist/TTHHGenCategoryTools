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
# =============================================================================

import argparse
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent


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
    for pr in projs:
        try:
            r = crabCommand("status", dir=str(pr))
        except Exception as exc:  # noqa: BLE001
            print(f"  {pr.name:60s}  ERROR: {exc}")
            continue
        jobs = r.get("jobsPerStatus", {}) or {}
        print(f"  {pr.name:60s}  status={r.get('status', '?'):14s}  "
              f"done={jobs.get('finished', 0)} run={jobs.get('running', 0)} "
              f"idle={jobs.get('idle', 0)} fail={jobs.get('failed', 0)} "
              f"tot={sum(jobs.values())}")


if __name__ == "__main__":
    main()
