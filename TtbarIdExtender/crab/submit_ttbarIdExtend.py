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
import contextlib
import datetime
import io
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

# =============================================================================
# Job-state buckets for --report
# =============================================================================
# DELIBERATELY IDENTICAL to NtupleForge/crab/submit_crab.py (same column names,
# same bucket rules, same "others"/unknown handling) so that a report from the
# two campaigns can be read side by side without re-learning the columns.
# If you change one, change the other -- that duplication is intentional and
# is noted in both files.
#
# Why "transferring" gets its own column: with units_per_job=1 the extend
# campaign has ~21k jobs, and a large fraction sits in `transferring` for a long
# time (stage-out to T3_CH_CERNBOX). crab/status.py used to omit it, so
# done+run+idle+fail did not add up to the total and those jobs were invisible.
REPORT_COLUMNS = ["finished", "running", "idle", "transferring", "failed"]
# Known-but-minor states folded into "others" WITHOUT raising an unknown warning.
KNOWN_OTHER_STATES = {
    "unsubmitted", "cooloff", "held", "killed", "killing",
    "toRetry", "on hold", "resubmitting",
}


def summarize_status(jobs_per_status):
    """Bucket a CRAB ``jobsPerStatus`` dict into REPORT_COLUMNS + others/total.

    Returns ``(row, unknown)``. ``unknown`` is the set of state names that are
    neither a column nor a known-other state, so the caller can warn: an
    unrecognised state silently hiding in "others" is exactly how you lose track
    of jobs.
    """
    row = {c: 0 for c in REPORT_COLUMNS}
    row["others"] = 0
    unknown = set()
    for state, n in (jobs_per_status or {}).items():
        if state in REPORT_COLUMNS:
            row[state] += n
        else:
            row["others"] += n
            if state not in KNOWN_OTHER_STATES:
                unknown.add(state)
    row["total"] = sum(row[c] for c in REPORT_COLUMNS) + row["others"]
    return row, unknown


def print_report(rows):
    """Print a compact per-sample job-state table. ``rows``: list of (name, row)."""
    cols = REPORT_COLUMNS + ["others", "total"]
    head = {"finished": "done", "running": "run", "idle": "idle",
            "transferring": "transf", "failed": "fail", "others": "other",
            "total": "total"}
    name_w = max([len("sample")] + [len(n) for n, _ in rows])
    header = "%-*s  " % (name_w, "sample") + "  ".join(
        "%6s" % head[c] for c in cols)
    bar = "=" * len(header)
    print("\n" + bar)
    print("CRAB job report (per sample)  [done=finished, transf=transferring]")
    print(bar)
    print(header)
    print("-" * len(header))
    agg = {c: 0 for c in cols}
    for name, row in rows:
        print("%-*s  " % (name_w, name) + "  ".join(
            "%6d" % row[c] for c in cols))
        for c in cols:
            agg[c] += row[c]
    print("-" * len(header))
    print("%-*s  " % (name_w, "TOTAL") + "  ".join(
        "%6d" % agg[c] for c in cols))
    print(bar)


def report_one(cfg, *, short_name, rows, unknown_acc):
    """Query one task quietly and append its bucketed row to ``rows``.

    Unlike --status (which lets `crab status` print its full dump), this
    swallows CRAB's stdout and keeps only the jobsPerStatus dict, so the table
    at the end is not buried under 7 screens of per-task output.
    """
    proj = Path(cfg.General.workArea) / ("crab_%s" % cfg.General.requestName)
    if not proj.exists():
        print("  [skip] no project dir: %s" % proj)
        rows.append((short_name, summarize_status({})[0]))
        return False
    try:
        from CRABAPI.RawCommand import crabCommand
    except ImportError as exc:
        sys.exit("ERROR: CRAB client missing (%s).\n"
                 "       source /cvmfs/cms.cern.ch/common/crab-setup.sh" % exc)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            res = crabCommand("status", dir=str(proj))
    except Exception as exc:  # noqa: BLE001
        print("  [status FAILED] %s" % exc)
        rows.append((short_name, summarize_status({})[0]))
        return False
    row, unk = summarize_status(res.get("jobsPerStatus", {}))
    rows.append((short_name, row))
    unknown_acc |= unk
    print("  [ok] task status = %s" % res.get("status", "?"))
    return True


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
                        "every selected sample -- FULL CRAB output per task. "
                        "Use --report instead if you just want the numbers. "
                        "Does not submit new tasks.")
    p.add_argument("--report",   action="store_true",
                   help="Compact per-sample job-state table "
                        "(done/run/idle/transf/fail/other/total + TOTAL row). "
                        "Same columns as NtupleForge's submit_crab.py --report. "
                        "Honors --process / --era. Does not submit new tasks.")
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


