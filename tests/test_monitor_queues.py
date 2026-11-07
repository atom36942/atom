"""The monitor's queue view counts Redis jobs per channel (waiting, running, failed, consumer) for Atom's channels and any channel a consumer has used, without reading payloads."""
import asyncio
import secrets
import unittest

from function.monitor import func_monitor_queues
from tests.support import service_setting

REDIS_URL = service_setting("ATOM_TEST_REDIS_URL")


@unittest.skipUnless(REDIS_URL, "set ATOM_TEST_REDIS_URL to run Redis tests")
class MonitorQueuesTests(unittest.TestCase):
    def test_counts_per_channel_including_one_found_by_its_keys(self):
        import redis.asyncio as redis
        atom, project = f"atom_test_{secrets.token_hex(4)}", f"atom_test_project_{secrets.token_hex(4)}"
        async def run():
            client = redis.Redis.from_url(REDIS_URL)
            keys = [atom, f"{atom}_processing", f"{atom}_failed", f"{project}_failed", f"{project}_consumer"]
            try:
                await client.lpush(atom, b"1", b"2")
                await client.lpush(f"{atom}_processing", b"3")
                await client.lpush(f"{project}_failed", b"4")
                await client.set(f"{project}_consumer", b"token")
                return await func_monitor_queues(client_redis=client, channels=[atom])
            finally:
                await client.delete(*keys)
                await client.aclose()
        report = asyncio.run(run())
        rows = {row["channel"]: row for row in report["channels"]}
        self.assertTrue(report["is_enabled"])
        self.assertEqual(rows[atom], {"channel": atom, "waiting": 2, "running": 1, "failed": 0, "is_consumer": False})
        self.assertEqual(rows[project], {"channel": project, "waiting": 0, "running": 0, "failed": 1, "is_consumer": True}, "a project's channel is found by its keys")

    def test_without_a_queue_redis_it_is_off(self):
        self.assertEqual(asyncio.run(func_monitor_queues(client_redis=None, channels=["x"])), {"is_enabled": False, "channels": []})


if __name__ == "__main__":
    unittest.main()
