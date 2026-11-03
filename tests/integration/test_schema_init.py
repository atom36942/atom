"""func_postgres_schema_init on a real database: a second start changes nothing, hand-made changes to managed triggers are repaired, and a failed init leaves the database as it was."""
import asyncio
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import asyncpg
import asyncpg.connection

import function
from function import func_postgres_schema_init
from tests.integration.support import config_postgres
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import requires_postgres

PASSWORD_HASH = "$argon2id$v=19$m=1024,t=1,p=1$c2FsdHNhbHQ$aGFzaGhhc2hoYXNoaGFzaA"
CHANGES = re.compile(r"\b(CREATE TABLE|ALTER TABLE|CREATE INDEX|DROP INDEX|CREATE TRIGGER|DROP TRIGGER|ANALYZE)\b")


@requires_postgres
class SchemaInitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db_name, self.url = await asyncio.to_thread(create_database)
        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=2)

    async def asyncTearDown(self):
        await self.pool.close()
        await asyncio.to_thread(drop_database, self.db_name)

    async def init(self, app_state=None):
        app_state = app_state or SimpleNamespace(**{name: getattr(function, name) for name in function.__all__})
        return await func_postgres_schema_init(app_state=app_state, client_postgres=self.pool, config_postgres=config_postgres(), root_user_password_hash=PASSWORD_HASH)

    async def recorded_init(self):
        statements = []
        originals = {name: getattr(asyncpg.connection.Connection, name) for name in ("execute", "fetch", "fetchval", "fetchrow")}
        def recorder(original):
            async def run(conn, query, *args, **kwargs):
                statements.append(str(query))
                return await original(conn, query, *args, **kwargs)
            return run
        with patch.multiple(asyncpg.connection.Connection, **{name: recorder(original) for name, original in originals.items()}):
            await self.init()
        return statements

    async def triggers(self):
        return {(r[0], r[1]): r[2] for r in await self.pool.fetch("SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid WHERE NOT t.tgisinternal")}

    async def test_a_second_start_reads_but_changes_nothing(self):
        first = await self.recorded_init()
        self.assertTrue([s for s in first if CHANGES.search(s)], "the first start creates the schema")
        trigger_ids = await self.pool.fetch("SELECT oid, tgname FROM pg_trigger WHERE NOT tgisinternal ORDER BY oid")
        second = await self.recorded_init()
        self.assertEqual([s[:80] for s in second if CHANGES.search(s) and not s.startswith("DO $$")], [], "no table, index or trigger is touched when nothing changed (the DO blocks only drop obsolete objects)")
        self.assertLessEqual(len(second), 25, f"{len(second)} statements on an unchanged start")
        self.assertEqual(await self.pool.fetch("SELECT oid, tgname FROM pg_trigger WHERE NOT tgisinternal ORDER BY oid"), trigger_ids, "no trigger was recreated (same oids)")

    async def test_a_guard_removed_or_changed_by_hand_is_put_back(self):
        await self.init()
        triggers = await self.triggers()
        await self.pool.execute("DROP TRIGGER trigger_delete_disable_users ON users")
        await self.pool.execute("DROP TRIGGER trigger_delete_disable_bulk_users ON users; CREATE TRIGGER trigger_delete_disable_bulk_users AFTER DELETE ON users REFERENCING OLD TABLE AS deleted_rows FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_bulk('100000')")
        await self.init()
        self.assertEqual(await self.triggers(), triggers)
        with self.assertRaisesRegex(asyncpg.RaiseError, "operation not allowed on users"):
            await self.pool.execute("DELETE FROM users WHERE id = 1")

    async def test_a_failed_init_leaves_tables_and_triggers_as_they_were(self):
        await self.init()
        triggers = await self.triggers()
        await self.pool.execute("DROP TRIGGER trigger_updated_at_set_test ON test; ALTER TABLE test DROP COLUMN description")
        app_state = SimpleNamespace(**{name: getattr(function, name) for name in function.__all__})
        async def failing_cleanup(**kwargs): raise RuntimeError("cleanup failed")
        app_state.func_postgres_schema_cleanup = failing_cleanup
        with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
            await self.init(app_state)
        self.assertNotIn(("test", "trigger_updated_at_set_test"), await self.triggers(), "nothing from the failed run is kept")
        self.assertIsNone(await self.pool.fetchval("SELECT 1 FROM information_schema.columns WHERE table_name = 'test' AND column_name = 'description'"))
        await self.init()
        self.assertEqual(await self.triggers(), triggers)


if __name__ == "__main__":
    unittest.main()
