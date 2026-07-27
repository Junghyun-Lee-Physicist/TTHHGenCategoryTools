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
# !! PYTHON 3.6 ONLY -- DO NOT USE 3.7+ APIs !!
#   This package is pinned to CMSSW_10_6_32_patch1, whose python is 3.6.4.
#   Anything newer breaks at run time, not at import, so it is easy to miss:
#     subprocess.run(..., text=True)        -> 3.7+  ; use universal_newlines=True
#     subprocess.run(..., capture_output=)  -> 3.7+  ; use stdout=/stderr=PIPE
#     dict |= / str.removeprefix / match    -> 3.9+ / 3.10+
#   (Both subprocess traps were actually hit on 2026-07-27.)
#   Related environment constraints of the same flavour:
#     * LANG=C  -> open() defaults to ASCII; always pass encoding= (see load_yaml)
#     * files under this package are kept ASCII-only (convention since v12.5)
#     * PyROOT is unusable here (ROOT 6.14 is a python2 build) -> use ROOT macros
#
# Author: JH (KNU)
# =============================================================================

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

THIS_DIR  = Path(__file__).resolve().parent
PKG_ROOT  = THIS_DIR.parent
# Absolute path to the cfg. CRAB resolves JobType.psetName against the *current
# working directory*, so a repo-relative string only works when you run from
# .../src/. Deriving it from PKG_ROOT (= .../TtbarIdExtender) makes submission
# work from any directory (e.g. from inside TtbarIdExtender/ itself).
EXTEND_PSET = str(PKG_ROOT / "test" / "run_ttbarIdExtend_cfg.py")


