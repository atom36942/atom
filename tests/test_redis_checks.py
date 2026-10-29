"""User checks and rate limits in redis mode, against a real Redis (set ATOM_TEST_REDIS_URL, e.g. redis://localhost:6379/15)."""
import asyncio
import datetime
import os
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from function.clients import func_client_redis
from function.middleware import func_middleware_check_ratelimiter
from function.middleware import func_middleware_check_role
from function.middleware import func_middleware_check_user_deactivated
from function.middleware import func_middleware_check_user_deleted

REDIS_URL = os.environ.get("ATOM_TEST_REDIS_URL")
USER_ID = 990001


def pool_returning(row):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[row])
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool


@unittest.skipUnless(REDIS_URL, "set ATOM_TEST_REDIS_URL to run Redis tests")
class RedisCheckTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.redis = func_client_redis(url=REDIS_URL)
        self.keys = [f"cache:user:{name}:{USER_ID}" for name in ("role", "active", "deleted_at")] + [f"ratelimiter:/test/rate:{USER_ID}"]
        await self.redis.delete(*self.keys)

    async def asyncTearDown(self):
        await self.redis.delete(*self.keys)
        await self.redis.aclose()

    async def status_check(self, check, key, row):
        cache = "cache_users_deactivated" if "deactivated" in key else "cache_users_deleted"
        return await check(user_dict={"id": USER_ID}, client_postgres=pool_returning(row), client_redis=self.redis, config_redis_cache_ttl_sec=60, **{key: {"mode": "redis"}, cache: {}})

    async def test_active_user_passes_on_cache_miss_and_hit(self):
        for check, key in ((func_middleware_check_user_deactivated, "user_check_deactivated"), (func_middleware_check_user_deleted, "user_check_deleted")):
            with self.subTest(check=key):
                for _ in range(2): await self.status_check(check, key, {"deactivated_at": None, "deleted_at": None})

    async def test_deactivated_or_deleted_user_is_blocked_on_cache_miss_and_hit(self):
        when = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        for check, key in ((func_middleware_check_user_deactivated, "user_check_deactivated"), (func_middleware_check_user_deleted, "user_check_deleted")):
            with self.subTest(check=key):
                await self.redis.delete(*self.keys)
                for _ in range(2):
                    with self.assertRaises(Exception) as caught: await self.status_check(check, key, {"deactivated_at": when, "deleted_at": when})
                    self.assertEqual(caught.exception.status_code, 403)

    async def test_role_is_read_back_from_cache_and_null_role_is_403(self):
        role_check = lambda row: func_middleware_check_role(user_dict={"id": USER_ID}, user_check_role={"mode": "redis", "roles": [2]}, client_postgres=pool_returning(row), client_redis=self.redis, cache_users_role={}, config_redis_cache_ttl_sec=60)
        for _ in range(2): await role_check({"role": 2})
        await self.redis.delete(*self.keys)
        for _ in range(2):
            with self.assertRaises(Exception) as caught: await role_check({"role": None})
            self.assertEqual(caught.exception.status_code, 403)

    async def rate(self, limit=3, window=60):
        await func_middleware_check_ratelimiter(client_redis=self.redis, rate_limit={"mode": "redis", "limit": limit, "window_sec": window}, url_path="/test/rate", identifier=str(USER_ID), cache_ratelimiter={})

    async def test_rate_limit_allows_limit_then_429_and_sets_window(self):
        for _ in range(3): await self.rate()
        with self.assertRaises(Exception) as caught: await self.rate()
        self.assertEqual(caught.exception.status_code, 429)
        self.assertTrue(0 < await self.redis.ttl(self.keys[-1]) <= 60)

    async def test_rate_limit_key_without_expiry_gets_one(self):
        await self.redis.set(self.keys[-1], 1)    # left without a TTL, as the old read-then-increment could do
        await self.rate()
        self.assertTrue(0 < await self.redis.ttl(self.keys[-1]) <= 60)

    async def test_concurrent_requests_never_exceed_the_limit(self):
        results = await asyncio.gather(*(self.rate(limit=5) for _ in range(20)), return_exceptions=True)
        self.assertEqual(sum(1 for r in results if r is None), 5)


if __name__ == "__main__":
    unittest.main()
