"""pgweb cell editing against a real throwaway PostgreSQL database."""
import asyncio
import unittest

import asyncpg

from function.pgweb import func_pgweb_delete_row
from function.pgweb import func_pgweb_insert_row
from function.pgweb import func_pgweb_query
from function.pgweb import func_pgweb_rows
from function.pgweb import func_pgweb_update_cell
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres


@requires_postgres
class PgwebEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        fetch(cls.url, """CREATE TABLE item (id bigserial PRIMARY KEY, title text, n integer, doubled integer GENERATED ALWAYS AS (n * 2) STORED,
                                            tags text[], data jsonb, rating numeric(3,1), seen_at timestamptz, status integer DEFAULT 1, blob bytea)""")
        fetch(cls.url, "CREATE TABLE users (id bigserial PRIMARY KEY, password text)")
        fetch(cls.url, "INSERT INTO users (password) VALUES ('old')")
        fetch(cls.url, "INSERT INTO item (title, n, tags, data, rating, seen_at) VALUES ('first', 1, '{a}', '{\"k\": 1}', 2.5, '2026-01-02 03:04:05+00'), ('second', 2, '{b}', NULL, NULL, NULL)")
        fetch(cls.url, "CREATE TABLE nokey (title text)")
        fetch(cls.url, "CREATE VIEW item_view AS SELECT * FROM item")

    @classmethod
    def tearDownClass(cls):
        drop_database(cls.db_name)

    def run_on_pool(self, coroutine_factory):
        async def run():
            pool = await asyncpg.create_pool(self.url, min_size=1, max_size=2)
            try: return await coroutine_factory(pool)
            finally: await pool.close()
        return asyncio.run(run())

    def loaded(self, row_id):
        """The row as the Rows view received it (same JSON encoding the page sees)."""
        import orjson
        from function.pgweb import func_pgweb_orjson_dumps
        page = orjson.loads(func_pgweb_orjson_dumps(self.run_on_pool(lambda pool: func_pgweb_rows(pool=pool, table="item", limit=50))))
        return dict(zip(page["cols"], next(row for row in page["rows"] if row[0] == row_id), strict=True))

    def edit(self, **kwargs):
        return self.run_on_pool(lambda pool: func_pgweb_update_cell(pool=pool, table="item", **kwargs))

    def test_rows_reports_its_query_time(self):
        page = self.run_on_pool(lambda pool: func_pgweb_rows(pool=pool, table="item", limit=5))
        self.assertIsInstance(page["ms"], float)
        self.assertGreaterEqual(page["ms"], 0)

    def test_edit_saves_and_returns_the_updated_row(self):
        row = self.loaded(1)
        out = self.edit(column="title", pk_value=1, original=row["title"], value="renamed")
        self.assertEqual(dict(zip(out["cols"], out["rows"][0], strict=True))["title"], "renamed")
        self.assertEqual(fetch(self.url, "SELECT title FROM item WHERE id = 1"), [{"title": "renamed"}])

    def test_values_are_converted_by_postgres_and_null_is_explicit(self):
        row = self.loaded(1)
        self.edit(column="data", pk_value=1, original=row["data"], value='{"k": 2, "x": [1, 2]}')
        self.edit(column="seen_at", pk_value=1, original=row["seen_at"], value="2026-05-06 07:08:09+00")
        self.edit(column="rating", pk_value=1, original=row["rating"], value="7.5")
        self.edit(column="n", pk_value=2, original=self.loaded(2)["n"], is_null=True)
        self.assertEqual(fetch(self.url, "SELECT data::text AS data, (seen_at AT TIME ZONE 'UTC')::text AS seen_at, rating::text AS rating FROM item WHERE id = 1"), [{"data": '{"k": 2, "x": [1, 2]}', "seen_at": "2026-05-06 07:08:09", "rating": "7.5"}])
        self.assertEqual(fetch(self.url, "SELECT n FROM item WHERE id = 2"), [{"n": None}])

    def test_arrays_bytea_and_the_default_are_edited_as_text(self):
        self.edit(column="tags", pk_value=1, original=self.loaded(1)["tags"], value='{z,"a b"}')
        self.edit(column="blob", pk_value=1, original=self.loaded(1)["blob"], value="\\x0a1b")
        self.edit(column="status", pk_value=1, original=self.loaded(1)["status"], value="5")
        self.edit(column="status", pk_value=1, original=self.loaded(1)["status"], is_default=True)
        self.assertEqual(fetch(self.url, "SELECT tags, encode(blob, 'hex') AS blob, status FROM item WHERE id = 1"), [{"tags": ["z", "a b"], "blob": "0a1b", "status": 1}])

    def test_users_password_is_saved_as_an_argon2_hash(self):
        from argon2 import PasswordHasher
        hasher = PasswordHasher()
        edit = lambda **kwargs: self.run_on_pool(lambda pool: func_pgweb_update_cell(pool=pool, table="users", column="password", pk_value=1, client_password_hasher=hasher, **kwargs))
        current = lambda: fetch(self.url, "SELECT password FROM users WHERE id = 1")[0]["password"]
        edit(original=current(), value="123456")
        self.assertTrue(hasher.verify(current(), "123456"))
        with self.assertRaisesRegex(Exception, "plain password is never stored"): edit(original=current(), value="123456", is_hash=False)
        pasted = hasher.hash("other")
        edit(original=current(), value=pasted, is_hash=False)
        self.assertEqual(current(), pasted)

    def test_a_write_reports_its_status_and_explain_never_runs_a_script(self):
        query = lambda **kwargs: self.run_on_pool(lambda pool: func_pgweb_query(pool=pool, **kwargs))
        self.assertEqual(query(sql="UPDATE item SET rating = rating WHERE id < 0")["rows"], [["UPDATE 0"]])
        before = fetch(self.url, "SELECT count(*) AS n FROM item")
        with self.assertRaisesRegex(Exception, "Explain takes one statement"): query(sql="EXPLAIN SELECT 1; DELETE FROM item WHERE id > 0", is_explain=True)
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM item"), before)

    def insert(self, table="item", **kwargs):
        return self.run_on_pool(lambda pool: func_pgweb_insert_row(pool=pool, table=table, **kwargs))

    def test_insert_converts_each_type_and_leaves_the_rest_to_the_database(self):
        out = self.insert(values={"title": "made", "n": "4", "tags": '{x,"y z"}', "data": '{"k": 2}', "rating": "1.5", "blob": "\\x0a"})
        row = dict(zip(out["cols"], out["rows"][0], strict=True))
        self.assertEqual((row["title"], row["n"], row["doubled"], row["tags"], row["status"]), ("made", 4, 8, ["x", "y z"], 1))    # generated, default and id from the database
        self.assertEqual(fetch(self.url, "SELECT encode(blob, 'hex') AS blob, data FROM item WHERE id = $1", row["id"]), [{"blob": "0a", "data": '{"k": 2}'}])
        fetch(self.url, "DELETE FROM item WHERE id = $1", row["id"])

    def test_insert_refuses_generated_columns_read_only_mode_and_views(self):
        with self.assertRaisesRegex(Exception, "filled by the database"): self.insert(values={"doubled": "3"})
        with self.assertRaisesRegex(Exception, "read-only"): self.insert(values={"title": "x"}, is_read_only=True)
        with self.assertRaisesRegex(Exception, "only in tables"): self.insert(table="item_view", values={"title": "x"})
        with self.assertRaisesRegex(Exception, "unknown column"): self.insert(values={"nope": "x"})
        with self.assertRaisesRegex(Exception, "invalid input syntax"): self.insert(values={"n": "four"})

    def test_insert_hashes_users_password(self):
        from argon2 import PasswordHasher
        hasher = PasswordHasher()
        out = self.insert(table="users", values={"password": "123456"}, client_password_hasher=hasher)
        new_id = out["rows"][0][out["cols"].index("id")]
        self.assertTrue(hasher.verify(fetch(self.url, "SELECT password FROM users WHERE id = $1", new_id)[0]["password"], "123456"))
        with self.assertRaisesRegex(Exception, "plain password is never stored"): self.insert(table="users", values={"password": "123456"}, is_hash=False)
        fetch(self.url, "DELETE FROM users WHERE id = $1", new_id)

    def test_a_cell_changed_meanwhile_is_not_overwritten(self):
        row = self.loaded(2)
        fetch(self.url, "UPDATE item SET title = 'changed elsewhere' WHERE id = 2")
        with self.assertRaisesRegex(Exception, "changed since the rows were loaded"): self.edit(column="title", pk_value=2, original=row["title"], value="mine")
        self.assertEqual(fetch(self.url, "SELECT title FROM item WHERE id = 2"), [{"title": "changed elsewhere"}])

    def test_bad_value_shows_the_postgres_error_and_saves_nothing(self):
        row = self.loaded(1)
        with self.assertRaisesRegex(Exception, "invalid input syntax for type integer"): self.edit(column="n", pk_value=1, original=row["n"], value="abc")
        self.assertEqual(fetch(self.url, "SELECT n FROM item WHERE id = 1"), [{"n": row["n"]}])

    def test_refusals(self):
        cases = [
            ({"column": "title", "pk_value": 1, "value": "x", "is_read_only": True}, "read-only mode"),
            ({"column": "id", "pk_value": 1, "value": "9"}, "primary key column cannot be edited"),
            ({"column": "doubled", "pk_value": 1, "value": "9"}, "generated and identity"),
            ({"column": "nope", "pk_value": 1, "value": "x"}, "unknown column"),
            ({"column": "title", "pk_value": 999, "value": "x"}, "row not found"),
            ({"column": "title", "pk_value": 9007199254740993, "value": "x"}, "too large for the browser"),
        ]
        for kwargs, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message): self.edit(original=None, **kwargs)
        for table, message in (("nokey", "single-column primary key"), ("item_view", "only tables can be changed here")):
            with self.subTest(table=table), self.assertRaisesRegex(Exception, message):
                self.run_on_pool(lambda pool, table=table: func_pgweb_update_cell(pool=pool, table=table, column="title", pk_value=1, value="x"))


    def delete(self, **kwargs):
        return self.run_on_pool(lambda pool: func_pgweb_delete_row(pool=pool, table="item", **kwargs))

    def test_delete_removes_exactly_the_row_shown(self):
        fetch(self.url, "INSERT INTO item (id, title, n) VALUES (50, 'to delete', 5)")
        self.assertEqual(self.delete(pk_value=50, original=self.loaded(50)), {"deleted": 1})
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM item WHERE id = 50"), [{"n": 0}])
        with self.assertRaisesRegex(Exception, "already deleted"): self.delete(pk_value=50, original={"id": 50})

    def test_delete_refuses_a_row_changed_meanwhile_and_in_read_only_mode(self):
        fetch(self.url, "INSERT INTO item (id, title, n) VALUES (51, 'keep me', 5)")
        shown = self.loaded(51)
        with self.assertRaisesRegex(Exception, "read-only mode"): self.delete(pk_value=51, original=shown, is_read_only=True)
        fetch(self.url, "UPDATE item SET n = 6 WHERE id = 51")
        with self.assertRaisesRegex(Exception, "row changed since it was loaded"): self.delete(pk_value=51, original=shown)
        with self.assertRaisesRegex(Exception, "the row as shown is required"): self.delete(pk_value=51, original=None)
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM item WHERE id = 51"), [{"n": 1}])

if __name__ == "__main__":
    unittest.main()
