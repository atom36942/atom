"""func_memory_report sizes Atom's in-memory data without exposing values; func_memory_trace starts and stops allocation tracing."""
import asyncio
import tracemalloc
import unittest

from starlette.datastructures import State

from function.memory import func_memory_deep_size, func_memory_report, func_memory_trace


class MemoryTests(unittest.TestCase):
    def state(self):
        state = State()
        state.cache_api_response = {f"key{i}": {"data": b"x" * 100, "expire_at": 1} for i in range(200)}
        state.cache_users_role = {1: 1}
        state.config_token_secret_key = "secret value"
        state.func_something = len
        state.client_postgres_dict = {"master": object(), "replica": object()}
        return state

    def test_deep_size_counts_contents_once_and_stops_at_the_limit(self):
        shared = "x" * 1000
        size = lambda obj, **kw: asyncio.run(func_memory_deep_size(obj=obj, **kw))
        self.assertLess(size([shared, shared])[0], size([shared, "y" * 1000])[0])
        self.assertGreater(size({"a": [1, 2, {"b": "c" * 500}]})[0], 500)
        self.assertEqual(size([[1], [2], [3]], max_objects=2)[1], True)

    def test_report_sizes_app_state_without_values(self):
        report = asyncio.run(func_memory_report(app_state=self.state()))
        items = {item["name"]: item for item in report["app_state"]}
        self.assertEqual(items["cache_api_response"]["entries"], 200)
        self.assertGreater(items["cache_api_response"]["bytes"], 200 * 100)
        self.assertEqual(report["app_state"][0]["name"], "cache_api_response")    # biggest first
        self.assertNotIn("func_something", items)
        self.assertEqual(items["config_* (all settings)"]["entries"], 1)
        self.assertEqual(report["clients"], [{"name": "client_postgres_dict", "count": 2, "type": "dict"}])
        self.assertNotIn("secret value", str(report))
        self.assertGreater(report["process"]["rss_bytes"], 0)
        self.assertGreater(report["system"]["total_bytes"], report["system"]["available_bytes"])
        self.assertEqual(report["trace"], {"is_tracing": False})

    def test_report_lets_other_requests_run_while_it_builds(self):
        state = self.state()
        state.cache_big = {i: [i] * 5 for i in range(30000)}
        async def run():
            ticks = 0
            async def other_request():
                nonlocal ticks
                while True:
                    ticks += 1
                    await asyncio.sleep(0)
            task = asyncio.create_task(other_request())
            report = await func_memory_report(app_state=state, yield_every=1000)
            task.cancel()
            return ticks, report
        ticks, report = asyncio.run(run())
        self.assertGreater(ticks, 10)    # the other task ran many times during one report
        self.assertEqual(next(item for item in report["app_state"] if item["name"] == "cache_big")["entries"], 30000)

    def test_trace_starts_reports_and_stops(self):
        state = self.state()
        async def run():
            started = func_memory_trace(app_state=state, action="start", duration_sec=60)
            held = [bytearray(2000) for _ in range(200)]
            trace = (await func_memory_report(app_state=state))["trace"]
            stopped = func_memory_trace(app_state=state, action="stop")
            return started, trace, stopped, len(held)
        started, trace, stopped, _ = asyncio.run(run())
        self.assertTrue(started["is_tracing"])
        self.assertTrue(trace["is_tracing"])
        self.assertTrue(any(line["file"] == __file__ for line in trace["top"]))
        self.assertEqual(stopped, {"is_tracing": False, "stops_at": None})
        self.assertFalse(tracemalloc.is_tracing())
        with self.assertRaisesRegex(Exception, "invalid action"): func_memory_trace(app_state=state, action="later")


if __name__ == "__main__":
    unittest.main()
