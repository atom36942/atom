"""Schema changes at startup are safe on a busy database: the plan shows what startup would change without changing it, flags what locks or rewrites a table, and a table another session holds makes startup stop within config_postgres_schema_lock_timeout_sec instead of hanging."""
import asyncio
import contextlib
import copy
import io
import time
import unittest
from types import SimpleNamespace

import asyncpg

import function
from function import func_postgres_schema_init
from function import func_postgres_schema_plan
from script.schema_plan import plan_print
from tests.integration.support import config_postgres
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import requires_postgres

PASSWORD_HASH = "$argon2id$v=19$m=1024,t=1,p=1$c2FsdHNhbHQ$aGFzaGhhc2hoYXNoaGFzaA"


def title_as_varchar(config):
    changed = copy.deepcopy(config)
    next(col for col in changed["table"]["test"] if col["name"] == "title")["datatype"] = "varchar(500)"
    return changed


@requires_postgres
class SchemaPlanTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db_name, self.url = await asyncio.to_thread(create_database)
        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=3)
        self.app_state = SimpleNamespace(**{name: getattr(function, name) for name in function.__all__})
        self.config = config_postgres()
        await func_postgres_schema_init(app_state=self.app_state, client_postgres=self.pool, config_postgres=self.config, root_user_password_hash=PASSWORD_HASH)

    async def asyncTearDown(self):
        await self.pool.close()
        await asyncio.to_thread(drop_database, self.db_name)

    async def title_type(self):
        return await self.pool.fetchval("SELECT data_type FROM information_schema.columns WHERE table_name = 'test' AND column_name = 'title'")

    async def test_an_unchanged_config_plans_no_changes(self):
        plan = await func_postgres_schema_plan(app_state=self.app_state, client_postgres=self.pool, config_postgres=self.config)
        self.assertEqual([step["sql"] for step in plan if not step["is_routine"]], [])
        self.assertTrue(plan, "the statements every start runs are still listed, as routine")

    async def test_a_type_change_is_flagged_and_nothing_is_changed(self):
        plan = await func_postgres_schema_plan(app_state=self.app_state, client_postgres=self.pool, config_postgres=title_as_varchar(self.config))
        flagged = [step for step in plan if step["risk"]]
        self.assertEqual([(step["table"], step["risk"]) for step in flagged], [("test", "rewrites the table, which stays locked until it finishes")])
        self.assertIn("ALTER COLUMN \"title\" TYPE varchar(500)", flagged[0]["sql"])
        self.assertEqual(await self.title_type(), "text", "planning changes nothing")
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed): plan_print(plan=plan)
        self.assertTrue(printed.getvalue().startswith("!! rewrites the table, which stays locked until it finishes (test: about 0 rows)"), printed.getvalue())
        self.assertIn("2 changes, 1 flagged", printed.getvalue(), "the type change and the ANALYZE after it")

    async def test_a_busy_table_stops_startup_within_the_lock_timeout(self):
        holder = await asyncpg.connect(self.url)
        try:
            await holder.execute("BEGIN; LOCK TABLE test IN ACCESS SHARE MODE")    # another session reading the table in a long transaction
            started = time.perf_counter()
            with self.assertRaisesRegex(Exception, r"schema init: a table stayed locked by other sessions for over 1 s .*nothing was changed"):
                await func_postgres_schema_init(app_state=self.app_state, client_postgres=self.pool, config_postgres=title_as_varchar(self.config), root_user_password_hash=PASSWORD_HASH, lock_timeout_sec=1)
            self.assertLess(time.perf_counter() - started, 5)
        finally: await holder.close()
        self.assertEqual(await self.title_type(), "text", "the whole change was rolled back")
        await func_postgres_schema_init(app_state=self.app_state, client_postgres=self.pool, config_postgres=title_as_varchar(self.config), root_user_password_hash=PASSWORD_HASH, lock_timeout_sec=1)
        self.assertEqual(await self.title_type(), "character varying", "once the table is free, the same start goes through")


if __name__ == "__main__":
    unittest.main()
