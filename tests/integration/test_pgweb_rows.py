"""pgweb reads a table in one round trip: the table list remembers each key, opening a table reads columns and rows at the same time, and an out-of-date key never shows the wrong page."""
import asyncio
import unittest

import asyncpg

from function.pgweb import PGWEB_CUT_PREVIEW
from function.pgweb import func_pgweb_row
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

    def test_like_and_ilike_search_any_column_type_as_text(self):
        for sql in ("CREATE TABLE item (id bigserial PRIMARY KEY, name varchar(20), tags text[], data jsonb)", """INSERT INTO item (name, tags, data) VALUES ('Apple', '{red}', '{"k": 1}'), ('pear', '{green}', '{}')"""): fetch(self.url, sql)
        async def run(pool):
            return [[r[0] for r in (await func_pgweb_rows(pool=pool, table="item", pk="id", filter_col=col, filter_op=op, filter_value=value))["rows"]] for col, op, value in (("name", "ILIKE", "%APP%"), ("tags", "ILIKE", "%RE%"), ("data", "LIKE", '%"k"%'), ("id", "LIKE", "2"))]
        self.assertEqual(self.run_on_pool(run), [[1], [1, 2], [1], [2]])

    def test_an_out_of_date_key_is_read_again_with_the_real_one(self):
        for sql in ("CREATE TABLE item (id bigserial PRIMARY KEY, code text UNIQUE)", "INSERT INTO item (code) VALUES ('b'), ('a'), ('c')"): fetch(self.url, sql)
        async def run(pool):
            stale = {"item": {"pk": "code", "latest_first": False, "types": {"code": "integer"}}}    # the key and a type changed since the list was read
            return await func_pgweb_rows(pool=pool, table="item", limit=10, is_meta=True, filter_col="code", filter_op="<>", filter_value="z", cache_table=stale), stale
        page, cache = self.run_on_pool(run)
        self.assertEqual(([r[0] for r in page["rows"]], page["meta"]["pk"]), ([3, 2, 1], "id"))
        self.assertEqual(cache["item"], {"pk": "id", "latest_first": True, "types": {"id": "bigint", "code": "text"}})

    def test_a_very_large_value_comes_as_a_preview_and_its_row_reads_whole(self):
        big = "x" * 40000
        for sql in ("CREATE TABLE doc (id bigserial PRIMARY KEY, body text, data jsonb, n integer)",
                    "INSERT INTO doc (body, data, n) VALUES ('short', '{\"a\": 1}', 1), (repeat('x', 40000), (SELECT jsonb_agg(md5(g::text)) FROM generate_series(1, 3000) g), 2)"): fetch(self.url, sql)
        async def run(pool):
            cache = {}
            await func_pgweb_schema(pool=pool, cache_table=cache)
            first = await func_pgweb_rows(pool=pool, table="doc", limit=10, is_meta=True, cache_table=cache)    # types not known yet: cut after reading
            again = await func_pgweb_rows(pool=pool, table="doc", pk="id", is_desc=True, limit=10, cache_table=cache)    # types known: cut in SQL
            whole = await func_pgweb_row(pool=pool, table="doc", pk="id", pk_value=2, cache_table=cache)
            return first, again, whole
        first, again, whole = self.run_on_pool(run)
        for page in (first, again):
            self.assertEqual(page["cols"], ["id", "body", "data", "n"])
            self.assertEqual(page["cut"], [[0, 1], [0, 2]])    # newest first: the large row is row 0
            self.assertEqual((page["rows"][0][1], page["rows"][0][3]), (big[:PGWEB_CUT_PREVIEW], 2))
            self.assertTrue(page["rows"][0][2].startswith('["'))
            self.assertEqual(page["rows"][1][1:], ["short", '{"a": 1}', 1])    # small values unchanged (jsonb as its text, as asyncpg reads it)
        self.assertEqual((whole["rows"][0][1], whole["rows"][0][2].count(",") + 1), (big, 3000))

    def test_any_table_name_opens(self):
        fetch(self.url, 'CREATE TABLE "Order Items" ("Id" bigserial PRIMARY KEY, "say ""hi""" text)')
        fetch(self.url, 'INSERT INTO "Order Items" ("say ""hi""") VALUES (\'a\'), (\'b\')')
        async def run(pool):
            cache = {}
            await func_pgweb_schema(pool=pool, cache_table=cache)
            page = await func_pgweb_rows(pool=pool, table="Order Items", limit=10, is_meta=True, cache_table=cache)
            filtered = await func_pgweb_rows(pool=pool, table="Order Items", pk="Id", limit=10, filter_col='say "hi"', filter_op="=", filter_value="b", cache_table=cache)
            return page, filtered
        page, filtered = self.run_on_pool(run)
        self.assertEqual((page["meta"]["pk"], [r[1] for r in page["rows"]]), ("Id", ["a", "b"]))
        self.assertEqual([r[1] for r in filtered["rows"]], ["b"])


if __name__ == "__main__":
    unittest.main()
