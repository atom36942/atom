"""The role, deactivated and deleted checks share one users query per request (func_middleware_user_row_reader)."""
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from function.middleware import func_middleware_check_role
from function.middleware import func_middleware_check_user_deactivated
from function.middleware import func_middleware_check_user_deleted
from function.middleware import func_middleware_user_row_reader

USER = {"id": 7}


def pool_returning(rows):
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=rows)
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    return pool, conn


async def run_checks(pool, *, modes=("realtime", "realtime", "realtime"), roles=(2,)):
    read = func_middleware_user_row_reader(client_postgres=pool, user_dict=USER)
    shared = {"client_postgres": pool, "client_redis": None, "config_redis_cache_ttl_sec": 60, "user_row_read": read}
    await func_middleware_check_role(user_dict=USER, user_check_role={"mode": modes[0], "roles": list(roles)}, cache_users_role={}, **shared)
    await func_middleware_check_user_deleted(user_dict=USER, user_check_deleted={"mode": modes[2]}, cache_users_deleted={}, **shared)    # deleted first, as in main.py and at login
    await func_middleware_check_user_deactivated(user_dict=USER, user_check_deactivated={"mode": modes[1]}, cache_users_deactivated={}, **shared)


class UserRowReaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_three_realtime_checks_run_one_query(self):
        pool, conn = pool_returning([{"role": 2, "deactivated_at": None, "deleted_at": None}])
        await run_checks(pool)
        self.assertEqual(conn.fetch.await_count, 1)
        self.assertEqual(pool.acquire.call_count, 1)
        self.assertIn("select role, deactivated_at, deleted_at from users", conn.fetch.await_args.args[0])

    async def test_inmemory_misses_reuse_the_same_row(self):
        pool, conn = pool_returning([{"role": 2, "deactivated_at": None, "deleted_at": None}])
        await run_checks(pool, modes=("inmemory", "inmemory", "realtime"))
        self.assertEqual(conn.fetch.await_count, 1)

    async def test_token_only_checks_never_query(self):
        pool, conn = pool_returning([])
        read = func_middleware_user_row_reader(client_postgres=pool, user_dict=USER)
        await func_middleware_check_role(user_dict={"id": 7, "role": 2}, user_check_role={"mode": "token", "roles": [2]}, client_postgres=pool, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60, user_row_read=read)
        conn.fetch.assert_not_awaited()

    async def test_errors_and_their_order_stay_the_same(self):
        cases = [
            ([], "user not found", 401),
            ([{"role": 9, "deactivated_at": None, "deleted_at": None}], "access denied", 403),
            ([{"role": 2, "deactivated_at": "2026-01-01", "deleted_at": "2026-01-02"}], "account deleted", 403),
            ([{"role": 2, "deactivated_at": "2026-01-01", "deleted_at": None}], "account deactivated", 403),
        ]
        for rows, message, status in cases:
            pool, conn = pool_returning(rows)
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message) as caught:
                await run_checks(pool)
            self.assertEqual(getattr(caught.exception, "status_code", None), status)
            self.assertEqual(conn.fetch.await_count, 1)

    async def test_missing_pool_is_a_server_error(self):
        read = func_middleware_user_row_reader(client_postgres=None, user_dict=USER)
        with self.assertRaisesRegex(Exception, "postgres client missing"):
            await read()


if __name__ == "__main__":
    unittest.main()
