#!/usr/bin/env python3
"""
das_lineage.py - Map CMS MiniAOD <-> NanoAOD file-level lineage via DAS.

For central production, DAS records authoritative file-level parent/child
provenance, so a single `dasgoclient` query per file resolves the mapping
exactly. No run/lumi/event comparison is needed.

  NanoAOD file -> MiniAOD parent :  dasgoclient -query="parent file=<lfn>"
  MiniAOD file -> NanoAOD child  :  dasgoclient -query="child  file=<lfn>"

Private productions not registered in DAS return empty lineage; those files
are reported separately as warnings rather than silently dropped.

Requires: a valid grid proxy (voms-proxy-init) and `dasgoclient` on PATH
(both available inside a CMSSW environment).

Compatible with Python 3.6+ (CMSSW-friendly).
"""

import argparse
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple

# --------------------------------------------------------------------------- #
#  Terminal styling (graceful no-color fallback when not a TTY)
# --------------------------------------------------------------------------- #


class _Style(object):
    """ANSI styling that auto-disables when stdout is not a terminal."""

    def __init__(self, enabled):
        # type: (bool) -> None
        self._on = enabled

    def _wrap(self, code, text):
        # type: (str, str) -> str
        return "\033[{}m{}\033[0m".format(code, text) if self._on else text

    def bold(self, t):    return self._wrap("1", t)
    def dim(self, t):     return self._wrap("2", t)
    def red(self, t):     return self._wrap("31", t)
    def green(self, t):   return self._wrap("32", t)
    def yellow(self, t):  return self._wrap("33", t)
    def blue(self, t):    return self._wrap("34", t)
    def cyan(self, t):    return self._wrap("36", t)


STYLE = _Style(sys.stdout.isatty())

# --------------------------------------------------------------------------- #
#  Domain types
# --------------------------------------------------------------------------- #


class Direction(Enum):
    """Lineage traversal direction relative to the input tier."""

    TO_PARENT = "parent"   # NanoAOD input -> MiniAOD
    TO_CHILD = "child"     # MiniAOD input -> NanoAOD

    @property
    def das_keyword(self):
        # type: () -> str
        return self.value

    @property
    def label(self):
        # type: () -> str
        return "MiniAOD parent" if self is Direction.TO_PARENT else "NanoAOD child"


class Lineage(NamedTuple):
    """Resolved lineage for a single input file."""

    source: str
    related: Tuple[str, ...]
    error: Optional[str] = None

    @property
    def ok(self):
        # type: () -> bool
        return self.error is None and bool(self.related)

    @property
    def is_orphan(self):
        # type: () -> bool
        return self.error is None and not self.related


class DasError(RuntimeError):
    """Raised when a dasgoclient invocation fails."""
    pass


# --------------------------------------------------------------------------- #
#  DAS client (thin wrapper over dasgoclient)
# --------------------------------------------------------------------------- #


class DasClient(object):
    """Minimal, side-effect-isolated wrapper around `dasgoclient`."""

    def __init__(self, binary="dasgoclient", timeout=120.0):
        # type: (str, float) -> None
        self._bin = binary
        self._timeout = timeout

    def _query(self, expr):
        # type: (str) -> List[str]
        try:
            proc = subprocess.run(
                [self._bin, "-query", expr],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,   # 3.6: text-mode (== text=True in 3.7+)
                timeout=self._timeout,
            )
        except FileNotFoundError as exc:
            raise DasError("`{}` not found on PATH (CMSSW env loaded?)".format(self._bin)) from exc
        except subprocess.TimeoutExpired as exc:
            raise DasError("query timed out after {:.0f}s: {}".format(self._timeout, expr)) from exc

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip() or "unknown dasgoclient error"
            raise DasError(stderr.splitlines()[-1])

        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    def dataset_of(self, lfn):
        # type: (str) -> Optional[str]
        """Resolve the parent dataset of a file LFN (for tier detection)."""
        results = self._query("dataset file={}".format(lfn))
        return results[0] if results else None

    def files_in(self, dataset):
        # type: (str) -> List[str]
        return self._query("file dataset={}".format(dataset))

    def related(self, lfn, direction):
        # type: (str, Direction) -> List[str]
        return self._query("{} file={}".format(direction.das_keyword, lfn))


