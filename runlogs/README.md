# runlogs -- run records of this repository

> **Purpose:** records of runs done on lxplus (launch, manager, preflight, resolve, reports) that a later session or the user
> reads instead of pasted terminal output. Rules: `00_PROMPT.md` sec.9 (2026-10-14).

- `lxplus/<UTC>_<what>.log` -- copies of `TtbarIdExtender/crab/launch_logs/<UTC>_<eras>/launch.log`,
  `TtbarIdExtender/crab/manager/<name>/manager.log` / `REPORT.txt`, preflight and resolve logs. Committed on the branch of the
  session that produced them (`agent/<YYYYMMDD>-<topic>`), merged by the user.
- Not here: full CRAB transcripts (`submit_*_20*.log`, git-ignored), grid proxies, anything with a pass phrase.
- A record without its tail line (`=== END ... EXIT=`) means the run was killed or is still running.
