#!/usr/bin/env python3
# =============================================================================
# submit_validation_condor.py
# =============================================================================
# Run the WHOLE ttbarId-extend validation for one era on HTCondor: one job per
# nano filelist chunk, all of them reading a shared pre-sorted extend directory.
# Each job writes a small JSON of counters; scripts/aggregate_validation.py sums
# them into one PASS/FAIL table per sample.
#
# WHY THIS EXISTS (2026-07-28, measured -- docs/08_troubleshooting.md T-22)
#   Running the matching interactively does not scale. Measured on lxplus:
#       ttbb_2L2Nu      4.79 M nano events   11.5 min
#       ttbb_Hadronic   8.05 M nano events   29   min
#   Extrapolated to the three large samples (145 M / 334 M / 476 M nano events)
#   that is ~6 h + ~13 h + ~19 h = ~38 h SERIAL. The bottleneck is not CPU
#   (measured 25% CPU efficiency) but reading ~1.2 TB of central NanoAOD over
#   the WAN. Splitting by nano chunk turns that into ~1-2 h wall clock.
#   Three terminals hand-driven in sequence was the wrong shape for this job.
#
# DESIGN
#   * UNIFORM PIPELINE. Every sample -- small and large -- goes through
#     sortSplitExtend first, then matchTtbarIdSorted. Sorting a small sample
#     costs seconds, and having ONE code path removes the "is this sample big
#     enough to need the sorted route?" branch that previously had to be decided
#     by hand. It also caps per-job memory at ~16 MB (one sorted part resident)
#     instead of the multi-GB in-memory map matchTtbarId builds.
#   * ONE JOB PER NANO CHUNK. make_nano_filelists_das.sh already writes
#     <nanodir>/<short>/file_<short>_<i>.txt (20 paths each) and calls them
#     "per-condor-job splits" -- this is the consumer it was written for.
#     Jobs only READ the sorted dir, so sharing it across jobs is safe.
#   * OUTPUTS ON EOS, NOT AFS. AFS home is quota-limited (measured 94% full,
#     10 GB quota) and its tokens expire in ~25 h, which is shorter than these
#     jobs. Writing results to AFS already produced
#     "SysError in <TFile::Flush>: ... (Input/output error)" twice. Default
#     --out-base therefore points at EOS.
#   * SMOKE FIRST. --smoke submits exactly ONE chunk of ONE sample so the first
#     thing you look at is a single job log, not 49 of them.
#
# WHERE TO RUN THIS, AND WHY IT MATTERS (2026-07-28, found by --preflight)
#   `condor_submit` does NOT exist inside the cmssw-el7 container, only on the
#   EL9 lxplus host. But the Validation binaries are built inside that container
#   (slc7_amd64_gcc700 / ROOT 6.14) and cannot run on a bare EL9 worker. So:
#
#       SUBMIT   from the EL9 host        (that is where condor_submit lives)
#       EXECUTE  inside an EL7 container  (that is where the binary runs)
#
#   Therefore this script does NOT use `getenv = True`. Shipping the host's EL9
#   environment into an EL7 payload would be actively wrong. Instead the submit
#   file asks HTCondor for the container image (MY.SingularityImage) and the
#   generated job script sets up CMSSW from cvmfs itself:
#       source /cvmfs/cms.cern.ch/cmsset_default.sh
#       cd <CMSSW_BASE>/src && eval `scramv1 runtime -sh`
#   That makes each job self-contained and independent of how it was submitted.
#
#   --no-container is available if you ever rebuild the tools against a native
#   EL9 ROOT (e.g. an LCG view) -- the docs do say Validation is CMSSW-agnostic
#   -- but do NOT use it with a container-built binary.
#
#   2026-10-15 (era 2024, O10): the image follows the CMSSW area the job sets
#   up -- el7 for a slc7 area (CMSSW_10_6_32_patch1), el8 for an el8 area (the
#   v15 area CMSSW_15_0_18 that builds and runs the 2024 tools: its ROOT 6.32
#   reads whatever the 15_0 extend files use), el9 for an el9 area. --container
#   still overrides it.
#
#   2026-10-15 (docs/08 T-42): the CMSSW area the job sets up is the one this
#   script lives in -- the area whose bin/ the jobs ship -- or --cmssw-base.
#   NOT $CMSSW_BASE: on the lxplus host that is whatever the last cmsenv in the
#   shell left. A cmsenv of the v15 area (CMSSW_15_0_18) left in the host shell
#   made all 22 jobs of era 2016 set up that release in the el8 image, where the
#   matcher built in CMSSW_10_6 could not start (exit 127, the loader's message
#   only in the .err). A different $CMSSW_BASE is now a WARN at submission and
#   in --preflight; the job prints its CMSSW_BASE, stops with exit 121 when
#   `ldd -r` finds a library or a symbol of the matcher missing (the 2016 jobs
#   had "undefined symbol: _ZN6TClass8GetClassERKSt9type_infobb" in the .err),
#   and explains an exit 127.
#
# USAGE
#   # 0) one-time: sort every sample (idempotent, skips completed ones)
#   python3 scripts/submit_validation_condor.py --era 2018 --sort-only
#
#   # 1) smoke: 1 sample, 1 chunk
#   python3 scripts/submit_validation_condor.py --era 2018 --smoke
#
#   # 2) everything
#   python3 scripts/submit_validation_condor.py --era 2018
#
#   # 3) aggregate when done
#   python3 scripts/aggregate_validation.py --era 2018
#
# Add --dry-run to any of the above to write the submit files without
# condor_submit. --preflight checks inputs and prints a report without writing
# anything.
#
# 2026-10-15 (docs/08 T-40): --report and --resubmit-failed ask condor_q which
#   chunks are still in the queue (jobs whose executable is this work base's
#   run_match.sh). Such a chunk is "queued" (idle/running/held), not missing:
#   --report no longer tells you to re-run a chunk whose job simply has not run
#   yet, and --resubmit-failed never submits a second job for a queued chunk
#   (run it on the host shell, where condor_q is). --report exits 0 all ok,
#   1 some chunk failed, is missing with no job, or is held, 2 nothing to do
#   but wait (idle/running jobs), 3 the queue could not be asked (no condor_q
#   here) and some chunk has no ok result. A chunk with a job in the queue is
#   queued even if an older result exists (the job will overwrite it). The
#   printed follow-up commands repeat the options in effect (--samples, the
#   directories, --memory ...), so a pasted command acts on the same chunks.
#   condor_q sees the schedd of this lxplus session (myschedd); after a
#   `myschedd bump` the jobs on the old schedd are invisible here -- look with
#   condor_q -name <old schedd> before resubmitting anything.
#   The submit file carries batch_name = val_<era>, so one campaign can be
#   watched or removed alone:
#     condor_q -constraint 'JobBatchName == "val_2016APV"'
#     condor_rm -constraint 'JobBatchName == "val_2016APV"'
#   (condor_rm <user> removes EVERY job of the user, other campaigns included.)
#   The printed follow-up commands carry absolute paths.
# =============================================================================

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
VAL_ROOT = THIS_DIR.parent                      # .../Validation

# The 7 ttbar stitching samples, by the short name used everywhere else
# (make_filelists_miniAOD.py sample_mapping values == make_nano_filelists_das.sh
# SHORT array). Keep this list in that same order for readable logs.
SHORTS = ["tt4b", "ttbb_Hadronic", "ttbb_SemiLeptonic", "ttbb_2L2Nu",
          "TTToHadronic", "TTToSemiLeptonic", "TTTo2L2Nu"]

