"""Pools skip asyncpg's reset query on release (one round trip less per request); SQL someone typed (query runners, pgweb) still leaves nothing behind for the next request on that connection."""
import asyncio
import unittest
from unittest.mock import patch

import asyncpg.connection

from function import func_client_postgres
from function import func_pgweb_query
from function import func_postgres_query_runner_read
from function import func_postgres_query_runner_write
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import requires_postgres


@requires_postgres
class PoolSessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db_name, self.url = await asyncio.to_thread(create_database)
        self.pool = await func_client_postgres(dsn=self.url, min_size=1, max_size=1)    # one connection: the next request always gets the same session

    async def asyncTearDown(self):
        await self.pool.close()
        await asyncio.to_thread(drop_database, self.db_name)

    async def session(self):
        async with self.pool.acquire() as conn:
            return dict(await conn.fetchrow("SELECT current_setting('search_path') AS search_path, current_setting('statement_timeout') AS statement_timeout, current_setting('application_name') AS application_name, (SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid()) AS advisory_locks, pg_backend_pid() AS pid"))

    async def test_a_normal_request_sends_no_reset_query(self):
        sent = []
        original = asyncpg.connection.Connection.execute
        async def spy(conn, query, *args, **kwargs):
            sent.append(query)
            return await original(conn, query, *args, **kwargs)
        with patch.object(asyncpg.connection.Connection, "execute", spy):
            async with self.pool.acquire() as conn: await conn.fetchval("SELECT 1")
        self.assertEqual([q for q in sent if "RESET ALL" in q], [])

    async def test_typed_sql_leaves_no_session_state_behind(self):
        clean = await self.session()
        await func_postgres_query_runner_write(client_postgres=self.pool, sql="SET search_path TO pg_catalog")
        await func_postgres_query_runner_write(client_postgres=self.pool, sql="DO $$ BEGIN PERFORM pg_advisory_lock(42); END $$")
        await func_postgres_query_runner_read(client_postgres=self.pool, config_query_runner_read_limit=10, sql="SELECT set_config('application_name', 'leaked', false)")
        await func_pgweb_query(pool=self.pool, sql="SET statement_timeout = '1ms'", is_confirmed=True)
        after = await self.session()
        self.assertEqual(after["pid"], clean["pid"], "the same connection was reused")
        self.assertEqual({k: after[k] for k in after if k != "pid"}, {k: clean[k] for k in clean if k != "pid"})

    async def test_an_open_transaction_is_rolled_back_on_release(self):
        asyncio.get_running_loop().set_exception_handler(lambda loop, context: None)    # asyncpg warns about the open transaction it rolls back, which is the case under test
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE TABLE tx_check (id int)")
            await conn.execute("BEGIN")
            await conn.execute("INSERT INTO tx_check VALUES (1)")
        async with self.pool.acquire() as conn:
            self.assertFalse(conn.is_in_transaction())
            self.assertEqual(await conn.fetchval("SELECT count(*) FROM tx_check"), 0)


if __name__ == "__main__":
    unittest.main()
