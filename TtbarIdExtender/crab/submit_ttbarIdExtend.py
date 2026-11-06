#!/usr/bin/env python3
# =============================================================================
# CRAB submitter for extend (Approach 3) production
# =============================================================================
# Reads datasets.yaml and site_config.yaml; for each entry where enabled:true,
# builds a CRAB Configuration object and submits.
#
# Typical use:
#   cmsenv                                      # inside CMSSW_10_6_X/src (Run 2 eras)
#                                               # or CMSSW_15_0_X/src (eras 2022, 2022EE,
#                                               # 2023, 2023BPix, 2024; cmssw-el8)
#   source /cvmfs/cms.cern.ch/common/crab-setup.sh
#   voms-proxy-init -voms cms -valid 192:00
#   python3 crab/submit_ttbarIdExtend.py --dry-run                    # preview
#   python3 crab/submit_ttbarIdExtend.py --process TTHHto4b --max-files 5  # smoke test
#   python3 crab/submit_ttbarIdExtend.py                              # all enabled
#   python3 crab/submit_ttbarIdExtend.py --request <name> --crab-dryrun   # crab submit --dryrun
#
# Every submission run (--dry-run and --crab-dryrun too) first builds and checks
# ALL its tasks and writes the task PLAN (TSV) before the first submit; one
# refused task (lumi mask missing / other md5, a duplicate request name, ...)
# means nothing is submitted (exit 3). When the run ends -- also when it is
# interrupted -- it writes the task RECORD: the plan's rows plus an outcome per
# task. See build_config(), task_table_paths() and write_task_tsv().
# Exit status of a submission run (unchanged; launch_extend.sh greps the
# output): 0 even if a task failed or was skipped -- the [FAILED] / [skip] lines
# and the record say so; 3 = refused before the first submission; 1 = an
# argument or setup error (sys.exit with a message).
# --crab-dryrun tasks live in their own work area, <work_area>_dryrun: a dry-run
# task stays UPLOADED there and is never submitted; the real submission is a
# fresh plain submit with its own project dir under <work_area>.
#
# Why a Python submitter and not a static crab_cfg.py?  Because we have a
# (process x era) matrix to walk and want fail-fast iteration; hand-editing
# request names / output LFNs across 20 templates would be busywork plus a
# reliable source of typos.
#
# !! PYTHON 3.6 ONLY -- DO NOT USE 3.7+ APIs !!
#   This package is pinned to CMSSW_10_6_32_patch1, whose python is 3.6.4
#   (era 2024 is submitted from CMSSW_15_0_X, python 3.9; the 3.6 rules keep
#   one file working in both).
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
import hashlib
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

# CRAB refuses any task whose splitting generates more than this many jobs.
# The refusal happens SERVER-SIDE, after the client has already reported a
# successful submit -- see the T-19 note in the --check-das block below.
CRAB_MAX_JOBS_PER_TASK = 10000

# requestName -> where its unitsPerJob came from, filled by build_config() and
# echoed by submit_one(). A plain dict rather than an attribute on the CRAB
# Configuration object, because that object is validated by CRABClient and does
# not want stray fields. See T-20.
_UPJ_SOURCE = {}

# ---- 2022-23 eras (2026-11-06, TTHHAnalyzer STEP 47, docs/04_decisions.md D25)
# The Data.lumiMask files of the MiniAODv3 entries. datasets.yaml names the
# file (lumi_mask, a bare file name in this directory) and its md5
# (lumi_mask_md5); build_config() refuses the task when the file is missing or
# its md5 differs, and a submission run with a refused task submits nothing.
LUMI_MASK_DIR = THIS_DIR / "lumimasks"

# CRAB's limit on General.requestName ("The maximum allowed length is 100
# characters", twiki CMSPublic/CRAB3ConfigurationFile r99, read 2026-11-06).
CRAB_MAX_REQUEST_NAME = 100

# miniaod_version -> the extract priority written in the task table:
#   extractTtbarIdPatch --input <NanoAOD dataset>=<filelist>:<priority>
# keeps, within one NanoAOD dataset, the row of the LOWER number (MiniAODv4 0
# over MiniAODv3 1; Validation/tools/extractTtbarIdPatch.cc, docs/07 sec.5).
# Entries without miniaod_version (every era before 2022-23) get 0.
EXTRACT_PRIORITY = {"v4": 0, "v3": 1}
# nano_role: which central NanoAODv12 dataset (nano_child) the task's events
# belong to. A MiniAODv3 task belongs to the MAIN dataset.
NANO_ROLES = ("main", "ext1")

# The task tables of a submission run (--dry-run included) go here unless
# --task-table names the plan: the PLAN (TASK_TABLE_COLUMNS, written before the
# first submission) and the RECORD (the same rows + `outcome`, written when the
# run ends). Git-ignored: the real submission's two tables are kept in lxplus's
# daily attachments in TTHHAnalyzer (README sec.2.2f).
TASK_TABLE_DIR = THIS_DIR / "task_tables"
TASK_TABLE_COLUMNS = ["request_name", "era", "sample", "nano_role", "miniaod_version",
                      "miniaod_dataset", "nano_dataset", "extract_priority",
                      "lumi_mask", "lumi_mask_md5", "units_per_job", "pset_year",
                      "out_lfn_dir_base"]
# outcome of a task in the record:
#   submitted                 crab submit went through (the task is on the CRAB server)
#   dryrun-uploaded           --crab-dryrun: uploaded and split, never submitted
#   skipped-existing-project  its project dir existed, nothing was done
#   failed                    crab submit failed, or the run was interrupted while
#                             submitting it (state unknown -- check by hand)
#   not-attempted             not reached (--dry-run, or the run stopped before it)
TASK_OUTCOMES = ("submitted", "dryrun-uploaded", "skipped-existing-project", "failed",
                 "not-attempted")

# --crab-dryrun uses its own CRAB work area: site_config's work_area + this, e.g.
# crab_projects_dryrun/ (2026-11-06). A dry-run task (UPLOADED, never run) can
# then never share a project dir with the real submission of the same task.
DRYRUN_WORK_AREA_SUFFIX = "_dryrun"


def dryrun_work_area(site_cfg):
    """The CRAB work area of --crab-dryrun: <work_area>_dryrun."""
    return str(site_cfg.get("work_area", "crab_projects")) + DRYRUN_WORK_AREA_SUFFIX

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


# Task-level states meaning "nothing will ever run in this task". These are NOT
# job states: jobsPerStatus is empty, so the --report row is all zeros and looks
# indistinguishable from "just submitted, not started yet". They must be called
# out or a dead task hides in plain sight (2026-07-27: 2018 TTbar_SemiLep sat
# SUBMITREFUSED for a day because 10,010 > the 10,000 jobs/task CRAB limit --
# docs/08_troubleshooting.md T-19).
DEAD_TASK_STATES = ("SUBMITREFUSED", "SUBMITFAILED", "FAILED", "UNKNOWN")

# Task state of a `crab submit --dryrun` task (2026-11-06): uploaded and split,
# then paused -- no job runs. Not dead, not [ok]: reported in its own block.
UPLOADED_TASK_STATES = ("UPLOADED",)