# Smallest sample -> the smoke target. 103 extend files / 6 nano files.
SMOKE_SHORT = "ttbb_2L2Nu"

DEFAULT_EOS = "/eos/user/j/junghyun/TTHHGenCategoryTools"

# EL7 image on cvmfs, so an slc7_amd64_gcc700 / ROOT 6.14 payload can run on the
# EL9 condor workers. Verified by --preflight before use.
DEFAULT_IMAGE = ("/cvmfs/unpacked.cern.ch/registry.hub.docker.com/"
                 "cmssw/el7:x86_64")
IMAGE_BY_OS = {
    "7": DEFAULT_IMAGE,
    "8": "/cvmfs/unpacked.cern.ch/registry.hub.docker.com/cmssw/el8:x86_64",
    "9": "/cvmfs/unpacked.cern.ch/registry.hub.docker.com/cmssw/el9:x86_64",
}


def image_for_area(cmssw_base):
    """(image, arch) for a CMSSW area: the OS of its SCRAM arch (.SCRAM/<arch>,
    else lib/<arch>); (DEFAULT_IMAGE, None) when it cannot be told -- the
    callers then WARN (2026-10-15 review: an el8 build must not silently get
    the el7 image)."""
    if not cmssw_base:
        return DEFAULT_IMAGE, None
    names = []
    for sub in (".SCRAM", "lib"):
        d = Path(cmssw_base, sub)
        try:
            if d.is_dir():
                names.extend(sorted(x.name for x in d.iterdir() if x.is_dir()))
        except OSError:          # e.g. no AFS token: treat as unknown
            continue
    for n in names:
        for pre, osv in (("slc7_", "7"), ("cc7_", "7"), ("el8_", "8"), ("el9_", "9")):
            if n.startswith(pre):
                return IMAGE_BY_OS[osv], n
    return DEFAULT_IMAGE, None

# CERN's standard batch schedds REFUSE any /eos path inside a submit file
# (2026-07-28: "Standard batch schedds cannot use /eos paths directly within the
# submit file"). Results must therefore leave the job over XRootD, and every
# condor-managed file (executable, args, output/error/log) must live on AFS.
# See https://batchdocs.web.cern.ch/local/file_xfer_plugin.html
EOS_URL_PREFIX = "root://eosuser.cern.ch/"
DEFAULT_MEMORY = 2000          # MB, --memory
DEFAULT_FLAVOUR = "workday"    # --flavour


def parse_args():
    p = argparse.ArgumentParser(
        description="Submit the ttbarId-extend validation to HTCondor "
                    "(one job per nano chunk).")
    p.add_argument("--era", required=True, help="e.g. 2018")
    p.add_argument("--samples", default=None,
                   help="Comma-separated short names; default = all 7.")
    p.add_argument("--extend-filelist-dir", default=None,
                   help="Default: <Validation>/filelists/sidecar<era>")
    p.add_argument("--nano-filelist-dir", default=None,
                   help="Default: <Validation>/filelists/nano<era>")
    p.add_argument("--sorted-base", default=None,
                   help="Where sortSplitExtend output lives / goes. "
                        "Default: %s/sorted<era>" % DEFAULT_EOS)
    p.add_argument("--out-base", default=None,
                   help="Where per-chunk JSON/ROOT/logs go (MUST NOT be AFS). "
                        "Default: %s/valout<era>" % DEFAULT_EOS)
    p.add_argument("--bin-dir", default=None,
                   help="Default: <Validation>/bin")
    p.add_argument("--work-base", default=None,
                   help="Where the condor scaffolding (executable, args, "
                        "output/error/log) goes. MUST NOT be on /eos -- the "
                        "standard schedds reject /eos paths in a submit file. "
                        "Default: <Validation>/condor_val<era> (on AFS).")
    p.add_argument("--eos-url-prefix", default=EOS_URL_PREFIX,
                   help="XRootD prefix used to send results to EOS "
                        "(default: %(default)s).")
    p.add_argument("--sort-only", action="store_true",
                   help="Only run sortSplitExtend for samples missing it, "
                        "locally and serially, then exit. Sorting is cheap "
                        "(~11 min for 146 M rows) and inherently serial.")
    p.add_argument("--smoke", action="store_true",
                   help="Submit ONE chunk of ONE sample (%s) and stop."
                        % SMOKE_SHORT)
    p.add_argument("--report", action="store_true",
                   help="Per-chunk plumbing status (ok / failed / missing / "
                        "queued) from the result JSONs and condor_q (a chunk "
                        "whose job is still in the queue is queued, not "
                        "missing). Writes nothing. Exit 0 all ok, 1 a chunk "
                        "failed or is missing with no job, 2 only queued ones "
                        "left. For the PHYSICS verdict use "
                        "scripts/aggregate_validation.py.")
    p.add_argument("--resubmit-failed", action="store_true",
                   help="Submit ONLY the chunks that --report calls failed or "
                        "missing and that have no job in the condor queue "
                        "(needs condor_q: run it on the host shell). Same "
                        "command, same memory as the original job -- a chunk "
                        "is self-contained (see chunk_status()).")
    p.add_argument("--preflight", action="store_true",
                   help="Read-only check of every input; writes nothing.")
    p.add_argument("--dry-run", action="store_true",
                   help="Write submit files but do not condor_submit.")
    p.add_argument("--memory", type=int, default=DEFAULT_MEMORY,
                   help="request_memory in MB (default 2000; the sorted "
                        "matcher keeps one ~16 MB part resident, so this is "
                        "already generous).")
    p.add_argument("--flavour", default=DEFAULT_FLAVOUR,
                   help='+JobFlavour (default "workday" = 8 h; a 20-file chunk '
                        'measured well under 1 h, but WAN reads are variable).')
    p.add_argument("--proxy", default=None,
                   help="x509 proxy path. Default: $X509_USER_PROXY, else the "
                        "conventional /tmp/x509up_u<uid>.")
    p.add_argument("--container", default=None,
                   help="Container image for the payload. Default: the OS of "
                        "the job's CMSSW area (el7 for slc7 = CMSSW_10_6, el8 "
                        "for the el8 CMSSW_15_0_18 area of era 2024).")
    p.add_argument("--no-container", action="store_true",
                   help="Do not request a container. ONLY correct if the "
                        "binaries were built against a native EL9 ROOT.")
    p.add_argument("--cmssw-base", default=None,
                   help="CMSSW area the job should set up. Default: the area "
                        "this script lives in (its bin/ is what the jobs ship); "
                        "$CMSSW_BASE only when the script is not inside a CMSSW "
                        "area (docs/08 T-42).")
    return p.parse_args()


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
def resolve_paths(a):
    """All paths absolute: condor resolves relative names against the submit
    dir, and transfer_output_remaps in particular is fragile with them."""
    era = a.era
    d = {}
    d["extend_dir"] = Path(a.extend_filelist_dir or
                           VAL_ROOT / "filelists" / ("sidecar%s" % era))
    d["nano_dir"] = Path(a.nano_filelist_dir or
                         VAL_ROOT / "filelists" / ("nano%s" % era))
    d["sorted_base"] = Path(a.sorted_base or ("%s/sorted%s" % (DEFAULT_EOS, era)))
    d["out_base"] = Path(a.out_base or ("%s/valout%s" % (DEFAULT_EOS, era)))
    d["bin_dir"] = Path(a.bin_dir or (VAL_ROOT / "bin"))
    d["work_base"] = Path(a.work_base or
                          (VAL_ROOT / ("condor_val%s" % era)))
    d["era"] = era        # carried for message text only
    # abspath, NOT resolve(): resolve() follows symlinks, which rewrote
    # /eos/user/j/<u>/... into /eos/home-j/<u>/... on 2026-07-28. The
    # /eos/user/... spelling is the documented, stable one and is what the
    # condor workers mount; /eos/home-j/... is an internal realization and may
    # not exist there. Keep the user's spelling and only make it absolute.
    for k in list(d):
        if k == "era":
            continue
        d[k] = Path(os.path.abspath(str(d[k])))
    return d


