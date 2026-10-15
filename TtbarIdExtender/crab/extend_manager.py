#!/usr/bin/env python3
# =============================================================================
# extend_manager.py -- watch an extend CRAB campaign to the end, then check it
# =============================================================================
# Plain deterministic code (no AI), the CRAB counterpart of the KNU
# manager.py of TTHHAnalyzer (tools/runlog). Started after
# crab/launch_extend.sh --submit; normally runs as a condor job
# (crab/manager_condor.sh), or once by hand with --once.
#
# One CHECK (every --interval-min minutes, default 30):
#   * crab status of every selected task (era x sample of datasets.yaml)
#   * a task whose submission died (SUBMITREFUSED, SUBMITFAILED, FAILED with
#     no jobs) or that was KILLED              -> ALERT
#   * failed jobs                              -> crab resubmit, at most
#     --max-resubmit times per task (default 3); after that, once the task has
#     nothing left running                     -> ALERT
#   * no job finished anywhere for --stall-hours (default 8)  -> ALERT
#   * grid proxy with < 2 h left                -> ALERT
# An ALERT stops the manager (RESULT STOPPED, exit 3). The state is kept in
# crab/manager/<name>/state.json; after fixing the cause, run the same command
# with --clear-alerts. A restart of the same command continues from the state.
#
# With --launch, the manager first runs crab/launch_extend.sh --era <E> --submit
# for every era none of whose tasks has a CRAB project dir (local cmsRun +
# invariants, resolve + --apply, preflight, dry-run, submit, report), with stdin
# closed (a grid pass-phrase prompt from CRAB then fails instead of hanging).
# Its output goes into manager.log; a non-zero exit is an ALERT. An era whose
# tasks all have project dirs is only watched. An era with only some dirs, or
# with a failed-submit shell (a dir without .requestcache), is an ALERT.
#
# When every job of every task has finished, the COMPLETION CHECKS run once:
#   1. exactly one CRAB timestamp directory per task on the storage
#      (two -> duplicate rows -> matchTtbarId exit 7, README sec.2.2c)
#   2. output files == jobs, job ids exactly 1..N
#   3. rows == DAS MiniAOD nevents of the task's dataset
#   4. Validation/scripts/check_extend_sample.C over every file of the task:
#      readable, ALL INVARIANTS PASS; tt+nb counts (61/62/71/72) are reported
# -> crab/manager/<name>/REPORT.txt, RESULT DONE (exit 0) or RESULT CHECK FAILED
#    (exit 4). The comparison with central NanoAODv9 and the patch extraction
#    are the next segment (Validation/), not done here.
#
# Usage (TtbarIdExtender/, after cmsenv + crab-setup + proxy):
#   python3 crab/extend_manager.py --era 2016APV,2016 --name extend2016 --once
#   python3 crab/extend_manager.py --era 2016APV,2016 --name extend2016
#   bash crab/manager_condor.sh --era 2016APV,2016 --name extend2016 --launch   (lxplus host)
# Exit: 0 DONE; 2 setup error / another manager holds the lock; 3 STOPPED
#       (ALERT); 4 CHECK FAILED; 75 time budget used up -- run again to go on
#       (the condor job is re-queued on 75); 130/143 SIGINT/SIGTERM.
#
# Log: crab/manager/<name>/manager.log, one line per event, each line appended
# with open + fsync + close (on AFS other hosts see a file's data only after
# the writer closes it, T-39); the job's stdout has the same lines:
#   [manager] <UTC> check <n> | jobs done <d>/<t> (<p>%) run .. idle .. ... | ETA ..
#   a START line at every start and an END line at every exit -- a log whose
#   last line is neither END nor a check younger than 2 x interval means the
#   manager died.
#
# PYTHON 3.6 ONLY (CMSSW_10_6_32_patch1): no text=/capture_output= in
# subprocess, always pass encoding=, ASCII-only file. Same rules as
# submit_ttbarIdExtend.py, whose helpers this file imports.
# =============================================================================

import argparse
import contextlib
import datetime
import io
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time

THIS_DIR = os.path.dirname(os.path.abspath(__file__))       # .../TtbarIdExtender/crab
PKG_ROOT = os.path.dirname(THIS_DIR)                         # .../TtbarIdExtender
REPO_ROOT = os.path.dirname(PKG_ROOT)                        # .../TTHHGenCategoryTools
MACRO = os.path.join(REPO_ROOT, "Validation", "scripts", "check_extend_sample.C")
sys.path.insert(0, THIS_DIR)
import submit_ttbarIdExtend as S  # noqa: E402  (shared YAML loading, build_config, resubmit classifier)

EXIT_DONE, EXIT_SETUP, EXIT_STOPPED, EXIT_CHECKFAIL, EXIT_CONTINUE = 0, 2, 3, 4, 75
ACTIVE_STATES = ("running", "idle", "transferring", "unsubmitted", "cooloff", "toRetry",
                 "resubmitting", "held", "on hold")
