#!/usr/bin/env python3
# =============================================================================
# CRAB submitter for extend (Approach 3) production
# =============================================================================
# Reads datasets.yaml and site_config.yaml; for each entry where enabled:true,
# builds a CRAB Configuration object and submits.
#
# Typical use:
#   cmsenv                                      # inside CMSSW_10_6_X/src
#   source /cvmfs/cms.cern.ch/common/crab-setup.sh
#   voms-proxy-init -voms cms -valid 192:00
#   python3 crab/submit_ttbarIdExtend.py --dry-run                    # preview
#   python3 crab/submit_ttbarIdExtend.py --process TTHHto4b --max-files 5  # smoke test
#   python3 crab/submit_ttbarIdExtend.py                              # all enabled
#
# Why a Python submitter and not a static crab_cfg.py?  Because we have a
# (process x era) matrix to walk and want fail-fast iteration; hand-editing
# request names / output LFNs across 20 templates would be busywork plus a
# reliable source of typos.
#
# Author: JH (KNU)
# =============================================================================

import argparse
import os
import sys
from pathlib import Path

THIS_DIR  = Path(__file__).resolve().parent
PKG_ROOT  = THIS_DIR.parent
EXTEND_PSET_REL = "TTHHGenCategoryTools/TtbarIdExtender/test/run_ttbarIdExtend_cfg.py"


# ----- YAML --------------------------------------------------------------
def load_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("ERROR: PyYAML not installed.  pip install --user pyyaml")
    with open(path) as fh:
        return yaml.safe_load(fh)


# ----- CLI ---------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="CRAB submitter (ttbar-Id extend, Approach 3).")
    p.add_argument("--datasets",     default=str(THIS_DIR / "datasets.yaml"))
    p.add_argument("--site-config",  default=str(THIS_DIR / "site_config.yaml"))
    p.add_argument("--process", help="Comma-separated logical names to submit.")
    p.add_argument("--era",     help="Comma-separated era keys to submit.")
    p.add_argument("--max-files", type=int, default=None,
                   help="Cap Data.totalUnits per task (smoke-tests).")
    p.add_argument("--dry-run",  action="store_true",
                   help="Print plan but do not submit.")
    p.add_argument("--force",    action="store_true",
                   help="Submit even datasets with enabled:false.")
    p.add_argument("--resubmit", action="store_true",
                   help="Bulk 'crab resubmit' on the existing crab_* project of "
                        "every selected sample (resubmits failed jobs). Honors "
                        "--process / --era. Does not submit new tasks.")
    p.add_argument("--status",   action="store_true",
                   help="Bulk 'crab status' on the existing crab_* project of "
                        "every selected sample. Does not submit new tasks.")
    return p.parse_args()


# ----- Build one Configuration ------------------------------------------
def build_config(*, process_name, era, dataset_entry, site_cfg, era_block,
                 max_files=None):
    """Return a CRAB Configuration with all fields populated."""
    from CRABClient.UserUtilities import config as _cfg
    cfg = _cfg()

    tag = (site_cfg.get("request_name_tag") or "").strip()
    rn  = f"{process_name}_{era}_extend"
    if tag:
        rn += f"_{tag}"

    # General
    cfg.General.requestName     = rn
    cfg.General.workArea        = site_cfg.get("work_area", "crab_projects")
    cfg.General.transferLogs    = False
    cfg.General.transferOutputs = True

    # JobType
    cfg.JobType.pluginName     = "Analysis"
    cfg.JobType.psetName       = EXTEND_PSET_REL
    cfg.JobType.pyCfgParams    = ["outputFile=ttbarIDExtend.root"]
    # NB: run_ttbarIdExtend_cfg.py has no `year` parameter (that was an
    # enriched-cfg option).  CRAB injects inputFiles for FileBased
    # splitting; we only fix the output filename here.  VarParsing
    # may append a _numEventN suffix -- confirm in the smoke test
    # that CRAB still collects the produced file (adjust
    # JobType.outputFiles below if needed).
    res = (site_cfg.get("resources") or {}).get("extend", {})
    cfg.JobType.maxMemoryMB        = int(res.get("max_memory_mb", 2000))
    cfg.JobType.maxJobRuntimeMin   = int(res.get("max_runtime_min", 1440))
    cfg.JobType.outputFiles    = ["ttbarIDExtend.root"]
    cfg.JobType.allowUndistributedCMSSW = True   # 10_6_X is "frozen" so this is needed

    # Data
    cfg.Data.inputDataset    = dataset_entry["dataset"]
    cfg.Data.inputDBS        = "global"
    cfg.Data.splitting       = "FileBased"
    cfg.Data.unitsPerJob     = int(
        dataset_entry.get("units_per_job", res.get("units_per_job", 1))
    )
    if max_files is not None:
        cfg.Data.totalUnits  = int(max_files)
    cfg.Data.publication     = False
    cfg.Data.outLFNDirBase   = f"{site_cfg['out_lfn_base']}/{era}"
    cfg.Data.outputDatasetTag = rn

    # Site
    cfg.Site.storageSite     = site_cfg["storage_site"]
    if site_cfg.get("whitelist_sites"):
        cfg.Site.whitelist   = list(site_cfg["whitelist_sites"])
    if site_cfg.get("blacklist_sites"):
        cfg.Site.blacklist   = list(site_cfg["blacklist_sites"])

    return cfg