# --------------------------------------------------------------------------- #
#  Tier / direction logic
# --------------------------------------------------------------------------- #


def _tier_of_dataset(dataset):
    # type: (str) -> str
    # /PrimaryDataset/ProcessingVersion/DATATIER
    parts = dataset.strip("/").split("/")
    return parts[-1].upper() if len(parts) == 3 else ""


def infer_direction(tier):
    # type: (str) -> Optional[Direction]
    if tier.startswith("MINIAOD"):
        return Direction.TO_CHILD
    if tier.startswith("NANOAOD"):
        return Direction.TO_PARENT
    return None


def is_dataset(token):
    # type: (str) -> bool
    return token.startswith("/") and token.count("/") == 3 and not token.endswith(".root")


# --------------------------------------------------------------------------- #
#  Input expansion
# --------------------------------------------------------------------------- #


def resolve_inputs(tokens, das, forced):
    # type: (Sequence[str], DasClient, Optional[Direction]) -> Tuple[List[str], Direction]
    """Expand dataset/file tokens into a flat file list and settle direction.

    Direction is determined once from the first input's tier (all inputs are
    assumed to be the same tier within a single invocation) unless overridden.
    """
    files = []  # type: List[str]
    direction = forced

    for token in tokens:
        if is_dataset(token):
            if direction is None:
                direction = _direction_or_die(_tier_of_dataset(token), token)
            files.extend(das.files_in(token))
        else:  # treat as file LFN
            if direction is None:
                dataset = das.dataset_of(token)
                if dataset is None:
                    _die("cannot resolve dataset (tier) for file: {}\n"
                         "  -> private file? pass --direction {{parent|child}} "
                         "explicitly.".format(token))
                direction = _direction_or_die(_tier_of_dataset(dataset), dataset)
            files.append(token)

    if not files:
        _die("no input files resolved.")
    assert direction is not None
    # de-duplicate, preserve order
    return list(dict.fromkeys(files)), direction


def _direction_or_die(tier, ctx):
    # type: (str, str) -> Direction
    d = infer_direction(tier)
    if d is None:
        _die("unsupported data tier '{}' for: {}\n"
             "  -> expected MINIAOD* or NANOAOD*; use --direction to "
             "override.".format(tier or "?", ctx))
    return d  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
#  Lineage resolution (parallel; DAS calls are I/O bound)
# --------------------------------------------------------------------------- #


def resolve_lineage(files, das, direction, workers):
    # type: (Sequence[str], DasClient, Direction, int) -> List[Lineage]
    def task(lfn):
        # type: (str) -> Lineage
        try:
            related = das.related(lfn, direction)
            return Lineage(source=lfn, related=tuple(related))
        except DasError as exc:
            return Lineage(source=lfn, related=tuple(), error=str(exc))

    results = []  # type: List[Lineage]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(task, f): f for f in files}
        for fut in as_completed(futures):
            results.append(fut.result())

    # stable ordering by source for reproducible output
    results.sort(key=lambda lin: lin.source)
    return results


# --------------------------------------------------------------------------- #
#  Pretty printing
# --------------------------------------------------------------------------- #


def _short(lfn):
    # type: (str) -> str
    """Drop the /store prefix noise, keep the informative tail."""
    return ".../" + "/".join(lfn.strip("/").split("/")[-2:])


