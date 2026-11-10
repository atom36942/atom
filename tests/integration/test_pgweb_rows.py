"""pgweb reads a table in one round trip: the table list remembers each key, opening a table reads columns and rows at the same time, and an out-of-date key never shows the wrong page."""
import asyncio
import unittest

import asyncpg

from function.pgweb import func_pgweb_rows
from function.pgweb import func_pgweb_schema
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres


@requires_postgres
class PgwebRowsTests(unittest.TestCase):
    def setUp(self):
        self.db_name, self.url = create_database()
        self.addCleanup(drop_database, self.db_name)

    def run_on_pool(self, coroutine_factory):
        async def run():
            pool = await asyncpg.create_pool(self.url, min_size=2, max_size=4)
            try: return await coroutine_factory(pool)
            finally: await pool.close()
        return asyncio.run(run())

    def test_an_empty_database_still_names_itself(self):
        schema = self.run_on_pool(lambda pool: func_pgweb_schema(pool=pool))
        self.assertEqual((schema["tree"], schema["database"]), ({}, self.db_name))
        self.assertTrue(schema["version"].startswith("PostgreSQL"))

    def test_the_table_list_remembers_keys_and_a_table_opens_newest_first(self):
        for sql in ("CREATE TABLE item (id bigserial PRIMARY KEY, n integer)", "INSERT INTO item (n) SELECT generate_series(1, 5)", "CREATE TABLE tag (code text PRIMARY KEY)", "CREATE VIEW item_view AS SELECT * FROM item"): fetch(self.url, sql)
        async def run(pool):
            cache = {}
            await func_pgweb_schema(pool=pool, cache_table=cache)
            keys = dict(cache)
            first = await func_pgweb_rows(pool=pool, table="item", limit=2, is_meta=True, cache_table=cache)
            following = await func_pgweb_rows(pool=pool, table="item", pk="id", is_desc=True, limit=2, after=first["after"], cache_table=cache)
            filtered = await func_pgweb_rows(pool=pool, table="item", pk="id", limit=10, filter_col="n", filter_op=">", filter_value="3", cache_table=cache)
            return keys, cache, first, following, filtered
        keys, cache, first, following, filtered = self.run_on_pool(run)
        self.assertEqual(keys, {"item": {"pk": "id", "latest_first": True}, "tag": {"pk": "code", "latest_first": False}, "item_view": {"pk": None, "latest_first": False}})
        self.assertEqual(cache["item"]["types"], {"id": "bigint", "n": "integer"})
        self.assertEqual(([r[0] for r in first["rows"]], first["meta"]["pk"], first["after"]), ([5, 4], "id", '["4"]'))
        self.assertEqual(([r[0] for r in following["rows"]], following["after"]), ([3, 2], '["2"]'))
        self.assertEqual([r[1] for r in filtered["rows"]], [4, 5])

    def test_an_out_of_date_key_is_read_again_with_the_real_one(self):
        for sql in ("CREATE TABLE item (id bigserial PRIMARY KEY, code text UNIQUE)", "INSERT INTO item (code) VALUES ('b'), ('a'), ('c')"): fetch(self.url, sql)
        async def run(pool):
            stale = {"item": {"pk": "code", "latest_first": False, "types": {"code": "integer"}}}    # the key and a type changed since the list was read
            return await func_pgweb_rows(pool=pool, table="item", limit=10, is_meta=True, filter_col="code", filter_op="<>", filter_value="z", cache_table=stale), stale
        page, cache = self.run_on_pool(run)
        self.assertEqual(([r[0] for r in page["rows"]], page["meta"]["pk"]), ([3, 2, 1], "id"))
        self.assertEqual(cache["item"], {"pk": "id", "latest_first": True, "types": {"id": "bigint", "code": "text"}})


if __name__ == "__main__":
    unittest.main()
