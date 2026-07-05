#!/usr/bin/env python3
# =============================================================================
# submit_hist_condor.py
# =============================================================================
# Submit one HTCondor job per ROOT file to run `makeTtbarHist` over a set of
# processes, for either nano (slimmedNtuple / central NanoAOD) or extend
# inputs.  Histograms come back as one ROOT file per job; merge them per
# process afterwards with scripts/merge_hists.sh.
#
# This submitter is deliberately self-contained: it does NOT depend on the
# user's analysis-framework modules (ProxyChecker, ttHHmodules, /pnfs layout).
# It mirrors the *pattern* of the Tier3 unified submitter (one job per input
# file, per-job filelist) but stays generic so it can run anywhere with a
# vanilla `condor_submit`.
#
# Inputs come from a "filelist directory" laid out like make_filelists.py:
#     <filelist_dir>/filelist_<process>.txt     (one ROOT path per line)
#
# For each enabled process it writes, under <work_dir>/<process>/:
#     file_<process>_<N>.txt    per-job single-path filelist
#     run_<process>.sh          the executable each job runs
#     <process>.sub             the condor submit description (queue = N jobs)
# and (unless --dry-run) submits it.
#
# The job runs:
#     makeTtbarHist --filelist file_<process>_<N>.txt \
#                   --mode <nano|extend> \
#                   --out  hist_<prefix>_<process>_<N>.root \
#                   --tree <tree> --label <process>
#
# Usage:
#   python3 submit_hist_condor.py \
#       --filelist-dir filelistTier3 \
#       --mode nano \
#       --processes ttHH,tt4b,TTToSemiLeptonic,ttbb_SemiLeptonic \
#       --work-dir condor_hist_nano \
#       --out-prefix hist_nano \
#       [--tree Events] [--makettbarhist /abs/path/to/makeTtbarHist] \
#       [--proxy /path/to/x509_proxy] [--memory 2000] [--dry-run]
#
# After jobs finish:
#   scripts/merge_hists.sh <work_dir>/outputs merged hist_nano
#   scripts/merge_hists.sh <work_dir>/outputs merged hist_extend   # for the extend pass
#   plotTtbarCompare --extend merged/hist_extend_<P>.root \
#                    --nano    merged/hist_nano_<P>.root \
#                    --out     <P>_ttbarId_compare.png
# =============================================================================

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(
        description="Submit HTCondor jobs running makeTtbarHist per input file.")
    p.add_argument("--filelist-dir", required=True,
                   help="Directory holding filelist_<process>.txt files "
                        "(as produced by make_filelists.py).")
    p.add_argument("--mode", required=True, choices=["nano", "extend", "sidecar"],
                   help="Passed to makeTtbarHist --mode (extend; sidecar accepted for back-compat).")
    p.add_argument("--processes", required=True,
                   help="Comma-separated process names; each maps to "
                        "filelist_<process>.txt in --filelist-dir.")
    p.add_argument("--work-dir", default="condor_hist",
                   help="Where to write per-job scripts/filelists/submit files.")
    p.add_argument("--out-prefix", default=None,
                   help="Output histogram filename prefix "
                        "(default: hist_<mode>).")
    p.add_argument("--tree", default="Events",
                   help="Tree name passed to makeTtbarHist (default Events).")
    p.add_argument("--makettbarhist", default=None,
                   help="Path to the makeTtbarHist executable "
                        "(default: <project_root>/bin/makeTtbarHist, i.e. the "
                        "binary produced by `make`).")
    p.add_argument("--proxy", default=None,
                   help="X509 proxy file to ship with the job "
                        "(default: $X509_USER_PROXY if set).")
    p.add_argument("--memory", type=int, default=2000,
                   help="request_memory in MB (default 2000).")
    p.add_argument("--max-files", type=int, default=None,
                   help="Cap number of input files per process (smoke test).")
    p.add_argument("--dry-run", action="store_true",
                   help="Write all job files but do not condor_submit.")
    return p.parse_args()


def read_filelist(path):
    files = []
    with open(path) as fh:
        for line in fh:
            s = line.strip()
            if s and not s.startswith("#"):
                files.append(s)
    return files


def write_run_script(script_path, *, makettbarhist, mode, tree):
    """The per-job executable.  Condor passes two args: the per-job filelist
    and the output ROOT file path."""
    content = f"""#!/usr/bin/env bash
set -euo pipefail
FILELIST="$1"
OUTFILE="$2"
LABEL="$3"

echo "[job] host=$(hostname)  pwd=$(pwd)"
echo "[job] filelist=${{FILELIST}}  out=${{OUTFILE}}  label=${{LABEL}}"

# The ROOT environment is expected to be already set up the same way the
# submitter's environment was (the .sub file uses getenv=True to ship it to
# the worker).  If your site needs an explicit source line (e.g. a CVMFS ROOT
# or an LCG view), add it here or rely on getenv.  We just invoke the binary.
MAKEHIST="{makettbarhist}"

"${{MAKEHIST}}" \\
    --filelist "${{FILELIST}}" \\
    --mode {mode} \\
    --out "${{OUTFILE}}" \\
    --tree {tree} \\
    --label "${{LABEL}}"

echo "[job] done"
"""
    with open(script_path, "w") as f:
        f.write(content)
    os.chmod(script_path, 0o755)