def render(results, direction):
    # type: (Sequence[Lineage], Direction) -> None
    s = STYLE
    matched = [r for r in results if r.ok]
    orphans = [r for r in results if r.is_orphan]
    errored = [r for r in results if r.error is not None]

    rule = "\u2500" * 78
    print()
    print(s.bold(s.cyan("  CMS MiniAOD <-> NanoAOD lineage (DAS file-level provenance)")))
    print(s.dim("  direction: each input file -> its {}(s)".format(s.bold(direction.label))))
    print(s.dim("  " + rule))

    if matched:
        for lin in matched:
            arrow = s.green("->")
            print("\n  {}".format(s.bold(_short(lin.source))))
            print(s.dim("    {}".format(lin.source)))
            for rel in lin.related:
                print("      {} {}".format(arrow, s.blue(_short(rel))))
                print(s.dim("          {}".format(rel)))

    if orphans:
        print()
        print(s.yellow(s.bold("  [!] no DAS lineage found ({}) "
                              "- likely private production:".format(len(orphans)))))
        for lin in orphans:
            print(s.yellow("      - {}".format(_short(lin.source))))

    if errored:
        print()
        print(s.red(s.bold("  [x] query errors ({}):".format(len(errored)))))
        for lin in errored:
            print(s.red("      - {}".format(_short(lin.source))))
            print(s.dim("          {}".format(lin.error)))

    n_rel = sum(len(r.related) for r in matched)
    print()
    print(s.dim("  " + rule))
    summary = ("  {} matched ({} related files)   "
               "{} orphan   {} error   / {} input(s)".format(
                   s.green(str(len(matched))), n_rel,
                   s.yellow(str(len(orphans))), s.red(str(len(errored))),
                   len(results)))
    print(s.bold(summary))
    print()


# --------------------------------------------------------------------------- #
#  Proxy check + CLI
# --------------------------------------------------------------------------- #


def check_proxy():
    # type: () -> None
    if shutil.which("voms-proxy-info") is None:
        print(STYLE.yellow("  [!] voms-proxy-info not found; skipping proxy check."),
              file=sys.stderr)
        return
    try:
        out = subprocess.run(
            ["voms-proxy-info", "--timeleft"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=15,
        )
        left = int((out.stdout or "").strip() or "0")
    except (ValueError, OSError, subprocess.SubprocessError):
        left = 0
    if left <= 0:
        _die("no valid grid proxy. Run: voms-proxy-init --voms cms")
    if left < 1800:
        print(STYLE.yellow("  [!] proxy expires in {} min; "
                           "consider renewing.".format(left // 60)), file=sys.stderr)


def _die(msg):
    # type: (str) -> None
    print(STYLE.red("error: {}".format(msg)), file=sys.stderr)
    raise SystemExit(2)


def parse_args(argv=None):
    # type: (Optional[Iterable[str]]) -> argparse.Namespace
    p = argparse.ArgumentParser(
        prog="das_lineage",
        description="Resolve MiniAOD<->NanoAOD file-level lineage via DAS.",
    )
    p.add_argument("inputs", nargs="+",
                   help="file LFN(s) and/or dataset path(s) (same tier per run)")
    p.add_argument("--direction", choices=[d.value for d in Direction], default=None,
                   help="force lineage direction (use for private files)")
    p.add_argument("-j", "--workers", type=int, default=8,
                   help="parallel DAS queries (default: 8)")
    p.add_argument("--no-proxy-check", action="store_true",
                   help="skip grid proxy validity check")
    p.add_argument("--dasgoclient", default="dasgoclient",
                   help="path to dasgoclient binary")
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv=None):
    # type: (Optional[Iterable[str]]) -> int
    args = parse_args(argv)
    if not args.no_proxy_check:
        check_proxy()

    das = DasClient(binary=args.dasgoclient)
    forced = Direction(args.direction) if args.direction else None

    files, direction = resolve_inputs(args.inputs, das, forced)
    results = resolve_lineage(files, das, direction, max(1, args.workers))
    render(results, direction)

    # non-zero exit if anything errored, so it composes in shell pipelines
    return 1 if any(r.error for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
