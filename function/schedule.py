# import
import asyncio
import datetime
import os
import re
import socket
import sys
from contextlib import asynccontextmanager
from typing import Any
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError
import asyncpg
from .background import func_runtime_error_record

# function
def func_schedule_parse(*, value: Any, key: str = "schedule") -> dict | None:
    """Read a schedule value: off (also None or False) gives None; every Nh (N divides 24), daily HH:MM, every Nd HH:MM (N 2-30), weekly mon,thu HH:MM and monthly D HH:MM (D 1-28) give a dict; anything else raises, naming the key."""
    if value is None or value is False: return None
    text = value.strip().lower() if isinstance(value, str) else None
    if text == "off": return None
    days = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    def clock(hour, minute):
        if int(hour) > 23 or int(minute) > 59: raise ValueError(f"{key}: {value!r} has no such time; use HH:MM from 00:00 to 23:59")
        return int(hour), int(minute)
    if text and (match := re.fullmatch(r"every (\d+)h", text)):
        if int(match.group(1)) not in (1, 2, 3, 4, 6, 8, 12): raise ValueError(f"{key}: {value!r}: hours must be 1, 2, 3, 4, 6, 8 or 12 (they divide the day evenly)")
        return {"kind": "hour", "every": int(match.group(1)), "time": (0, 0)}
    if text and (match := re.fullmatch(r"daily (\d\d):(\d\d)", text)): return {"kind": "day", "every": 1, "time": clock(*match.groups())}
    if text and (match := re.fullmatch(r"every (\d+)d (\d\d):(\d\d)", text)):
        if not 2 <= int(match.group(1)) <= 30: raise ValueError(f"{key}: {value!r}: days must be 2 to 30 (use daily for every day)")
        return {"kind": "day", "every": int(match.group(1)), "time": clock(*match.groups()[1:])}
    if text and (match := re.fullmatch(r"weekly ([a-z,]+) (\d\d):(\d\d)", text)):
        names = match.group(1).split(",")
        if not names or any(name not in days for name in names): raise ValueError(f"{key}: {value!r}: weekdays are {', '.join(days)}, comma separated")
        return {"kind": "week", "weekdays": sorted({days.index(name) for name in names}), "time": clock(*match.groups()[1:])}
    if text and (match := re.fullmatch(r"monthly (\d+) (\d\d):(\d\d)", text)):
        if not 1 <= int(match.group(1)) <= 28: raise ValueError(f"{key}: {value!r}: the day must be 1 to 28 (every month has it)")
        return {"kind": "month", "day": int(match.group(1)), "time": clock(*match.groups()[1:])}
    raise ValueError(f"{key}: {value!r} is not a schedule; use off, every 6h, daily 02:00, every 3d 02:00, weekly sun 02:00 or monthly 1 02:00")

def func_schedule_timezone(*, name: Any) -> datetime.tzinfo:
    """The tzinfo for config_schedule_timezone: UTC, or a zone name such as Asia/Kolkata; an unknown name raises."""
    if name == "UTC": return datetime.UTC
    try: return ZoneInfo(str(name))
    except (ZoneInfoNotFoundError, ValueError): raise ValueError(f"config_schedule_timezone: unknown time zone {name!r}; use UTC or a name such as Asia/Kolkata") from None

