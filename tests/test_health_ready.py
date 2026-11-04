"""/health-ready: every configured database answers within the timeout, checked at the same time; a slow or failing one is named, with no host or error text."""
import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from function.app import func_app_health_ready


def state(**clients):
    return SimpleNamespace(**{f"client_{kind}_dict": clients.get(kind, {}) for kind in ("postgres", "redis", "mssql", "clickhouse")})


class HealthReadyTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_database_is_checked(self):
        cursor = MagicMock(execute=AsyncMock())
        conn = MagicMock(cursor=MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=cursor), __aexit__=AsyncMock(return_value=False))))
        mssql = MagicMock(acquire=MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock(return_value=False))))
        app_state = state(postgres={"master": MagicMock(fetchval=AsyncMock(return_value=1)), "reports": None}, redis={"queue": MagicMock(ping=AsyncMock(return_value=True))}, mssql={"erp": mssql}, clickhouse={"master": MagicMock(query=AsyncMock())})
        checks = await func_app_health_ready(app_state=app_state)
        self.assertEqual(sorted(checks), ["clickhouse.master", "mssql.erp", "postgres.master", "redis.queue"], "a database without a pool is not checked")
        self.assertTrue(all(check["is_ok"] for check in checks.values()))
        cursor.execute.assert_awaited_once_with("SELECT 1")

    async def test_a_slow_or_failing_database_is_named_without_its_error(self):
        async def hang(*args): await asyncio.sleep(10)
        app_state = state(postgres={"master": MagicMock(fetchval=AsyncMock(return_value=1)), "reports": MagicMock(fetchval=AsyncMock(side_effect=hang))}, redis={"cache": MagicMock(ping=AsyncMock(side_effect=ConnectionError("redis.internal:6379 refused")))})
        started = time.perf_counter()
        checks = await func_app_health_ready(app_state=app_state, timeout_sec=0.2)
        self.assertLess(time.perf_counter() - started, 1, "checked at the same time, each within the timeout")
        self.assertEqual({name: check["is_ok"] for name, check in checks.items()}, {"postgres.master": True, "postgres.reports": False, "redis.cache": False})
        self.assertNotIn("refused", str(checks))


if __name__ == "__main__":
    unittest.main()
