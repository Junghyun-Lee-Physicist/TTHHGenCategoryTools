#!/usr/bin/env python3
# =============================================================================
# preflight checks before CRAB submission
# =============================================================================
# Catches the obvious things that break submissions before they cost you
# grid time.  Run this once before each batch.
# =============================================================================

import os
import shutil
import subprocess
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("ERROR: PyYAML not installed.  pip install --user pyyaml")
    with open(path) as fh:
        return yaml.safe_load(fh)


def ok(s):   print(f"  [OK]   {s}")
def fail(s): print(f"  [FAIL] {s}")
def warn(s): print(f"  [WARN] {s}")


def check_cmssw():
    print("\n[1] CMSSW environment")
    base = os.environ.get("CMSSW_BASE")
    ver  = os.environ.get("CMSSW_VERSION", "")
    if not base:
        fail("CMSSW_BASE not set; run cmsenv inside CMSSW_*/src.")
        return False
    ok(f"CMSSW_BASE = {base}")
    ok(f"CMSSW_VERSION = {ver or '(unknown)'}")
    if not ver.startswith("CMSSW_10_6_"):
        warn(f"CMSSW_10_6_X required: for UL Run2 byte-identity; got {ver}.  "
             "Gen-level branches will still agree, but reco-level (Jet_pt, "
             "MET, b-tagger) won't.")
    return True


def check_built():
    print("\n[2] Plugin library + python module")
    base = os.environ.get("CMSSW_BASE", "")
    arch = os.environ.get("SCRAM_ARCH", "")
    if not base or not arch:
        fail("CMSSW_BASE/SCRAM_ARCH missing.")
        return False
    libs = list((Path(base) / "lib" / arch).glob(
        "pluginTTHHGenCategoryToolsTtbarIdExtender*.so"))
    if not libs:
        fail(f"plugin .so missing under {base}/lib/{arch}.  "
             f"cd {base}/src && scram b -j 8")
        return False
    ok(f"plugin library: {libs[0].name}")
    pkg_init = Path(base) / "python" / "TTHHGenCategoryTools" / "TtbarIdExtender" / "__init__.py"
    if not pkg_init.exists():
        fail("python module not registered.  Re-run scram b.")
        return False
    ok("python module TTHHGenCategoryTools.TtbarIdExtender registered")
    return True


def check_proxy():
    print("\n[3] VOMS proxy")
    if shutil.which("voms-proxy-info") is None:
        fail("voms-proxy-info not in PATH; cmsenv?")
        return False
    try:
        out = subprocess.check_output(["voms-proxy-info", "-all"],
                                       stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError:
        fail("No active proxy.  voms-proxy-init -voms cms -valid 192:00")
        return False
    if "timeleft  : 00:00:00" in out:
        fail("Proxy expired.  voms-proxy-init -voms cms -valid 192:00")
        return False
    ok("proxy is valid")
    if "/cms" not in out:
        warn("proxy doesn't appear to carry the /cms VOMS attribute.")
    return True


def check_yaml_placeholder():
    print("\n[4] site_config.yaml customised")
    p = THIS_DIR / "site_config.yaml"
    if not p.exists():
        fail(f"missing {p}")
        return False
    cfg = load_yaml(p)
    if "__YOUR_CERN_USERNAME__" in (cfg.get("out_lfn_base") or ""):
        fail("out_lfn_base still has placeholder username.  Edit it.")
        return False
    ok(f"out_lfn_base = {cfg['out_lfn_base']}")
    ok(f"storage_site = {cfg['storage_site']}")
    return True


def check_pset():
    print("\n[5] cfg files parse")
    base = os.environ.get("CMSSW_BASE", "")
    rels = [
        "TTHHGenCategoryTools/TtbarIdExtender/test/run_ttbarIdExtend_cfg.py",          # extend (primary)
    ]
    all_ok = True
    for rel in rels:
        pset = Path(base) / "src" / rel
        if not pset.exists():
            fail(f"cfg missing at {pset}")
            all_ok = False
            continue
        try:
            compile(pset.read_text(), str(pset), "exec")
        except SyntaxError as exc:
            fail(f"cfg has SyntaxError: {exc}")
            all_ok = False
            continue
        ok(f"cfg compiles: {rel}")
    return all_ok


def main():
    print("=" * 65)
    print(" pre-flight check (extend)")
    print("=" * 65)

    results = [
        check_cmssw(),
        check_built(),
        check_proxy(),
        check_yaml_placeholder(),
        check_pset(),
    ]
    n_fail = sum(1 for r in results if not r)
    print("\n" + "=" * 65)
    if n_fail:
        print(f"  {n_fail} check(s) failed -- fix above before submitting.")
        sys.exit(1)
    print("  All checks passed.  Safe to submit.")


if __name__ == "__main__":
    main()
