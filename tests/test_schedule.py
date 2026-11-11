"""Scheduled scripts: config_schedule_* values, slots, the start decision, startup errors and a run that never records itself, without a database."""
import datetime
import os
import tempfile
import unittest
from unittest.mock import AsyncMock
from unittest.mock import patch
from zoneinfo import ZoneInfo

from function.schedule import func_schedule_decide
from function.schedule import func_schedule_parse
from function.schedule import func_schedule_read
from function.schedule import func_schedule_script_start
from function.schedule import func_schedule_slot
from function.schedule import func_schedule_timezone
from function.schedule import func_script_run_message

IST = ZoneInfo("Asia/Kolkata")


def at(text):
    return datetime.datetime.fromisoformat(text).replace(tzinfo=IST)


class ScheduleValueTests(unittest.TestCase):
    def test_values(self):
        for value in ("off", "OFF", None, False): self.assertIsNone(func_schedule_parse(value=value))
        self.assertEqual(func_schedule_parse(value="every 6h"), {"kind": "hour", "every": 6, "time": (0, 0)})
        self.assertEqual(func_schedule_parse(value="daily 02:00"), {"kind": "day", "every": 1, "time": (2, 0)})
        self.assertEqual(func_schedule_parse(value="every 3d 23:30"), {"kind": "day", "every": 3, "time": (23, 30)})
        self.assertEqual(func_schedule_parse(value="weekly thu,mon 02:00"), {"kind": "week", "weekdays": [0, 3], "time": (2, 0)})
        self.assertEqual(func_schedule_parse(value="monthly 28 02:00"), {"kind": "month", "day": 28, "time": (2, 0)})

    def test_bad_values_name_the_key(self):
        for value in ("", "on", True, "every 5h", "every 0h", "every 30m", "daily 2:00", "daily 25:00", "every 1d 02:00", "every 31d 02:00", "weekly fun 02:00", "monthly 29 02:00", "0 2 * * *", 6):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "config_schedule_x"): func_schedule_parse(value=value, key="config_schedule_x")

    def test_timezone(self):
        self.assertIs(func_schedule_timezone(name="UTC"), datetime.UTC)
        self.assertEqual(str(func_schedule_timezone(name="Asia/Kolkata")), "Asia/Kolkata")
        with self.assertRaisesRegex(ValueError, "unknown time zone"): func_schedule_timezone(name="Mars/Base")


class ScheduleSlotTests(unittest.TestCase):
    def slot(self, value, now):
        return tuple(time.isoformat(timespec="minutes")[:16] for time in func_schedule_slot(schedule=func_schedule_parse(value=value), now=at(now)))

    def test_slots(self):
        cases = [
            ("every 6h", "2026-11-11 13:20", ("2026-11-11T12:00", "2026-11-11T18:00")),
            ("daily 02:00", "2026-11-11 01:59", ("2026-11-10T02:00", "2026-11-11T02:00")),
            ("daily 02:00", "2026-11-11 02:00", ("2026-11-11T02:00", "2026-11-12T02:00")),
            ("every 3d 02:00", "2026-01-05 10:00", ("2026-01-04T02:00", "2026-01-07T02:00")),    # counted from 1 Jan 2026: the 1st, 4th, 7th
            ("weekly mon,thu 02:00", "2026-11-11 09:00", ("2026-11-09T02:00", "2026-11-12T02:00")),    # Wed 11 Nov: since Monday, until Thursday
            ("weekly sun 02:00", "2026-11-15 01:00", ("2026-11-08T02:00", "2026-11-15T02:00")),
            ("monthly 1 02:00", "2026-03-01 01:00", ("2026-02-01T02:00", "2026-03-01T02:00")),
            ("monthly 28 02:00", "2026-12-30 00:00", ("2026-12-28T02:00", "2027-01-28T02:00")),
        ]
        for value, now, expected in cases:
            with self.subTest(value=value, now=now): self.assertEqual(self.slot(value, now), expected)


