"""Apps sharing one Redis keep their keys apart: every cache, user-state and rate-limit key starts with the app's master database name, with nothing to set."""
import asyncio
import unittest

from function.clients import func_client_redis
from function.clients import func_redis_key
from function.clients import func_redis_key_prefix
from function.middleware import func_middleware_api_cache
from function.middleware import func_middleware_check_ratelimiter


class FakeRedis:
    def __init__(self, prefix): self.atom_key_prefix, self.keys = prefix, []
    async def get(self, key): self.keys.append(key)
    async def setex(self, key, ttl, value): self.keys.append(key)
    async def eval(self, script, count, key, window): self.keys.append(key); return 1


class RedisKeyPrefixTests(unittest.TestCase):
    def test_prefix_is_the_master_database_name(self):
        self.assertEqual(func_redis_key_prefix(postgres_url="postgresql://u:p@pg.example.com:5432/shop?sslmode=require"), "shop:")
        for url in (None, "", "postgresql://u:p@host", "not a url"):
            with self.subTest(url=url): self.assertEqual(func_redis_key_prefix(postgres_url=url), "")

    def test_client_carries_the_prefix_and_none_adds_nothing(self):
        client = func_client_redis(url="redis://localhost:6379/0", key_prefix="crm:")
        self.assertEqual(func_redis_key(client_redis=client, key="cache:api:/x"), "crm:cache:api:/x")
        self.assertEqual(func_redis_key(client_redis=None, key="cache:api:/x"), "cache:api:/x")
        self.assertIsNone(func_client_redis(url="", key_prefix="crm:"))

    def test_api_cache_and_rate_limit_keys_start_with_the_prefix(self):
        redis = FakeRedis("shop:")
        asyncio.run(func_middleware_api_cache(mode="get", path="/my/task-list", query_params={"page": "1"}, cache={"mode": "redis", "ttl_sec": 60, "is_per_user": True}, client_redis=redis, user_id=5))
        asyncio.run(func_middleware_check_ratelimiter(client_redis=redis, rate_limit={"mode": "redis", "limit": 10, "window_sec": 60}, url_path="/my/task-list", identifier="5", cache_ratelimiter={}))
        self.assertEqual(redis.keys, ["shop:cache:api:/my/task-list?page=1:5", "shop:ratelimiter:/my/task-list:5"])

    def test_inmemory_modes_are_unprefixed(self):
        store = {}
        asyncio.run(func_middleware_check_ratelimiter(client_redis=FakeRedis("shop:"), rate_limit={"mode": "inmemory", "limit": 10, "window_sec": 60}, url_path="/x", identifier="5", cache_ratelimiter=store))
        self.assertEqual(list(store), ["ratelimiter:/x:5"])


if __name__ == "__main__":
    unittest.main()