def guess_cmssw_base():
    """Walk up from this script to the release top (the dir containing src/).

    Lets the job set up the right release even when the submitting shell has no
    CMSSW environment -- which is the normal case now that we submit from the
    EL9 host rather than from inside the container.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "src").is_dir() and parent.name.startswith("CMSSW"):
            return str(parent)
    return ""


def job_cmssw_base(a):
    """(base, warning): the CMSSW area the jobs set up -- --cmssw-base when
    given, else the area this script lives in (and with it the bin/ the jobs
    ship: the matcher only runs with the ROOT it was built against).

    $CMSSW_BASE of the submitting shell is deliberately NOT the default
    (2026-10-15, docs/08 T-42): on the lxplus host it is whatever the last
    `cmsenv` in that shell left. A cmsenv of the v15 area left in the host
    shell made all 22 jobs of era 2016 set up CMSSW_15_0_18 in the el8 image,
    where the matcher built in CMSSW_10_6 could not start (exit 127). It is used
    only when this script is not inside a CMSSW area at all.
    """
    env = os.environ.get("CMSSW_BASE", "")
    if a.cmssw_base:
        return os.path.abspath(a.cmssw_base), None
    base = guess_cmssw_base()
    if not base:
        if env:
            return os.path.abspath(env), ("this script is not inside a CMSSW area; "
                                          "the jobs set up $CMSSW_BASE=%s" % env)
        return "", None
    if env and os.path.realpath(env) != os.path.realpath(base):
        return base, ("$CMSSW_BASE of this shell is %s, another area (a cmsenv left "
                      "in this shell?) -- ignored: the jobs set up %s, the area of "
                      "this script and of the bin/ they ship (--cmssw-base "
                      "overrides)" % (env, base))
    return base, None


def chunks_for(nano_dir, short):
    """Per-job nano filelists written by make_nano_filelists_das.sh.

    Falls back to the master filelist as a single chunk if the split directory
    is absent -- that keeps the tool usable with hand-made filelists, at the
    cost of no parallelism for that sample.
    """
    split_dir = nano_dir / short
    if split_dir.is_dir():
        cs = sorted(split_dir.glob("file_%s_*.txt" % short),
                    key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        if cs:
            return cs
    master = nano_dir / ("filelist_%s.txt" % short)
    return [master] if master.is_file() else []


def sorted_ready(sorted_base, short):
    """A sorted dir is usable iff index.txt exists and lists >= 1 part."""
    idx = sorted_base / short / "index.txt"
    if not idx.is_file():
        return False
    try:
        with open(idx) as fh:
            for line in fh:
                s = line.strip()
                if s and not s.startswith("#"):
                    return True
    except OSError:
        return False
    return False


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------
# condor JobStatus values of a job that is still in the queue and may still
# write its result: 1 idle, 2 running, 5 held, 6 transferring output,
# 7 suspended. 3 (removed) and 4 (completed) are on their way out.
_INFLIGHT = {1: "idle", 2: "running", 5: "held", 6: "running", 7: "suspended"}


def queued_chunks(P):
    """{chunk tag: [(state, "cluster.proc"), ...]} of this work base's jobs
    that are still in the condor queue (a list: a chunk may have been submitted
    twice), or None when condor_q cannot be asked here (not on PATH -- e.g.
    inside cmssw-el7 -- or it failed).

    2026-10-15 (docs/08 T-40): --report ran one minute after a submission and
    called all 15 idle chunks "missing ... need re-running"; the jobs were then
    removed and resubmitted. The jobs are recognised by their executable (Cmd =
    <work base>/run_match.sh), so jobs submitted before this change count too;
    the tag is the json name in the job's arguments.
    """
    exe = shutil_which("condor_q")
    if not exe:
        return None
    run_sh = os.path.abspath(str(P["work_base"] / "run_match.sh"))
    lit = run_sh.replace("\\", "\\\\").replace('"', '\\"')   # ClassAd string literal
    try:
        out = subprocess.check_output(
            [exe, "-constraint", 'Cmd =?= "%s"' % lit,
             "-af", "ClusterId", "ProcId", "JobStatus", "Args", "Arguments"],
            stderr=subprocess.DEVNULL, timeout=180)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None
    q = {}
    for line in out.decode("utf-8", "replace").splitlines():
        f = line.split()
        if len(f) < 4 or not (f[0].isdecimal() and f[1].isdecimal() and f[2].isdecimal()):
            continue
        st = int(f[2])
        if st not in _INFLIGHT:
            continue
        tag = next((x[:-5] for x in f[3:] if x.endswith(".json")), None)
        if tag:
            q.setdefault(tag, []).append((_INFLIGHT[st], "%s.%s" % (f[0], f[1])))
    return q


def chunk_status(P, shorts, queued=None):
    """Per-chunk plumbing state from the result JSONs: (rows, failing, inq).

    rows    : [(short, total, ok, fail, miss, queue, [detail strings])]
    failing : [(short, chunk_path)] -- what --resubmit-failed would send
    inq     : [(short, tag, [(state, "cluster.proc"), ...])] -- chunks with a
              job still in the condor queue (queued_chunks()); never in
              `failing`, and counted as queued even when an older result exists
              (ok or not): that job will overwrite it

    WHY A CHUNK IS A SAFE RESUBMIT UNIT
      Each job streams ONE nano chunk against the FULL sorted extend set, so
      chunks are independent and there are no boundary effects. Memory does not
      depend on chunk size either: the matcher keeps the index (tens of KB) plus
      exactly ONE 500k-row part (16 MB) resident, so re-running one chunk costs
      the same as it did the first time (measured peak RSS 489 MB).

    This reports PLUMBING only (did the job produce a result). The physics
    verdict -- unmatched/disagree/invariants/DAS completeness -- belongs to
    scripts/aggregate_validation.py and is deliberately not duplicated here.
    """
    import json as _json
    queued = queued or {}
    resdir = P["out_base"] / "results"
    rows, failing, inq = [], [], []
    for short in shorts:
        cs = chunks_for(P["nano_dir"], short)
        ok = fail = miss = nq = 0
        detail = []
        for c in cs:
            if c.stem in queued:             # a job will (re)write this result
                jobs = queued[c.stem]
                nq += 1
                detail.append("%s(%s)" % (c.stem, "+".join("%s %s" % j for j in jobs)))
                inq.append((short, c.stem, jobs))
                continue
            jf = resdir / ("%s.json" % c.stem)
            state = None                     # None = ok
            if not jf.is_file():
                state = "missing"
            else:
                try:
                    with open(str(jf), encoding="utf-8") as fh:
                        d = _json.load(fh)
                    ec = int(d.get("exit_code", -1))
                    if ec != 0 or d.get("job_failed"):
                        state = "exit %d" % ec
                except (OSError, ValueError):
                    state = "unreadable"
            if state is None:
                ok += 1
            else:
                if state == "missing":
                    miss += 1
                else:
                    fail += 1
                detail.append("%s(%s)" % (c.stem, state))
                failing.append((short, c))
        rows.append((short, len(cs), ok, fail, miss, nq, detail))
    return rows, failing, inq


def _self_cmd():
    """This script by absolute, resolved path (works from any directory and
    through a symlink; 2026-10-15: the --resubmit-failed hint lacked
    'scripts/')."""
    return str(Path(__file__).resolve())


def _opts_in_effect(a, shorts):
    """The options of this call that a printed follow-up command must repeat
    so it acts on the same chunks, directories and job settings (2026-10-15
    review of T-40: a hint without --samples after --smoke would have sent the
    whole campaign; one without --work-base would not see the queue)."""
    out = ["--era", a.era]
    if a.samples or a.smoke:
        out += ["--samples", ",".join(shorts)]
    for opt, val in (("--extend-filelist-dir", a.extend_filelist_dir),
                     ("--nano-filelist-dir", a.nano_filelist_dir),
                     ("--sorted-base", a.sorted_base),
                     ("--out-base", a.out_base),
                     ("--bin-dir", a.bin_dir),
                     ("--work-base", a.work_base),
                     ("--cmssw-base", a.cmssw_base),
                     ("--proxy", a.proxy)):
        if val:
            out += [opt, os.path.abspath(val)]
    if a.eos_url_prefix != EOS_URL_PREFIX:
        out += ["--eos-url-prefix", a.eos_url_prefix]
    if a.memory != DEFAULT_MEMORY:
        out += ["--memory", str(a.memory)]
    if a.flavour != DEFAULT_FLAVOUR:
        out += ["--flavour", a.flavour]
    if a.container:
        out += ["--container", a.container]
    if a.no_container:
        out.append("--no-container")
    return out


def _cmd(a, shorts, *mode):
    """A follow-up command of this script, shell-quoted, ready to paste."""
    return "python3 " + " ".join(shlex.quote(x) for x in
                                 [_self_cmd()] + _opts_in_effect(a, shorts) + list(mode))


def _agg_cmd(a, shorts):
    """aggregate_validation.py for the same chunks and outputs."""
    args = [str(THIS_DIR / "aggregate_validation.py"), "--era", a.era]
    if a.samples or a.smoke:
        args += ["--samples", ",".join(shorts)]
    if a.out_base:
        args += ["--out-base", os.path.abspath(a.out_base)]
    if a.nano_filelist_dir:
        args += ["--nano-filelist-dir", os.path.abspath(a.nano_filelist_dir)]
    return "python3 " + " ".join(shlex.quote(x) for x in args)


def print_report(a, P, shorts):
    queued = queued_chunks(P)
    rows, failing, inq = chunk_status(P, shorts, queued)
    print("=" * 88)
    print("per-chunk report   results = %s" % (P["out_base"] / "results"))
    if queued is None:
        print("[WARN] condor_q is not available here (or failed): the queue was not "
              "asked, so a chunk without a result may still have a job.")
    print("=" * 88)
    print("%-22s %6s %5s %5s %5s %5s  %s"
          % ("sample", "total", "ok", "fail", "miss", "queue", "chunks not ok"))
    print("-" * 88)
    tt = to = tf = tm = tq = 0
    for short, n, ok, fail, miss, nq, detail in rows:
        d = ", ".join(detail[:4]) + (" ..." if len(detail) > 4 else "")
        print("%-22s %6d %5d %5d %5d %5d  %s" % (short, n, ok, fail, miss, nq, d))
        tt += n; to += ok; tf += fail; tm += miss; tq += nq
    print("-" * 88)
    print("%-22s %6d %5d %5d %5d %5d" % ("TOTAL", tt, to, tf, tm, tq))
    held = [qid for _, _, jobs in inq for qs, qid in jobs if qs == "held"]
    if inq:
        by = {}
        for _, _, jobs in inq:
            for qs, _ in jobs:
                by[qs] = by.get(qs, 0) + 1
        print("\n%d chunk(s) have a job in the condor queue (%s) -- NOT failures; "
              "wait for them, then run the report again:"
              % (len(inq), ", ".join("%s %d" % kv for kv in sorted(by.items()))))
        print("  condor_q -constraint 'Cmd =?= \"%s\"'"
              % os.path.abspath(str(P["work_base"] / "run_match.sh")))
        print("  " + _cmd(a, shorts, "--report"))
        if held:
            print("  HELD (never finish by themselves): condor_q -hold %s ; after fixing "
                  "the cause: condor_rm %s , then --resubmit-failed"
                  % (" ".join(held[:8]), " ".join(held[:8])))
        dup = [(tag, jobs) for _, tag, jobs in inq if len(jobs) > 1]
        for tag, jobs in dup:
            print("  [WARN] %s has %d jobs in the queue (%s): a duplicate submission -- "
                  "condor_rm the extra one(s)" % (tag, len(jobs), " ".join(j[1] for j in jobs)))
    if failing and queued is None:
        print("\nqueue state UNKNOWN: %d chunk(s) have no ok result -- they may still have "
              "a job. Run the report on the lxplus host shell before re-running anything:"
              % len(failing))
        print("  " + _cmd(a, shorts, "--report"))
    elif failing:
        print("\n%d chunk(s) have no ok result and no job in the queue (never submitted, "
              "or the job ended without an ok result) -- submit them (same cost as the "
              "first run; a chunk is self-contained):" % len(failing))
        print("  " + _cmd(a, shorts, "--resubmit-failed"))
    if not failing and not inq:
        print("\nAll chunks produced a result. Now check the PHYSICS verdict:")
    else:
        print("\nFor the PHYSICS verdict (unmatched/disagree/DAS completeness), "
              "once every chunk is ok:")
    print("  " + _agg_cmd(a, shorts))
    if failing and queued is None:
        return 3
    if failing or held:
        return 1
    return 2 if inq else 0


def run_preflight(a, P, shorts):
    rows = []

    def add(level, check, detail=""):
        rows.append((level, check, detail))
        print("[%-4s] %-42s %s" % (level, check, detail))

    print("=" * 88)
    print("submit_validation_condor.py PREFLIGHT   era=%s" % a.era)
    print("=" * 88)

    # environment
    for exe in ("matchTtbarIdSorted", "sortSplitExtend"):
        p = P["bin_dir"] / exe
        add("PASS" if p.is_file() and os.access(p, os.X_OK) else "FAIL",
            "binary %s" % exe,
            str(p) if p.is_file() else "MISSING -- run `make -j4` in Validation/")
    cs = shutil_which("condor_submit")
    if cs:
        add("PASS", "condor_submit", cs)
    else:
        # This is the normal state INSIDE cmssw-el7: the condor client lives on
        # the EL9 host only. Submitting is a host-side action; the payload runs
        # in a container (see the header).
        add("FAIL", "condor_submit",
            "not on PATH -- are you inside cmssw-el7/-el8? Submit from the EL9 "
            "host (type `exit` first); the jobs still run in the area's container.")

    cb, cb_warn = job_cmssw_base(a)
    if a.no_container:
        add("WARN", "container",
            "--no-container: only valid for a native-EL9 build of the tools")
    else:
        img, arch = image_for_area(cb)
        img = a.container or img
        # Singularity images live on cvmfs; a missing path means every job would
        # fail to start, which is worth catching before 49 submissions.
        if not Path(img).exists():
            add("FAIL", "container image", "%s NOT FOUND on cvmfs" % img)
        elif a.container:
            add("PASS", "container image", img)
        elif arch is None:
            add("WARN", "container image",
                "%s  (the SCRAM arch of the CMSSW area is unknown -> el7 default; "
                "an el8/el9 build needs --container)" % img)
        else:
            add("PASS", "container image", "%s  (from the area's arch %s)" % (img, arch))

    ok_cb = bool(cb) and Path(cb, "src").is_dir()
    add("PASS" if ok_cb else "FAIL", "CMSSW base for job env",
        cb if ok_cb else "cannot determine -- pass --cmssw-base")
    if cb_warn:
        add("WARN", "$CMSSW_BASE of this shell", cb_warn)
    add("PASS" if Path("/cvmfs/cms.cern.ch/cmsset_default.sh").is_file() else "FAIL",
        "cvmfs cmsset_default.sh", "/cvmfs/cms.cern.ch/cmsset_default.sh")
    # Jobs read central NanoAOD as root://cms-xrd-global.cern.ch//store/... so a
    # proxy is mandatory, and it must be readable by the SCHEDD, not just here.
    proxy, problem = resolve_proxy(a.proxy)
    if problem:
        add("FAIL", "x509 proxy", problem)
    else:
        left = proxy_timeleft(proxy)
        if left is None:
            add("PASS", "x509 proxy", "%s  (lifetime not checked)" % proxy)
        elif left < 3600:
            add("FAIL", "x509 proxy lifetime",
                "%s  expires in %d min -- renew:\n    %s"
                % (proxy, left // 60, PROXY_CMD))
        elif left < 24 * 3600:
            add("WARN", "x509 proxy lifetime",
                "%s  only %.1f h left; the campaign may outlive it"
                % (proxy, left / 3600.0))
        else:
            add("PASS", "x509 proxy",
                "%s  (%.0f h left)" % (proxy, left / 3600.0))

    # output base must not be AFS (quota + 25 h token lifetime, T-21/T-22)
    ob = str(P["out_base"])
    add("FAIL" if ob.startswith("/afs/") else "PASS", "out-base not on AFS", ob)
    sb = str(P["sorted_base"])
    add("WARN" if sb.startswith("/afs/") else "PASS", "sorted-base not on AFS", sb)

    # per sample
    total_jobs = 0
    for s in shorts:
        ef = P["extend_dir"] / ("filelist_%s.txt" % s)
        n_ext = sum(1 for _ in open(ef)) if ef.is_file() else -1
        add("PASS" if n_ext > 0 else "FAIL", "extend filelist %s" % s,
            ("%d files" % n_ext) if n_ext > 0 else "MISSING %s" % ef)

        cs = chunks_for(P["nano_dir"], s)
        add("PASS" if cs else "FAIL", "nano chunks %s" % s,
            ("%d chunk(s)" % len(cs)) if cs
            else "none under %s" % (P["nano_dir"] / s))
        total_jobs += len(cs)

        ready = sorted_ready(P["sorted_base"], s)
        add("PASS" if ready else "WARN", "sorted dir %s" % s,
            str(P["sorted_base"] / s) if ready
            else "not sorted yet -- run --sort-only first")

    # Was a WARN until the 2026-07-28 smoke proved it: the job logged
    # "sorted parts in index: 10", i.e. a worker does read EOS as POSIX. Kept as
    # a PASS line rather than removed, because it is a real environment
    # dependency and the job still exits 125 with a clear message if it breaks.
    add("PASS", "worker reads EOS (POSIX)",
        "verified 2026-07-28 smoke; job exits 125 if it ever stops working")
    add("PASS", "total condor jobs", str(total_jobs))
    n_fail = sum(1 for l, _, _ in rows if l == "FAIL")
    n_warn = sum(1 for l, _, _ in rows if l == "WARN")
    print("-" * 88)
    print("PREFLIGHT: %d PASS, %d WARN, %d FAIL"
          % (sum(1 for l, _, _ in rows if l == "PASS"), n_warn, n_fail))
    print("RESULT: %s" % ("NOT READY -- fix the FAIL items" if n_fail
                          else "READY" + (" (review WARNs)" if n_warn else "")))
    return 1 if n_fail else 0


# The one command that makes a submittable proxy. Printed verbatim whenever the
# proxy is missing or unusable, so the remedy is never something to look up.
PROXY_CMD = ("voms-proxy-init -voms cms -rfc --valid 192:00 "
             "--out $PWD/proxy.cert && export X509_USER_PROXY=$PWD/proxy.cert")


def resolve_proxy(explicit):
    """Return (path, problem). Never copies, never writes anything.

    WHY /tmp IS REJECTED (2026-07-28, job 13284914 went on hold)
        Hold reason: Transfer input files failure at access point bigbird27
        ... reading from file /tmp/x509up_u148947: (errno 2) No such file
    /tmp is NODE-LOCAL. The submit host is not the access point, so a /tmp path
    in x509userproxy is unreadable exactly when condor needs it. The proxy must
    sit somewhere the schedd can see (AFS, e.g. the working directory).

    We deliberately do NOT auto-copy it into $HOME: a credential should not
    appear in the user's home directory as a side effect of a submit command.
    The user creates it where they want it; this function only checks.
    """
    cand = explicit or os.environ.get("X509_USER_PROXY")
    if not cand:
        tmp_default = "/tmp/x509up_u%d" % os.getuid()
        if Path(tmp_default).is_file():
            return tmp_default, (
                "proxy is on /tmp, which the schedd cannot read (jobs would go "
                "on hold). Re-create it in a shared location:\n    " + PROXY_CMD)
        return None, ("no proxy found ($X509_USER_PROXY unset, no %s).\n    "
                      % tmp_default + PROXY_CMD)
    if not Path(cand).is_file():
        return None, "proxy path does not exist: %s\n    %s" % (cand, PROXY_CMD)
    if str(cand).startswith("/tmp/"):
        return cand, ("proxy is on /tmp (node-local); the schedd cannot read it "
                      "and jobs will go on hold. Re-create it elsewhere:\n    "
                      + PROXY_CMD)
    return str(cand), None


def proxy_timeleft(path):
    """Remaining proxy lifetime in seconds, or None if it cannot be determined.

    Jobs here run for hours and the whole campaign is 49 of them, so a proxy
    that expires mid-flight produces XRootD read failures that look exactly
    like the transient AAA errors of T-21. Worth checking up front.
    """
    if not shutil_which("voms-proxy-info"):
        return None
    try:
        out = subprocess.check_output(
            ["voms-proxy-info", "-file", str(path), "-timeleft"],
            stderr=subprocess.DEVNULL)
        return int(out.decode().strip().split()[0])
    except (subprocess.CalledProcessError, ValueError, IndexError, OSError):
        return None


def shutil_which(x):
    from shutil import which
    return which(x)


# ---------------------------------------------------------------------------
# sorting (local, serial -- it is an external merge sort over the whole sample)
# ---------------------------------------------------------------------------
def do_sort(a, P, shorts):
    rc_all = 0
    for s in shorts:
        if sorted_ready(P["sorted_base"], s):
            print("[sort] %-20s SKIP (index.txt already present)" % s)
            continue
        ef = P["extend_dir"] / ("filelist_%s.txt" % s)
        if not ef.is_file():
            print("[sort] %-20s FAIL: no extend filelist %s" % (s, ef))
            rc_all = 1
            continue
        outd = P["sorted_base"] / s
        tmpd = P["sorted_base"] / ("_tmp_%s" % s)
        cmd = [str(P["bin_dir"] / "sortSplitExtend"),
               "--filelist", str(ef), "--out-dir", str(outd),
               "--tmp-dir", str(tmpd)]
        print("[sort] %-20s RUN  %s" % (s, " ".join(cmd)))
        if a.dry_run:
            continue
        outd.parent.mkdir(parents=True, exist_ok=True)
        rc = subprocess.call(cmd)
        print("[sort] %-20s exit=%d" % (s, rc))
        if rc != 0:
            rc_all = 1
    return rc_all


# ---------------------------------------------------------------------------
# condor files
# ---------------------------------------------------------------------------
RUN_SH = """#!/usr/bin/env bash
# Auto-generated by submit_validation_condor.py -- do not edit by hand.
#
# NOTE ON /eos: the sorted-input path is baked in HERE rather than passed as a
# condor argument, because CERN's standard schedds reject /eos paths appearing in
# a submit file. The job reads it as a normal POSIX path at RUN time, which is a
# different thing from condor being asked to manage it at SUBMIT time.
#
# NOTE ON `set -u`: deliberately NOT enabled globally. cmsset_default.sh is not
# -u clean (2026-07-28: "cmsset_local.sh: line 8: CVS_RSH: unbound variable"),
# and under -u that aborts the whole job at the very first setup line.
set -o pipefail

