"""The monitor's Redis view lists every configured Redis by name, read-only: where it is (never the password), memory, keys, hit ratio and a ping; an unreachable one shows its error and none configured gives an empty list."""
import asyncio
import unittest

from function.monitor import func_monitor_redis
from tests.support import service_setting

REDIS_URL = service_setting("ATOM_TEST_REDIS_URL")


class FakeRedis:
    def __init__(self, info=None, error=None): self.info_dict, self.error = info or {}, error
    async def ping(self):
        if self.error: raise self.error
        return True
    async def info(self): return self.info_dict
    async def dbsize(self): return 3


class MonitorRedisTests(unittest.TestCase):
    def test_none_configured_is_an_empty_list(self):
        self.assertEqual(asyncio.run(func_monitor_redis(client_redis_dict={}, url_dict={"unused": ""})), {"connections": []})

    def test_one_row_per_name_with_its_numbers_and_no_password(self):
        info = {"redis_version": "7.4.3", "used_memory": 1000, "used_memory_peak": 2000, "maxmemory": 0, "maxmemory_policy": "noeviction", "keyspace_hits": 3, "keyspace_misses": 1, "connected_clients": 2}
        clients = {"api_response": FakeRedis(info=info), "queue": FakeRedis(error=ConnectionError("refused"))}
        urls = {"api_response": "rediss://:secret@cache.example.net:10000/0", "queue": "redis://localhost:6379/1"}
        rows = {row["name"]: row for row in asyncio.run(func_monitor_redis(client_redis_dict=clients, url_dict=urls))["connections"]}
        cache = rows["api_response"]
        self.assertEqual((cache["status"], cache["host"], cache["port"], cache["db"], cache["is_tls"]), ("ok", "cache.example.net", 10000, "0", True))
        self.assertEqual((cache["keys"], cache["hit_ratio_pct"], cache["max_memory_bytes"], cache["used_memory_bytes"]), (3, 75.0, None, 1000), "maxmemory 0 means no limit reported")
        self.assertNotIn("secret", str(rows))
        self.assertEqual((rows["queue"]["status"], rows["queue"]["error"]), ("error", "refused"))

    @unittest.skipUnless(REDIS_URL, "set ATOM_TEST_REDIS_URL to run Redis tests")
    def test_a_real_redis_answers(self):
        import redis.asyncio as redis
        async def run():
            client = redis.Redis.from_url(REDIS_URL)
            try: return await func_monitor_redis(client_redis_dict={"test": client}, url_dict={"test": REDIS_URL})
            finally: await client.aclose()
        row = asyncio.run(run())["connections"][0]
        self.assertEqual(row["status"], "ok")
        self.assertIsNotNone(row["used_memory_bytes"])
        self.assertGreaterEqual(row["ping_ms"], 0)


if __name__ == "__main__":
    unittest.main()
