"""pgweb query runner and CSV download against a real throwaway PostgreSQL database: SQL that reads rows runs wrapped (no cursor, so parallel workers), the rest as typed; read-only mode on the read-only pool and on a plain one."""
import asyncio
import io
import json
import unittest

from function.clients import func_client_postgres
from function.pgweb import func_pgweb_query
from function.pgweb import func_pgweb_select_body
from function.pgweb import func_pgweb_stream
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres


class PgwebSelectBodyTests(unittest.TestCase):
    def test_reads_rows_or_not(self):
        self.assertEqual(func_pgweb_select_body(" select 1 ;; "), "select 1")
        self.assertEqual(func_pgweb_select_body("-- note\n/* x */ (SELECT 1) UNION (SELECT 2)"), "-- note\n/* x */ (SELECT 1) UNION (SELECT 2)")
        for sql in ("WITH a AS (SELECT 1) SELECT * FROM a", "VALUES (1)", "TABLE item", "select\n1"): self.assertIsNotNone(func_pgweb_select_body(sql), sql)
        for sql in ("UPDATE item SET n = 1", "EXPLAIN SELECT 1", "SHOW search_path", "tablex", "selected", ""): self.assertIsNone(func_pgweb_select_body(sql), sql)


@requires_postgres
class PgwebQueryTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        fetch(cls.url, "CREATE TABLE item (id bigserial PRIMARY KEY, title text, tags text[], ok boolean, data jsonb)")
        fetch(cls.url, "INSERT INTO item (title, tags, ok, data) SELECT 'row ' || g, ARRAY['a', 'b c'], g % 2 = 0, jsonb_build_object('g', g) FROM generate_series(1, 10005) g")
        fetch(cls.url, "INSERT INTO item (title) VALUES ('')")

    @classmethod
    def tearDownClass(cls):
        drop_database(cls.db_name)

    async def asyncSetUp(self):
        self.pool = await func_client_postgres(dsn=self.url, min_size=1, max_size=2)
        self.pool_read = await func_client_postgres(dsn=self.url, min_size=1, max_size=1, is_read_only=True)

    async def asyncTearDown(self):
        await self.pool.close()
        await self.pool_read.close()

    async def query(self, sql, pool=None, **kwargs):
        return await func_pgweb_query(pool=pool or self.pool, sql=sql, is_confirmed=True, **kwargs)

    async def csv(self, sql, pool=None, **kwargs):
        return b"".join([chunk async for chunk in await func_pgweb_stream(pool=pool or self.pool, sql=sql, is_confirmed=True, **kwargs)]).decode()

    async def test_reads_rows_with_their_limit_and_keeps_names_and_order(self):
        out = await self.query("select id, title from item order by id desc;")
        self.assertEqual((len(out["rows"]), out["truncated"], out["rows"][0][0]), (10000, True, 10006))
        self.assertEqual(await self.query("select 1 as a, 2 as a -- trailing comment"), {"cols": ["a", "a"], "rows": [[1, 2]], "truncated": False, "limit": None})
        self.assertEqual((await self.query("values (1, 'x')"))["rows"], [[1, "x"]])

    async def test_sql_that_cannot_be_wrapped_runs_as_typed(self):
        self.assertEqual((await self.query("SELECT 7 AS n INTO copied"))["rows"], [["SELECT 1"]])
        self.assertEqual(await asyncio.to_thread(fetch, self.url, "SELECT n FROM copied"), [{"n": 7}])
        out = await self.query("WITH moved AS (UPDATE copied SET n = 8 RETURNING n) SELECT n FROM moved")
        self.assertEqual(out["rows"], [[8]])
        self.assertEqual((await self.query("SELECT 1; SELECT 2"))["cols"], ["status"])
        self.assertEqual((await self.query("INSERT INTO copied VALUES (9) RETURNING n"))["rows"], [[9]])
        self.assertEqual((await self.query("SHOW standard_conforming_strings"))["rows"], [["on"]])
        with self.assertRaisesRegex(Exception, "syntax error"): await self.query("select from where")

    async def test_read_only_refuses_writes_on_both_pools(self):
        self.assertTrue(self.pool_read.atom_read_only)
        self.assertFalse(self.pool.atom_read_only)
        for pool in (self.pool, self.pool_read):
            self.assertEqual((await self.query("select count(*) from item", pool=pool, is_read_only=True))["rows"], [[10006]])
            for sql in ("INSERT INTO item (title) VALUES ('x')", "WITH x AS (DELETE FROM item WHERE id < 0 RETURNING id) SELECT * FROM x", "SELECT 1 INTO nope"):
                with self.assertRaisesRegex(Exception, "read-only transaction"): await self.query(sql, pool=pool, is_read_only=True)
            with self.assertRaisesRegex(Exception, "read-only transaction"): await self.csv("INSERT INTO item (title) VALUES ('x') RETURNING id", pool=pool, is_read_only=True)

    async def test_the_read_only_pool_stays_read_only_after_a_script_changes_its_default(self):
        await self.query("SET default_transaction_read_only = off", pool=self.pool_read)
        with self.assertRaisesRegex(Exception, "read-only transaction"): await self.query("INSERT INTO item (title) VALUES ('x')", pool=self.pool_read, is_read_only=True)

    async def test_csv_comes_from_copy_for_rows_and_from_a_cursor_otherwise(self):
        text = await self.csv("select id, title, tags, ok, data from item where id in (1, 10006) order by id;")
        self.assertEqual(text, 'id,title,tags,ok,data\n1,row 1,"{a,""b c""}",f,"{""g"": 1}"\n10006,"",,,\n')
        self.assertEqual(len((await self.csv("select id from item", pool=self.pool_read, is_read_only=True)).splitlines()), 10007)
        self.assertEqual(await self.csv("SHOW standard_conforming_strings"), "standard_conforming_strings\r\non\r\n")
        with self.assertRaisesRegex(Exception, "one row-returning statement"): await self.csv("select 1; select 2")
        with self.assertRaisesRegex(Exception, "does not exist"): await self.csv("select * from missing")

    async def test_a_result_stops_at_the_row_or_size_limit(self):
        import function.pgweb as pgweb
        out = await self.query("select id, title from item order by id")
        self.assertEqual((len(out["rows"]), out["truncated"], out["limit"]), (10000, True, "rows"))
        small = await self.query("select id from item where id <= 3 order by id")
        self.assertEqual((small["truncated"], small["limit"]), (False, None))
        original = pgweb.PGWEB_RESULT_MAX_BYTES
        pgweb.PGWEB_RESULT_MAX_BYTES = 2000    # about 100 small rows
        try: capped = await self.query("select id, title from item order by id")
        finally: pgweb.PGWEB_RESULT_MAX_BYTES = original
        self.assertEqual((capped["truncated"], capped["limit"]), (True, "size"))
        self.assertTrue(0 < len(capped["rows"]) < 200)

    async def test_sql_dumps_load_back_with_the_same_rows_and_json_lines_hold_every_row(self):
        await asyncio.to_thread(fetch, self.url, "CREATE TABLE odd (id int, note text, code char(3), bits bit(4), raw bytea, tags text[])")
        await asyncio.to_thread(fetch, self.url, "INSERT INTO odd SELECT g, CASE g % 3 WHEN 0 THEN E'two\\nlines \\\\ ''q'' \"d\"\\ttab' WHEN 1 THEN '' END, CASE WHEN g % 2 = 0 THEN 'US' ELSE 'USD' END, B'1010', '\\x00ff'::bytea, ARRAY['a', NULL, 'b c'] FROM generate_series(1, 1201) g")
        same = "SELECT md5(string_agg(x::text, '|' ORDER BY id)) AS h FROM {} x"
        insert = await self.csv("select * from odd", file_format="insert", table_name="odd_insert")
        self.assertIn('CREATE TABLE "odd_insert" (\n    "id" integer,\n    "note" text,\n    "code" bpchar,\n    "bits" bit varying', insert)
        async with self.pool.acquire() as conn: await conn.execute(insert)
        dump = await self.csv("select * from odd", file_format="copy", table_name="public.odd_copy")
        script, data = dump.split(' FROM stdin;\n')
        self.assertTrue(data.endswith("\\.\n"))
        async with self.pool.acquire() as conn:
            await conn.execute(script.rsplit("\nCOPY ", 1)[0])
            await conn.copy_to_table("odd_copy", source=io.BytesIO(data[:-3].encode()), format="text")
        hashes = [(await asyncio.to_thread(fetch, self.url, same.format(name)))[0]["h"] for name in ("odd", "odd_insert", "odd_copy")]
        self.assertEqual(len(set(hashes)), 1, hashes)
        no_create = await self.csv("select 1 as a, 2 as a", file_format="copy", is_create=False)
        self.assertNotIn("CREATE TABLE", no_create)
        self.assertIn('COPY "query_result" ("a", "a_2") FROM stdin;\n1\t2\n\\.\n', no_create)
        lines = (await self.csv("select id, note from odd order by id", file_format="jsonl")).splitlines()
        self.assertEqual((len(lines), json.loads(lines[2])), (1201, {"id": 3, "note": "two\nlines \\ 'q' \"d\"\ttab"}))
        with self.assertRaisesRegex(Exception, "need SQL that reads rows"): await self.csv("show search_path", file_format="copy")
        with self.assertRaisesRegex(Exception, "unknown file format"): await self.csv("select 1", file_format="xml")