# ----- YAML --------------------------------------------------------------
def load_yaml(path):
    """Load a YAML file with an EXPLICIT utf-8 encoding.

    Do not drop `encoding=`: inside CMSSW_10_6_X the locale is `LANG=C`, so
    python3.6's `open()` defaults to ASCII and a single non-ASCII byte anywhere
    in the file aborts the whole submitter with
        UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 ...
    (observed 2026-07-27: one em-dash in a datasets.yaml comment). The YAML
    files themselves are kept ASCII-only by convention (v12.5), but reading
    them as utf-8 means a stray character degrades to a cosmetic issue instead
    of a hard failure.
    """
    try:
        import yaml
    except ImportError:
        sys.exit("ERROR: PyYAML not installed.  pip install --user pyyaml")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ----- CLI ---------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="CRAB submitter (ttbar-Id extend, Approach 3).")
    p.add_argument("--datasets",     default=str(THIS_DIR / "datasets.yaml"))
    p.add_argument("--site-config",  default=str(THIS_DIR / "site_config.yaml"))
    p.add_argument("--process", help="Comma-separated logical names to submit.")
    p.add_argument("--era",     help="Comma-separated era keys to submit.")
    p.add_argument("--max-files", type=int, default=None,
                   help="Cap Data.totalUnits per task. DISCOURAGED (DECIDED "
                        "2026-07-27): it creates a task that can NEVER reach full "
                        "coverage -- 5 of 103 files shows as 'done 5/5 = 100%%' in "
                        "--report while only 5%% of the dataset is processed, and "
                        "finishing the rest needs a SECOND task, which splits the "
                        "output across two timestamp dirs under the same LFN and "
                        "makes make_filelists_miniAOD.py pick up both (duplicate "
                        "3-key rows -> matchTtbarId exit 7). For a smoke test, "
                        "submit the SMALLEST DATASET IN FULL instead "
                        "(--process TTbb_DiLep, 103 files).")
    p.add_argument("--dry-run",  action="store_true",
                   help="Print plan but do not submit.")
    p.add_argument("--preflight", action="store_true",
                   help="READ-ONLY pre-submission check (stronger than --dry-run): "
                        "environment (cmsenv/CRABClient/proxy), pset presence + "
                        "compile + `year` option, site config, and per-era dataset "
                        "state (path syntax, campaign-vs-era coherence, primary "
                        "match, enabled/verified, existing CRAB project). Writes "
                        "preflight_extend_<eras>_<timestamp>.log; exits non-zero on FAIL.")
    p.add_argument("--check-das", action="store_true",
                   help="With --preflight: also query DAS for every MiniAOD/Nano path "
                        "(catches a wrong -vN suffix before submission).")
    p.add_argument("--force",    action="store_true",
                   help="Submit even datasets with enabled:false.")
    p.add_argument("--resubmit", action="store_true",
                   help="Bulk 'crab resubmit' on the existing crab_* project of "
                        "every selected sample (resubmits failed jobs). Honors "
                        "--process / --era. Does not submit new tasks.")
    p.add_argument("--status",   action="store_true",
                   help="Bulk 'crab status' on the existing crab_* project of "
                        "every selected sample. Does not submit new tasks.")
    p.add_argument("--kill",     action="store_true",
                   help="Bulk 'crab kill' on the existing crab_* project of "
                        "every selected sample (kills all running/idle jobs). "
                        "Honors --process / --era. Prompts for confirmation "
                        "unless --yes is given. Does not remove project dirs.")
    p.add_argument("--yes",      action="store_true",
                   help="Skip the confirmation prompt for --kill.")
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
    cfg.JobType.psetName       = EXTEND_PSET
    # `year` is passed per task so the pset picks the matching era modifier.
    # (2026-07-26: run_ttbarIdExtend_cfg.py gained a `year` VarParsing option
    # for the 2018UL run; it defaults to 2017, so old behaviour is unchanged if
    # this argument is ever dropped.)  The era key of datasets.yaml IS the year.
    cfg.JobType.pyCfgParams    = ["outputFile=ttbarIDExtend.root",
                                  f"year={era}"]
    # CRAB injects inputFiles for FileBased splitting; we only fix the output
    # filename and the year here.  VarParsing may append a _numEventN suffix --
    # confirm in the smoke test that CRAB still collects the produced file
    # (adjust JobType.outputFiles below if needed).
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
    """Run 'crab resubmit' / 'crab status' / 'crab kill' on an existing project dir.

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


# =============================================================================
# PREFLIGHT (--preflight) -- read-only, era-aware pre-submission check
# =============================================================================
# Complements crab/preflight.py (environment + build + pset compile) by checking
# the things that actually differ per era: the datasets.yaml era block, the
# enabled/verified state, the DAS resolvability of every path, and the pset's
# `year` handling. Nothing is submitted; a log file is written.
_DS_RE = re.compile(r"^/[^/]+/[^/]+/(MINIAODSIM|NANOAODSIM)$")


def run_preflight(args, cat, site):
    rows, lines = [], []

    def emit(level, check, detail=""):
        rows.append((level, check, detail))
        line = "[%-4s] %-38s %s" % (level, check, detail)
        print(line)
        lines.append(line)

    def note(text=""):
        print(text)
        lines.append(text)

    ok   = lambda c, d="": emit("PASS", c, d)
    warn = lambda c, d="": emit("WARN", c, d)
    bad  = lambda c, d="": emit("FAIL", c, d)

    era_filter = ({s.strip() for s in args.era.split(",")} if args.era else None)
    proc_filter = ({s.strip() for s in args.process.split(",")} if args.process else None)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = str(THIS_DIR / ("preflight_extend_%s_%s.log"
                               % ("-".join(sorted(era_filter)) if era_filter else "allEras", ts)))

    note("=" * 84)
    note("TtbarIdExtender CRAB PREFLIGHT (read-only)")
    note("  datasets    : %s" % args.datasets)
    note("  site config : %s" % args.site_config)
    note("  era filter  : %s" % (sorted(era_filter) if era_filter else "(none -> all)"))
    note("  proc filter : %s" % (sorted(proc_filter) if proc_filter else "(none -> all)"))
    note("  DAS check   : %s" % ("ON (--check-das)" if args.check_das else "OFF (add --check-das)"))
    note("  time        : %s" % datetime.datetime.now().isoformat(timespec="seconds"))
    note("=" * 84)

    # ---- 1. environment ------------------------------------------------------
    cmssw = os.environ.get("CMSSW_BASE", "")
    if not cmssw:
        bad("env CMSSW_BASE", "unset -- run cmsenv inside CMSSW_10_6_32_patch1/src")
    elif "CMSSW_10_6_" not in os.environ.get("CMSSW_VERSION", ""):
        warn("env CMSSW_VERSION", "%s (this package is pinned to CMSSW_10_6_32_patch1)"
             % os.environ.get("CMSSW_VERSION", "?"))
    else:
        ok("env CMSSW", "%s" % os.environ.get("CMSSW_VERSION"))
    try:
        import CRABClient  # noqa: F401
        ok("CRABClient import", "ok")
    except Exception as e:
        bad("CRABClient import", "%s -- source /cvmfs/cms.cern.ch/common/crab-setup.sh" % e)
    try:
        out = subprocess.run(["voms-proxy-info", "-timeleft"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True)
        left = int((out.stdout or "0").strip() or 0)
        if left <= 0:
            bad("VOMS proxy", "expired/absent -- voms-proxy-init -voms cms -rfc --valid 192:00")
        elif left < 24 * 3600:
            warn("VOMS proxy", "only %.1f h left" % (left / 3600.0))
        else:
            ok("VOMS proxy", "%.1f h left" % (left / 3600.0))
    except (OSError, ValueError) as e:
        bad("VOMS proxy", "voms-proxy-info unusable: %s" % e)

    # ---- 2. pset + year handling --------------------------------------------
    if os.path.isfile(EXTEND_PSET):
        ok("pset present", EXTEND_PSET)
        src = open(EXTEND_PSET).read()
        try:
            compile(src, EXTEND_PSET, "exec")
            ok("pset compiles", "syntax ok (import-time behaviour not tested)")
        except SyntaxError as e:
            bad("pset compiles", str(e)[:140])
        if 'opts.register("year"' in src or "opts.register('year'" in src:
            ok("pset year option", "present -- submitter passes year=<era>")
        else:
            bad("pset year option",
                "MISSING: the pset has no `year` VarParsing option, so the era "
                "modifier stays hardcoded regardless of the era being submitted")
    else:
        bad("pset present", "not found: %s" % EXTEND_PSET)

    # ---- 3. site config -----------------------------------------------------
    lfn = str(site.get("out_lfn_base") or "")
    if "__YOUR_CERN_USERNAME__" in lfn:
        bad("out_lfn_base", "still contains the placeholder username")
    elif not lfn.startswith("/store/"):
        bad("out_lfn_base", "should start with /store/ : %r" % lfn)
    else:
        ok("out_lfn_base", lfn)
    ok("storage site", str(site.get("storage_site")))
    work_area = str(site.get("work_area", "crab_projects"))
    ok("work_area", work_area)

    # ---- 4. era blocks / datasets ------------------------------------------
    eras = (cat.get("eras") or {})
    if not eras:
        bad("datasets.yaml eras", "no eras defined")
        return _preflight_finish(rows, lines, log_path)
    ok("datasets.yaml eras", ", ".join(sorted(eras.keys())))
    if era_filter:
        unknown = era_filter - set(eras.keys())
        if unknown:
            bad("--era value", "not in datasets.yaml: %s" % sorted(unknown))

    total_sel = n_enabled = n_verified = 0
    for era, block in sorted(eras.items()):
        if era_filter and era not in era_filter:
            continue
        note("-" * 84)
        note("era %s  (global_tag: %s | era_modifiers: %s)"
             % (era, block.get("global_tag"), block.get("era_modifiers")))
        ds_list = block.get("datasets") or []
        if not ds_list:
            bad("era %s datasets" % era, "empty")
            continue
        for d in ds_list:
            name = d.get("name", "?")
            if proc_filter and name not in proc_filter:
                continue
            total_sel += 1
            mini, nano = d.get("dataset", ""), d.get("nano_child", "")
            en, ver = bool(d.get("enabled")), bool(d.get("verified"))
            n_enabled += en
            n_verified += ver
            tags = []
            if not _DS_RE.match(str(mini)) or not str(mini).endswith("MINIAODSIM"):
                bad("%s/%s dataset syntax" % (era, name), "not a MINIAODSIM path: %r" % mini)
            if not _DS_RE.match(str(nano)) or not str(nano).endswith("NANOAODSIM"):
                bad("%s/%s nano_child syntax" % (era, name), "not a NANOAODSIM path: %r" % nano)
            # campaign/era coherence: the era key must appear in both campaign strings
            camp_mini = str(mini).split("/")[2] if str(mini).count("/") >= 3 else ""
            camp_nano = str(nano).split("/")[2] if str(nano).count("/") >= 3 else ""
            if era not in camp_mini or era not in camp_nano:
                bad("%s/%s campaign vs era" % (era, name),
                    "era key not found in campaign strings (mini=%s, nano=%s)" % (camp_mini, camp_nano))
            else:
                tags.append("campaign-era ok")
            # primary dataset must be identical on both sides
            if str(mini).split("/")[1:2] != str(nano).split("/")[1:2]:
                bad("%s/%s primary match" % (era, name),
                    "MiniAOD and Nano primary datasets differ")
            else:
                tags.append("primary match")
            if en and not ver:
                bad("%s/%s state" % (era, name),
                    "enabled:true but verified:false -- resolve the MiniAOD parent first "
                    "(bash crab/resolve_parents.sh %s)" % era)
            elif not en:
                warn("%s/%s state" % (era, name),
                     "enabled:false -> will be SKIPPED (verified=%s). Open it after "
                     "resolve_parents.sh %s" % (ver, era))
            else:
                ok("%s/%s state" % (era, name), "enabled+verified; " + ", ".join(tags))
            req = "%s_%s_extend" % (name, era)
            tag = (site.get("request_name_tag") or "").strip()
            if tag:
                req += "_%s" % tag
            proj = os.path.join(work_area, "crab_%s" % req)
            if os.path.isdir(proj):
                warn("%s/%s existing project" % (era, name),
                     "%s exists -> submit would be SKIPPED (rm -rf to retry)" % proj)
            note("        requestName=%-34s outLFN=%s/%s" % (req, lfn, era))

    note("-" * 84)
    ok("selected datasets", "%d (enabled=%d, verified=%d)" % (total_sel, n_enabled, n_verified))
    if total_sel and n_enabled == 0:
        warn("submittable now", "0 -- every selected entry is enabled:false")

    # ---- 5. optional DAS check ---------------------------------------------
    if args.check_das:
        note("-" * 84)
        if subprocess.run(["which", "dasgoclient"], stdout=subprocess.PIPE).returncode != 0:
            bad("dasgoclient", "not found -- cannot verify datasets")
        else:
            for era, block in sorted(eras.items()):
                if era_filter and era not in era_filter:
                    continue
                for d in (block.get("datasets") or []):
                    name = d.get("name", "?")
                    if proc_filter and name not in proc_filter:
                        continue
                    for label, path in (("mini", d.get("dataset", "")),
                                        ("nano", d.get("nano_child", ""))):
                        # Must use -json: the PLAIN-TEXT output of
                        # `dasgoclient -query "summary dataset=..."` is a column
                        # layout, NOT `nevents=N`, so a regex over it never
                        # matches and every dataset is falsely reported
                        # unresolvable (all 14 FAILed on 2026-07-27 while the
                        # datasets were demonstrably fine -- CRAB accepted them
                        # and `dasgoclient -query "file dataset=..."` listed
                        # 10,010 files). Same bug was fixed earlier in
                        # NtupleForge/crab/submit_crab.py; it had not been
                        # propagated here. Structure follows the proven path in
                        # NtupleForge/script/das_ul18_scan.sh.
                        q = subprocess.run(["dasgoclient", "-query",
                                            "summary dataset=%s" % path, "-json"],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           universal_newlines=True)
                        nev = None
                        try:
                            for rec in json.loads(q.stdout or "[]"):
                                for smry in (rec.get("summary") or []):
                                    if smry.get("nevents") is not None:
                                        nev = int(smry["nevents"])
                                        break
                                if nev is not None:
                                    break
                        except (ValueError, TypeError, KeyError):
                            nev = None
                        if nev is None:      # plain-text fallback, just in case
                            m = re.search(r"nevents\s*[:=]\s*(\d+)", q.stdout or "")
                            nev = int(m.group(1)) if m else None
                        if nev is not None:
                            ok("DAS %s/%s %s" % (era, name, label),
                               "nevents=%s" % format(nev, ","))
                        else:
                            bad("DAS %s/%s %s" % (era, name, label),
                                "not resolvable -- wrong -vN suffix? %s" % path)
    return _preflight_finish(rows, lines, log_path)


def _preflight_finish(rows, lines, log_path):
    n_fail = sum(1 for l, _, _ in rows if l == "FAIL")
    n_warn = sum(1 for l, _, _ in rows if l == "WARN")
    n_pass = sum(1 for l, _, _ in rows if l == "PASS")
    tail = ["-" * 84,
            "PREFLIGHT SUMMARY: %d PASS, %d WARN, %d FAIL" % (n_pass, n_warn, n_fail),
            ("RESULT: NOT READY TO SUBMIT -- fix the FAIL items above." if n_fail
             else "RESULT: READY TO SUBMIT" + (" (review the WARNs first)" if n_warn else ""))]
    for t in tail:
        print(t)
    lines.extend(tail)
    try:
        with open(log_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print("Log written: %s" % log_path)
    except OSError as e:
        print("WARNING: could not write log %s: %s" % (log_path, e))
    return 1 if n_fail else 0


# ----- Main --------------------------------------------------------------
def main():
    args = parse_args()
    cat  = load_yaml(args.datasets)
    site = load_yaml(args.site_config)

    if args.preflight:
        sys.exit(run_preflight(args, cat, site))

    if "__YOUR_CERN_USERNAME__" in (site.get("out_lfn_base") or ""):
        sys.exit("ERROR: site_config.yaml still has the placeholder username "
                 "in out_lfn_base.  Edit it before submitting.")

    proc_filter = ({s.strip() for s in args.process.split(",")}
                   if args.process else None)
    era_filter  = ({s.strip() for s in args.era.split(",")}
                   if args.era else None)

    # Which mode are we in? submit (default), or a bulk action on existing tasks.
    chosen = [a for a in ("resubmit", "status", "kill")
              if getattr(args, a)]
    if len(chosen) > 1:
        sys.exit("ERROR: choose only one of --resubmit / --status / --kill.")
    bulk_action = chosen[0] if chosen else None

    # kill is destructive: confirm which samples first, unless --yes.
    if bulk_action == "kill" and not args.yes:
        sel = args.process or "ALL enabled+listed samples"
        era_sel = args.era or "all eras"
        ans = input(f"About to 'crab kill' -- process={sel}, era={era_sel}. "
                    f"Continue? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            sys.exit("Aborted (no jobs killed).")

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
    label = {"resubmit": "resubmitted", "status": "queried",
             "kill": "killed"}.get(bulk_action, "submitted")
    print(f"  {label:9s} : {n_submitted}")


if __name__ == "__main__":
    main()