# ----- Submit one --------------------------------------------------------
def submit_one(cfg, *, dry_run):
    print(f"  request    : {cfg.General.requestName}")
    print(f"  dataset    : {cfg.Data.inputDataset}")
    print(f"  storage    : {cfg.Site.storageSite} -> {cfg.Data.outLFNDirBase}")
    print(f"  pyCfgParams: {','.join(cfg.JobType.pyCfgParams) or '(none)'}")
    if hasattr(cfg.Data, "totalUnits"):
        print(f"  totalUnits : {cfg.Data.totalUnits}  (capped via --max-files)")

    if dry_run:
        print("  [dry-run]\n")
        return True

    proj = Path(cfg.General.workArea) / f"crab_{cfg.General.requestName}"
    if proj.exists():
        print(f"  [skip] project dir already exists: {proj}\n"
              f"         Bump request_name_tag in site_config.yaml to re-submit.\n")
        return False

    try:
        from CRABAPI.RawCommand import crabCommand
    except ImportError as exc:
        sys.exit(f"ERROR: CRAB client missing ({exc}).\n"
                 f"       source /cvmfs/cms.cern.ch/common/crab-setup.sh")

    try:
        crabCommand("submit", config=cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAILED] {exc}\n")
        return False
    print("  [submitted]\n")
    return True


def crab_action_one(cfg, *, action):
    """Run 'crab resubmit' or 'crab status' on an existing project dir.

    Returns True if the CRAB command ran (regardless of per-job outcome),
    False if the project dir is missing or the command raised.
    """
    proj = Path(cfg.General.workArea) / f"crab_{cfg.General.requestName}"
    print(f"  request    : {cfg.General.requestName}")
    print(f"  project    : {proj}")
    if not proj.exists():
        print(f"  [skip] no project dir (nothing to {action})\n")
        return False
    try:
        from CRABAPI.RawCommand import crabCommand
    except ImportError as exc:
        sys.exit(f"ERROR: CRAB client missing ({exc}).\n"
                 f"       source /cvmfs/cms.cern.ch/common/crab-setup.sh")
    try:
        crabCommand(action, dir=str(proj))
    except Exception as exc:  # noqa: BLE001
        print(f"  [{action} FAILED] {exc}\n")
        return False
    print(f"  [{action} ok]\n")
    return True


# ----- Main --------------------------------------------------------------
def main():
    args = parse_args()
    cat  = load_yaml(args.datasets)
    site = load_yaml(args.site_config)

    if "__YOUR_CERN_USERNAME__" in (site.get("out_lfn_base") or ""):
        sys.exit("ERROR: site_config.yaml still has the placeholder username "
                 "in out_lfn_base.  Edit it before submitting.")

    proc_filter = ({s.strip() for s in args.process.split(",")}
                   if args.process else None)
    era_filter  = ({s.strip() for s in args.era.split(",")}
                   if args.era else None)

    # Which mode are we in? submit (default), or a bulk action on existing tasks.
    bulk_action = "resubmit" if args.resubmit else ("status" if args.status else None)
    if args.resubmit and args.status:
        sys.exit("ERROR: choose only one of --resubmit / --status.")

    n_total = n_skipped = n_attempted = n_submitted = 0
    for era, era_block in (cat.get("eras") or {}).items():
        if era_filter and era not in era_filter:
            continue
        for ds in (era_block.get("datasets") or []):
            n_total += 1
            name = ds["name"]
            if proc_filter and name not in proc_filter:
                continue
            # For bulk actions we act on every selected sample regardless of
            # the enabled flag (you may want to resubmit/status a task whose
            # entry you have since toggled off). For submission we honor it.
            if bulk_action is None and not args.force and not ds.get("enabled", False):
                n_skipped += 1
                continue

            verb = bulk_action or "extend"
            print(f"--- {verb}  era={era}  process={name} ---")
            cfg = build_config(
                process_name=name, era=era, dataset_entry=ds,
                site_cfg=site, era_block=era_block,
                max_files=args.max_files,
            )
            n_attempted += 1
            if bulk_action is not None:
                if crab_action_one(cfg, action=bulk_action):
                    n_submitted += 1
            else:
                if submit_one(cfg, dry_run=args.dry_run):
                    n_submitted += 1

    print("=" * 65)
    mode = bulk_action or ("submit" + (" (DRY RUN)" if args.dry_run else ""))
    print(f"  mode      : {mode}")
    print(f"  scanned   : {n_total}")
    if bulk_action is None:
        print(f"  skipped   : {n_skipped}  (enabled:false; use --force to override)")
    print(f"  attempted : {n_attempted}")
    label = {"resubmit": "resubmitted", "status": "queried"}.get(bulk_action, "submitted")
    print(f"  {label:9s} : {n_submitted}")


if __name__ == "__main__":
    main()