DEAD_SUBMIT_STATES = ("SUBMITREFUSED", "SUBMITFAILED")
KILLED_STATES = ("KILLED", "KILLFAILED")
CRAB_TS_RE = re.compile(r"^\d{6}_\d{6}$")
OUT_FILE_RE = re.compile(r"^ttbarIDExtend_(\d+)\.root$")


def utc():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


class Log(object):
    # Every line is appended with open + write + fsync + close. AFS stores what a
    # host wrote to a file on the file server when that host closes (or fsyncs)
    # the file, so other hosts see it only then (write-on-close): with the log
    # kept open for the whole run, lxplus would see the manager's lines only when
    # the manager exits (up to 22 h). The [job] lines of job.sh come from tee -a,
    # which closes after every line. 2026-10-15, T-39.
    def __init__(self, path):
        self.path = path
        io.open(path, "a", encoding="utf-8").close()   # fail here if not writable

    def _append(self, text):
        print(text)
        sys.stdout.flush()
        with io.open(self.path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def __call__(self, msg):
        self._append("[manager] %s %s" % (utc(), msg))

    def raw(self, text):
        self._append(text)


class Alarm(Exception):
    pass


def _alarm(signum, frame):
    raise Alarm("timed out")


class Stop(BaseException):
    # BaseException on purpose: the "except Exception" around CRAB calls must not swallow it
    def __init__(self, signame, code):
        BaseException.__init__(self, signame)
        self.signame, self.code = signame, code


def _stop_handler(signum, frame):
    name = {signal.SIGTERM: "SIGTERM", signal.SIGINT: "SIGINT"}.get(signum, str(signum))
    raise Stop(name, 128 + signum)


# ----------------------------------------------------------------------------
# state, lock
# ----------------------------------------------------------------------------
def save_json(path, obj):
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, indent=1, sort_keys=True))
    os.replace(tmp, path)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ----------------------------------------------------------------------------
# CRAB calls (in-process, output captured, with a timeout)
# ----------------------------------------------------------------------------
def crab_call(action, proj, timeout_s):
    """Return (result dict or None, captured text, exception or None)."""
    from CRABAPI.RawCommand import crabCommand
    buf = io.StringIO()
    res, exc = None, None
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(int(timeout_s))
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            res = crabCommand(action, dir=proj)
    except Alarm as e:
        exc = e
    except (Exception, SystemExit) as e:  # noqa: BLE001 -- CRAB raises many types (and may sys.exit)
        exc = e
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
    return res, buf.getvalue(), exc


def failed_job_summary(res, limit=8):
    """Best effort: 'job 12 exit 8028, job 40 exit 50660' from res['jobs']."""
    out = []
    jobs = (res or {}).get("jobs") or {}
    try:
        for jid in sorted(jobs, key=lambda x: int(x) if str(x).isdigit() else 0):
            info = jobs[jid] or {}
            if str(info.get("State", "")).lower() != "failed":
                continue
            err = info.get("Error")
            code = err[0] if isinstance(err, (list, tuple)) and err else err
            out.append("job %s exit %s" % (jid, code if code is not None else "?"))
            if len(out) >= limit:
                out.append("...")
                break
    except Exception:  # noqa: BLE001
        return ""
    return ", ".join(out)