NANO_CHUNK="$1"      # transferred into the scratch dir by condor
LABEL="$2"           # sample short name; selects the sorted sub-directory
JSON_OUT="$3"        # written here, shipped to EOS by output_destination
ROOT_OUT="$4"

SORTED_BASE="%(sorted_base)s"
SORTED_DIR="${SORTED_BASE}/${LABEL}"
DEST_URL="%(dest_url)s"

# ---------------------------------------------------------------------------
# Guarantee the declared output files exist, NO MATTER where this script dies.
#
# WHY A TRAP AND NOT A TAIL CHECK (2026-07-28, jobs 13284916 / 13284914):
#   transfer_output_files is a HARD contract -- a missing file puts the job on
#   HOLD and the hold reason is a *transfer* error, which HIDES the payload's
#   real failure. A tail-of-script check does not help when the script aborts
#   early (which is exactly what happened: `set -u` killed it at the first
#   cmsset line, long before any check). An EXIT trap always runs.
# ---------------------------------------------------------------------------
ensure_outputs() {
  rc=$?
  # 1) Always have a JSON, even if the matcher never ran. A stub with
  #    job_failed:true lets the aggregator mark this chunk FAILED instead of
  #    silently missing. The EXIT trap (not a tail check) is what makes this
  #    reliable: the script can die at the very first setup line.
  if [ ! -f "${JSON_OUT}" ]; then
    echo "[job] no JSON from the matcher; writing a failure stub (rc=${rc})."
    cat > "${JSON_OUT}" <<JSONEOF
{
  "tool": "run_match.sh",
  "label": "${LABEL}",
  "nano_filelist": "${NANO_CHUNK}",
  "job_failed": true,
  "exit_code": ${rc},
  "note": "no counters produced -- see this job's condor .out/.err on AFS"
}
JSONEOF
  fi

  # 2) Stage results to EOS OURSELVES (condor manages no output files -- see the
  #    submit template). mkdir is idempotent; -f overwrites a previous attempt.
  echo "[job] staging results to ${DEST_URL}"
  xrdfs %(eos_host)s mkdir -p "%(dest_dir)s" 2>/dev/null || true
  # Retry: EOS hiccups happen, and losing the JSON of a good run means redoing
  # the whole chunk. Three tries with backoff.
  xrc=1
  for attempt in 1 2 3; do
    xrdcp -f "${JSON_OUT}" "${DEST_URL}/${JSON_OUT}" && { xrc=0; break; }
    xrc=$?
    echo "[job] xrdcp attempt ${attempt} failed (rc=${xrc}); retrying"
    sleep $((attempt * 5))
  done
  if [ ${xrc} -ne 0 ]; then
    echo "[job] ERROR: could not stage the JSON to EOS after 3 tries (rc=${xrc})."
    echo "[job]        The counters ARE in this .out between the BEGIN JSON /"
    echo "[job]        END JSON markers, so nothing is lost -- but the aggregator"
    echo "[job]        will report this chunk as missing until it is re-run."
    echo "[job]        Exiting 122 so condor_history flags it immediately."
    rc=122
  fi
  if [ -f "${ROOT_OUT}" ]; then
    xrdcp -f "${ROOT_OUT}" "${DEST_URL}/${ROOT_OUT}" \\
      || echo "[job] WARNING: xrdcp of the ROOT file failed (plot input only)"
  fi
  echo "[job] done rc=${rc}"
}
trap ensure_outputs EXIT

