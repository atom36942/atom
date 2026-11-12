# Scheduled scripts

Atom runs a script by itself on a schedule: one setting per script, and one line in the script. The script stays a normal script, run by hand with its usual command.

## Turn one on

```python
# config_extend.py (or the server's environment)
config_schedule_timezone = "Asia/Kolkata"
config_schedule_nightly_import = "daily 02:00"
```

`config_schedule_<script>` names a file in `script/` or `script_extend/` (`nightly_import` → `script_extend/nightly_import.py`).

| Value | Runs |
|---|---|
| `off` (or not set) | never by itself |
| `every Nh` | every N hours from 00:00; N is 1, 2, 3, 4, 6, 8 or 12, so the times are the same every day |
| `daily HH:MM` | every day at that time |
| `every Nd HH:MM` | every N days (2–30) at that time, counted from 1 Jan 2026 so the dates never move |
| `weekly DAY HH:MM` | those weekdays, e.g. `weekly sun 02:00`, `weekly mon,thu 02:00` |
| `monthly D HH:MM` | that day of each month (1–28, which every month has) |

Times are in `config_schedule_timezone` (default `UTC`; any zone name, such as `Asia/Kolkata`). The words are simpler than cron on purpose: cron cannot say "every 3 days" and needs a parser. An unknown value, time zone or script name, a script in both folders, or a script whose first line is not `# type: job` (below), stops startup with the setting's name.

Atom's own:

| Setting | Default | Script |
|---|---|---|
| `config_schedule_postgres_cleanup` | `every 1h` | `script/postgres_cleanup.py`: deletes OTP, API-log and finished `script_run` rows older than `config_retention_day_otp` (1), `config_retention_day_log_api` (7) and `config_retention_day_script_run` (90); a retention of `None` skips that table |
| `config_schedule_postgres_backup` | `off` | `script/postgres_backup.py`: every table of the master database to CSV, with its columns and indexes, from one snapshot, into `tmp/postgres_backup/<date_time>/`; keeps 7 days. Useful before changing data; on hosts whose disk is reset on deploy (Azure App Service, containers) it is a working copy, not disaster recovery |

## Write one

```python
# type: job

# command: venv/bin/python -m script_extend.nightly_import

# info: Imports the day's orders from the source.

...

# logic
async def import_run(*, postgres_url) -> None:
    async with func_script_run(postgres_url=postgres_url, script="nightly_import"):
        print("step: download", flush=True)
        rows = await source_read()
        print("step: save", flush=True)
        await rows_save(rows)
        print(f"saved {len(rows)} rows", flush=True)
```

`func_script_run` does the rest, for a scheduled run and a run by hand alike:
- **One at a time:** it takes the script's Postgres lock; another run of it, on any machine using that database, prints `already running` and exits with code 75. Postgres releases the lock when the process ends, even if it crashes.
- **A record:** one row in `script_run`: `started_by` (`schedule` when Atom started it, `manual` otherwise), `host`, `status` (1 Running, 2 Done, 3 Failed), `step` (the latest printed `step: ...` line), `message`, `peak_memory_mb`, start and end times.
- **Done or Failed:** Done keeps the last line the script printed as its message; Failed keeps the error's first line (`Can't reach the source`), the exit code, or `stopped by hand`. Raise errors with a sentence a user can act on.
- **A run that died** (killed, machine asleep, deploy) is marked Failed `stopped before finishing` by the next run or check.

The lock covers only what is inside the block. Scripts whose runs may overlap harmlessly still use it, to be recorded.

## How a run starts

- **Startup:** when no `config_schedule_*` is on, nothing starts. Otherwise one loop starts with the app (not in read-only mode, only with a master database) and stops at shutdown; there is no `func_extend` to write.
- **Every `config_schedule_check_sec`** (600; 60 to 3600; first a minute after startup), for each scheduled script, a run starts when all hold:
  - its slot is open (the latest scheduled time has passed) and within the slot's first 4 hours, or its whole length when shorter, so a server back at 11:00 does not start a 02:00 job in office hours;
  - no run of it holds the lock;
  - no run finished Done in this slot (a run by hand counts);
  - fewer than 2 runs failed in this slot (also counting runs by hand).
- **Start:** `python -m script.<name>` (or `script_extend.<name>`) as a separate process with no terminal, so a crash cannot take the app down; its output goes to `tmp/<name>/schedule.log` (replaced each run). A run still going after 4 hours is stopped and marked Failed. A run that exits without writing its row (it does not use `func_script_run`, or failed on import) gets a Failed row with its exit code and the log's last line.
- **Several app workers or servers:** each runs the loop; the lock lets one run start, the others exit with code 75 and record nothing.

## Jobs, not workers

The schedule is for jobs that start, finish and exit (an import, a refresh, a cleanup). A worker that loops forever (`while True`: wait for work, do it, sleep) does not fit: started by the schedule, it is stopped at the 4-hour limit and marked Failed, started once more, then left until the next slot; an app restart or deploy stops it too. Every script says which it is in its first line, `# type: job` or `# type: continuous` (a continuous one is named `worker_<x>` when it polls for work, `consumer_<x>` when it listens on a queue); startup refuses a schedule that is not `off` for a script without `# type: job`. Run a worker as its own process instead, kept alive by the platform (a separate container or WebJob, systemd, supervisor), like `script/worker_users_delete.py`: one copy at a time with `func_postgres_advisory_lock`, and a heartbeat (a row's `updated_at`) if a page should show whether it is alive. Not `func_script_run`: its run would show Running forever.

## Show it

Read `script_run` in the project's own route, e.g. the latest row of a script plus whether its lock is held, and show Running (with the step), Done or Failed (with the message) on the page; poll only while a run is going.

## Sizing

The script runs on the app's machine and shares its CPU and memory. Run it once by hand and read `peak_memory_mb` before scheduling it on a shared server; a job needing more than the server can spare belongs on its own worker machine (run it there by hand or with the system's scheduler, the lock and record stay the same).

---

📚 [Back to README](../readme.md)