def write_submit_file(sub_path, *, run_script, arg_lines, log_dir,
                      memory, proxy, getenv=True):
    """One submit file with a multi-line queue (one job per arg line)."""
    proxy_line = f"x509userproxy = {proxy}\n" if proxy else ""
    # Build the queue block: each job gets filelist, outfile, label.
    # We use 'queue ... from' with a here-file of arguments.
    args_file = sub_path.with_suffix(".args")
    with open(args_file, "w") as af:
        for (flist, outfile, label) in arg_lines:
            af.write(f"{flist}, {outfile}, {label}\n")

    content = f"""universe                = vanilla
executable              = {run_script}
arguments               = $(flist) $(outfile) $(label)
should_transfer_files   = YES
when_to_transfer_output = ON_EXIT
transfer_input_files    = $(flist)
transfer_output_files   = $(outfile)
output                  = {log_dir}/$(ClusterId).$(ProcId).out
error                   = {log_dir}/$(ClusterId).$(ProcId).err
log                     = {log_dir}/$(ClusterId).log
request_memory          = {memory}
getenv                  = {"True" if getenv else "False"}
{proxy_line}+JobFlavour            = "longlunch"
queue flist, outfile, label from {args_file}
"""
    with open(sub_path, "w") as f:
        f.write(content)
    return args_file


def main():
    args = parse_args()
    out_prefix = args.out_prefix or f"hist_{args.mode}"
    proxy = args.proxy or os.environ.get("X509_USER_PROXY")

    filelist_dir = Path(args.filelist_dir)
    if not filelist_dir.is_dir():
        sys.exit(f"ERROR: --filelist-dir not found: {filelist_dir}")

    # Resolve the makeTtbarHist binary.  Default is <project_root>/bin/makeTtbarHist,
    # where project_root is the parent of this script's directory (scripts/).
    project_root = Path(__file__).resolve().parent.parent
    if args.makettbarhist:
        makehist = str(Path(args.makettbarhist).resolve())
    else:
        makehist = str((project_root / "bin" / "makeTtbarHist").resolve())
    if not Path(makehist).is_file():
        print(f"WARNING: makeTtbarHist not found at '{makehist}'.\n"
              f"         Build it with `make` (produces ./bin/makeTtbarHist), "
              f"or pass --makettbarhist with an absolute path.\n"
              f"         (Generating job files anyway; jobs will fail if the "
              f"binary is missing at run time.)")

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    out_dir = work / "outputs"
    out_dir.mkdir(exist_ok=True)
    log_dir = work / "logs"
    log_dir.mkdir(exist_ok=True)

    processes = [p.strip() for p in args.processes.split(",") if p.strip()]
    n_submitted = 0

    for proc in processes:
        flist_path = filelist_dir / f"filelist_{proc}.txt"
        if not flist_path.is_file():
            print(f"[skip] {proc}: {flist_path} not found")
            continue

        files = read_filelist(flist_path)
        if args.max_files is not None:
            files = files[: args.max_files]
        if not files:
            print(f"[skip] {proc}: filelist empty")
            continue

        proc_dir = work / proc
        proc_dir.mkdir(exist_ok=True)

        # per-job single-path filelists + argument lines
        arg_lines = []
        for i, fpath in enumerate(files):
            per_job = proc_dir / f"file_{proc}_{i}.txt"
            with open(per_job, "w") as pj:
                pj.write(fpath + "\n")
            outfile = f"{out_prefix}_{proc}_{i}.root"
            arg_lines.append((str(per_job.resolve()),
                              str((out_dir / outfile).resolve()),
                              proc))

        run_script = proc_dir / f"run_{proc}.sh"
        write_run_script(run_script, makettbarhist=makehist,
                         mode=args.mode, tree=args.tree)

        sub_path = proc_dir / f"{proc}.sub"
        write_submit_file(sub_path, run_script=str(run_script.resolve()),
                          arg_lines=arg_lines, log_dir=str(log_dir.resolve()),
                          memory=args.memory, proxy=proxy)

        print(f"[{proc}] {len(files)} job(s)  ->  {sub_path}")

        if args.dry_run:
            print(f"  [dry-run] condor_submit {sub_path}")
            continue

        if shutil.which("condor_submit") is None:
            print("  [skip submit] condor_submit not on PATH (dry-run only here)")
            continue
        try:
            subprocess.run(["condor_submit", str(sub_path)], check=True)
            n_submitted += 1
        except subprocess.CalledProcessError as exc:
            print(f"  [FAILED] condor_submit: {exc}")

    print("=" * 65)
    print(f"  processes : {len(processes)}")
    print(f"  submitted : {n_submitted}{' (DRY RUN)' if args.dry_run else ''}")
    print(f"  outputs will land in : {out_dir}")
    print(f"  then: scripts/merge_hists.sh {out_dir} merged {out_prefix}")


if __name__ == "__main__":
    main()
