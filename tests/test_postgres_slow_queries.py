"""Slow-query report from pg_stat_statements, with a mocked database."""
import unittest
from decimal import Decimal

import asyncpg

from function import func_postgres_slow_queries_read
from function import func_postgres_slow_queries_reset
from tests.support import database


class SlowQueriesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pool, self.conn = database()

    async def test_missing_extension_returns_help_without_querying_stats(self):
        self.conn.fetchval.return_value = None
        res = await func_postgres_slow_queries_read(client_postgres=self.pool, limit=5, order="total_time")
        self.assertEqual((res["is_enabled"], res["query_list"]), (False, []))
        self.assertIn("shared_preload_libraries", res["help"])
        self.conn.fetch.assert_not_awaited()

    async def test_extension_created_but_not_preloaded_returns_help(self):
        self.conn.fetchval.side_effect = [1, asyncpg.ObjectNotInPrerequisiteStateError("must be loaded via shared_preload_libraries")]
        res = await func_postgres_slow_queries_read(client_postgres=self.pool, limit=5, order="total_time")
        self.assertFalse(res["is_enabled"])

    async def test_rows_are_ordered_by_whitelisted_column_with_share_of_all_time(self):
        self.conn.fetchval.side_effect = [1, "2026-10-14", 200.0]
        self.conn.fetch.return_value = [{"calls": 3, "total_ms": Decimal("50.00"), "mean_ms": Decimal("16.667"), "max_ms": Decimal("20.00"), "rows": 3, "shared_blks_hit": 9, "shared_blks_read": 0, "query": "SELECT $1"}]
        res = await func_postgres_slow_queries_read(client_postgres=self.pool, limit=5, order="mean_time")
        sql, limit = self.conn.fetch.await_args.args
        self.assertIn("ORDER BY mean_exec_time DESC LIMIT $1", sql)
        self.assertEqual(limit, 5)
        self.assertEqual(res["query_list"][0], {"calls": 3, "total_ms": 50.0, "mean_ms": 16.667, "max_ms": 20.0, "rows": 3, "shared_blks_hit": 9, "shared_blks_read": 0, "query": "SELECT $1", "share_pct": 25.0})

    async def test_order_outside_whitelist_never_reaches_sql(self):
        with self.assertRaisesRegex(Exception, "invalid order"):
            await func_postgres_slow_queries_read(client_postgres=self.pool, limit=5, order="calls; DROP TABLE users")
        self.conn.fetch.assert_not_awaited()

    async def test_reset_clears_only_the_current_database(self):
        self.conn.fetchval.return_value = 1
        self.assertEqual(await func_postgres_slow_queries_reset(client_postgres=self.pool), "reset")
        self.assertIn("current_database()", self.conn.execute.await_args.args[0])
        self.conn.fetchval.return_value = None
        with self.assertRaisesRegex(Exception, "not enabled"):
            await func_postgres_slow_queries_reset(client_postgres=self.pool)


if __name__ == "__main__":
    unittest.main()
