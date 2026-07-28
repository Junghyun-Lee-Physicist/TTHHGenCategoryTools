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
# =============================================================================

import argparse
import os
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
    p.add_argument("--sort-only", action="store_true",
                   help="Only run sortSplitExtend for samples missing it, "
                        "locally and serially, then exit. Sorting is cheap "
                        "(~11 min for 146 M rows) and inherently serial.")
    p.add_argument("--smoke", action="store_true",
                   help="Submit ONE chunk of ONE sample (%s) and stop."
                        % SMOKE_SHORT)
    p.add_argument("--preflight", action="store_true",
                   help="Read-only check of every input; writes nothing.")
    p.add_argument("--dry-run", action="store_true",
                   help="Write submit files but do not condor_submit.")
    p.add_argument("--memory", type=int, default=2000,
                   help="request_memory in MB (default 2000; the sorted "
                        "matcher keeps one ~16 MB part resident, so this is "
                        "already generous).")
    p.add_argument("--flavour", default="workday",
                   help='+JobFlavour (default "workday" = 8 h; a 20-file chunk '
                        'measured well under 1 h, but WAN reads are variable).')
    p.add_argument("--proxy", default=None,
                   help="x509 proxy path. Default: $X509_USER_PROXY, else the "
                        "conventional /tmp/x509up_u<uid>.")
    p.add_argument("--container", default=DEFAULT_IMAGE,
                   help="Container image for the payload (EL7, to match the "
                        "slc7/ROOT-6.14 build). Default: %(default)s")
    p.add_argument("--no-container", action="store_true",
                   help="Do not request a container. ONLY correct if the "
                        "binaries were built against a native EL9 ROOT.")
    p.add_argument("--cmssw-base", default=None,
                   help="CMSSW release the job should set up. Default: "
                        "$CMSSW_BASE, else derived from this script's path.")
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
    for k in list(d):
        d[k] = d[k].resolve()
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
            "not on PATH -- are you inside cmssw-el7? Submit from the EL9 host "
            "(type `exit` first); the jobs still run in an EL7 container.")

    if a.no_container:
        add("WARN", "container",
            "--no-container: only valid for a native-EL9 build of the tools")
    else:
        img = a.container
        # Singularity images live on cvmfs; a missing path means every job would
        # fail to start, which is worth catching before 49 submissions.
        add("PASS" if Path(img).exists() else "FAIL", "container image",
            img if Path(img).exists() else "%s NOT FOUND on cvmfs" % img)

    cb = a.cmssw_base or os.environ.get("CMSSW_BASE") or guess_cmssw_base()
    ok_cb = bool(cb) and Path(cb, "src").is_dir()
    add("PASS" if ok_cb else "FAIL", "CMSSW base for job env",
        cb if ok_cb else "cannot determine -- pass --cmssw-base")
    add("PASS" if Path("/cvmfs/cms.cern.ch/cmsset_default.sh").is_file() else "FAIL",
        "cvmfs cmsset_default.sh", "/cvmfs/cms.cern.ch/cmsset_default.sh")
    proxy = find_proxy(a.proxy)
    if proxy:
        add("PASS", "x509 proxy", proxy)
    else:
        # jobs read central NanoAOD over XRootD; without a proxy every job fails
        add("FAIL", "x509 proxy",
            "not found (checked --proxy, $X509_USER_PROXY, /tmp/x509up_u%d) -- "
            "voms-proxy-init -voms cms -rfc --valid 168:00" % os.getuid())

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

    # The jobs read the sorted parts from EOS POSIX directly. That is standard on
    # lxplus batch, but it IS an assumption about the worker, so say so instead of
    # letting a 49-job failure explain it. The job script exits 125 with a clear
    # message if index.txt is unreadable.
    add("WARN", "worker must see EOS (POSIX)",
        "%s -- verified by --smoke, job exits 125 with a clear message if not"
        % P["sorted_base"])
    add("PASS", "total condor jobs", str(total_jobs))
    n_fail = sum(1 for l, _, _ in rows if l == "FAIL")
    n_warn = sum(1 for l, _, _ in rows if l == "WARN")
    print("-" * 88)
    print("PREFLIGHT: %d PASS, %d WARN, %d FAIL"
          % (sum(1 for l, _, _ in rows if l == "PASS"), n_warn, n_fail))
    print("RESULT: %s" % ("NOT READY -- fix the FAIL items" if n_fail
                          else "READY" + (" (review WARNs)" if n_warn else "")))
    return 1 if n_fail else 0