class ScheduleDecideTests(unittest.TestCase):
    def decide(self, now, value="daily 02:00", **counts):
        state = {"is_running": False, "done_count": 0, "failed_count": 0, **counts}
        return func_schedule_decide(now=at(now), slot=func_schedule_slot(schedule=func_schedule_parse(value=value), now=at(now)), **state)

    def test_decisions(self):
        self.assertEqual(self.decide("2026-11-11 02:05"), "start")
        self.assertEqual(self.decide("2026-11-11 02:05", is_running=True), "running")
        self.assertEqual(self.decide("2026-11-11 02:05", done_count=1), "done")
        self.assertEqual(self.decide("2026-11-11 03:00", failed_count=1), "start")    # one more try
        self.assertEqual(self.decide("2026-11-11 03:00", failed_count=2), "tries")
        self.assertEqual(self.decide("2026-11-11 05:59"), "start")
        self.assertEqual(self.decide("2026-11-11 06:00"), "late")    # a server back at 11:00 waits for the next night
        self.assertEqual(self.decide("2026-11-11 13:50", value="every 1h"), "start")    # an hour-long slot may start any time in it


class ScheduleReadTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        for folder, name in (("script", "cleanup"), ("script_extend", "nightly"), ("script", "twice"), ("script_extend", "twice")):
            os.makedirs(os.path.join(self.root.name, folder), exist_ok=True)
            open(os.path.join(self.root.name, folder, f"{name}.py"), "w").close()

    def tearDown(self): self.root.cleanup()

    def read(self, **values): return func_schedule_read(values={"config_schedule_timezone": "UTC", "config_schedule_check_sec": 600, **values}, root=self.root.name)

    def test_scheduled_scripts_and_their_folder(self):
        self.assertEqual(self.read(config_schedule_cleanup="every 1h", config_schedule_nightly="daily 02:00", config_schedule_other="off"), {
            "cleanup": {"schedule": {"kind": "hour", "every": 1, "time": (0, 0)}, "module": "script.cleanup"},
            "nightly": {"schedule": {"kind": "day", "every": 1, "time": (2, 0)}, "module": "script_extend.nightly"},
        })
        self.assertEqual(self.read(config_schedule_cleanup="off"), {})

    def test_startup_errors(self):
        for values, error in (({"config_schedule_missing": "daily 02:00"}, "no script named missing"), ({"config_schedule_twice": "off"}, "in both script/ and script_extend/"),
                              ({"config_schedule_cleanup": "every 7h"}, "config_schedule_cleanup"), ({"config_schedule_check_sec": 30}, "60 to 3600"), ({"config_schedule_timezone": "IST"}, "unknown time zone")):
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, error): self.read(**values)


class ScriptRunTests(unittest.IsolatedAsyncioTestCase):
    def test_failure_messages(self):
        self.assertIsNone(func_script_run_message(error=SystemExit(0)))
        self.assertEqual(func_script_run_message(error=SystemExit(2)), "exit code 2")
        self.assertEqual(func_script_run_message(error=SystemExit("config_postgres_url_master is not set")), "config_postgres_url_master is not set")
        self.assertEqual(func_script_run_message(error=Exception("Can't reach the source\ntraceback detail")), "Can't reach the source")
        self.assertEqual(func_script_run_message(error=KeyError()), "KeyError")
        self.assertEqual(func_script_run_message(error=KeyboardInterrupt()), "stopped by hand")

    async def test_a_run_that_never_records_itself_is_marked_failed(self):
        pool = AsyncMock()
        pool.fetchval.side_effect = ["2026-11-11 02:00", 0]    # the start time, then no script_run row since it
        process = AsyncMock()
        process.wait.return_value = 1
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            os.chdir(folder)
            try:
                with patch("function.schedule.asyncio.create_subprocess_exec", AsyncMock(return_value=process)) as start:
                    self.assertEqual(await func_schedule_script_start(client_postgres=pool, script="nightly", module="script_extend.nightly"), 1)
            finally: os.chdir(cwd)
        self.assertEqual(start.call_args.args[1:], ("-m", "script_extend.nightly"))
        self.assertEqual(start.call_args.kwargs["env"]["ATOM_SCRIPT_STARTED_BY"], "schedule")
        query, *values = pool.execute.call_args.args
        self.assertIn("INSERT INTO script_run", query)
        self.assertIn("exited with code 1 without recording its run", values[2])

    async def test_a_run_another_process_holds_is_not_recorded(self):
        pool = AsyncMock()
        pool.fetchval.side_effect = ["2026-11-11 02:00"]
        process = AsyncMock()
        process.wait.return_value = 75
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            os.chdir(folder)
            try:
                with patch("function.schedule.asyncio.create_subprocess_exec", AsyncMock(return_value=process)):
                    self.assertEqual(await func_schedule_script_start(client_postgres=pool, script="nightly", module="script_extend.nightly"), 75)
            finally: os.chdir(cwd)
        pool.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
