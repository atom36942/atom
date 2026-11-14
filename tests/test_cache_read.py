"""func_postgres_cache_read: the startup caches load at most their config_cache_row_limit_* rows; 0 skips the query."""
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from function import func_postgres_cache_read


def pool_returning(rows_by_table):
    conn = MagicMock()
    async def fetch(sql, limit):
        table = "config" if "FROM config" in sql else sql.split("SELECT ")[1].split(" FROM")[0]
        return rows_by_table.get(table, [])[:limit]
    conn.fetch = AsyncMock(side_effect=fetch)
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


LIMITS = dict(config_cache_row_limit_config=1000, config_cache_row_limit_users_role=2, config_cache_row_limit_users_deactivated=0, config_cache_row_limit_users_deleted=10)


class CacheReadTests(unittest.IsolatedAsyncioTestCase):
    async def test_limits_rows_and_zero_skips(self):
        pool, conn = pool_returning({"config": [("theme", '{"a": 1}')], "id, role": [(1, 1), (2, 2), (3, 2)], "id, deleted_at": [(1, None)]})
        caches = await func_postgres_cache_read(client_postgres=pool, is_config_table=True, **LIMITS)
        self.assertEqual(caches["cache_config"], {"theme": {"a": 1}}, "config values are JSON")
        self.assertEqual(caches["cache_users_role"], {1: 1, 2: 2}, "at most the row limit")
        self.assertEqual(caches["cache_users_deactivated"], {}, "0 = not loaded")
        self.assertEqual(caches["cache_users_deleted"], {1: None})
        self.assertEqual(conn.fetch.await_count, 3, "no query for a cache that is off")
        self.assertTrue(all(call.args[1] in (1000, 2, 10) for call in conn.fetch.await_args_list), "the limit is a bound parameter")

    async def test_no_config_table_or_no_database(self):
        pool, conn = pool_returning({})
        caches = await func_postgres_cache_read(client_postgres=pool, is_config_table=False, **LIMITS)
        self.assertEqual(caches["cache_config"], {})
        self.assertFalse(any("FROM config" in call.args[0] for call in conn.fetch.await_args_list))
        self.assertEqual(await func_postgres_cache_read(client_postgres=None, is_config_table=True, **LIMITS), {"cache_config": {}, "cache_users_role": {}, "cache_users_deactivated": {}, "cache_users_deleted": {}})