echo "[job] host=$(hostname)"
echo "[job] date=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)"
echo "[job] pwd=$(pwd)"
echo "[job] os=$(cat /etc/redhat-release 2>/dev/null || echo unknown)"
echo "[job] chunk=${NANO_CHUNK}  label=${LABEL}"
echo "[job] sorted=${SORTED_DIR}"

# ---------------------------------------------------------------------------
# Environment. We do NOT rely on `getenv = True`: submitted from EL9, executed
# in EL7, so the submitter's environment is the WRONG one to inherit. Set the
# release up from cvmfs instead. `set +u` is required around this -- see above.
# ---------------------------------------------------------------------------
set +u
%(env_setup)s
echo "[job] which root-config: $(which root-config 2>/dev/null || echo NONE)"
echo "[job] SCRAM_ARCH=${SCRAM_ARCH:-unset}"
echo "[job] CMSSW_BASE=${CMSSW_BASE:-unset}"
if ! command -v root-config >/dev/null 2>&1; then
  echo "[job] FATAL: root-config not on PATH after environment setup."
  echo "[job]        The matcher links ROOT, so it cannot run. Check the .err"
  echo "[job]        for cmsset/scram messages."
  exit 123
fi

MATCH="./%(match_name)s"
chmod +x "${MATCH}" 2>/dev/null || true
if [ ! -x "${MATCH}" ]; then
  echo "[job] FATAL: matcher not executable: ${MATCH}"
  echo "[job]        expected it to be transferred into $(pwd); ls follows:"
  ls -la
  exit 127