def find_proxy(explicit):
    """Locate the x509 proxy.

    voms-proxy-init writes /tmp/x509up_u<uid> and does NOT export
    X509_USER_PROXY, so checking only the env var reports "no proxy" on a
    perfectly good session -- which is exactly what the first --preflight run
    did on 2026-07-28.
    """
    for cand in (explicit,
                 os.environ.get("X509_USER_PROXY"),
                 "/tmp/x509up_u%d" % os.getuid()):
        if cand and Path(cand).is_file():
            return cand
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
set -uo pipefail
NANO_CHUNK="$1"      # transferred into the scratch dir by condor
SORTED_DIR="$2"      # read directly from EOS (shared, read-only)
LABEL="$3"
JSON_OUT="$4"        # local name; condor ships it back
ROOT_OUT="$5"

echo "[job] host=$(hostname)"
echo "[job] date=$(date -u +%%Y-%%m-%%dT%%H:%%M:%%SZ)"
echo "[job] pwd=$(pwd)"
echo "[job] os=$(cat /etc/redhat-release 2>/dev/null || echo unknown)"
echo "[job] chunk=${NANO_CHUNK}  label=${LABEL}"
echo "[job] sorted=${SORTED_DIR}"

# ---------------------------------------------------------------------------
# Environment. We do NOT rely on `getenv = True`: this job is submitted from the
# EL9 lxplus host but the payload is an slc7_amd64_gcc700 / ROOT 6.14 binary
# running inside an EL7 container, so the submitter's environment is the WRONG
# one to inherit. Set up the release from cvmfs instead -- that makes the job
# reproducible regardless of how it was launched.
# ---------------------------------------------------------------------------
%(env_setup)s
echo "[job] which root-config: $(which root-config 2>/dev/null || echo NONE)"
echo "[job] SCRAM_ARCH=${SCRAM_ARCH:-unset}"

# Transferred into the scratch dir by condor (see transfer_input_files).
MATCH="./$(basename "%(match_bin)s")"
chmod +x "${MATCH}" 2>/dev/null || true
if [ ! -x "${MATCH}" ]; then
  echo "[job] FATAL: matcher not executable: ${MATCH}"
  echo "[job]        expected it to be transferred into $(pwd); ls follows:"
  ls -la
  exit 127
fi
if [ ! -r "${NANO_CHUNK}" ]; then
  echo "[job] FATAL: nano chunk not readable: ${NANO_CHUNK}"; exit 126
fi
echo "[job] nano files in chunk: $(wc -l < "${NANO_CHUNK}")"
if [ ! -r "${SORTED_DIR}/index.txt" ]; then
  echo "[job] FATAL: no index.txt under ${SORTED_DIR} (sample not sorted?)"
  exit 125
fi

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
# Emit the JSON into the job stdout too, so a lost file transfer still leaves
# the numbers recoverable from the condor .out file.
if [ -f "${JSON_OUT}" ]; then
  echo "[job] ---- BEGIN JSON ----"; cat "${JSON_OUT}"; echo "[job] ---- END JSON ----"
else
  echo "[job] WARNING: no JSON produced"