# --- Outcome classification for bulk actions ---------------------------------
# WHY THIS EXISTS (2026-07-27): `crabCommand("resubmit", ...)` is not honest
# through its return path. Three distinct things used to collapse into two
# misleading labels:
#
#   1. "Found no jobs to resubmit. Only jobs in status failed can be
#      resubmitted."  -> RAISES, so it printed "[resubmit FAILED]".
#      But this is the GOOD case: there are no failed jobs. Nothing is wrong.
#   2. "The task has not been submitted to the Grid scheduler yet ...
#      will not proceed with the resubmission."  -> does NOT raise; CRAB just
#      prints the refusal and returns. So it printed "[resubmit ok]" and was
#      COUNTED AS RESUBMITTED even though nothing happened. That is the
#      dangerous one -- you walk away thinking failed jobs were requeued.
#   3. "Resubmit request sent to the server."  -> the only real success.
#
# So we capture CRAB's stdout, echo it back, and classify on the text as well
# as on the exception. Never report a resubmit as done unless CRAB said it sent
# the request.
_RESUB_NOTHING = (
    "found no jobs to resubmit",
    "no jobs to resubmit",
)
_RESUB_REFUSED = (
    "will not proceed with the resubmission",
    "status information is unavailable",
    "has not been submitted to the grid scheduler yet",
)
_RESUB_SENT = (
    "resubmit request sent to the server",
)


def classify_resubmit(text, exc):
    """Return one of 'sent' / 'nothing' / 'refused' / 'error' for a resubmit.

    ``text`` is CRAB's captured stdout+stderr, ``exc`` the exception it raised
    (or None). Text wins over the exception, because CRAB reports the benign
    "no failed jobs" case by raising.
    """
    low = (text or "").lower()
    blob = low + " " + (str(exc) or "").lower()
    if any(p in blob for p in _RESUB_NOTHING):
        return "nothing"
    if any(p in blob for p in _RESUB_REFUSED):
        return "refused"
    if any(p in low for p in _RESUB_SENT):
        return "sent"
    if exc is not None:
        return "error"
    # No recognised marker and no exception: do NOT claim success.
    return "unclear"


_ACTION_OUTCOME_LABEL = {
    "sent":    "[resubmit SENT]      request accepted by the server",
    "nothing": "[resubmit -- NOTHING TO DO]  no failed jobs (this is fine)",
    "refused": "[resubmit REFUSED]   CRAB declined; nothing was requeued",
    "error":   "[resubmit ERROR]",
    "unclear": "[resubmit UNCLEAR]   no recognised marker in CRAB output -- "
               "check by hand with --report",
}