def func_schedule_slot(*, schedule: dict, now: datetime.datetime) -> tuple:
    """(start, end) of the slot holding now, in now's time zone: start is the latest scheduled time at or before now, end the next one. every Nd counts days from 1 Jan 2026, so its dates never move."""
    hour, minute = schedule["time"]
    def at(day): return datetime.datetime(day.year, day.month, day.day, hour, minute, tzinfo=now.tzinfo)
    today = now.date()
    if schedule["kind"] == "hour":
        start = at(today) + datetime.timedelta(hours=now.hour // schedule["every"] * schedule["every"])
        return start, start + datetime.timedelta(hours=schedule["every"])
    if schedule["kind"] == "day":
        day = today - datetime.timedelta(days=(today - datetime.date(2026, 1, 1)).days % schedule["every"])
        if at(day) > now: day -= datetime.timedelta(days=schedule["every"])
        return at(day), at(day + datetime.timedelta(days=schedule["every"]))
    if schedule["kind"] == "week":
        start = next(at(day) for back in range(8) if (day := today - datetime.timedelta(days=back)).weekday() in schedule["weekdays"] and at(day) <= now)
        end = next(at(day) for ahead in range(1, 8) if (day := start.date() + datetime.timedelta(days=ahead)).weekday() in schedule["weekdays"])
        return start, end
    month = today.replace(day=schedule["day"])
    if at(month) > now: month = (month.replace(day=1) - datetime.timedelta(days=1)).replace(day=schedule["day"])
    following = (month.replace(day=28) + datetime.timedelta(days=4)).replace(day=schedule["day"])
    return at(month), at(following)

def func_schedule_decide(*, now: datetime.datetime, slot: tuple, is_running: bool, done_count: int, failed_count: int, try_max: int = 2, late_sec: int = 14400) -> str:
    """start, or why not: running (a run holds the lock), done (this slot already succeeded), tries (try_max runs failed in this slot) or late (past the slot's first late_sec, or its whole length when shorter)."""
    if is_running: return "running"
    if done_count: return "done"
    if failed_count >= try_max: return "tries"
    start, end = slot
    if now >= start + min(datetime.timedelta(seconds=late_sec), end - start): return "late"
    return "start"

def func_schedule_read(*, values: dict, root: str = None) -> dict:
    """{script: {"schedule": dict, "module": "script.x" or "script_extend.x"}} for every config_schedule_<script> that is not off; raises on a bad value, a bad timezone or interval, a missing script or one in both folders."""
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # the project folder, wherever the app is started from
    func_schedule_timezone(name=values.get("config_schedule_timezone", "UTC"))
    check_sec = values.get("config_schedule_check_sec", 600)
    if isinstance(check_sec, bool) or not isinstance(check_sec, int) or not 60 <= check_sec <= 3600: raise ValueError("config_schedule_check_sec must be a whole number of seconds from 60 to 3600")
    schedules = {}
    for key in sorted(values):
        if not key.startswith("config_schedule_") or key in ("config_schedule_timezone", "config_schedule_check_sec"): continue
        script = key.removeprefix("config_schedule_")
        schedule = func_schedule_parse(value=values[key], key=key)
        found = [folder for folder in ("script", "script_extend") if os.path.isfile(os.path.join(root, folder, f"{script}.py"))]
        if len(found) == 2: raise ValueError(f"{key}: {script}.py is in both script/ and script_extend/; rename one")
        if schedule is None: continue
        if not found: raise ValueError(f"{key}: no script named {script} (script/{script}.py or script_extend/{script}.py)")
        schedules[script] = {"schedule": schedule, "module": f"{found[0]}.{script}"}
    return schedules

async def func_schedule_check(*, client_postgres: asyncpg.Pool, script: str, schedule: dict, timezone: datetime.tzinfo) -> str:
    """Decide whether a scheduled script starts now (func_schedule_decide); a Running row whose lock is free belongs to a run that died, so it is marked Failed first."""
    async with client_postgres.acquire(timeout=10) as conn:
        is_running = await conn.fetchval("SELECT CASE WHEN pg_try_advisory_lock(1096044366, hashtext($1)) THEN NOT pg_advisory_unlock(1096044366, hashtext($1)) ELSE true END", script, timeout=10)
        if not is_running: await conn.execute("UPDATE script_run SET status = 3, message = 'stopped before finishing', finished_at = now() WHERE script = $1 AND status = 1", script, timeout=10)
        now = datetime.datetime.now(timezone)
        slot = func_schedule_slot(schedule=schedule, now=now)
        row = await conn.fetchrow("SELECT count(*) FILTER (WHERE status = 2) AS done, count(*) FILTER (WHERE status = 3) AS failed FROM script_run WHERE script = $1 AND created_at >= $2", script, slot[0], timeout=10)
    return func_schedule_decide(now=now, slot=slot, is_running=is_running, done_count=row["done"], failed_count=row["failed"])

def _schedule_log_open(*, script: str):
    os.makedirs(f"tmp/{script}", exist_ok=True)
    return open(f"tmp/{script}/schedule.log", "wb")    # noqa: SIM115 - closed by func_schedule_script_start

def _schedule_log_last_line(*, path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as file: return next((line.strip() for line in reversed(file.read().splitlines()) if line.strip()), "")

def _schedule_env() -> dict:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # python -m script.<name> is found from any working folder
    return {**os.environ, "ATOM_SCRIPT_STARTED_BY": "schedule", "PYTHONUNBUFFERED": "1", "PYTHONPATH": os.pathsep.join(filter(None, (root, os.environ.get("PYTHONPATH"))))}

async def func_schedule_script_start(*, client_postgres: asyncpg.Pool, script: str, module: str, timeout_sec: int = 14400) -> int | None:
    """Run python -m <module> with no terminal (it records itself as started by the schedule), output to tmp/<script>/schedule.log, stopped after timeout_sec; a run that ends without writing its script_run row gets a Failed one. Returns the exit code."""
    started_at = await client_postgres.fetchval("SELECT now()", timeout=10)
    async def fail(message):
        await client_postgres.execute("UPDATE script_run SET status = 3, message = $3, finished_at = now() WHERE script = $1 AND status = 1 AND created_at >= $2", script, started_at, message, timeout=10)
    log_file = await asyncio.to_thread(_schedule_log_open, script=script)
    try:
        process = await asyncio.create_subprocess_exec(sys.executable, "-m", module, stdin=asyncio.subprocess.DEVNULL, stdout=log_file, stderr=asyncio.subprocess.STDOUT, env=_schedule_env())
        try: code = await asyncio.wait_for(process.wait(), timeout=timeout_sec)
        except TimeoutError:
            process.kill()
            await process.wait()
            await fail(f"stopped after the {timeout_sec // 3600}-hour limit")
            return None
        except asyncio.CancelledError:
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
                await asyncio.wait_for(fail("stopped by an app restart"), timeout=2)
            except Exception as e: print(f"❌ schedule: {script} stopped, its run not marked: {e!r}", flush=True)
            raise
    finally: log_file.close()
    if code == 75: return code    # another run held the lock: nothing ran
    if not await client_postgres.fetchval("SELECT count(*) FROM script_run WHERE script = $1 AND created_at >= $2", script, started_at, timeout=10):
        last = await asyncio.to_thread(_schedule_log_last_line, path=log_file.name)
        message = f"exited with code {code} without recording its run (wrap its work in func_script_run); {log_file.name}: {last}"[:500]
        await client_postgres.execute("INSERT INTO script_run (script, started_by, host, status, message, finished_at) VALUES ($1, 'schedule', $2, 3, $3, now())", script, socket.gethostname(), message, timeout=10)
    return code

async def func_schedule_periodic_task(*, client_postgres: asyncpg.Pool, schedules: dict, timezone: datetime.tzinfo, check_sec: int, runtime_error_count: dict) -> None:
    """Every check_sec (first a minute after startup), start each scheduled script whose slot is due and that is not running in this worker; at shutdown, stop the scripts it started."""
    running = {}
    try:
        await asyncio.sleep(min(60, check_sec))
        while True:
            for script, item in schedules.items():
                if script in running and not running[script].done(): continue
                try:
                    if await func_schedule_check(client_postgres=client_postgres, script=script, schedule=item["schedule"], timezone=timezone) == "start":
                        print(f"schedule: starting {script}", flush=True)
                        running[script] = asyncio.create_task(func_schedule_script_start(client_postgres=client_postgres, script=script, module=item["module"]))
                        running[script].add_done_callback(lambda task, script=script: task.cancelled() or not task.exception() or func_runtime_error_record(runtime_error_count=runtime_error_count, key="schedule", error=task.exception()))
                except Exception as e: func_runtime_error_record(runtime_error_count=runtime_error_count, key="schedule", error=e)
            await asyncio.sleep(check_sec)
    except asyncio.CancelledError:
        tasks = [task for task in running.values() if not task.done()]
        for task in tasks: task.cancel()
        if tasks: await asyncio.wait(tasks, timeout=4)
    return

async def func_script_run_cleanup(*, conn: asyncpg.Connection, cutoff, timeout_sec: float) -> int:
    """Delete at most 5,000 finished script_run rows started before cutoff; a run still going is kept (script/cleanup.py calls it until done)."""
    result = await conn.execute("DELETE FROM script_run WHERE id IN (SELECT id FROM script_run WHERE created_at < $1 AND status <> 1 ORDER BY created_at LIMIT 5000 FOR UPDATE SKIP LOCKED)", cutoff, timeout=timeout_sec)
    return int(result.split()[-1])

def func_script_run_message(*, error: BaseException) -> str | None:
    """The plain message a failed run keeps: the error's own text (first line, 500 characters), the exit code, or how it was stopped; None for a clean exit."""
    if isinstance(error, SystemExit):
        if error.code in (None, 0): return None
        return str(error.code)[:500] if not isinstance(error.code, int) else f"exit code {error.code}"
    if isinstance(error, KeyboardInterrupt): return "stopped by hand"
    if isinstance(error, asyncio.CancelledError): return "stopped"
    text = next((line.strip() for line in str(error).splitlines() if line.strip()), "")
    return (text or type(error).__name__)[:500]

class _ScriptOutput:
    """Passes the script's prints through and keeps the latest 'step: ...' line and the latest other line."""
    def __init__(self, stream):
        self.stream, self.step, self.last, self.partial = stream, None, None, ""
    def write(self, text):
        self.partial += text
        *lines, self.partial = self.partial.split("\n")
        for line in (line.strip() for line in lines):
            if line.lower().startswith("step:"): self.step = line[5:].strip()[:200] or None
            elif line: self.last = line[:500]
        return self.stream.write(text)
    def __getattr__(self, name): return getattr(self.stream, name)

def _script_peak_memory_mb() -> int | None:
    try: import resource
    except ImportError: return None    # Windows
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / 1048576) if sys.platform == "darwin" else round(peak / 1024)

@asynccontextmanager
async def func_script_run(*, postgres_url: str, script: str):
    """Wrap a script's work: take its Postgres lock (another run of it anywhere exits at once, code 75), record it in script_run (Running, started by schedule or by hand, host), keep the latest printed 'step: ...' line as its step, then mark it Done (message: its last printed line) or Failed (message: the error)."""
    conn = await asyncpg.connect(postgres_url)
    if not await conn.fetchval("SELECT pg_try_advisory_lock(1096044366, hashtext($1))", script):
        await conn.close()
        print(f"{script} is already running", file=sys.stderr, flush=True)
        raise SystemExit(75)
    output = _ScriptOutput(sys.stdout)
    sync_task = None
    try:
        await conn.execute("UPDATE script_run SET status = 3, message = 'stopped before finishing', finished_at = now() WHERE script = $1 AND status = 1", script)
        started_by = "schedule" if os.environ.get("ATOM_SCRIPT_STARTED_BY") == "schedule" else "manual"
        run_id = await conn.fetchval("INSERT INTO script_run (script, started_by, host, status) VALUES ($1, $2, $3, 1) RETURNING id", script, started_by, socket.gethostname())
        async def step_sync():    # writes the step when it changes, and keeps the lock's connection busy so it is not dropped as idle
            written, idle_sec = None, 0
            while True:
                await asyncio.sleep(1)
                idle_sec += 1
                if output.step != written or idle_sec >= 30:
                    written, idle_sec = output.step, 0
                    await conn.execute("UPDATE script_run SET step = $2, updated_at = now() WHERE id = $1", run_id, written)
        sys.stdout = output
        sync_task = asyncio.create_task(step_sync())
        error = None
        try: yield run_id
        except BaseException as e:
            error = e
            raise
        finally:
            sys.stdout = output.stream
            sync_task.cancel()
            await asyncio.gather(sync_task, return_exceptions=True)
            message = func_script_run_message(error=error) if error is not None else None
            status = 3 if message is not None else 2
            try: await conn.execute("UPDATE script_run SET status = $2, step = $3, message = $4, peak_memory_mb = $5, finished_at = now(), updated_at = now() WHERE id = $1", run_id, status, output.step, message if status == 3 else output.last, _script_peak_memory_mb(), timeout=10)
            except Exception as e: print(f"❌ {script}: could not record the run's end: {e!r}", file=sys.stderr, flush=True)
    finally:
        sys.stdout = output.stream
        await conn.close()    # closing the session releases the lock