fi
echo "[job] done rc=${rc}"
exit ${rc}
"""

SUB = """universe                = vanilla
executable              = %(run_sh)s
arguments               = $(chunk) $(sorted) $(label) $(json) $(rootout)
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
# The matcher is TRANSFERRED, not read from AFS: a condor worker has no AFS
# token for this home directory, so reading bin/ over AFS would fail. Its
# ROOT libraries come from cvmfs via the cmsenv done inside the job.
transfer_input_files    = $(chunk), %(match_bin)s
transfer_output_files   = $(json), $(rootout)
transfer_output_remaps  = "$(json) = %(jsondir)s/$(json) ; $(rootout) = %(rootdir)s/$(rootout)"
output                  = %(logdir)s/$(label).$(ClusterId).$(ProcId).out
error                   = %(logdir)s/$(label).$(ClusterId).$(ProcId).err
log                     = %(logdir)s/$(label).$(ClusterId).log
request_memory          = %(memory)d
request_cpus            = 1
# getenv is deliberately False: submitted from EL9, executed in EL7 (see header).
getenv                  = False
%(image_line)s%(proxy_line)s+JobFlavour            = "%(flavour)s"
queue chunk, sorted, label, json, rootout from %(argsfile)s
"""


def write_condor(a, P, plan):
    """plan: list of (short, chunk_path, json_name, root_name)."""
    work = P["out_base"] / "condor"
    logdir = P["out_base"] / "logs"
    jsondir = P["out_base"] / "json"
    rootdir = P["out_base"] / "root"
    for d in (work, logdir, jsondir, rootdir):
        d.mkdir(parents=True, exist_ok=True)

    cmssw_base = (a.cmssw_base or os.environ.get("CMSSW_BASE")
                  or guess_cmssw_base())
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

    run_sh = work / "run_match.sh"
    run_sh.write_text(RUN_SH % {
        "match_bin": P["bin_dir"] / "matchTtbarIdSorted",
        "env_setup": env_setup,
    })
    run_sh.chmod(0o755)

    argsfile = work / "match.args"
    with open(argsfile, "w") as fh:
        for short, chunk, jname, rname in plan:
            fh.write("%s, %s, %s, %s, %s\n"
                     % (chunk, P["sorted_base"] / short, short, jname, rname))

    proxy = find_proxy(a.proxy) or ""
    image_line = ("" if a.no_container
                  else 'MY.SingularityImage = "%s"\n' % a.container)
    sub = work / "match.sub"
    sub.write_text(SUB % {
        "run_sh": run_sh, "logdir": logdir, "jsondir": jsondir,
        "match_bin": P["bin_dir"] / "matchTtbarIdSorted",
        "rootdir": rootdir, "memory": a.memory, "flavour": a.flavour,
        "image_line": image_line,
        "proxy_line": ("x509userproxy = %s\n" % proxy) if proxy else "",
        "argsfile": argsfile,
    })
    return sub, argsfile, logdir


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
    print("out base         : %s" % P["out_base"])
    print("samples          : %s" % ", ".join(shorts))
    print()

    if a.preflight:
        return run_preflight(a, P, shorts)

    if a.sort_only:
        return do_sort(a, P, shorts)

    # refuse to write results onto AFS -- this bit us twice (T-21/T-22)
    if str(P["out_base"]).startswith("/afs/"):
        sys.exit("FATAL: --out-base is on AFS (%s).\n"
                 "  AFS home is quota-limited and its token expires in ~25 h,\n"
                 "  which is shorter than this campaign. Use EOS."
                 % P["out_base"])

    plan = []
    for s in shorts:
        if not sorted_ready(P["sorted_base"], s):
            sys.exit("FATAL: %s is not sorted yet (%s/index.txt missing).\n"
                     "  Run:  python3 %s --era %s --sort-only%s"
                     % (s, P["sorted_base"] / s, Path(__file__).name, a.era,
                        "" if not a.samples else " --samples " + s))
        cs = chunks_for(P["nano_dir"], s)
        if not cs:
            sys.exit("FATAL: no nano chunks for %s under %s\n"
                     "  Run:  ./filelists/make_nano_filelists_das.sh %s"
                     % (s, P["nano_dir"], a.era))
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
        print("\nmonitor:   condor_q")
        print("logs:      %s" % logdir)
        print("aggregate: python3 %s --era %s%s"
              % (THIS_DIR / "aggregate_validation.py", a.era,
                 " --samples " + ",".join(shorts) if a.samples or a.smoke else ""))
    return rc


if __name__ == "__main__":
    sys.exit(main())