# ----------------------------------------------------------------------------
# DAS / storage helpers
# ----------------------------------------------------------------------------
def das_nevents(dataset, timeout_s=300):
    try:
        p = subprocess.run(["dasgoclient", "-query", "summary dataset=%s" % dataset, "-json"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=timeout_s)
        for rec in json.loads(p.stdout or "[]"):
            for smry in (rec.get("summary") or []):
                if smry.get("nevents") is not None:
                    return int(smry["nevents"])
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
        return None
    return None


def lfn_to_eos(lfn_base, storage_site):
    """T3_CH_CERNBOX: /store/user/<u>/X -> /eos/user/<u0>/<u>/X (site_config.yaml)."""
    if storage_site != "T3_CH_CERNBOX":
        return None
    m = re.match(r"^/store/user/([^/]+)(/.*)?$", lfn_base or "")
    if not m:
        return None
    user = m.group(1)
    return "/eos/user/%s/%s%s" % (user[0], user, m.group(2) or "")


class Storage(object):
    """List and name files under the output base: EOS FUSE if mounted, else xrootd."""

    def __init__(self, base, xrd_door, log):
        self.base, self.door, self.log = base, xrd_door, log
        self.mode = None
        if os.path.isdir(base):
            self.mode = "fuse"
        elif xrd_door:
            try:
                p = subprocess.run(["xrdfs", xrd_door, "stat", base], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
                if p.returncode == 0:
                    self.mode = "xrootd"
            except (OSError, subprocess.TimeoutExpired):
                pass

    def listdir(self, path):
        if self.mode == "fuse":
            return os.listdir(path)
        p = subprocess.run(["xrdfs", self.door, "ls", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=600)
        if p.returncode != 0:
            raise OSError("xrdfs ls %s: %s" % (path, (p.stderr or "").strip()[:200]))
        return [ln.rstrip("/").split("/")[-1] for ln in p.stdout.split() if ln.strip()]

    def walk_files(self, top):
        """(name, path) of every file below top."""
        if self.mode == "fuse":
            for root, _dirs, names in os.walk(top):
                for nm in names:
                    yield nm, os.path.join(root, nm)
            return
        p = subprocess.run(["xrdfs", self.door, "ls", "-R", top], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=1800)
        if p.returncode != 0:
            raise OSError("xrdfs ls -R %s: %s" % (top, (p.stderr or "").strip()[:200]))
        for ln in p.stdout.split():
            if ln.endswith(".root"):
                yield ln.split("/")[-1], ln

    def url(self, path):
        return path if self.mode == "fuse" else "root://%s/%s" % (self.door, path)


def proxy_seconds_left():
    try:
        p = subprocess.run(["voms-proxy-info", "-timeleft"], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
        txt = (p.stdout or "").strip()
        return int(txt) if txt.isdigit() else 0
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def has_cache(proj):
    """A submitted CRAB project dir has .requestcache; a failed submit leaves a shell without it."""
    return os.path.exists(os.path.join(proj, ".requestcache"))


def fmt_h(seconds):
    return "%.1f h" % (seconds / 3600.0)


# ----------------------------------------------------------------------------
# the manager
# ----------------------------------------------------------------------------
class Manager(object):
    def __init__(self, args):
        self.a = args
        self.t_start = time.time()
        self.eras = [e.strip() for e in args.era.split(",") if e.strip()]
        self.dir = os.path.join(THIS_DIR, "manager", args.name)
        os.makedirs(os.path.join(self.dir, "check"), exist_ok=True)
        self.log = Log(os.path.join(self.dir, "manager.log"))
        self.state_path = os.path.join(self.dir, "state.json")
        self.lock_path = os.path.join(self.dir, "manager.lock")
        self.owner = args.lock_owner or "%s:%d" % (socket.gethostname(), os.getpid())
        self.have_lock = False
        self.child = None

    # ---- setup --------------------------------------------------------------
    def tasks(self):
        cat = S.load_yaml(self.a.datasets)
        site = S.load_yaml(self.a.site_config)
        self.site = site
        eras = cat.get("eras") or {}
        out = []
        for era in self.eras:
            if era not in eras:
                raise SystemExit("ERROR: era %s not in %s" % (era, self.a.datasets))
            for d in (eras[era].get("datasets") or []):
                # 2026-10-15 review: a new era (2024) starts with dataset: "" until
                # resolve_parents.sh --fill; say so instead of an IndexError below.
                if not str(d.get("dataset") or "").strip():
                    raise SystemExit("ERROR: %s/%s has dataset: \"\" in %s -- run "
                                     "bash crab/resolve_parents.sh %s --fill first (in the "
                                     "era's CMSSW area, after cmsenv), check the diff, then "
                                     "start the manager again" % (era, d.get("name", "?"),
                                                                 self.a.datasets, era))
                cfg = S.build_config(process_name=d["name"], era=era, dataset_entry=d,
                                     site_cfg=site, era_block=eras[era])
                rn = cfg.General.requestName
                proj = os.path.join(PKG_ROOT, cfg.General.workArea, "crab_%s" % rn) \
                    if not os.path.isabs(cfg.General.workArea) \
                    else os.path.join(cfg.General.workArea, "crab_%s" % rn)
                out.append({"key": "%s/%s" % (era, d["name"]), "era": era, "name": d["name"],
                            "request": rn, "proj": proj, "dataset": d["dataset"],
                            "primary": d["dataset"].split("/")[1],
                            "enabled": bool(d.get("enabled"))})
        return out

    def take_lock(self):
        lk = load_json(self.lock_path, None)
        now = time.time()
        fresh = 2 * self.a.interval_min * 60 + 600
        if lk and lk.get("owner") != self.owner and now - lk.get("updated", 0) < fresh and not self.a.force_lock:
            if self.a.dry_run:
                self.log("lock held by %s (updated %d s ago); --dry-run continues read-only"
                         % (lk.get("owner"), now - lk.get("updated", 0)))
                return True
            self.log("ERROR: another manager holds %s (owner %s, updated %d s ago). "
                     "Stop it (condor_rm) or wait; a lock older than %d s is taken over."
                     % (self.lock_path, lk.get("owner"), now - lk.get("updated", 0), fresh))
            return False
        if lk and lk.get("owner") != self.owner:
            self.log("taking over a stale lock of %s (updated %d s ago)" % (lk.get("owner"), now - lk.get("updated", 0)))
        self.touch_lock()
        self.have_lock = True
        return True

    def touch_lock(self):
        if self.a.dry_run:
            return
        save_json(self.lock_path, {"owner": self.owner, "host": socket.gethostname(), "pid": os.getpid(),
                                   "updated": time.time(), "updated_utc": utc()})

    def drop_lock(self):
        if self.have_lock and not self.a.dry_run:
            lk = load_json(self.lock_path, None)
            if lk and lk.get("owner") == self.owner:
                os.remove(self.lock_path)

    # ---- run ----------------------------------------------------------------
    def run(self):
        a = self.a
        self.log("=== START extend_manager.py host=%s pid=%d owner=%s eras=%s name=%s interval=%s min "
                 "max_resubmit=%d stall=%s h budget=%s h%s%s"
                 % (socket.gethostname(), os.getpid(), self.owner, ",".join(self.eras), a.name,
                    a.interval_min, a.max_resubmit, a.stall_hours, a.max_runtime_hours,
                    " ONCE" if a.once else "", " DRY-RUN" if a.dry_run else "") + (" LAUNCH" if a.launch else ""))
        try:
            tasks = self.tasks()
        except SystemExit as e:
            self.log(str(e))
            return EXIT_SETUP
        if not self.take_lock():
            return EXIT_SETUP
        st = load_json(self.state_path, {"created": utc(), "phase": "watch", "alerts": [], "checks": 0,
                                         "tasks": {}, "last_progress": time.time(), "last_finished": -1})
        if a.recheck and st.get("phase") in ("checkfailed", "done"):
            self.log("--recheck: completion checks will run again")
            st["phase"] = "check"
        if a.clear_alerts and st.get("alerts"):
            self.log("--clear-alerts: dropping %d alert(s): %s" % (len(st["alerts"]), " | ".join(st["alerts"])))
            st["alerts"] = []
            st["last_progress"] = time.time()
            if st.get("phase") == "stopped":
                st["phase"] = "watch"
        for t in tasks:
            st["tasks"].setdefault(t["key"], {"resubmits": 0, "status_errors": 0, "done": False})
        if st.get("alerts"):
            for al in st["alerts"]:
                self.log("ALERT (from state) %s" % al)
            self.log("RESULT STOPPED -- fix the cause, then run the same command with --clear-alerts")
            return EXIT_STOPPED
        if a.launch:
            rc = self.launch_missing_eras(st, tasks)
            if rc is not None:
                return rc
        shells = [t for t in tasks if os.path.isdir(t["proj"]) and not has_cache(t["proj"])]
        for t in shells:
            self.alert(st, "%s: %s has no .requestcache -- a failed submit left this shell; move it with "
                           "python3 crab/submit_ttbarIdExtend.py --era %s --clean-failed-shells --yes, "
                           "then submit the era again" % (t["key"], t["proj"], t["era"]))
        if shells:
            self.save(st)
            self.log("RESULT STOPPED")
            return EXIT_STOPPED
        missing = [t for t in tasks if not os.path.isdir(t["proj"])]
        if len(missing) == len(tasks):
            self.log("ERROR: none of the %d CRAB project dirs exists (first: %s) -- was the campaign "
                     "submitted from this checkout (crab/launch_extend.sh --submit)?" % (len(tasks), tasks[0]["proj"]))
            return EXIT_SETUP
        for t in missing:
            self.alert(st, "%s: no CRAB project dir %s (not submitted?)" % (t["key"], t["proj"]))
        if st["alerts"]:
            self.save(st)
            self.log("RESULT STOPPED")
            return EXIT_STOPPED
        self.log("%d tasks: %s" % (len(tasks), ", ".join(t["request"] for t in tasks)))

        while True:
            if st["phase"] == "watch":
                self.check(st, tasks)
                self.save(st)
                if st["alerts"]:
                    self.log("RESULT STOPPED -- %d alert(s); state kept in %s; after fixing, re-run with --clear-alerts"
                             % (len(st["alerts"]), self.state_path))
                    return EXIT_STOPPED
            if st["phase"] == "check":
                rc = self.completion_checks(st, tasks)
                self.save(st)
                return rc
            if st["phase"] == "done":
                self.log("RESULT DONE (already done earlier; see %s)" % os.path.join(self.dir, "REPORT.txt"))
                return EXIT_DONE
            if st["phase"] == "checkfailed":
                self.log("RESULT CHECK FAILED (earlier; see %s). To re-run the checks after fixing: "
                         "edit nothing, run with --recheck" % os.path.join(self.dir, "REPORT.txt"))
                return EXIT_CHECKFAIL
            if a.once:
                self.log("RESULT ONCE -- one check done (phase %s)" % st["phase"])
                return EXIT_DONE
            used = (time.time() - self.t_start) / 3600.0
            if used + a.interval_min / 60.0 > a.max_runtime_hours:
                self.log("RESULT CONTINUE -- %.1f h of the %.1f h budget used; exit 75 (the condor job "
                         "is re-queued and resumes from the state)" % (used, a.max_runtime_hours))
                return EXIT_CONTINUE
            nxt = time.time() + a.interval_min * 60
            self.log("next check at %s" % datetime.datetime.utcfromtimestamp(nxt).strftime("%H:%M:%SZ"))
            while time.time() < nxt:
                time.sleep(min(30, max(0.05, nxt - time.time())))

    def launch_missing_eras(self, st, tasks):
        """--launch: submit (launch_extend.sh) every era none of whose tasks has a project dir.

        An era whose tasks all have a project dir was submitted before and is only
        watched. An era with SOME dirs, or with a shell (no .requestcache), is an
        ALERT: a human decides. Returns None to go on, or the exit code to stop with.
        """
        a = self.a
        to_launch = []
        for era in self.eras:
            et = [t for t in tasks if t["era"] == era]
            have = [t for t in et if os.path.isdir(t["proj"])]
            shells = [t for t in have if not has_cache(t["proj"])]
            if shells:
                self.alert(st, "era %s: %d project dir(s) without .requestcache (failed-submit shells: %s) -- "
                               "python3 crab/submit_ttbarIdExtend.py --era %s --clean-failed-shells --yes, then "
                               "run again" % (era, len(shells), " ".join(os.path.basename(t["proj"]) for t in shells), era))
            elif len(have) == len(et):
                self.log("--launch: era %s: all %d tasks were submitted earlier -> watch only" % (era, len(et)))
            elif have:
                self.alert(st, "era %s: only %d of %d tasks have a project dir -- submit the missing ones by "
                               "hand (submit_ttbarIdExtend.py --era %s --process ...)" % (era, len(have), len(et), era))
            else:
                to_launch.append(era)
        if st.get("alerts"):
            self.save(st)
            self.log("RESULT STOPPED")
            return EXIT_STOPPED
        if not to_launch:
            return None
        if a.dry_run:
            self.log("--launch: would run crab/launch_extend.sh --era %s --submit (dry-run)" % ",".join(to_launch))
            return EXIT_DONE
        rc = self.launch(to_launch)
        if rc != 0:
            self.alert(st, "launch_extend.sh --era %s stopped with exit %d -- read the [launch] lines above "
                           "(and crab/launch_logs/<UTC>_<eras>/launch.log)" % (",".join(to_launch), rc))
            self.save(st)
            self.log("RESULT STOPPED")
            return EXIT_STOPPED
        with io.open(os.path.join(self.dir, "launch.done"), "a", encoding="utf-8") as fh:
            fh.write("launch_extend.sh --era %s exit 0 at %s\n" % (",".join(to_launch), utc()))
        st["last_progress"] = time.time()
        return None

    def launch(self, eras):
        cmd = ["bash", os.path.join(THIS_DIR, "launch_extend.sh"), "--era", ",".join(eras), "--submit"]
        cmd += shlex.split(self.a.launch_args or "")
        self.log("launch: $ %s  (cwd %s; stdin closed: a grid pass-phrase prompt fails instead of hanging)"
                 % (" ".join(cmd), PKG_ROOT))
        self.child = subprocess.Popen(cmd, cwd=PKG_ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        for line in self.child.stdout:
            self.log.raw(line.rstrip("\n"))
        rc = self.child.wait()
        self.child = None
        self.log("launch: launch_extend.sh exit %d" % rc)
        return rc

    def save(self, st):
        if not self.a.dry_run:
            save_json(self.state_path, st)
            self.touch_lock()

    def alert(self, st, msg):
        st.setdefault("alerts", []).append(msg)
        self.log("ALERT %s" % msg)

    # ---- one check ----------------------------------------------------------
    def check(self, st, tasks):
        a = self.a
        st["checks"] = st.get("checks", 0) + 1
        n = st["checks"]
        left = proxy_seconds_left()
        if left is None:
            self.log("WARN voms-proxy-info unusable; proxy lifetime not checked")
        elif left < 2 * 3600:
            self.alert(st, "grid proxy has %s left -- voms-proxy-init -voms cms -rfc -valid 192:00 --out <proxy> "
                           "and re-submit the manager" % fmt_h(left))
            return
        elif left < 24 * 3600:
            self.log("WARN grid proxy has only %s left" % fmt_h(left))
        totals = {"finished": 0, "running": 0, "idle": 0, "transferring": 0, "failed": 0, "others": 0, "total": 0}
        rows, n_done = [], 0
        for t in tasks:
            ts = st["tasks"][t["key"]]
            if ts.get("done"):
                n_done += 1
                totals["finished"] += ts.get("jobs", 0)
                totals["total"] += ts.get("jobs", 0)
                rows.append("  %-22s done (%d jobs)" % (t["key"], ts.get("jobs", 0)))
                continue
            res, text, exc = crab_call("status", t["proj"], a.crab_timeout)
            if res is None:
                ts["status_errors"] = ts.get("status_errors", 0) + 1
                rows.append("  %-22s status error %d/3: %s" % (t["key"], ts["status_errors"], str(exc)[:120]))
                if ts["status_errors"] >= 3:
                    self.alert(st, "%s: crab status failed 3 checks in a row (%s)" % (t["key"], str(exc)[:200]))
                continue
            ts["status_errors"] = 0
            tstat = str(res.get("status", "?")).upper()
            jps = res.get("jobsPerStatus") or {}
            row, unknown = S.summarize_status(jps)
            for k in totals:
                totals[k] += row.get(k, 0)
            active = sum(int(jps.get(s, 0)) for s in ACTIVE_STATES)
            desc = "%-13s done %d/%d run %d idle %d transf %d fail %d other %d" % (
                tstat, row["finished"], row["total"], row["running"], row["idle"], row["transferring"],
                row["failed"], row["others"])
            if unknown:
                desc += " (unknown states %s)" % ",".join(sorted(unknown))
            if tstat in DEAD_SUBMIT_STATES or (tstat == "FAILED" and row["total"] == 0):
                self.alert(st, "%s: task %s -- it will never run; fix the cause and re-submit the task "
                               "(docs/08 T-19)" % (t["key"], tstat))
            elif tstat in KILLED_STATES:
                self.alert(st, "%s: task %s (killed by someone)" % (t["key"], tstat))
            elif row["total"] > 0 and row["finished"] == row["total"]:
                ts["done"], ts["jobs"] = True, row["total"]
                n_done += 1
                desc += "  -> DONE"
            elif row["failed"] > 0:
                gap = (time.time() - ts.get("last_resubmit", 0)) / 60.0
                if ts.get("resubmits", 0) < a.max_resubmit and gap < a.resubmit_gap_min:
                    desc += "  (%d failed; last resubmit %.0f min ago, waiting %s min for CRAB to act)" % (
                        row["failed"], gap, a.resubmit_gap_min)
                elif ts.get("resubmits", 0) < a.max_resubmit:
                    if a.dry_run:
                        desc += "  -> would resubmit (%d failed)" % row["failed"]
                    else:
                        _, rtext, rexc = crab_call("resubmit", t["proj"], a.crab_timeout)
                        outcome = S.classify_resubmit(rtext, rexc)
                        if outcome == "sent":
                            ts["resubmits"] = ts.get("resubmits", 0) + 1
                            ts["last_resubmit"] = time.time()
                        desc += "  -> resubmit %s (%d failed; round %d/%d)%s" % (
                            outcome.upper(), row["failed"], ts.get("resubmits", 0), a.max_resubmit,
                            ("; " + failed_job_summary(res)) if failed_job_summary(res) else "")
                elif active == 0:
                    self.alert(st, "%s: %d job(s) still failed after %d resubmits (%s) -- look at "
                                   "crab status -d %s --long" % (t["key"], row["failed"], ts.get("resubmits", 0),
                                                                 failed_job_summary(res) or "exit codes: see crab status",
                                                                 t["proj"]))
                else:
                    desc += "  (resubmits used up; waiting for the %d active job(s))" % active
            ts["last_status"] = tstat
            rows.append("  %-22s %s" % (t["key"], desc))
        if totals["finished"] > st.get("last_finished", -1):
            st["last_finished"] = totals["finished"]
            st["last_progress"] = time.time()
            st["last_progress_utc"] = utc()
        hist = st.setdefault("history", [])
        hist.append([time.time(), totals["finished"]])
        del hist[:-12]
        pct = 100.0 * totals["finished"] / totals["total"] if totals["total"] else 0.0
        eta = "?"
        if len(hist) >= 2 and hist[-1][1] > hist[0][1] and totals["total"]:
            rate = (hist[-1][1] - hist[0][1]) / max(1.0, hist[-1][0] - hist[0][0])
            eta = fmt_h((totals["total"] - totals["finished"]) / rate)
        self.log("check %d | jobs done %d/%d (%.1f%%) run %d idle %d transf %d fail %d other %d | tasks done %d/%d "
                 "| ETA %s | proxy %s" % (n, totals["finished"], totals["total"], pct, totals["running"],
                                          totals["idle"], totals["transferring"], totals["failed"], totals["others"],
                                          n_done, len(tasks), eta, fmt_h(left) if left else "?"))
        for r in rows:
            self.log.raw(r)
        stalled = (time.time() - st.get("last_progress", time.time())) / 3600.0
        if n_done < len(tasks) and stalled >= a.stall_hours:
            self.alert(st, "no job finished for %.1f h (limit %s h; last progress %s) -- look at crab status"
                           % (stalled, a.stall_hours, st.get("last_progress_utc", "?")))
        if n_done == len(tasks) and not st.get("alerts"):
            self.log("all %d tasks finished every job -> completion checks" % len(tasks))
            st["phase"] = "check"

    # ---- completion checks ----------------------------------------------------
    def completion_checks(self, st, tasks):
        a = self.a
        base = a.out_base or lfn_to_eos(self.site.get("out_lfn_base"), self.site.get("storage_site"))
        if not base:
            self.log("ERROR: cannot map out_lfn_base %s at %s to a path; give --out-base"
                     % (self.site.get("out_lfn_base"), self.site.get("storage_site")))
            return EXIT_SETUP
        door = a.xrd_door if a.xrd_door else ("eosuser.cern.ch" if base.startswith("/eos/user/") else None)
        store = Storage(base, door, self.log)
        if store.mode is None:
            self.log("ERROR: output base %s is neither mounted (FUSE) nor reachable with xrdfs %s" % (base, door))
            self.alert(st, "completion checks cannot reach %s -- run them by hand later: python3 "
                           "crab/extend_manager.py --era %s --name %s --once --recheck" % (base, ",".join(self.eras), a.name))
            return EXIT_STOPPED
        self.log("completion checks: %d tasks, outputs under %s (access: %s)" % (len(tasks), base, store.mode))
        results, all_ok = [], True
        t0 = time.time()
        for i, t in enumerate(tasks, 1):
            ts = st["tasks"][t["key"]]
            r = {"key": t["key"], "jobs": ts.get("jobs", 0), "problems": []}
            tdir = os.path.join(base, t["era"], t["primary"], t["request"])
            self.log("[%d/%d] %s: %s" % (i, len(tasks), t["key"], tdir))
            # 1. exactly one timestamp dir
            try:
                stamps = sorted(d for d in store.listdir(tdir) if CRAB_TS_RE.match(d))
            except (OSError, subprocess.TimeoutExpired) as e:
                stamps = []
                r["problems"].append("cannot list %s (%s)" % (tdir, e))
            if len(stamps) != 1 and not r["problems"]:
                r["problems"].append("%d CRAB timestamp dirs (%s), want exactly 1" % (len(stamps), " ".join(stamps)))
            # 2. files == jobs, ids 1..N
            files = []
            if len(stamps) == 1:
                try:
                    for nm, path in store.walk_files(os.path.join(tdir, stamps[0])):
                        m = OUT_FILE_RE.match(nm)
                        if m:
                            files.append((int(m.group(1)), store.url(path)))
                except (OSError, subprocess.TimeoutExpired) as e:
                    r["problems"].append("cannot list the files (%s)" % e)
                ids = sorted(x[0] for x in files)
                r["files"] = len(files)
                if not r["problems"] and ids != list(range(1, r["jobs"] + 1)):
                    missing = sorted(set(range(1, r["jobs"] + 1)) - set(ids))
                    extra = sorted(set(ids) - set(range(1, r["jobs"] + 1)))
                    dup = len(ids) - len(set(ids))
                    r["problems"].append("files %d vs jobs %d (missing ids %s%s%s)" % (
                        len(ids), r["jobs"], missing[:10], "; extra ids %s" % extra[:10] if extra else "",
                        "; %d duplicate ids" % dup if dup else ""))
            # 3. + 4. rows and invariants (only if the file set is complete)
            if files and not r["problems"]:
                flist = os.path.join(self.dir, "check", "files_%s_%s.txt" % (t["name"], t["era"]))
                with io.open(flist, "w", encoding="utf-8") as fh:
                    for _jid, path in sorted(files):
                        fh.write(path + "\n")
                summary = self.run_macro(t, flist)
                r.update(summary)
                if summary.get("verdict") != "ALL INVARIANTS PASS":
                    r["problems"].append("check_extend_sample: %s" % summary.get("verdict", "no verdict line"))
                nev = das_nevents(t["dataset"])
                r["mini_nevents"] = nev
                if nev is None:
                    r["problems"].append("DAS nevents of %s not available" % t["dataset"])
                elif summary.get("entries") != nev:
                    r["problems"].append("rows %s != MiniAOD nevents %d (diff %s)" % (
                        summary.get("entries"), nev,
                        (summary.get("entries") - nev) if summary.get("entries") is not None else "?"))
            r["ok"] = not r["problems"]
            all_ok = all_ok and r["ok"]
            results.append(r)
            el = time.time() - t0
            self.log("[%d/%d] %s: %s  (%.0f s so far, ETA %.0f s)" % (
                i, len(tasks), t["key"], "PASS" if r["ok"] else "FAIL: " + "; ".join(r["problems"]),
                el, el / i * (len(tasks) - i)))
        self.write_report(results, all_ok, base)
        st["phase"] = "done" if all_ok else "checkfailed"
        st["completion"] = {"utc": utc(), "ok": all_ok}
        if all_ok:
            self.log("RESULT DONE -- every task complete and checked; report %s" % os.path.join(self.dir, "REPORT.txt"))
            return EXIT_DONE
        self.log("RESULT CHECK FAILED -- see %s" % os.path.join(self.dir, "REPORT.txt"))
        return EXIT_CHECKFAIL

    def run_macro(self, t, flist):
        out = {}
        logp = os.path.join(self.dir, "check", "sample_%s_%s.log" % (t["name"], t["era"]))
        cmd = ["root", "-l", "-b", "-q", '%s("%s")' % (MACRO, flist)]
        self.log("  $ %s  (log %s)" % (" ".join(cmd), logp))
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 universal_newlines=True, bufsize=1)
        except OSError as e:
            out["verdict"] = "root not runnable: %s" % e
            return out
        with io.open(logp, "w", encoding="utf-8") as lg:
            for line in p.stdout:
                line = line.rstrip("\n")
                lg.write(line + "\n")
                lg.flush()
                if line.startswith("  progress ") or line.startswith("  BAD_OPEN") or line.startswith("  NO_TREE") \
                        or line.startswith("  READ_ERRORS") or line.startswith("  MISSING_BRANCH"):
                    self.log.raw("    " + line.strip())
                if line.startswith("SAMPLE "):
                    for k, v in re.findall(r"(\w+)=(\d+)", line):
                        out[k] = int(v)
                if line.startswith("VERDICT:"):
                    out["verdict"] = line[len("VERDICT:"):].strip()
        rc = p.wait()
        if rc != 0 and "verdict" in out and out["verdict"] == "ALL INVARIANTS PASS":
            out["verdict"] = "root exited %d after the verdict line" % rc
        return out

    def write_report(self, results, all_ok, base):
        lines = ["extend campaign report  %s  eras=%s  name=%s" % (utc(), ",".join(self.eras), self.a.name),
                 "outputs: %s" % base, ""]
        hdr = "%-22s %6s %6s %12s %12s %9s %8s %8s %8s %8s  %s" % (
            "task", "jobs", "files", "rows", "MiniAOD ev", "ge3", "61", "62", "71", "72", "verdict")
        lines += [hdr, "-" * len(hdr)]
        for r in results:
            lines.append("%-22s %6s %6s %12s %12s %9s %8s %8s %8s %8s  %s" % (
                r["key"], r.get("jobs", "?"), r.get("files", "?"), r.get("entries", "?"),
                r.get("mini_nevents", "?"), r.get("ge3", "?"), r.get("c61", "?"), r.get("c62", "?"),
                r.get("c71", "?"), r.get("c72", "?"), "PASS" if r["ok"] else "FAIL"))
        lines.append("")
        for r in results:
            for p in r["problems"]:
                lines.append("FAIL %s: %s" % (r["key"], p))
        lines.append("RESULT: %s" % ("ALL PASS" if all_ok else "CHECK FAILED"))
        lines.append("next segment: central NanoAODv9 comparison + patch extraction (Validation/, docs/01 O9 steps 7-9)")
        with io.open(os.path.join(self.dir, "REPORT.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        for ln in lines:
            self.log.raw(ln)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Watch an extend CRAB campaign, resubmit, then check its outputs.")
    p.add_argument("--era", required=True, help="comma-separated era keys, e.g. 2016APV,2016")
    p.add_argument("--name", required=True, help="manager name (state dir crab/manager/<name>/)")
    p.add_argument("--datasets", default=os.path.join(THIS_DIR, "datasets.yaml"))
    p.add_argument("--site-config", default=os.path.join(THIS_DIR, "site_config.yaml"))
    p.add_argument("--interval-min", type=float, default=30.0)
    p.add_argument("--max-resubmit", type=int, default=3)
    p.add_argument("--stall-hours", type=float, default=8.0)
    p.add_argument("--max-runtime-hours", type=float, default=22.0,
                   help="exit 75 before this (condor re-queues the job; JobFlavour tomorrow = 24 h)")
    p.add_argument("--crab-timeout", type=int, default=900, help="seconds per crab status/resubmit call")
    p.add_argument("--out-base", default=None, help="storage path of out_lfn_base (default: mapped from site_config)")
    p.add_argument("--xrd-door", default=None,
                   help="xrootd door used when --out-base is not mounted (default eosuser.cern.ch for /eos/user)")
    p.add_argument("--lock-owner", default=None, help="lock identity (manager_condor.sh passes condor:<cluster>)")
    p.add_argument("--launch", action="store_true",
                   help="run crab/launch_extend.sh --submit first if nothing was submitted yet")
    p.add_argument("--launch-args", default="",
                   help='extra arguments for launch_extend.sh, e.g. "--skip-local" or "--report-wait 600"')
    p.add_argument("--once", action="store_true", help="one check (and the completion checks if due), then exit")
    p.add_argument("--dry-run", action="store_true", help="no resubmit, no state/lock writes")
    p.add_argument("--clear-alerts", action="store_true", help="drop recorded alerts and continue")
    p.add_argument("--recheck", action="store_true", help="run the completion checks again (after CHECK FAILED)")
    p.add_argument("--force-lock", action="store_true", help="take the lock even if another owner updated it recently")
    p.add_argument("--resubmit-gap-min", type=float, default=60.0,
                   help="minutes to wait after a resubmit of a task before resubmitting it again")
    a = p.parse_args(argv)
    if a.interval_min <= 0 or a.max_resubmit < 0 or a.stall_hours <= 0 or a.max_runtime_hours <= 0:
        p.error("intervals, limits and budgets must be positive")
    return a


def main(argv=None):
    args = parse_args(argv)
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)
    m = Manager(args)
    rc = EXIT_SETUP
    try:
        rc = m.run()
    except Stop as s:
        if m.child is not None and m.child.poll() is None:
            m.log("stopping the running launch_extend.sh (SIGTERM)")
            m.child.terminate()
            try:
                m.child.wait(timeout=60)
            except subprocess.TimeoutExpired:
                m.child.kill()
        m.log("stopped by %s (state is saved after every check; the same command resumes)" % s.signame)
        rc = s.code
    except Exception as e:  # noqa: BLE001 -- log the traceback, never die silently
        import traceback
        for ln in traceback.format_exc().splitlines():
            m.log.raw("[manager] TRACEBACK " + ln)
        m.log("crashed: %s: %s" % (type(e).__name__, e))
        rc = EXIT_SETUP
    finally:
        if rc != EXIT_CONTINUE:
            m.drop_lock()
        m.log("=== END extend_manager.py EXIT=%d elapsed=%.0f s" % (rc, time.time() - m.t_start))
    return rc


if __name__ == "__main__":
    sys.exit(main())