def report_one(cfg, *, short_name, rows, unknown_acc, dead_acc=None, uploaded_acc=None):
    """Query one task quietly and append its bucketed row to ``rows``.

    Unlike --status (which lets `crab status` print its full dump), this
    swallows CRAB's stdout and keeps only the jobsPerStatus dict, so the table
    at the end is not buried under 7 screens of per-task output. The exception
    is a dead task: then the captured text is echoed, because that text carries
    the reason (job-count limit, stage-out permission, ...). A task in UPLOADED
    (a `crab submit --dryrun` task, 2026-11-06) goes to ``uploaded_acc``: its
    row of zeros means "uploaded, not running", never "not started yet".
    ``short_name`` is the label of the row: <era>/<name>[label] (task_id()).
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
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            res = crabCommand("status", dir=str(proj))
    except Exception as exc:  # noqa: BLE001
        print("  [status FAILED] %s" % exc)
        rows.append((short_name, summarize_status({})[0]))
        return False
    row, unk = summarize_status(res.get("jobsPerStatus", {}))
    rows.append((short_name, row))
    unknown_acc |= unk
    tstat = str(res.get("status", "?"))
    if tstat.upper() in DEAD_TASK_STATES:
        if dead_acc is not None:
            dead_acc.append((short_name, tstat))
        print("  [!! %s !!] this task will NEVER run. --resubmit CANNOT fix it "
              "(resubmit only requeues FAILED jobs of a task that reached the "
              "scheduler); the task has to be re-submitted after fixing the "
              "cause. CRAB said:" % tstat)
        for line in buf.getvalue().splitlines():
            s = line.strip()
            if any(k in s for k in ("Warning:", "Error", "maximum number",
                                    "Status on the CRAB server", "refused",
                                    "Permission")):
                print("    | " + s)
    elif tstat.upper() in UPLOADED_TASK_STATES:
        if uploaded_acc is not None:
            uploaded_acc.append((short_name, tstat))
        print("  [UPLOADED -- uploaded, not running] task status = %s: a `crab submit "
              "--dryrun` task -- CRAB split it but runs no job. It is not the real "
              "submission of this task." % tstat)
    else:
        print("  [ok] task status = %s" % tstat)
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
    p.add_argument("--request",
                   help="Comma-separated request names (exactly as --dry-run prints "
                        "them): only those tasks. Picks ONE task where a name has "
                        "several entries in an era (2022-23: main, ext1, v3). An "
                        "unknown name is an error. Honored by every mode.")
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
                   help="Print plan but do not submit (no CRAB contact). Builds and "
                        "checks every task and writes the task plan and record like a "
                        "submit (every outcome not-attempted).")
    p.add_argument("--crab-dryrun", action="store_true",
                   help="'crab submit --dryrun' for the tasks named by --request "
                        "(required; comma-separated names allowed). CRABAPI "
                        "dryrun=True: CRAB uploads the task and does the splitting "
                        "(with Data.lumiMask) but submits nothing to the grid; it "
                        "prints 'Task consists of N jobs ...' and leaves the task "
                        "UPLOADED, where it stays: it is never submitted. The "
                        "project dir goes to its own work area <work_area>_dryrun "
                        "(e.g. crab_projects_dryrun/), so the real submission -- a "
                        "fresh plain submit -- is not affected.")
    p.add_argument("--task-table", default=None,
                   help="Where the task PLAN (TSV) of this submission run goes; the "
                        "RECORD (plan + outcome per task, written when the run ends) "
                        "goes next to it as <plan>_record.tsv. Default: "
                        "crab/task_tables/tasks_<eras>_<UTC>Z_<mode>_plan.tsv and "
                        "..._record.tsv (mode dryrun | crabdryrun | submit). An "
                        "existing file is never overwritten (exit 1, nothing "
                        "submitted).")
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
                   help="Skip the confirmation prompt for --kill; with "
                        "--clean-failed-shells, actually move the shells.")
    p.add_argument("--clean-failed-shells", action="store_true",
                   help="Find crab_projects dirs of the selected tasks that have no "
                        ".requestcache: the shell a FAILED submit leaves behind "
                        "(docs/08 T-16), which blocks a new submit. Lists them; with "
                        "--yes moves them to <work_area>/_failed_<UTC>/ (nothing is "
                        "deleted). Dirs WITH .requestcache are submitted tasks and "
                        "are never touched. Honors --process / --era.")
    return p.parse_args()


# ----- Task identity, pset year, lumi mask (2026-11-06, STEP 47) ---------
# The 2022-23 era blocks hold up to three entries with one `name` (MiniAODv4 of
# the main and of the ext1 NanoAODv12 dataset, MiniAODv3 of the main one), so
# `name` + era no longer identify a task. Every place that needs a request name
# (build_config, --preflight, --clean-failed-shells, --request) calls
# request_name(); for an entry without miniaod_version (all eras before
# 2022-23) and an era block without request_name_suffix it gives exactly the old
# <name>_<era>_extend[_<request_name_tag>].
class TaskRefused(Exception):
    """build_config() refuses a task (its lumi mask is missing or has another md5)."""


def request_label(dataset_entry):
    """The part of the request name between era and 'extend': '' for an entry
    without miniaod_version (every era before 2022-23), 'v3' for a MiniAODv3
    entry, else its nano_role ('main' | 'ext1'). The rule of the lxplus plan
    (crab_plan.py, 2026-11-06)."""
    ver = str(dataset_entry.get("miniaod_version") or "").strip()
    if not ver:
        return ""
    if ver == "v3":
        return "v3"
    return str(dataset_entry.get("nano_role") or "").strip()


def request_name(process_name, era, dataset_entry, era_block, site_cfg):
    """<name>_<era>[_<label>]_extend[_<era's request_name_suffix>][_<request_name_tag>]

    2022-23 (label main | ext1 | v3, suffix 'fp'): e.g. TTbar_Hadronic_2022_v3_extend_fp,
    the request_name column of the lxplus plan. Older eras: <name>_<era>_extend
    (+ _<request_name_tag>), unchanged. requestName = outputDatasetTag, so it also
    names the task's output directory under <out_lfn_base>/<era>/<primary>/.
    """
    rn = "%s_%s" % (process_name, era)
    label = request_label(dataset_entry)
    if label:
        rn += "_" + label
    rn += "_extend"
    suffix = str((era_block or {}).get("request_name_suffix") or "").strip()
    if suffix:
        rn += "_" + suffix
    tag = (site_cfg.get("request_name_tag") or "").strip()
    if tag:
        rn += "_" + tag
    return rn


def task_id(era, dataset_entry):
    """<era>/<name>[<label>] for log lines (<era>/<name> for the older eras)."""
    label = request_label(dataset_entry)
    return "%s/%s%s" % (era, dataset_entry.get("name", "?"),
                        "[%s]" % label if label else "")


def pset_year(era, era_block):
    """The year= value given to run_ttbarIdExtend_cfg.py: the era block's
    pset_year, else the era key itself (every era before 2022-23).

    2022, 2022EE, 2023, 2023BPix set pset_year "2024": the pset's year option
    knows 2016/2016APV/2017/2018/2024 only, the job is gen level and none of its
    modules is era-modified, and lxplus ran year=2024 on 2022-23 MiniAODv4 files
    (CMSSW_15_0_18, 2026-11-06) with the fingerprint and the ids equal to
    NanoAOD bit for bit -- the tested, era-neutral path (the pset is unchanged).
    """
    y = str((era_block or {}).get("pset_year") or "").strip()
    return y or era


def lumi_mask_path(dataset_entry):
    """Absolute path of the entry's lumi mask (crab/lumimasks/<lumi_mask>), or
    None when the entry has no lumi_mask."""
    name = str(dataset_entry.get("lumi_mask") or "").strip()
    if not name:
        return None
    return str(LUMI_MASK_DIR / name)


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expected_lumi_mask_name(era, name):
    """The mask file name an entry must use: crab_lumimask_<era>_<name>_v3.json
    (2026-11-06, review L4: a mask of another era or sample is refused)."""
    return "crab_lumimask_%s_%s_v3.json" % (era, name)


def mask_lumi_count(path):
    """(lumis, runs) of a CRAB lumi-mask JSON {"<run>": [[first, last], ...]}.
    ValueError when the file is not such a mask (bad JSON, a range with
    first > last, a non-integer run or lumi)."""
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    if not isinstance(d, dict):
        raise ValueError("not a JSON object of runs")
    n = 0
    for run, ranges in d.items():
        int(run)
        if not isinstance(ranges, list):
            raise ValueError("run %s: not a list of [first, last] ranges" % run)
        for rr in ranges:
            if not isinstance(rr, list) or len(rr) != 2:
                raise ValueError("run %s: range %r is not [first, last]" % (run, rr))
            a, b = int(rr[0]), int(rr[1])
            if a < 1 or b < a:
                raise ValueError("run %s: range [%d, %d]" % (run, a, b))
            n += b - a + 1
    return n, len(d)


def lumi_mask_problem(dataset_entry, era=None):
    """None when the entry has no lumi_mask, or when its file exists, has the
    md5 that lumi_mask_md5 names, is the entry's own mask (era given: the file
    name crab_lumimask_<era>_<name>_v3.json) and holds at least one lumi; else
    the reason (the task is refused)."""
    name = str(dataset_entry.get("lumi_mask") or "").strip()
    if not name:
        return None
    if os.path.basename(name) != name or name in (".", ".."):
        return ("lumi_mask %r must be a bare file name in %s" % (name, LUMI_MASK_DIR))
    if era is not None:
        want_name = expected_lumi_mask_name(era, dataset_entry.get("name", "?"))
        if name != want_name:
            return ("lumi_mask %s is not this entry's mask (want %s)" % (name, want_name))
    want = str(dataset_entry.get("lumi_mask_md5") or "").strip().lower()
    if not want:
        return "lumi_mask %s has no lumi_mask_md5 in datasets.yaml" % name
    path = lumi_mask_path(dataset_entry)
    if not os.path.isfile(path):
        return "lumi mask file missing: %s" % path
    got = file_md5(path)
    if got != want:
        return ("lumi mask %s has md5 %s, but datasets.yaml lumi_mask_md5 is %s"
                % (path, got, want))
    try:
        n_lumis, _n_runs = mask_lumi_count(path)
    except (OSError, ValueError, TypeError) as e:
        return "lumi mask %s is not a CRAB lumi mask (%s)" % (path, e)
    if n_lumis == 0:
        return "lumi mask %s holds 0 lumis" % path
    return None


def mask_summary(path):
    """'<lumis> lumis in <runs> run(s)' of a CRAB lumi-mask JSON, or why not."""
    try:
        n, runs = mask_lumi_count(path)
        return "%s lumis in %d run(s)" % (format(n, ","), runs)
    except (OSError, ValueError, TypeError, AttributeError) as e:
        return "not readable as a lumi mask (%s)" % e


# ----- Build one Configuration ------------------------------------------
def build_config(*, process_name, era, dataset_entry, site_cfg, era_block,
                 max_files=None, check_lumi_mask=True):
    """Return a CRAB Configuration with all fields populated.

    An entry with lumi_mask (the MiniAODv3 entries of 2022 / 2022EE) gets
    Data.lumiMask = the absolute path of crab/lumimasks/<lumi_mask>, after
    lumi_mask_problem(): the file is crab_lumimask_<era>_<name>_v3.json, exists,
    has the md5 of lumi_mask_md5 and holds at least one lumi (else TaskRefused).
    check_lumi_mask=False only for the bulk actions (status/report/resubmit/
    kill), which need the request name and nothing else. The work area is
    site_config's; main() moves --crab-dryrun tasks to dryrun_work_area().
    """
    from CRABClient.UserUtilities import config as _cfg
    cfg = _cfg()

    rn = request_name(process_name, era, dataset_entry, era_block, site_cfg)

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
    # this argument is ever dropped.)  The era key of datasets.yaml IS the year,
    # except where the era block sets pset_year (2026-11-06: the 2022-23 eras
    # run year=2024 -- see pset_year()).
    cfg.JobType.pyCfgParams    = ["outputFile=ttbarIDExtend.root",
                                  "year=%s" % pset_year(era, era_block)]
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
    # =========================================================================
    # !!  DO NOT LOWER units_per_job WITHOUT CHECKING THE JOB COUNT FIRST  !!
    # =========================================================================
    # FileBased splitting means:  njobs = ceil(nfiles / unitsPerJob).
    # CRAB REFUSES any task with more than CRAB_MAX_JOBS_PER_TASK (= 10,000)
    # jobs -- and it refuses it SILENTLY from the client's point of view:
    #   * `crab submit` returns success and this script prints "[submitted]"
    #   * the SERVER then parks the task as SUBMITREFUSED with
    #     "The splitting on your task generated N jobs. The maximum number of
    #      jobs in each task is 10000"
    #   * jobsPerStatus stays empty, so --report shows a row of all zeros,
    #     indistinguishable from "submitted, not started yet"
    #   * `crab resubmit` CANNOT fix it (it only requeues FAILED jobs of a task
    #     that reached the scheduler) -- the task must be re-submitted
    # Net effect: a whole sample produces nothing and you may not notice for
    # days. This happened on 2026-07-27 with 2018 TTbar_SemiLep (10,010 MiniAOD
    # files, units_per_job was 1 -> 10,010 jobs). See docs/08_troubleshooting.md
    # T-19 and docs/04_decisions.md D15.
    #
    # Guards in place (keep them):
    #   1. `--preflight --check-das` computes ceil(nfiles/units_per_job) per task
    #      from the DAS `nfiles` and FAILs above the limit (WARNs above 90%).
    #      ALWAYS run it before a campaign; it is the only pre-submission check.
    #   2. site_config.yaml resources.extend.units_per_job defaults to 10, which
    #      keeps every sample here far below the limit (largest = 1,001 jobs).
    #   3. datasets.yaml keeps an explicit per-entry units_per_job: 10 on
    #      TTbar_SemiLep as a floor -- that one cannot run at 1 under any
    #      circumstances.
    # Raising units_per_job is always safe for the job-count limit (fewer jobs)
    # and is physics-neutral: the consumer matches on (run, luminosityBlock,
    # event) across the whole filelist and never looks at file->job packing.
    # The only upward constraint is maxJobRuntimeMin (1440 min vs ~11 min/job at
    # units_per_job=10, i.e. ~130x headroom).
    if "units_per_job" in dataset_entry:
        _upj, _upj_src = int(dataset_entry["units_per_job"]), "datasets.yaml per-entry"
    elif "units_per_job" in res:
        _upj, _upj_src = int(res["units_per_job"]), "site_config resources.extend"
    else:
        _upj, _upj_src = 1, "hardcoded fallback (1) -- site_config key MISSING"
    cfg.Data.unitsPerJob = _upj
    _UPJ_SOURCE[cfg.General.requestName] = _upj_src
    if max_files is not None:
        cfg.Data.totalUnits  = int(max_files)
    cfg.Data.publication     = False
    cfg.Data.outLFNDirBase   = f"{site_cfg['out_lfn_base']}/{era}"
    cfg.Data.outputDatasetTag = rn
    # ---- Data.lumiMask (2026-11-06, STEP 47): the MiniAODv3 entries only ----
    # A v3 task must process ONLY the lumis of its mask: the events of those
    # lumis have no MiniAODv4 parent any more (lxplus 2026-11-05); the rest of
    # the v3 dataset duplicates the v4 tasks. The CRAB client reads the file at
    # submit time (a URL or a JSON path, twiki CRAB3ConfigurationFile) and the
    # server splits only the masked lumis. FileBased splitting is kept: nothing
    # in this code base or in that documentation says FileBased cannot carry a
    # lumi mask; the job count with the mask is confirmed by `crab submit
    # --dryrun` (--crab-dryrun) on lxplus before the real submission.
    mask = lumi_mask_path(dataset_entry)
    if mask is not None:
        if check_lumi_mask:
            why = lumi_mask_problem(dataset_entry, era)
            if why:
                raise TaskRefused("%s: %s" % (rn, why))
        cfg.Data.lumiMask    = mask

    # Site
    cfg.Site.storageSite     = site_cfg["storage_site"]
    if site_cfg.get("whitelist_sites"):
        cfg.Site.whitelist   = list(site_cfg["whitelist_sites"])
    if site_cfg.get("blacklist_sites"):
        cfg.Site.blacklist   = list(site_cfg["blacklist_sites"])

    return cfg


# ----- Submit one --------------------------------------------------------
def submit_one(cfg, *, dry_run, crab_dryrun=False):
    """Print the task, then submit it (or not). Returns (ok, outcome).

    ok keeps the old meaning (True: submitted, or listed by --dry-run, or
    uploaded by --crab-dryrun) and feeds the 'submitted :' count; outcome is the
    record's word (TASK_OUTCOMES).
    """
    print(f"  request    : {cfg.General.requestName}")
    print(f"  dataset    : {cfg.Data.inputDataset}")
    print(f"  storage    : {cfg.Site.storageSite} -> {cfg.Data.outLFNDirBase}")
    print(f"  pyCfgParams: {','.join(cfg.JobType.pyCfgParams) or '(none)'}")
    if getattr(cfg.Data, "lumiMask", None):
        # 2026-11-06: md5 already checked in build_config (else no submission)
        print("  lumiMask   : %s  (md5 checked; %s)"
              % (cfg.Data.lumiMask, mask_summary(cfg.Data.lumiMask)))
    # ---- effective resource settings, echoed per task (added 2026-07-27) ------
    # WHY: these were NOT in the submit log before, and that cost three rounds of
    # forensics. The 2026-07-27 18:50 resubmission ran 6 of 7 samples at
    # unitsPerJob=1 (only TTbar_SemiLep at 10) because the checkout had the
    # datasets.yaml per-entry override but not yet the site_config default bump;
    # the only surviving evidence was `config.Data.unitsPerJob` buried in each
    # crab_projects/*/crab.log. Printing it here makes "what settings did this
    # campaign actually use?" answerable from the tee'd submit log alone.
    # See docs/08_troubleshooting.md T-20.
    print(f"  splitting  : {cfg.Data.splitting}  unitsPerJob={cfg.Data.unitsPerJob}"
          f"  (source: {_UPJ_SOURCE.get(cfg.General.requestName, 'unknown')})")
    print(f"  resources  : maxMemoryMB={cfg.JobType.maxMemoryMB}"
          f"  maxJobRuntimeMin={cfg.JobType.maxJobRuntimeMin}")
    if hasattr(cfg.Data, "totalUnits"):
        print(f"  totalUnits : {cfg.Data.totalUnits}  (capped via --max-files)")

    if crab_dryrun:
        print("  work area  : %s  (crab submit --dryrun: the task stays UPLOADED, "
              "never submitted)" % cfg.General.workArea)
    if dry_run:
        print("  [dry-run]\n")
        return True, "not-attempted"

    proj = Path(cfg.General.workArea) / f"crab_{cfg.General.requestName}"
    if proj.exists():
        # 2026-11-06: never advise bumping request_name_tag -- it renames every
        # task of every era. One task again: move its dir aside, then --request.
        print(f"  [skip] project dir already exists: {proj}\n"
              f"         This task was submitted from here before (crab status -d {proj}).\n"
              f"         To submit this one task again: move the dir aside, e.g.\n"
              f"           mv {proj} {proj}.moved_$(date +%Y%m%d_%H%M%S)\n"
              f"         (a failed-submit shell without .requestcache: --clean-failed-shells --yes),\n"
              f"         then run again with --request {cfg.General.requestName}\n")
        return False, "skipped-existing-project"

    try:
        from CRABAPI.RawCommand import crabCommand  # noqa: F401  (import check only)
    except ImportError as exc:
        sys.exit(f"ERROR: CRAB client missing ({exc}).\n"
                 f"       source /cvmfs/cms.cern.ch/common/crab-setup.sh")

    # ONE PROCESS PER SUBMISSION (2026-10-14). The CRAB client imports the pset
    # once per Python process and refuses a second import with other parameters:
    #   "FATAL ERROR: A different CMSSW configuration was already cached. Either
    #    configuration file name or configuration parameters have been changed."
    # Every task of one era has the same pyCfgParams, so 2017 and 2018 (one era
    # per call) never hit it; --era 2016APV,2016 did: the 7 year=2016APV tasks
    # went out, all 7 year=2016 ones failed (docs/08 T-36). The CRAB
    # documentation's answer for scripted multi-submission is a separate process
    # per crabCommand('submit'), which is what this does (fork: the child inherits
    # the terminal, so a grid pass-phrase prompt still works interactively).
    import multiprocessing
    sys.stdout.flush()
    sys.stderr.flush()
    child = multiprocessing.get_context("fork").Process(target=_submit_in_child,
                                                        args=(cfg, crab_dryrun))
    child.start()
    child.join()
    if child.exitcode != 0:
        print(f"  [FAILED] crab submit exited {child.exitcode} in its own process (message above)\n")
        if crab_dryrun:
            # 2026-11-06 (review L2): the upload may have happened before the
            # failure (e.g. in the local test job).
            print("  [crab-dryrun FAILED] the dry-run project dir %s may exist (dry-run "
                  "work area %s). The real submission is NOT affected: it uses its own "
                  "project dir under the normal work area. Look at CRAB's message above, "
                  "%s/crab.log and, if the task was uploaded, crab status -d %s.\n"
                  % (proj, cfg.General.workArea, proj, proj))
        return False, "failed"
    if crab_dryrun:
        # 2026-11-06: `crab submit --dryrun` (twiki CMSPublic/CRAB3Commands r42):
        # the server splits the task but submits no job; the client prints
        # "Task consists of N jobs to process ..." and "Dry run requested: task
        # paused". The task is left UPLOADED in the dry-run work area: it never
        # runs and nobody submits it. The real submission is a fresh plain
        # submit (its own project dir under the normal work area).
        print("  [crab-dryrun] uploaded and split, NOTHING submitted to the grid. The job "
              "count is CRAB's 'Task consists of N jobs' line above.\n"
              "               The dry-run task stays UPLOADED in %s and is never "
              "submitted; the real submission is a separate plain submit.\n" % proj)
        return True, "dryrun-uploaded"
    print("  [submitted]\n")
    return True, "submitted"


def _submit_in_child(cfg, crab_dryrun=False):
    """Body of the per-task submit process (see submit_one).

    crab_dryrun: CRABAPI turns a keyword set to True into the long option, so
    dryrun=True is `crab submit --dryrun` (twiki CMSPublic/CRABClientLibraryAPI
    r36: an option that takes no value is given as keyword=True).
    """
    from CRABAPI.RawCommand import crabCommand
    try:
        if crab_dryrun:
            crabCommand("submit", config=cfg, dryrun=True)
        else:
            crabCommand("submit", config=cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"  [child] crab submit raised: {exc}")
        sys.stdout.flush()
        sys.exit(1)
    sys.stdout.flush()
    sys.exit(0)


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

# era key -> (MiniAODv2 campaign prefix, NanoAODv9 campaign prefix) for the
# "campaign vs era" check. Added 2026-10-14 with the 2016 eras: the old rule
# ("the era key is a substring of both campaign strings") only worked for 2017
# and 2018 because their global tags spell the year (mc2017_..., upgrade2018_...).
# UL16 campaigns say "UL16", their GT "mcRun2_asymptotic" has no year, and
# preVFP differs from postVFP only by "APV" -- a substring test cannot tell them
# apart. Same verdict as before for every 2017/2018 entry. Era keys missing from
# this table keep the old substring rule.
_ERA_CAMPAIGN_PREFIX = {
    "2016APV": ("RunIISummer20UL16MiniAODAPVv2-", "RunIISummer20UL16NanoAODAPVv9-"),
    "2016":    ("RunIISummer20UL16MiniAODv2-",    "RunIISummer20UL16NanoAODv9-"),
    "2017":    ("RunIISummer20UL17MiniAODv2-",    "RunIISummer20UL17NanoAODv9-"),
    "2018":    ("RunIISummer20UL18MiniAODv2-",    "RunIISummer20UL18NanoAODv9-"),
    # 2026-10-15 (Run 3): the NanoAODv15 children's MiniAOD parents; the MiniAOD
    # version is whatever DAS says (resolve_parents.sh 2024 --fill), so only the
    # campaign family is fixed here.
    "2024":    ("RunIII2024Summer24MiniAOD",      "RunIII2024Summer24NanoAODv15-"),
    # 2026-11-06 (STEP 47): the 2022-23 eras. The MiniAOD prefix depends on the
    # entry's miniaod_version -- MiniAODv4, or MiniAODv3 for the masked tasks of
    # 2022 / 2022EE -- so it is a {version: prefix} dict here; the child is
    # always NanoAODv12. Taken from the dataset names of the lxplus plan
    # crab_plan_2022-23.tsv (2026-11-06): campaign = the processed name up to
    # its first '-'. "Run3Summer22MiniAODv4-" is no prefix of
    # "Run3Summer22EEMiniAODv4-" (nor 23 of 23BPix), so neighbouring eras
    # cannot pass for each other, and a v4 dataset in a v3 entry fails.
    "2022":     ({"v4": "Run3Summer22MiniAODv4-",     "v3": "Run3Summer22MiniAODv3-"},
                 "Run3Summer22NanoAODv12-"),
    "2022EE":   ({"v4": "Run3Summer22EEMiniAODv4-",   "v3": "Run3Summer22EEMiniAODv3-"},
                 "Run3Summer22EENanoAODv12-"),
    "2023":     ({"v4": "Run3Summer23MiniAODv4-"},     "Run3Summer23NanoAODv12-"),
    "2023BPix": ({"v4": "Run3Summer23BPixMiniAODv4-"}, "Run3Summer23BPixNanoAODv12-"),
}

# era key -> the CMSSW_VERSION prefix its submission needs (2026-10-15). The
# 10_6 release cannot read Run 3 MiniAOD and has no Run3_2024 era; one CRAB
# submission (one pset import) serves one release, so eras of two families are
# never handled in one call. Era keys missing here count as Run 2 (10_6).
# 2026-11-06: 2022, 2022EE, 2023, 2023BPix like 2024 (they run year=2024, see
# pset_year()); one call may mix them with 2024, never with a Run 2 era.
_ERA_CMSSW_PREFIX = {
    "2016APV": "CMSSW_10_6_",
    "2016":    "CMSSW_10_6_",
    "2017":    "CMSSW_10_6_",
    "2018":    "CMSSW_10_6_",
    "2024":    "CMSSW_15_0_",
    "2022":    "CMSSW_15_0_",
    "2022EE":  "CMSSW_15_0_",
    "2023":    "CMSSW_15_0_",
    "2023BPix": "CMSSW_15_0_",
}


def _is_run2_era(era):
    """True for the CMSSW_10_6 (Run 2 UL) eras; unknown keys count as Run 2,
    like release_problem() does."""
    return _ERA_CMSSW_PREFIX.get(era, "CMSSW_10_6_") == "CMSSW_10_6_"


def release_problem(eras):
    """None if CMSSW_VERSION fits every era in `eras`, else the reason."""
    eras = sorted(eras)
    if not eras:
        return None
    need = sorted({_ERA_CMSSW_PREFIX.get(e, "CMSSW_10_6_") for e in eras})
    if len(need) > 1:
        return ("eras %s need different releases (%s) -- give --era for one "
                "release at a time" % (",".join(eras), " and ".join(n + "X" for n in need)))
    have = os.environ.get("CMSSW_VERSION", "")
    if not have.startswith(need[0]):
        return ("CMSSW_VERSION=%s, but era(s) %s need %sX (Run 2: CMSSW_10_6_32_patch1 "
                "in cmssw-el7; Run 3 -- 2022, 2022EE, 2023, 2023BPix, 2024: "
                "~/TTHHGenCategoryTools_v15/CMSSW_15_0_18 in cmssw-el8)"
                % (have or "unset", ",".join(eras), need[0]))
    return None


def acted_eras(cat, era_filter, proc_filter, force=False, req_filter=None, site=None):
    """Eras that a submission with these filters would touch: selected by
    --era (all when absent) and holding at least one selected enabled entry
    (any selected entry with --force). An entry whose dataset: is still ""
    (a new era before resolve_parents.sh --fill) is never submitted, so it
    does not count (2026-10-15 review: a closed 2024 block made --force
    without --era refuse a Run 2 submission). req_filter (--request, 2026-11-06)
    needs `site` for the request names."""
    out = set()
    for era, block in (cat.get("eras") or {}).items():
        if era_filter and era not in era_filter:
            continue
        for d in (block.get("datasets") or []):
            if proc_filter and d.get("name") not in proc_filter:
                continue
            if req_filter and request_name(d.get("name"), era, d, block,
                                           site or {}) not in req_filter:
                continue
            if not str(d.get("dataset") or "").strip():
                continue        # dataset: "" is never submitted (see main())
            if force or d.get("enabled", False):
                out.add(era)
                break
    return out


def campaign_matches_era(era, camp_mini, camp_nano, miniaod_version=None):
    """True if both campaign strings belong to the datasets.yaml era key.

    2026-11-06: for the eras whose MiniAOD prefix is per version (2022-23) the
    entry's miniaod_version picks it; an unknown or missing version is False.
    """
    pref = _ERA_CAMPAIGN_PREFIX.get(era)
    if pref is None:
        return era in camp_mini and era in camp_nano
    mini_pref = pref[0]
    if isinstance(mini_pref, dict):
        mini_pref = mini_pref.get(str(miniaod_version or "").strip())
        if mini_pref is None:
            return False
    return camp_mini.startswith(mini_pref) and camp_nano.startswith(pref[1])


def _versioned_era(era):
    """True for the eras whose entries must carry nano_role / miniaod_version
    (their campaign prefix is per MiniAOD version: 2022-23)."""
    pref = _ERA_CAMPAIGN_PREFIX.get(era)
    return pref is not None and isinstance(pref[0], dict)


def _processed(path):
    """Processed-dataset part (the campaign string) of /<primary>/<processed>/<tier>."""
    p = str(path or "")
    return p.split("/")[2] if p.count("/") >= 3 else ""


def entry_problems(era, d):
    """The rules of the 2026-11-06 per-entry fields (nano_role, miniaod_version,
    lumi_mask, lumi_mask_md5): [] when the entry is consistent, else reasons.
    Entries of the older eras carry none of these fields and get [].

      * a 2022-23 entry needs miniaod_version v4 | v3 and nano_role main | ext1;
      * v3 only with nano_role main (its events belong to the main NanoAOD
        dataset; and 'v3' is its request label, which a v3 ext1 would repeat);
      * v3 entries need lumi_mask + lumi_mask_md5, the others carry none;
      * the mask is this entry's file (crab_lumimask_<era>_<name>_v3.json),
        exists with that md5 and holds at least one lumi (lumi_mask_problem);
      * nano_role main: neither dataset name has '_ext'; ext1: both have '_ext1-'.
    The campaign check is campaign_matches_era() (preflight and task_problems).
    """
    probs = []
    ver = str(d.get("miniaod_version") or "").strip()
    role = str(d.get("nano_role") or "").strip()
    if _versioned_era(era) or ver or role:
        if ver not in EXTRACT_PRIORITY:
            probs.append("miniaod_version %r is not one of %s"
                         % (ver, ", ".join(sorted(EXTRACT_PRIORITY))))
        if role not in NANO_ROLES:
            probs.append("nano_role %r is not one of %s" % (role, ", ".join(NANO_ROLES)))
        if ver == "v3" and role in NANO_ROLES and role != "main":
            probs.append("a v3 entry belongs to the main NanoAOD dataset (nano_role main), "
                         "not %r" % role)
        if role in NANO_ROLES:
            mini, nano = _processed(d.get("dataset")), _processed(d.get("nano_child"))
            if role == "main":
                bad = [x for x in (mini, nano) if "_ext" in x]
                if bad:
                    probs.append("nano_role main, but '_ext' is in %s" % " and ".join(bad))
            else:
                bad = [x for x in (mini, nano) if ("_%s-" % role) not in x]
                if bad:
                    probs.append("nano_role %s, but '_%s-' is not in %s"
                                 % (role, role, " and ".join(bad)))
    has_mask = bool(str(d.get("lumi_mask") or "").strip())
    if ver == "v3" and not has_mask:
        probs.append("a v3 entry needs lumi_mask and lumi_mask_md5 (it may run only over "
                     "the lumis of its mask)")
    if has_mask and ver != "v3":
        probs.append("lumi_mask on a %s entry -- only v3 entries carry a mask"
                     % (ver or "non-v3"))
    if str(d.get("lumi_mask_md5") or "").strip() and not has_mask:
        probs.append("lumi_mask_md5 without lumi_mask")
    mp = lumi_mask_problem(d, era)
    if mp:
        probs.append(mp)
    return probs


def task_problems(era, d):
    """What refuses a task at submission (2026-11-06): entry_problems() and,
    for the 2022-23 eras, the per-version campaign check. The older eras keep
    their campaign check in --preflight only, as before."""
    probs = entry_problems(era, d)
    if _versioned_era(era):
        mini, nano = _processed(d.get("dataset")), _processed(d.get("nano_child"))
        if not campaign_matches_era(era, mini, nano, d.get("miniaod_version")):
            probs.append("campaign strings do not belong to era %s / miniaod_version %s "
                         "(mini=%s, nano=%s)" % (era, d.get("miniaod_version"), mini, nano))
    return probs


def request_name_clashes(cat, site):
    """{request name: [task ids]} for every name that two or more entries of
    datasets.yaml (any era, enabled or not) would get -- two tasks with one
    name would share a CRAB project dir and an output directory."""
    seen = {}
    for era, block in (cat.get("eras") or {}).items():
        for d in (block.get("datasets") or []):
            rn = request_name(d.get("name", "?"), era, d, block, site)
            seen.setdefault(rn, []).append(task_id(era, d))
    return {rn: ids for rn, ids in seen.items() if len(ids) > 1}


# The year= values the pset accepts are the keys of its _ERA_NAME_BY_YEAR dict.
_PSET_YEARS_RE = re.compile(r"_ERA_NAME_BY_YEAR\s*=\s*\{(.*?)\}", re.S)


def pset_supported_years(src):
    """Set of year keys in the pset's _ERA_NAME_BY_YEAR, or None if not found."""
    m = _PSET_YEARS_RE.search(src)
    if not m:
        return None
    return set(re.findall(r"[\"']([^\"']+)[\"']\s*:", m.group(1)))


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
    req_filter = _csv_set(getattr(args, "request", None))
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = str(THIS_DIR / ("preflight_extend_%s_%s.log"
                               % ("-".join(sorted(era_filter)) if era_filter else "allEras", ts)))

    note("=" * 84)
    note("TtbarIdExtender CRAB PREFLIGHT (read-only)")
    note("  datasets    : %s" % args.datasets)
    note("  site config : %s" % args.site_config)
    note("  era filter  : %s" % (sorted(era_filter) if era_filter else "(none -> all)"))
    note("  proc filter : %s" % (sorted(proc_filter) if proc_filter else "(none -> all)"))
    if req_filter:
        note("  req filter  : %s" % sorted(req_filter))
    note("  DAS check   : %s" % ("ON (--check-das)" if args.check_das else "OFF (add --check-das)"))
    note("  time        : %s" % datetime.datetime.now().isoformat(timespec="seconds"))
    note("=" * 84)

    def selected(era, block, d):
        """--process / --request (the era filter is applied by the callers)."""
        if proc_filter and d.get("name", "?") not in proc_filter:
            return False
        if req_filter and request_name(d.get("name", "?"), era, d, block, site) not in req_filter:
            return False
        return True

    # ---- 1. environment ------------------------------------------------------
    # 2026-10-15: the release must fit the eras (10_6 for Run 2, 15_0 for 2024).
    # Without --era: the eras whose entries are enabled (what a submit would do).
    cmssw = os.environ.get("CMSSW_BASE", "")
    rel_eras = (era_filter & set((cat.get("eras") or {}).keys())) if era_filter \
        else acted_eras(cat, None, proc_filter, req_filter=req_filter, site=site)
    if not cmssw:
        bad("env CMSSW_BASE", "unset -- run cmsenv in the CMSSW area of the era "
            "(Run 2: CMSSW_10_6_32_patch1; Run 3 2022-2024: CMSSW_15_0_18)")
    else:
        why = release_problem(rel_eras)
        if why:
            bad("env CMSSW_VERSION", why)
        else:
            ok("env CMSSW", "%s (fits era(s) %s)" % (os.environ.get("CMSSW_VERSION"),
                                                    ",".join(sorted(rel_eras)) or "-"))
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
            ok("pset year option", "present -- submitter passes year=<era> "
               "(or the era's pset_year)")
        else:
            bad("pset year option",
                "MISSING: the pset has no `year` VarParsing option, so the era "
                "modifier stays hardcoded regardless of the era being submitted")
        # Every era to be submitted must be a year= value the pset accepts;
        # otherwise CRAB's submit-time import of the pset raises ValueError.
        # 2026-11-06: the value is pset_year() -- the same one build_config passes
        # (2022-23: "2024").
        years = pset_supported_years(src)
        sel_eras = sorted(era_filter) if era_filter else sorted((cat.get("eras") or {}).keys())
        _blocks = cat.get("eras") or {}
        yr = {e: pset_year(e, _blocks.get(e)) for e in sel_eras}
        yr_txt = lambda e: e if yr[e] == e else "%s (era %s)" % (yr[e], e)
        if years is None:
            warn("pset year values", "no _ERA_NAME_BY_YEAR in the pset -- year support not checked")
        else:
            missing = [e for e in sel_eras if yr[e] not in years]
            if missing:
                bad("pset year values", "pset does not accept year=%s (accepts: %s)"
                    % (",".join(yr_txt(e) for e in missing), ", ".join(sorted(years))))
            else:
                ok("pset year values", "accepts year=%s" % ",".join(yr_txt(e) for e in sel_eras))
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
        extra = ""
        if block.get("pset_year") or block.get("request_name_suffix"):
            # 2026-11-06: the 2022-23 blocks (year=2024, request names ..._extend_fp)
            extra = " | pset_year: %s | request_name_suffix: %s" % (
                block.get("pset_year"), block.get("request_name_suffix"))
        note("era %s  (global_tag: %s | era_modifiers: %s%s)"
             % (era, block.get("global_tag"), block.get("era_modifiers"), extra))
        ds_list = block.get("datasets") or []
        if not ds_list:
            bad("era %s datasets" % era, "empty")
            continue
        for d in ds_list:
            name = d.get("name", "?")
            if not selected(era, block, d):
                continue
            tid = task_id(era, d)       # <era>/<name>, 2022-23: <era>/<name>[label]
            total_sel += 1
            mini, nano = d.get("dataset", ""), d.get("nano_child", "")
            en, ver = bool(d.get("enabled")), bool(d.get("verified"))
            n_enabled += en
            n_verified += ver
            tags = []
            # 2026-10-15: a new era starts with dataset: "" (resolve_parents.sh
            # <era> --fill writes the DAS parent). Not resolved yet = one WARN for a
            # closed entry (it is skipped anyway), FAIL for an open one.
            if not str(mini).strip():
                (bad if en else warn)("%s dataset" % tid,
                                      "dataset: is empty (MiniAOD parent not resolved) -- "
                                      "bash crab/resolve_parents.sh %s --fill, then --apply" % era)
                continue
            if not _DS_RE.match(str(mini)) or not str(mini).endswith("MINIAODSIM"):
                bad("%s dataset syntax" % tid, "not a MINIAODSIM path: %r" % mini)
            if not _DS_RE.match(str(nano)) or not str(nano).endswith("NANOAODSIM"):
                bad("%s nano_child syntax" % tid, "not a NANOAODSIM path: %r" % nano)
            # campaign/era coherence: both campaign strings must belong to the
            # era key (_ERA_CAMPAIGN_PREFIX; substring rule for other keys;
            # 2026-11-06: per miniaod_version for 2022-23)
            camp_mini = str(mini).split("/")[2] if str(mini).count("/") >= 3 else ""
            camp_nano = str(nano).split("/")[2] if str(nano).count("/") >= 3 else ""
            if not campaign_matches_era(era, camp_mini, camp_nano, d.get("miniaod_version")):
                bad("%s campaign vs era" % tid,
                    "campaign strings do not belong to era %s%s (mini=%s, nano=%s)"
                    % (era, (" / miniaod_version %s" % d.get("miniaod_version"))
                       if _versioned_era(era) else "", camp_mini, camp_nano))
            else:
                tags.append("campaign-era ok")
            # primary dataset must be identical on both sides
            if str(mini).split("/")[1:2] != str(nano).split("/")[1:2]:
                bad("%s primary match" % tid,
                    "MiniAOD and Nano primary datasets differ")
            else:
                tags.append("primary match")
            # 2026-11-06: nano_role / miniaod_version / lumi mask rules (2022-23)
            eprobs = entry_problems(era, d)
            for p in eprobs:
                bad("%s entry fields" % tid, p)
            if d.get("miniaod_version") and not eprobs:
                tags.append("%s %s ok" % (d.get("nano_role"), d.get("miniaod_version")))
            mpath = lumi_mask_path(d)
            if mpath is not None and lumi_mask_problem(d, era) is None:
                ok("%s lumi mask" % tid, "%s md5 %s ok; %s -> Data.lumiMask"
                   % (d.get("lumi_mask"), d.get("lumi_mask_md5"), mask_summary(mpath)))
            if en and not ver:
                bad("%s state" % tid,
                    "enabled:true but verified:false -- resolve the MiniAOD parent first "
                    "(bash crab/resolve_parents.sh %s)" % era)
            elif not en:
                warn("%s state" % tid,
                     "enabled:false -> will be SKIPPED (verified=%s). Open it with "
                     "bash crab/resolve_parents.sh %s --apply" % (ver, era))
            else:
                ok("%s state" % tid, "enabled+verified; " + ", ".join(tags))
            req = request_name(name, era, d, block, site)
            if len(req) > CRAB_MAX_REQUEST_NAME:
                bad("%s request name" % tid, "%s has %d characters > CRAB limit %d"
                    % (req, len(req), CRAB_MAX_REQUEST_NAME))
            proj = os.path.join(work_area, "crab_%s" % req)
            if os.path.isdir(proj):
                # 2026-11-06: no rm -rf, no request_name_tag bump (it renames every
                # task of every era): move this one dir aside and use --request.
                warn("%s existing project" % tid,
                     "%s exists -> submit would be SKIPPED. To submit this one task "
                     "again: move the dir aside (mv %s %s.moved_<date>), then "
                     "--request %s" % (proj, proj, proj, req))
            note("        requestName=%-34s outLFN=%s/%s" % (req, lfn, era))

    note("-" * 84)
    ok("selected datasets", "%d (enabled=%d, verified=%d)" % (total_sel, n_enabled, n_verified))
    if total_sel and n_enabled == 0:
        warn("submittable now", "0 -- every selected entry is enabled:false")
    # 2026-11-06: no two entries of datasets.yaml (any era) may share a request
    # name -- they would share a CRAB project dir and an output directory.
    clashes = request_name_clashes(cat, site)
    if clashes:
        for rn, ids in sorted(clashes.items()):
            bad("request name clash", "%s <- %s" % (rn, ", ".join(ids)))
    else:
        n_all = sum(len(b.get("datasets") or []) for b in eras.values())
        ok("request names", "%d entries, all names distinct" % n_all)
    if req_filter:
        # 2026-11-06 (review D6): the same rule as main() -- --era and --process
        # narrow the names a --request may pick
        known = {request_name(d.get("name", "?"), e, d, b, site)
                 for e, b in eras.items() if not (era_filter and e not in era_filter)
                 for d in (b.get("datasets") or [])
                 if not (proc_filter and d.get("name") not in proc_filter)}
        unknown_req = sorted(req_filter - known)
        if unknown_req:
            bad("--request value", "no entry of the selected eras/processes has request "
                "name %s" % ", ".join(unknown_req))

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
                    if not selected(era, block, d):
                        continue
                    tid = task_id(era, d)
                    for label, path in (("mini", d.get("dataset", "")),
                                        ("nano", d.get("nano_child", ""))):
                        if not str(path).strip():
                            note("        DAS %s %s: not resolved yet (empty), not queried"
                                 % (tid, label))
                            continue
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
                        nfl = None
                        try:
                            for rec in json.loads(q.stdout or "[]"):
                                for smry in (rec.get("summary") or []):
                                    if smry.get("nfiles") is not None:
                                        nfl = int(smry["nfiles"])
                                        break
                                if nfl is not None:
                                    break
                        except (ValueError, TypeError, KeyError):
                            nfl = None
                        if nev is None:      # plain-text fallback, just in case
                            m = re.search(r"nevents\s*[:=]\s*(\d+)", q.stdout or "")
                            nev = int(m.group(1)) if m else None
                        if nev is not None:
                            ok("DAS %s %s" % (tid, label),
                               "nevents=%s%s" % (format(nev, ","),
                                                 "" if nfl is None
                                                 else "  nfiles=%s" % format(nfl, ",")))
                        else:
                            bad("DAS %s %s" % (tid, label),
                                "not resolvable -- wrong -vN suffix? %s" % path)

                        # ---- CRAB hard limit: 10,000 jobs per task ------------
                        # FileBased splitting -> njobs = ceil(nfiles/unitsPerJob).
                        # Exceeding it does NOT fail at submit time: the client
                        # accepts the request and the SERVER later marks the task
                        # SUBMITREFUSED with "The splitting on your task generated
                        # N jobs. The maximum number of jobs in each task is
                        # 10000". So `submit` prints success, nothing ever runs,
                        # and --resubmit cannot help (resubmit only requeues
                        # FAILED jobs of a task that reached the scheduler).
                        # This bit us on 2026-07-27: 2018 TTbar_SemiLep has
                        # 10,010 MiniAOD files -> 10,010 jobs -> refused, silently.
                        # Fix = per-entry `units_per_job:` override in
                        # datasets.yaml. See docs/08_troubleshooting.md T-19.
                        if label == "mini" and nfl:
                            # Same precedence as build_config(): per-entry
                            # override wins over resources.extend.units_per_job.
                            _res = (site.get("resources") or {}).get("extend", {})
                            upj = int(d.get("units_per_job",
                                            _res.get("units_per_job", 1)) or 1)
                            njobs = -(-nfl // upj)          # ceil division
                            det = ("nfiles=%s / units_per_job=%d -> %s jobs"
                                   % (format(nfl, ","), upj, format(njobs, ",")))
                            if lumi_mask_path(d) is not None:
                                # 2026-11-06: only the files with a masked lumi are
                                # split, so this is an upper bound
                                det += (" at most (lumi mask: only files with a masked "
                                        "lumi; --crab-dryrun shows CRAB's count)")
                            if njobs > CRAB_MAX_JOBS_PER_TASK:
                                need = -(-nfl // CRAB_MAX_JOBS_PER_TASK)
                                bad("job count %s" % tid,
                                    "%s > CRAB limit %s. Task WILL be "
                                    "SUBMITREFUSED. Set 'units_per_job: %d' on "
                                    "this datasets.yaml entry (-> %s jobs)."
                                    % (det, format(CRAB_MAX_JOBS_PER_TASK, ","),
                                       need, format(-(-nfl // need), ",")))
                            elif njobs > 0.9 * CRAB_MAX_JOBS_PER_TASK:
                                warn("job count %s" % tid,
                                     "%s -- within 10%% of the CRAB limit %s"
                                     % (det, format(CRAB_MAX_JOBS_PER_TASK, ",")))
                            else:
                                ok("job count %s" % tid, det)

                        # ---- where is the MiniAOD? (2026-10-15, era 2024) -------
                        # A MiniAOD held only on tape makes CRAB ask for a tape
                        # recall first (task state TAPERECALL, can take days), and
                        # the manager ALERTs after 8 h without a finished job.
                        # Any site name not ending in _Tape/_MSS counts as disk.
                        # Run 2 eras are not checked: their preflight stays as it
                        # was (their MiniAODv2 launches passed without it, and a
                        # new WARN would stop launch_extend.sh at step 6).
                        if label == "mini" and nev is not None \
                                and not _is_run2_era(era):
                            try:
                                sq = subprocess.run(["dasgoclient", "-query",
                                                     "site dataset=%s" % path],
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE,
                                                    universal_newlines=True,
                                                    timeout=180)
                                sites = sorted({s.strip() for s in
                                                (sq.stdout or "").splitlines()
                                                if s.strip()})
                            except (OSError, subprocess.TimeoutExpired):
                                sites = None
                            if not sites:
                                note("        sites %s: DAS returned no site "
                                     "list (not checked)" % tid)
                            else:
                                disk = [s for s in sites
                                        if not (s.endswith("_Tape") or s.endswith("_MSS"))]
                                if disk:
                                    ok("MiniAOD on disk %s" % tid,
                                       "%d site(s): %s%s" % (len(disk), ", ".join(disk[:3]),
                                                             " ..." if len(disk) > 3 else ""))
                                else:
                                    warn("MiniAOD on disk %s" % tid,
                                         "only on tape (%s): CRAB would start with a "
                                         "tape recall (TAPERECALL, days) and the manager "
                                         "ALERTs after 8 h without a finished job. "
                                         "launch_extend.sh stops on this WARN: ask for a "
                                         "disk copy and launch again, or submit by hand "
                                         "after --apply (python3 crab/submit_ttbarIdExtend.py "
                                         "--era %s) and start the manager once jobs run"
                                         % (", ".join(sites), era))
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


# ----- Failed-submit shells -----------------------------------------------
def clean_failed_shells(cat, site, proc_filter, era_filter, really, req_filter=None):
    """List (and with really=True move away) project dirs without .requestcache.

    Returns 0 when nothing is left blocking (no shells, or all moved), 1 when
    shells were found but not moved (run again with --yes), 2 on a move error.
    """
    work_area = Path(site.get("work_area", "crab_projects"))
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = work_area / ("_failed_%s" % stamp)
    shells, ok_tasks, absent = [], 0, 0
    for era, block in (cat.get("eras") or {}).items():
        if era_filter and era not in era_filter:
            continue
        for ds in (block.get("datasets") or []):
            if proc_filter and ds["name"] not in proc_filter:
                continue
            # 2026-11-06: request_name() (2022-23: <name>_<era>_<label>_extend_fp)
            req = request_name(ds["name"], era, ds, block, site)
            if req_filter and req not in req_filter:
                continue
            proj = work_area / ("crab_%s" % req)
            if not proj.is_dir():
                absent += 1
                continue
            if (proj / ".requestcache").exists():
                ok_tasks += 1
                print("  [task ] %-40s submitted (has .requestcache) -- left alone" % proj)
                continue
            shells.append(proj)
            print("  [SHELL] %-40s no .requestcache -> a failed submit" % proj)
            log = proj / "crab.log"
            if log.exists():
                tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-3:]
                for ln in tail:
                    print("          | " + ln[:160])
    print("summary: %d shell(s), %d submitted task(s), %d without a project dir" % (len(shells), ok_tasks, absent))
    if not shells:
        return 0
    if not really:
        print("nothing moved -- re-run with --yes to move the shell(s) to %s/" % dest)
        return 1
    try:
        dest.mkdir(parents=True, exist_ok=False)
        for proj in shells:
            proj.rename(dest / proj.name)
            print("  moved %s -> %s/" % (proj, dest))
    except OSError as exc:
        print("ERROR: could not move a shell: %s" % exc)
        return 2
    print("moved %d shell(s) to %s/ -- those tasks can be submitted again" % (len(shells), dest))
    return 0


# ----- Task table (2026-11-06, STEP 47) ------------------------------------
def _csv_set(text):
    """{'a', 'b'} from 'a,b' (blanks dropped); None for no value."""
    if not text:
        return None
    out = {s.strip() for s in str(text).split(",") if s.strip()}
    return out or None


def _one_line(text):
    """A header field on one line: CR, LF and TAB become spaces (review L1)."""
    return str(text).replace("\r", " ").replace("\n", " ").replace("\t", " ")


def _git_state():
    """'<HEAD sha> (...)' of the checkout this submitter runs from -- the job
    records name the commit (AGENTS.md sec.5: no production from uncommitted
    code); 'unknown (...)' when git cannot tell.

    git runs in PKG_ROOT (cwd=) with GIT_OPTIONAL_LOCKS=0 in its environment
    instead of -C / --no-optional-locks: the el7 git 1.8.3 knows neither
    option (2026-11-06, review L1). LC_ALL=C keeps its messages English/ASCII.
    """
    env = dict(os.environ, LC_ALL="C", LANG="C", GIT_OPTIONAL_LOCKS="0")
    ascii_ = lambda t: t.encode("ascii", "replace").decode("ascii")
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(PKG_ROOT),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60, env=env)
        if head.returncode != 0:
            return "unknown (git rev-parse failed: %s)" % (ascii_(head.stderr.strip())[:80] or "?")
        st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", "."],
                            cwd=str(PKG_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, timeout=60, env=env)
        if st.returncode != 0:
            return "%s (git status failed)" % head.stdout.strip()
        return "%s (%s)" % (head.stdout.strip(),
                            "UNCOMMITTED changes in TtbarIdExtender/" if st.stdout.strip()
                            else "TtbarIdExtender/ clean")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        # ValueError covers UnicodeDecodeError (LANG=C python 3.6 decodes as ASCII)
        return "unknown (%s)" % ascii_(str(exc))[:80]


def task_table_paths(args, era_filter, mode_tag):
    """(plan path, record path) of this submission run; neither may exist.

    Default: crab/task_tables/tasks_<eras>_<UTC>Z_<mode>_plan.tsv and
    ..._record.tsv (two runs in one second: _2, _3, ... before _plan). With
    --task-table PATH: the plan is PATH, the record PATH with '_record' before
    '.tsv'. An existing file is never overwritten: exit 1 (sys.exit with a
    message), nothing submitted.
    """
    def record_of(plan):
        if plan.endswith("_plan.tsv"):
            return plan[:-len("_plan.tsv")] + "_record.tsv"
        if plan.endswith(".tsv"):
            return plan[:-len(".tsv")] + "_record.tsv"
        return plan + "_record.tsv"
    if args.task_table:
        plan = os.path.abspath(args.task_table)
    else:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        eras = "-".join(sorted(era_filter)) if era_filter else "allEras"
        stem = "tasks_%s_%s_%s" % (eras, stamp, mode_tag)
        plan = str(TASK_TABLE_DIR / (stem + "_plan.tsv"))
        k = 1
        while os.path.exists(plan) or os.path.exists(record_of(plan)):
            k += 1
            plan = str(TASK_TABLE_DIR / ("%s_%d_plan.tsv" % (stem, k)))
    record = record_of(plan)
    for path in (plan, record):
        if os.path.exists(path):
            sys.exit("ERROR: task table %s exists -- it is never overwritten (it may be the "
                     "record of a submission); give another --task-table. Nothing submitted."
                     % path)
    return plan, record


def task_rows(planned):
    """The plan's rows (TASK_TABLE_COLUMNS), one per planned task, in order."""
    rows = []
    for era, era_block, ds, cfg, _shown in planned:
        ver = str(ds.get("miniaod_version") or "").strip()
        rows.append([cfg.General.requestName, era, str(ds.get("name", "")),
                     str(ds.get("nano_role") or "").strip(), ver,
                     str(cfg.Data.inputDataset), str(ds.get("nano_child") or "").strip(),
                     str(EXTRACT_PRIORITY.get(ver, 0)),
                     str(ds.get("lumi_mask") or "").strip(),
                     str(ds.get("lumi_mask_md5") or "").strip().lower(),
                     str(cfg.Data.unitsPerJob), pset_year(era, era_block),
                     str(cfg.Data.outLFNDirBase)])
    return rows


def task_table_head(args, kind, mode_tag, work_area):
    """The '#' lines of the plan (kind 'plan') or the record (kind 'record')."""
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mode_txt = {"dryrun": "--dry-run (nothing submitted; every outcome not-attempted)",
                "crabdryrun": "--crab-dryrun (crab submit --dryrun: split by CRAB, no job "
                              "to the grid; the tasks stay UPLOADED, never submitted)",
                "submit": "submit"}[mode_tag]
    what = ("PLAN -- written before the first submission" if kind == "plan" else
            "RECORD -- the plan's rows and the outcome of each task, written when the run "
            "ended (outcomes: %s)" % ", ".join(TASK_OUTCOMES))
    head = [
        "TtbarIdExtender CRAB task %s; crab/submit_ttbarIdExtend.py, %s, mode %s"
        % (what, when, mode_txt),
        "git %s; datasets.yaml %s md5 %s; site_config.yaml md5 %s"
        % (_git_state(), args.datasets, file_md5(args.datasets), file_md5(args.site_config)),
        "CRAB work area (project dirs crab_<request_name>): %s" % work_area,
        "command: %s" % " ".join(sys.argv),
        "extract: extractTtbarIdPatch --input <nano_dataset>=<filelist of this task's CRAB "
        "output>:<extract_priority> (one NanoAOD dataset: the lower number wins, MiniAODv4 0, "
        "MiniAODv3 1); output: <out_lfn_dir_base>/<primary dataset>/<request_name>/<timestamp>/",
    ]
    if args.max_files is not None:
        head.append("--max-files %d: Data.totalUnits capped (DISCOURAGED, see --help)"
                    % args.max_files)
    return ["# " + _one_line(h) for h in head]


def write_task_tsv(path, head, columns, rows):
    """Write one task table (plan or record) atomically. Every header line
    starts with '#', no cell holds a tab or a line break (ValueError);
    OSError when the file cannot be written."""
    for h in head:
        if not h.startswith("#") or "\n" in h or "\r" in h:
            raise ValueError("task-table header line not a '#' line: %r" % h)
    for r in rows:
        if len(r) != len(columns) or any(("\t" in c or "\n" in c or "\r" in c) for c in r):
            raise ValueError("task-table row malformed: %r" % (r,))
    text = "\n".join(head + ["\t".join(columns)] + ["\t".join(r) for r in rows]) + "\n"
    d = os.path.dirname(path)
    tmp = "%s.tmp.%d" % (path, os.getpid())
    if d:
        os.makedirs(d, exist_ok=True)
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


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
    req_filter  = _csv_set(args.request)        # 2026-11-06

    # 2026-11-06: an unknown --request name is an error, never an empty run.
    if req_filter:
        known = set()
        for era, block in (cat.get("eras") or {}).items():
            if era_filter and era not in era_filter:
                continue
            for d in (block.get("datasets") or []):
                if proc_filter and d.get("name") not in proc_filter:
                    continue
                known.add(request_name(d.get("name", "?"), era, d, block, site))
        unknown = sorted(req_filter - known)
        if unknown:
            sys.exit("ERROR: --request %s: no entry of the selected eras/processes has "
                     "this request name (--dry-run prints them)" % ",".join(unknown))

    if args.clean_failed_shells:
        sys.exit(clean_failed_shells(cat, site, proc_filter, era_filter, args.yes,
                                     req_filter))

    # Which mode are we in? submit (default), or a bulk action on existing tasks.
    chosen = [a for a in ("resubmit", "status", "report", "kill")
              if getattr(args, a)]
    if len(chosen) > 1:
        sys.exit("ERROR: choose only one of "
                 "--resubmit / --status / --report / --kill.")
    bulk_action = chosen[0] if chosen else None
    if args.crab_dryrun and (bulk_action or args.dry_run):
        sys.exit("ERROR: --crab-dryrun is a submission ('crab submit --dryrun'); it does "
                 "not go with --dry-run or --%s." % (bulk_action or "dry-run"))
    # 2026-11-06 (review): a crab dry run is for named tasks only -- never a
    # whole era by accident.
    if args.crab_dryrun and not req_filter:
        sys.exit("ERROR: --crab-dryrun needs --request <request name>[,<request name>...] "
                 "(the names as --dry-run prints them); it is meant for one task per era.")

    # --report accumulators (printed once after the loop so the columns align)
    report_rows = []
    report_unknown = set()
    report_dead = []
    report_uploaded = []     # 2026-11-06: tasks in UPLOADED (crab submit --dryrun)

    # kill is destructive: confirm which tasks first, unless --yes. 2026-11-06
    # (review M3): the exact request names and their count are listed first.
    if bulk_action == "kill":
        work_area = str(site.get("work_area", "crab_projects"))
        to_kill = []
        for era, block in (cat.get("eras") or {}).items():
            if era_filter and era not in era_filter:
                continue
            for d in (block.get("datasets") or []):
                if proc_filter and d.get("name") not in proc_filter:
                    continue
                rn = request_name(d.get("name", "?"), era, d, block, site)
                if req_filter and rn not in req_filter:
                    continue
                to_kill.append((rn, os.path.isdir(os.path.join(work_area, "crab_%s" % rn))))
        n_dirs = sum(1 for _rn, has in to_kill if has)
        print("About to 'crab kill' %d task(s) -- %d with a project dir under %s/ "
              "(the others are skipped):" % (len(to_kill), n_dirs, work_area))
        for rn, has in to_kill:
            print("    %s%s" % (rn, "" if has else "   (no project dir here)"))
        if not args.yes:
            ans = input("Kill these %d task(s)? [y/N] " % len(to_kill)).strip().lower()
            if ans not in ("y", "yes"):
                sys.exit("Aborted (no jobs killed).")

    # 2026-10-15: a submission imports the pset in THIS release, so the release
    # must fit the eras it submits (2024 needs CMSSW_15_0_X). Bulk actions
    # (status/report/resubmit/kill) work from any release and are not checked.
    if bulk_action is None:
        why = release_problem(acted_eras(cat, era_filter, proc_filter, args.force,
                                         req_filter=req_filter, site=site))
        if why:
            sys.exit("ERROR: %s" % why)

    n_total = n_skipped = n_attempted = n_submitted = 0
    n_unresolved = 0
    # Per-outcome tally for bulk actions (see crab_action_one). Kept separate
    # from n_submitted because "the command ran" != "something happened".
    outcomes = {}
    # Submission (2026-11-06, STEP 47): every selected task is built and checked
    # FIRST -- lumi mask present with its md5, the entry fields, the 2022-23
    # campaign per MiniAOD version, the request name (length, not shared with
    # another entry). One refused task -> nothing is submitted (exit 3). Then
    # the task table is written, then the tasks are submitted in order.
    planned = []      # (era, era_block, entry, cfg, shown name)
    refused = []      # (task id, request name, reason)
    for era, era_block in (cat.get("eras") or {}).items():
        if era_filter and era not in era_filter:
            continue
        for ds in (era_block.get("datasets") or []):
            n_total += 1
            name = ds["name"]
            if proc_filter and name not in proc_filter:
                continue
            if req_filter and request_name(name, era, ds, era_block, site) not in req_filter:
                continue
            # For bulk actions we act on every selected sample regardless of
            # the enabled flag (you may want to resubmit/status a task whose
            # entry you have since toggled off). For submission we honor it.
            if bulk_action is None and not args.force and not ds.get("enabled", False):
                n_skipped += 1
                continue
            # 2026-10-15 review: a new era's entry keeps dataset: "" until
            # resolve_parents.sh --fill; CRAB must never get an empty
            # inputDataset, so it is not submitted, not even with --force.
            if bulk_action is None and not str(ds.get("dataset") or "").strip():
                print("[skip] era=%s process=%s: dataset: is empty -- "
                      "bash crab/resolve_parents.sh %s --fill, then --apply"
                      % (era, name, era))
                n_unresolved += 1
                continue
            label = request_label(ds)
            shown = name + ("[%s]" % label if label else "")   # 2022-23: name[label]

            if bulk_action is None:
                tid = task_id(era, ds)
                probs = task_problems(era, ds)    # includes the lumi mask md5
                cfg = None
                try:
                    cfg = build_config(
                        process_name=name, era=era, dataset_entry=ds,
                        site_cfg=site, era_block=era_block,
                        max_files=args.max_files,
                    )
                except TaskRefused as exc:
                    if not probs:
                        probs.append(str(exc))
                rn = (cfg.General.requestName if cfg is not None
                      else request_name(name, era, ds, era_block, site))
                if len(rn) > CRAB_MAX_REQUEST_NAME:
                    probs.append("request name has %d characters > CRAB limit %d"
                                 % (len(rn), CRAB_MAX_REQUEST_NAME))
                if probs:
                    refused.extend((tid, rn, p) for p in probs)
                    continue
                if args.crab_dryrun:
                    # 2026-11-06: crab submit --dryrun tasks get their own work
                    # area -- never the real submission's project dir
                    cfg.General.workArea = dryrun_work_area(site)
                planned.append((era, era_block, ds, cfg, shown))
                continue

            verb = bulk_action
            print(f"--- {verb}  era={era}  process={shown} ---")
            cfg = build_config(
                process_name=name, era=era, dataset_entry=ds,
                site_cfg=site, era_block=era_block,
                max_files=args.max_files, check_lumi_mask=False,
            )
            n_attempted += 1
            if bulk_action == "report":
                # 2026-11-06 (review M2): rows and the DEAD block carry the era,
                # <era>/<name>[label] -- the label only, no config field changes
                if report_one(cfg, short_name=task_id(era, ds), rows=report_rows,
                              unknown_acc=report_unknown,
                              dead_acc=report_dead, uploaded_acc=report_uploaded):
                    n_submitted += 1
            else:
                oc = crab_action_one(cfg, action=bulk_action)
                outcomes[oc] = outcomes.get(oc, 0) + 1
                # Only a real effect counts. For resubmit that is 'sent' alone.
                if (oc == "sent") or (bulk_action != "resubmit" and oc == "ok"):
                    n_submitted += 1

    plan_path = record_path = None
    if bulk_action is None:
        # two entries with one request name would share a project dir and an
        # output directory: refuse every planned task that has a shared name
        clashes = request_name_clashes(cat, site)
        for era, _blk, ds, cfg, _shown in planned:
            rn = cfg.General.requestName
            if rn in clashes:
                refused.append((task_id(era, ds), rn, "request name shared by the entries %s"
                                % ", ".join(clashes[rn])))
        if refused:
            print("=" * 65)
            for tid, rn, why in refused:
                print("[REFUSED] %s (%s): %s" % (tid, rn, why))
            print("RESULT: NOTHING SUBMITTED -- %d problem(s) above. Every task of a "
                  "run is checked before the first submission; fix crab/datasets.yaml "
                  "or crab/lumimasks/ and run again (exit 3)." % len(refused))
            sys.exit(3)
        mode_tag = ("crabdryrun" if args.crab_dryrun else
                    "dryrun" if args.dry_run else "submit")
        # 2026-11-06: the PLAN before the first submission, the RECORD (plan +
        # outcome per task) when the run ends -- also on an interruption.
        rows = task_rows(planned)
        outcome = ["not-attempted"] * len(planned)
        work_area = (dryrun_work_area(site) if args.crab_dryrun
                     else str(site.get("work_area", "crab_projects")))
        if planned:
            plan_path, record_path = task_table_paths(args, era_filter, mode_tag)
            try:
                write_task_tsv(plan_path, task_table_head(args, "plan", mode_tag, work_area),
                               TASK_TABLE_COLUMNS, rows)
            except (OSError, ValueError) as exc:
                sys.exit("ERROR: cannot write the task plan %s (%s) -- nothing submitted"
                         % (plan_path, exc))
            print("task plan  : %s  (%d task(s); written before the first submission)"
                  % (plan_path, len(planned)))
        current = None
        try:
            for i, (era, era_block, ds, cfg, shown) in enumerate(planned):
                print(f"--- extend  era={era}  process={shown} ---")
                n_attempted += 1
                current = i
                ok, outcome[i] = submit_one(cfg, dry_run=args.dry_run,
                                            crab_dryrun=args.crab_dryrun)
                current = None
                if ok:
                    n_submitted += 1
        except BaseException:
            if current is not None:
                outcome[current] = "failed"
                rn_cur = planned[current][3].General.requestName
                print("\n  [INTERRUPTED] while submitting %s: its state is unknown -- check "
                      "crab status -d %s/crab_%s. Tasks after it: not-attempted."
                      % (rn_cur, work_area, rn_cur))
            raise
        finally:
            if planned:
                try:
                    write_task_tsv(record_path,
                                   task_table_head(args, "record", mode_tag, work_area),
                                   TASK_TABLE_COLUMNS + ["outcome"],
                                   [r + [o] for r, o in zip(rows, outcome)])
                    print("task record: %s  (%s)" % (record_path, ", ".join(
                        "%s %d" % (o, outcome.count(o)) for o in TASK_OUTCOMES
                        if outcome.count(o))))
                except (OSError, ValueError) as exc:
                    print("ERROR: cannot write the task record %s (%s); the outcomes: %s"
                          % (record_path, exc, list(zip([r[0] for r in rows], outcome))))

    # -- Post-loop: the compact table (if requested) --
    if bulk_action == "report":
        if report_rows:
            print_report(report_rows)
        if report_dead:
            print("\n[!! DEAD TASK(S) -- a row of all zeros here is NOT "
                  "'not started yet' !!]")
            for nm, st in report_dead:
                print("    %-24s %s" % (nm, st))
            print("    These will never produce output. Fix the cause and "
                  "RE-SUBMIT (kill + delete the project dir + delete the EOS "
                  "timestamp dir first). --resubmit does nothing for them.")
            print("    Most common cause here: >%s jobs in one task "
                  "(run --preflight --check-das, which now checks this)."
                  % format(CRAB_MAX_JOBS_PER_TASK, ","))
        if report_uploaded:
            # 2026-11-06 (review M1): a task in UPLOADED is a crab submit --dryrun
            # task -- its row of zeros is "uploaded, not running", not a dead
            # task and not "not started yet".
            print("\n[UPLOADED TASK(S) -- uploaded, not running]")
            for nm, st in report_uploaded:
                print("    %-24s %s" % (nm, st))
            print("    `crab submit --dryrun` tasks: CRAB split them but runs no job, "
                  "and nobody submits them. The real submission of a task is a "
                  "separate plain submit with its own project dir.")
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
    mode = bulk_action or ("submit" + (" (DRY RUN)" if args.dry_run else "")
                           + (" (CRAB DRY RUN: crab submit --dryrun, no job to the grid)"
                              if args.crab_dryrun else ""))
    print(f"  mode      : {mode}")
    print(f"  scanned   : {n_total}")
    if bulk_action is None:
        print(f"  skipped   : {n_skipped}  (enabled:false; use --force to override)")
        if n_unresolved:
            print("  unresolved: %d  (dataset: is empty -- run "
                  "bash crab/resolve_parents.sh <era> --fill first)" % n_unresolved)
    print(f"  attempted : {n_attempted}")
    label = {"resubmit": "resubmitted", "status": "queried",
             "report": "queried", "kill": "killed"}.get(bulk_action, "submitted")
    if bulk_action is None and args.crab_dryrun:
        label = "uploaded"          # 2026-11-06: split by CRAB, not submitted
    print(f"  {label:9s} : {n_submitted}")
    if plan_path:
        print("  task plan : %s" % plan_path)
        print("  task record: %s" % record_path)

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
