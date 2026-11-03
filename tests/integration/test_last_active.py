"""last_active_at is written at most once per 5 minutes, and recording it never changes updated_at, which marks real edits only."""
import asyncio
import unittest
from types import SimpleNamespace

import asyncpg

import function
from function import func_postgres_schema_init
from function import func_user_last_active_update
from tests.integration.support import config_postgres
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import requires_postgres

PASSWORD_HASH = "$argon2id$v=19$m=1024,t=1,p=1$c2FsdHNhbHQ$aGFzaGhhc2hoYXNoaGFzaA"


@requires_postgres
class LastActiveTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db_name, self.url = await asyncio.to_thread(create_database)
        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=2)
        app_state = SimpleNamespace(**{name: getattr(function, name) for name in function.__all__})
        await func_postgres_schema_init(app_state=app_state, client_postgres=self.pool, config_postgres=config_postgres(), root_user_password_hash=PASSWORD_HASH)
        await self.pool.execute("UPDATE users SET updated_at = '2026-01-01', last_active_at = NULL WHERE id = 1")    # what the trigger keeps is checked against this

    async def asyncTearDown(self):
        await self.pool.close()
        await asyncio.to_thread(drop_database, self.db_name)

    async def row(self):
        return dict(await self.pool.fetchrow("SELECT xmin::text AS version, updated_at, last_active_at FROM users WHERE id = 1"))

    async def test_activity_is_written_once_per_interval_and_never_moves_updated_at(self):
        before = await self.row()
        await func_user_last_active_update(client_postgres=self.pool, user_id=1)
        first = await self.row()
        self.assertIsNotNone(first["last_active_at"])
        self.assertEqual(first["updated_at"], before["updated_at"], "recording activity is not an edit")
        await func_user_last_active_update(client_postgres=self.pool, user_id=1)
        self.assertEqual(await self.row(), first, "within 5 minutes nothing is written: same row version")
        await self.pool.execute("UPDATE users SET last_active_at = now() - interval '6 minutes' WHERE id = 1")
        await func_user_last_active_update(client_postgres=self.pool, user_id=1)
        later = await self.row()
        self.assertGreater(later["last_active_at"], first["last_active_at"])
        self.assertEqual(later["updated_at"], before["updated_at"])

    async def test_a_real_edit_still_moves_updated_at(self):
        before = await self.row()
        await self.pool.execute("UPDATE users SET username = 'admin-renamed', last_active_at = now() WHERE id = 1")
        self.assertGreater((await self.row())["updated_at"], before["updated_at"])

    async def test_tables_without_activity_keep_the_plain_trigger(self):
        definition = await self.pool.fetchval("SELECT pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname = 'trigger_updated_at_set_test'")
        self.assertTrue(definition.endswith("func_set_updated_at()"), definition)


if __name__ == "__main__":
    unittest.main()