fi
# The matcher only starts with the ROOT it was built against. Built in another
# CMSSW area than the one set up above, it dies in the loader with exit 127 and
# the reason only in the .err (2026-10-15, docs/08 T-42: "symbol lookup error:
# ./matchTtbarIdSorted: undefined symbol: _ZN6TClass8GetClassERKSt9type_infobb"
# -- ROOT's library names carry no version, so the other release's libCore.so
# loads and the failure is a symbol). `ldd -r` resolves every symbol without
# running the program: a library not found, or an undefined symbol of the
# matcher itself (not of a ROOT library), stops the job here with its own code
# and the reason in the .out.
if command -v ldd >/dev/null 2>&1; then
  LDD_OUT="$(ldd -r "${MATCH}" 2>&1)"
  MISSING_LIBS="$(echo "${LDD_OUT}" | grep 'not found')"
  MISSING_SYMS="$(echo "${LDD_OUT}" | grep 'undefined symbol' | grep -F "${MATCH##*/})")"
  if [ -n "${MISSING_LIBS}" ] || [ -n "${MISSING_SYMS}" ]; then
    echo "[job] FATAL: the matcher cannot run with CMSSW_BASE=${CMSSW_BASE:-unset}:"
    [ -n "${MISSING_LIBS}" ] && echo "${MISSING_LIBS}" | head -n 3
    [ -n "${MISSING_SYMS}" ] && echo "${MISSING_SYMS}" | head -n 3
    echo "[job]        built in another CMSSW area? submit with --cmssw-base <that area>"
    exit 121
  fi
fi
if [ ! -r "${NANO_CHUNK}" ]; then
  echo "[job] FATAL: nano chunk not readable: ${NANO_CHUNK}"; exit 126
fi
echo "[job] nano files in chunk: $(wc -l < "${NANO_CHUNK}")"
if [ ! -r "${SORTED_DIR}/index.txt" ]; then
  echo "[job] FATAL: cannot read ${SORTED_DIR}/index.txt"
  echo "[job]        Either the sample is not sorted, or this worker does not"
  echo "[job]        expose EOS as POSIX. Listing the base directory:"
  ls -la "${SORTED_BASE}" 2>&1 | head -20
  exit 125
fi
echo "[job] sorted parts in index: $(grep -cv '^#' "${SORTED_DIR}/index.txt")"

# NOTE: no --allow-missing-files here, deliberately. If a nano file in this
# chunk cannot be read after the built-in retries, this job MUST fail (exit 4)
# rather than silently validate a fraction of the chunk (docs/08 T-21).
"${MATCH}" \\
    --sorted-dir     "${SORTED_DIR}" \\
    --nano-filelist  "${NANO_CHUNK}" \\
    --label          "${LABEL}" \\
    --json           "${JSON_OUT}" \\
    --out            "${ROOT_OUT}"
rc=$?
echo "[job] matchTtbarIdSorted exit=${rc}"
if [ ${rc} -eq 127 ] || [ ${rc} -eq 126 ]; then
  echo "[job] exit ${rc} = the matcher could not be started (loader: a library or a"
  echo "[job]        symbol of another ROOT; the message is in this job's .err). Usual"
  echo "[job]        cause: the job set up another CMSSW area than the one the matcher"
  echo "[job]        was built in (CMSSW_BASE above; docs/08 T-42)."
fi
# Echo the JSON into stdout too: the .out lands on AFS, so the numbers survive
# even if the EOS copy below fails.
if [ -f "${JSON_OUT}" ]; then
  echo "[job] ---- BEGIN JSON ----"; cat "${JSON_OUT}"; echo "[job] ---- END JSON ----"
fi
exit ${rc}
"""

SUB = """universe                = vanilla
batch_name              = val_%(era)s
executable              = %(run_sh)s
arguments               = $(chunk) $(label) $(json) $(rootout)
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_input_files    = $(chunk), %(match_bin)s
# Condor manages NO output files. The job xrdcp's its own results to EOS.
#
# WHY (2026-07-28, and it is what TopCPVGenCategorizer/condor already did):
#   With a non-empty transfer_output_files, a payload that dies leaves the
#   declared file missing -> condor HOLDS the job and reports a *transfer*
#   error, hiding the real failure. Two holds were spent learning this. Letting
#   the job stage its own output means a failing job just exits nonzero and its
#   .out tells you why.
transfer_output_files   = ""
output                  = %(logdir)s/$(label).$(ClusterId).$(ProcId).out
error                   = %(logdir)s/$(label).$(ClusterId).$(ProcId).err
log                     = %(logdir)s/$(label).$(ClusterId).log
request_memory          = %(memory)d
request_cpus            = 1
# getenv is deliberately False: submitted from EL9, executed in EL7 (see header).
getenv                  = False
use_x509userproxy       = true
%(image_line)s%(proxy_line)s+JobFlavour            = "%(flavour)s"
notification            = never
queue chunk, label, json, rootout from %(argsfile)s
"""


def write_condor(a, P, plan):
    """plan: list of (short, chunk_path, json_name, root_name).

    Scaffolding on AFS (work_base); the JOB stages its own results to EOS over
    XRootD. Modelled on TopCPVGenCategorizer/condor, which has been running at
    CERN: condor manages no output files there either, precisely so a failing
    payload reports its own error instead of a transfer error.
    """
    work = P["work_base"]
    logdir = work / "logs"
    for d in (work, logdir):
        d.mkdir(parents=True, exist_ok=True)

    cmssw_base, cb_warn = job_cmssw_base(a)
    if cb_warn:
        print("[WARN] %s" % cb_warn)
    if a.no_container:
        env_setup = ('echo "[job] --no-container: expecting root-config already '
                     'on PATH"')
    else:
        if not cmssw_base:
            sys.exit("FATAL: cannot determine CMSSW base for the job "
                     "environment. Pass --cmssw-base /path/to/CMSSW_X_Y_Z.")
        env_setup = ("source /cvmfs/cms.cern.ch/cmsset_default.sh\n"
                     'cd "%s/src" || { echo "[job] FATAL: no %s/src"; exit 124; }\n'
                     "eval `scramv1 runtime -sh`\n"
                     "cd - >/dev/null" % (cmssw_base, cmssw_base))

    # XRootD destination for the job's own xrdcp. Host and path are needed
    # separately for `xrdfs <host> mkdir -p <path>`.
    #
    # XRootD REQUIRES A DOUBLE SLASH between host and an absolute path:
    #     root://eosuser.cern.ch//eos/user/...
    # A single slash gives "xrdcp ... rc=54". This exact mistake was made TWICE
    # (2026-07-28: once with output_destination, then reintroduced here via
    # rstrip("/")), so the invariant is asserted below rather than trusted.
    dest_dir = str(P["out_base"] / "results")
    prefix = a.eos_url_prefix if a.eos_url_prefix.endswith("/") \
        else a.eos_url_prefix + "/"
    eos_host = prefix.rstrip("/")                     # root://eosuser.cern.ch
    dest_url = eos_host + "/" + dest_dir              # '/' + '/eos/...' -> '//'
    if "://" in dest_url:
        _host, _path = dest_url.split("://", 1)[1], None
        _rest = dest_url.split("://", 1)[1]
        if "//" not in _rest:
            sys.exit("FATAL(internal): XRootD destination lacks the required "
                     "double slash between host and path:\n    %s\n"
                     "  Expected the form root://<host>//<abs-path>." % dest_url)

    # written next to it and renamed: queued jobs of an earlier submission read
    # this file when they start, so it must never be seen half-written
    run_sh = work / "run_match.sh"
    tmp_sh = work / (".run_match.sh.%d" % os.getpid())
    tmp_sh.write_text(RUN_SH % {
        "match_name": "matchTtbarIdSorted",
        "sorted_base": P["sorted_base"],
        "env_setup": env_setup,
        "dest_url": dest_url,
        "dest_dir": dest_dir,
        "eos_host": prefix.rstrip("/"),
    })
    tmp_sh.chmod(0o755)
    os.replace(str(tmp_sh), str(run_sh))

    argsfile = work / "match.args"
    with open(argsfile, "w") as fh:
        for short, chunk, jname, rname in plan:
            fh.write("%s, %s, %s, %s\n" % (chunk, short, jname, rname))

    proxy, problem = resolve_proxy(a.proxy)
    if problem:
        sys.exit("FATAL: %s" % problem)
    left = proxy_timeleft(proxy)
    if left is not None and left < 3600:
        sys.exit("FATAL: proxy %s expires in %d min; renew before submitting:\n"
                 "    %s" % (proxy, left // 60, PROXY_CMD))
    print("[proxy] %s%s" % (proxy,
          "" if left is None else "  (%.0f h left)" % (left / 3600.0)))

    image = a.container
    if not a.no_container and not image:
        image, arch = image_for_area(cmssw_base)
        if arch is None:
            print("[WARN] the SCRAM arch of %s is unknown -> container %s (el7). An "
                  "el8/el9 build of the tools needs --container." % (cmssw_base, image))
    image_line = ("" if a.no_container
                  else 'MY.SingularityImage = "%s"\n' % image)
    print("[job env] %s" % ("--no-container: the worker's own environment" if a.no_container
                            else "%s   image %s" % (cmssw_base, image)))
    sub = work / "match.sub"
    sub.write_text(SUB % {
        "era": P["era"], "run_sh": run_sh, "logdir": logdir,
        "match_bin": P["bin_dir"] / "matchTtbarIdSorted",
        "memory": a.memory, "flavour": a.flavour,
        "image_line": image_line,
        "proxy_line": "x509userproxy = %s\n" % proxy,
        "argsfile": argsfile,
    })

    # ---- self-check: no bare /eos path may survive in the submit file ------
    # The standard schedds reject them outright (T-23). Catch it here rather
    # than letting the schedd explain it again.
    bad = [ln for ln in sub.read_text().splitlines()
           if re.search(r"(^|[^:/])/eos/", ln) and not ln.lstrip().startswith("#")]
    if bad:
        sys.exit("FATAL: generated submit file still contains bare /eos paths;\n"
                 "  the standard schedds will reject it. Offending line(s):\n    "
                 + "\n    ".join(bad))
    print("results -> %s/" % dest_url)
    return sub, argsfile, logdir


def print_next_steps(a, shorts, logdir):
    """What to run after a submission (2026-10-15, T-40): absolute paths, the
    options in effect, and the batch name instead of condor_rm <user>."""
    print("\nmonitor:   condor_q -constraint 'JobBatchName == \"val_%s\"'" % a.era)
    print("logs:      %s" % logdir)
    print("report:    %s" % _cmd(a, shorts, "--report"))
    print("           (a chunk whose job is still queued shows as queued, not missing)")
    print("aggregate: %s   (when every chunk is ok)" % _agg_cmd(a, shorts))
    print("remove:    condor_rm -constraint 'JobBatchName == \"val_%s\"'   (not "
          "condor_rm <user>: that removes every job of yours)" % a.era)


def main():
    a = parse_args()
    P = resolve_paths(a)
    shorts = ([s.strip() for s in a.samples.split(",")] if a.samples
              else list(SHORTS))
    if a.smoke:
        shorts = [SMOKE_SHORT]

    print("era              : %s" % a.era)
    print("extend filelists : %s" % P["extend_dir"])
    print("nano filelists   : %s" % P["nano_dir"])
    print("sorted base      : %s" % P["sorted_base"])
    print("out base         : %s   (results via %s)"
          % (P["out_base"], a.eos_url_prefix))
    print("work base        : %s   (condor scaffolding, must NOT be /eos)"
          % P["work_base"])
    print("samples          : %s" % ", ".join(shorts))
    print()

    if a.report:
        return print_report(a, P, shorts)

    if a.preflight:
        return run_preflight(a, P, shorts)

    if a.sort_only:
        return do_sort(a, P, shorts)

    # the condor scaffolding must NOT be on /eos (schedd rejects it outright)
    if str(P["work_base"]).startswith("/eos/"):
        sys.exit("FATAL: --work-base is on /eos (%s).\n"
                 "  CERN's standard schedds reject /eos paths inside a submit\n"
                 "  file. Put the scaffolding on AFS; results still go to EOS."
                 % P["work_base"])

    # refuse to write results onto AFS -- this bit us twice (T-21/T-22)
    if str(P["out_base"]).startswith("/afs/"):
        sys.exit("FATAL: --out-base is on AFS (%s).\n"
                 "  AFS home is quota-limited and its token expires in ~25 h,\n"
                 "  which is shorter than this campaign. Use EOS."
                 % P["out_base"])

    if a.resubmit_failed:
        queued = queued_chunks(P)
        if queued is None:
            sys.exit("FATAL: condor_q is not available here (or failed), so a chunk "
                     "whose job is still queued cannot be told from a failed one.\n"
                     "  Run --resubmit-failed on the lxplus host shell (not inside "
                     "cmssw-el7/-el8); if condor_q itself failed, try again in a minute.")
        _, failing, inq = chunk_status(P, shorts, queued)
        if inq:
            print("not resubmitted -- a job is in the condor queue (%d):" % len(inq))
            for short, tag, jobs in inq:
                print("   %-22s %-28s %s" % (short, tag, " ".join("%s %s" % j for j in jobs)))
            print()
        if not failing:
            if inq:
                print("Nothing to resubmit: every chunk has an ok result or a job in "
                      "the queue. When the queue is empty:")
                print("  " + _cmd(a, shorts, "--report"))
            else:
                print("Nothing to resubmit: every chunk already produced a result. "
                      "Check the physics verdict:")
                print("  " + _agg_cmd(a, shorts))
            return 0
        plan = []
        for short, c in failing:
            if not sorted_ready(P["sorted_base"], short):
                sys.exit("FATAL: %s is not sorted (%s/index.txt missing)."
                         % (short, P["sorted_base"] / short))
            tag = c.stem
            plan.append((short, c, "%s.json" % tag, "match_%s.root" % tag))
        print("resubmitting %d failed/missing chunk(s):" % len(plan))
        for short, c, _, _ in plan:
            print("   %-22s %s" % (short, c.stem))
        print()
        sub, argsfile, logdir = write_condor(a, P, plan)
        print("wrote %s" % sub)
        if a.dry_run:
            print("\n[dry-run] not submitting.")
            return 0
        rc = subprocess.call(["condor_submit", str(sub)])
        print("condor_submit exit=%d" % rc)
        if rc == 0:
            print_next_steps(a, shorts, logdir)
        return rc

    plan = []
    for s in shorts:
        if not sorted_ready(P["sorted_base"], s):
            sys.exit("FATAL: %s is not sorted yet (%s/index.txt missing).\n"
                     "  Run (inside the area's container, after cmsenv):\n  %s"
                     % (s, P["sorted_base"] / s, _cmd(a, shorts, "--sort-only")))
        cs = chunks_for(P["nano_dir"], s)
        if not cs:
            sys.exit("FATAL: no nano chunks for %s under %s\n"
                     "  Run:  cd %s && ./make_nano_filelists_das.sh %s"
                     % (s, P["nano_dir"], shlex.quote(str(VAL_ROOT / "filelists")), a.era))
        if a.smoke:
            cs = cs[:1]
        for c in cs:
            tag = c.stem                       # file_<short>_<i>  (unique)
            plan.append((s, c, "%s.json" % tag, "match_%s.root" % tag))

    print("planned jobs: %d" % len(plan))
    for s in shorts:
        n = sum(1 for x in plan if x[0] == s)
        print("   %-20s %3d job(s)" % (s, n))
    print()

    sub, argsfile, logdir = write_condor(a, P, plan)
    print("wrote %s" % sub)
    print("wrote %s" % argsfile)
    print("logs  %s" % logdir)

    if a.dry_run:
        print("\n[dry-run] not submitting. Inspect the files above, then re-run "
              "without --dry-run.")
        return 0

    rc = subprocess.call(["condor_submit", str(sub)])
    print("condor_submit exit=%d" % rc)
    if rc == 0:
        print_next_steps(a, shorts, logdir)
    return rc


if __name__ == "__main__":
    sys.exit(main())