def crab_action_one(cfg, *, action):
    """Run 'crab resubmit' / 'crab status' / 'crab kill' on an existing project dir.

    Returns an outcome string:
      'noproj'                                  project dir missing
      'ok' / 'error'                            for status / kill
      'sent'/'nothing'/'refused'/'error'/'unclear'   for resubmit (see
                                                classify_resubmit)
    Only 'sent' means a resubmit actually took effect.
    """
    proj = Path(cfg.General.workArea) / f"crab_{cfg.General.requestName}"
    print(f"  request    : {cfg.General.requestName}")
    print(f"  project    : {proj}")
    if not proj.exists():
        print(f"  [skip] no project dir (nothing to {action})\n")
        return "noproj"
    try:
        from CRABAPI.RawCommand import crabCommand
    except ImportError as exc:
        sys.exit(f"ERROR: CRAB client missing ({exc}).\n"
                 f"       source /cvmfs/cms.cern.ch/common/crab-setup.sh")

    buf = io.StringIO()
    exc = None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            crabCommand(action, dir=str(proj))
    except Exception as e:  # noqa: BLE001
        exc = e
    out = buf.getvalue()
    # Echo CRAB's own words -- we classify, we do not hide.
    for line in out.splitlines():
        if line.strip():
            print("    | " + line.rstrip())

    if action != "resubmit":
        if exc is not None:
            print(f"  [{action} FAILED] {exc}\n")
            return "error"
        print(f"  [{action} ok]\n")
        return "ok"

    outcome = classify_resubmit(out, exc)
    msg = _ACTION_OUTCOME_LABEL[outcome]
    if outcome in ("error", "unclear") and exc is not None:
        msg += f" {exc}"
    print(f"  {msg}\n")
    return outcome


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
    chosen = [a for a in ("resubmit", "status", "report", "kill")
              if getattr(args, a)]
    if len(chosen) > 1:
        sys.exit("ERROR: choose only one of "
                 "--resubmit / --status / --report / --kill.")
    bulk_action = chosen[0] if chosen else None

    # --report accumulators (printed once after the loop so the columns align)
    report_rows = []
    report_unknown = set()

    # kill is destructive: confirm which samples first, unless --yes.
    if bulk_action == "kill" and not args.yes:
        sel = args.process or "ALL enabled+listed samples"
        era_sel = args.era or "all eras"
        ans = input(f"About to 'crab kill' -- process={sel}, era={era_sel}. "
                    f"Continue? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            sys.exit("Aborted (no jobs killed).")

    n_total = n_skipped = n_attempted = n_submitted = 0
    # Per-outcome tally for bulk actions (see crab_action_one). Kept separate
    # from n_submitted because "the command ran" != "something happened".
    outcomes = {}
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
            if bulk_action == "report":
                if report_one(cfg, short_name=name, rows=report_rows,
                              unknown_acc=report_unknown):
                    n_submitted += 1
            elif bulk_action is not None:
                oc = crab_action_one(cfg, action=bulk_action)
                outcomes[oc] = outcomes.get(oc, 0) + 1
                # Only a real effect counts. For resubmit that is 'sent' alone.
                if (oc == "sent") or (bulk_action != "resubmit" and oc == "ok"):
                    n_submitted += 1
            else:
                if submit_one(cfg, dry_run=args.dry_run):
                    n_submitted += 1

    # -- Post-loop: the compact table (if requested) --
    if bulk_action == "report":
        if report_rows:
            print_report(report_rows)
        if report_unknown:
            print("\n[WARN] Unknown CRAB job state(s) counted under 'others': %s"
                  % sorted(report_unknown))
            print("       The report code does not recognise these -- add them to "
                  "REPORT_COLUMNS / KNOWN_OTHER_STATES near the top of this file "
                  "(see summarize_status()), and read the full "
                  "`crab status -d <project_dir>` output for what they mean.")
            print("       Keep the same change in NtupleForge/crab/submit_crab.py "
                  "so the two reports stay comparable.")

    print("=" * 65)
    mode = bulk_action or ("submit" + (" (DRY RUN)" if args.dry_run else ""))
    print(f"  mode      : {mode}")
    print(f"  scanned   : {n_total}")
    if bulk_action is None:
        print(f"  skipped   : {n_skipped}  (enabled:false; use --force to override)")
    print(f"  attempted : {n_attempted}")
    label = {"resubmit": "resubmitted", "status": "queried",
             "report": "queried", "kill": "killed"}.get(bulk_action, "submitted")
    print(f"  {label:9s} : {n_submitted}")

    # Per-outcome breakdown. Without this, "resubmitted : N" is ambiguous:
    # a task CRAB refused, and a task with no failed jobs, are not the same as
    # a task whose resubmit request was accepted.
    if bulk_action == "resubmit":
        expl = {
            "sent":    "request accepted by the server -- ACTUALLY RESUBMITTED",
            "nothing": "no failed jobs -> nothing to do (GOOD, not an error)",
            "refused": "CRAB declined (task not on the scheduler yet, or status "
                       "unavailable) -> NOTHING was requeued; run again later",
            "unclear": "no recognised marker -> verify with --report",
            "error":   "command raised for another reason",
            "noproj":  "no crab_* project dir here (e.g. submitted from a "
                       "different checkout -- see docs/08_troubleshooting T-13)",
        }
        print("  " + "-" * 61)
        print("  resubmit outcome breakdown:")
        for key in ("sent", "nothing", "refused", "unclear", "error", "noproj"):
            if outcomes.get(key):
                print(f"    {key:8s} {outcomes[key]:3d}   {expl[key]}")
        if outcomes.get("refused"):
            print("  NOTE: 'refused' tasks were NOT resubmitted. Re-run "
                  "--resubmit for them in a few minutes.")
        if not outcomes.get("sent"):
            print("  => Nothing was actually resubmitted in this pass.")
    elif bulk_action in ("status", "kill") and outcomes:
        print(f"  outcomes  : " + ", ".join(
            f"{k}={v}" for k, v in sorted(outcomes.items())))


if __name__ == "__main__":
    main()
