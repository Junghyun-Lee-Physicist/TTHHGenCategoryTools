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
                   help="x509 proxy path; default $X509_USER_PROXY.")
    return p.parse_args()


# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
def resolve_paths(a):
    era = a.era
    d = {}
    d["extend_dir"] = Path(a.extend_filelist_dir or
                           VAL_ROOT / "filelists" / ("sidecar%s" % era))
    d["nano_dir"] = Path(a.nano_filelist_dir or
                         VAL_ROOT / "filelists" / ("nano%s" % era))
    d["sorted_base"] = Path(a.sorted_base or ("%s/sorted%s" % (DEFAULT_EOS, era)))
    d["out_base"] = Path(a.out_base or ("%s/valout%s" % (DEFAULT_EOS, era)))
    d["bin_dir"] = Path(a.bin_dir or (VAL_ROOT / "bin"))
    return d


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
    add("PASS" if shutil_which("condor_submit") else "FAIL", "condor_submit",
        shutil_which("condor_submit") or "not on PATH")
    proxy = a.proxy or os.environ.get("X509_USER_PROXY") or ""
    if proxy and Path(proxy).is_file():
        add("PASS", "x509 proxy", proxy)
    else:
        # jobs read central NanoAOD over XRootD; without a proxy every job fails
        add("FAIL", "x509 proxy",
            "not found -- voms-proxy-init -voms cms -rfc --valid 168:00")

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

    add("PASS", "total condor jobs", str(total_jobs))
    n_fail = sum(1 for l, _, _ in rows if l == "FAIL")
    n_warn = sum(1 for l, _, _ in rows if l == "WARN")
    print("-" * 88)
    print("PREFLIGHT: %d PASS, %d WARN, %d FAIL"
          % (sum(1 for l, _, _ in rows if l == "PASS"), n_warn, n_fail))
    print("RESULT: %s" % ("NOT READY -- fix the FAIL items" if n_fail
                          else "READY" + (" (review WARNs)" if n_warn else "")))
    return 1 if n_fail else 0


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
echo "[job] date=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[job] chunk=${NANO_CHUNK}  label=${LABEL}"
echo "[job] sorted=${SORTED_DIR}"
echo "[job] nano files in chunk: $(wc -l < "${NANO_CHUNK}")"

MATCH="%(match_bin)s"
test -x "${MATCH}" || { echo "[job] FATAL: matcher not executable: ${MATCH}"; exit 127; }

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
# Emit the JSON into the job stdout too, so a lost transfer still leaves the
# numbers recoverable from the condor .out file.
if [ -f "${JSON_OUT}" ]; then
  echo "[job] ---- BEGIN JSON ----"; cat "${JSON_OUT}"; echo "[job] ---- END JSON ----"
fi
echo "[job] done rc=${rc}"
exit ${rc}
"""

SUB = """universe                = vanilla
executable              = %(run_sh)s
arguments               = $(chunk) $(sorted) $(label) $(json) $(rootout)
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_input_files    = $(chunk)
transfer_output_files   = $(json), $(rootout)
transfer_output_remaps  = "$(json) = %(jsondir)s/$(json) ; $(rootout) = %(rootdir)s/$(rootout)"
output                  = %(logdir)s/$(label).$(ClusterId).$(ProcId).out
error                   = %(logdir)s/$(label).$(ClusterId).$(ProcId).err
log                     = %(logdir)s/$(label).$(ClusterId).log
request_memory          = %(memory)d
request_cpus            = 1
getenv                  = True
%(proxy_line)s+JobFlavour            = "%(flavour)s"
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

    run_sh = work / "run_match.sh"
    run_sh.write_text(RUN_SH % {"match_bin": P["bin_dir"] / "matchTtbarIdSorted"})
    run_sh.chmod(0o755)

    argsfile = work / "match.args"
    with open(argsfile, "w") as fh:
        for short, chunk, jname, rname in plan:
            fh.write("%s, %s, %s, %s, %s\n"
                     % (chunk, P["sorted_base"] / short, short, jname, rname))

    proxy = a.proxy or os.environ.get("X509_USER_PROXY") or ""
    sub = work / "match.sub"
    sub.write_text(SUB % {
        "run_sh": run_sh, "logdir": logdir, "jsondir": jsondir,
        "rootdir": rootdir, "memory": a.memory, "flavour": a.flavour,
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
