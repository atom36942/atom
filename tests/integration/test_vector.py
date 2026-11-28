"""Vector search (pgvector) end to end: the extension installed from config_postgres_schema_master, a vector column with its hnsw index, writes from lists, the <=> filter with order by distance and cursor paging, the column returned only when named, export, and the clear error when the extension is missing.

Same real-app boot as test_http.py (support.app_start), against a throwaway database; skipped where the Postgres server has no pgvector.
"""
import asyncio
import functools
import json
import unittest

import asyncpg

from function.postgres_schema import func_postgres_schema_types_check

from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres

DOC = [{"name": "id", "datatype": "bigint", "is_primary_key": True, "identity": "always"}, {"name": "created_by_id", "datatype": "bigint"}, {"name": "title", "datatype": "text"}, {"name": "embedding", "datatype": "vector(3)", "index": ["hnsw(embedding)"]}]
DOCS = [("north", [0, 1, 0]), ("north-east", [0.7, 0.7, 0]), ("east", [1, 0, 0]), ("south", [0, -1, 0]), ("up", [0, 0, 1]), ("empty", None)]


@requires_postgres
class VectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        if not fetch(cls.url, "SELECT 1 AS ok FROM pg_available_extensions WHERE name = 'vector'"):
            drop_database(cls.db_name)
            raise unittest.SkipTest("pgvector is not on this Postgres server")
        cls.handle = app_start(env={"config_postgres_url_master": cls.url})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        state = cls.app.state
        cls.call = lambda fn, **kwargs: cls.client.portal.call(functools.partial(fn, **kwargs))
        cls.call(state.func_postgres_schema_tables_init, app_state=state, client_postgres=state.client_postgres_dict["master"], tables={"doc": {"column": DOC}})
        state.cache_postgres_table_rule["master"]["doc"] = {"private_read_blocked": []}    # the table the test adds, in the schema like a project table
        state.cache_postgres_schema_dict["master"] = cls.call(state.func_postgres_schema_read, client_postgres=state.client_postgres_dict["master"])
        for path in ("/admin/object-create", "/admin/object-read", "/admin/object-read-export"): state.config_api[path]["rate_limit"] = None
        cls.admin = {"Authorization": "Bearer " + app_login(cls.client, path="/auth/login-username-password", body={"username": "admin", "password": "root-test-password"})}
        response = cls.client.post("/admin/object-create", params={"table": "doc"}, json={"obj_list": [{"title": title, "embedding": vector} for title, vector in DOCS]}, headers=cls.admin)
        assert response.status_code == 200, response.text

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    def read(self, status=200, **params):
        query = {"table": "doc", **{k: json.dumps(v) if isinstance(v, list) else v for k, v in params.items()}}
        response = self.client.get("/admin/object-read", params=query, headers=self.admin)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    def nearest(self, vector, **params):
        return [row["title"] for row in self.read(filter=[f"embedding <=> {json.dumps(vector)}"], order="embedding", **params)["obj_list"]]

    def test_the_extension_column_and_index_are_there(self):
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM pg_extension WHERE extname = 'vector'"), [{"n": 1}], "installed at startup from config_postgres_schema_master extension")
        [index] = fetch(self.url, "SELECT indexdef FROM pg_indexes WHERE tablename = 'doc' AND indexname = 'idx_doc_embedding_hnsw'")
        self.assertIn("hnsw (embedding vector_cosine_ops)", index["indexdef"])

    def test_nearest_first_rows_without_a_vector_left_out(self):
        self.assertEqual(self.nearest([0.1, 0.9, 0]), ["north", "north-east", "east", "up", "south"])
        self.assertEqual(self.nearest([1, 0, 0], limit=2), ["east", "north-east"])
        titles = [row["title"] for row in self.read(filter=["embedding <=> [0,0,1]", "title != up"], order="embedding", limit=1)["obj_list"]]
        self.assertNotEqual(titles, ["up"], "other filters work alongside it")

    def test_paged_after_a_cursor(self):
        ranked = self.nearest([0.1, 0.9, 0])
        rest, after = [], None
        while True:
            page = self.read(filter=["embedding <=> [0.1,0.9,0]"], order="embedding", limit=2, **({"after": after} if after else {}))
            rest += [row["title"] for row in page["obj_list"]]
            after = page["after"]
            if not after: break
        self.assertEqual(rest, ranked, "page by page, the same order, every row once")

    def test_returned_only_when_named_as_a_list(self):
        self.assertTrue(all("embedding" not in row for row in self.read()["obj_list"]))
        [row] = self.read(filter=["title = east"], column="title,embedding")["obj_list"]
        self.assertEqual(row["embedding"], [1.0, 0.0, 0.0])
        [row] = self.read(filter=["embedding <=> [1,0,0]"], order="embedding", column="title,embedding", limit=1)["obj_list"]
        self.assertEqual(row, {"title": "east", "embedding": [1.0, 0.0, 0.0]}, "the distance stays out of the row")
        self.assertEqual([row["title"] for row in self.read(filter=["embedding is null"])["obj_list"]], ["empty"], "rows still to fill")
        response = self.client.get("/admin/object-read-export", params={"table": "doc"}, headers=self.admin)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("embedding", response.content.decode().splitlines()[0].split(","))

    def test_refusals(self):
        self.assertIn("needs its vector", self.read(400, order="embedding"))
        self.assertIn("list of numbers", self.read(400, filter=["embedding <=> hello"], order="embedding"))
        self.assertIn("invalid operator", self.read(400, filter=["embedding = [1,0,0]"]))
        self.assertIn("the vector has 2 numbers, the column vector(3) takes 3", self.read(400, filter=["embedding <=> [1,0]"], order="embedding"))
        response = self.client.post("/admin/object-create", params={"table": "doc"}, json={"obj_list": [{"title": "bad", "embedding": ["a"]}]}, headers=self.admin)
        self.assertEqual(response.status_code, 400, response.text)

    def test_a_vector_column_without_the_extension_names_it(self):
        db_name, url = create_database()
        async def run():
            conn = await asyncpg.connect(url)
            try: await func_postgres_schema_types_check(conn=conn, tables={"doc": DOC})
            finally: await conn.close()
        try:
            with self.assertRaisesRegex(Exception, "doc.embedding is a vector column: it needs the PostgreSQL extension vector"): asyncio.run(run())
        finally: drop_database(db_name)


if __name__ == "__main__":
    unittest.main()
