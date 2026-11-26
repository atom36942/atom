"""Vector search building blocks: the vector value check, the hnsw index rule, the <=> filter and the extension rule (no database)."""
import asyncio
import io
import unittest
from contextlib import redirect_stdout

from function import func_postgres_schema_config_validate
from function import func_postgres_schema_extensions_init
from function import func_postgres_vector_text
from function import func_postgres_where_build

ID = {"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True}
SCHEMA = {"doc": {"id": {"datatype": "bigint"}, "title": {"datatype": "text"}, "embedding": {"datatype": "vector(3)"}}}


def where(filters):
    return asyncio.run(func_postgres_where_build(client_postgres=None, client_password_hasher=None, cache_postgres_schema=SCHEMA, table="doc", filter=filters))


class VectorValueTests(unittest.TestCase):
    def test_lists_and_text_become_pgvector_text(self):
        self.assertEqual(func_postgres_vector_text(value=[1, 0.5, -2]), "[1.0,0.5,-2.0]")
        self.assertEqual(func_postgres_vector_text(value="[1, 0.5, -2]", datatype="vector(3)"), "[1.0,0.5,-2.0]")

    def test_refused(self):
        for value in ([], ["a"], [True], [float("nan")], "hello", {"a": 1}, None):
            with self.subTest(value=value), self.assertRaisesRegex(Exception, "list of numbers"): func_postgres_vector_text(value=value)
        with self.assertRaisesRegex(Exception, "has 2 numbers, the column vector\\(3\\) takes 3"): func_postgres_vector_text(value=[1, 2], datatype="vector(3)")


class VectorSchemaTests(unittest.TestCase):
    def test_a_vector_column_takes_only_an_hnsw_index(self):
        column = {"name": "embedding", "datatype": "vector(3)", "index": "hnsw(embedding)"}
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"doc": [ID, column]}})
        for bad in ({**column, "index": "btree(embedding)"}, {"name": "title", "datatype": "text", "index": "hnsw(title)"}):
            with self.subTest(bad=bad), self.assertRaisesRegex(Exception, "hnsw"): func_postgres_schema_config_validate(config_postgres_schema={"table": {"doc": [ID, bad]}})

    def test_every_extension_is_optional(self):
        class Conn:
            def __init__(self): self.executed = []
            async def fetch(self, sql, names): return [("pg_trgm", None), ("vector", None), ("btree_gin", "1.3")]
            async def execute(self, sql):
                self.executed.append(sql)
                if "vector" in sql: raise Exception('extension "vector" is not allow-listed for users')
        conn, out = Conn(), io.StringIO()
        with redirect_stdout(out): asyncio.run(func_postgres_schema_extensions_init(conn=conn, extensions=["postgis", "pg_trgm", "vector", "btree_gin"]))
        self.assertEqual(conn.executed, ['CREATE EXTENSION IF NOT EXISTS "pg_trgm";', 'CREATE EXTENSION IF NOT EXISTS "vector";'], "installed ones left alone")
        self.assertIn("postgis", out.getvalue())
        self.assertIn("not on this server", out.getvalue())
        self.assertIn("not allow-listed", out.getvalue())


class VectorFilterTests(unittest.TestCase):
    def test_the_filter_keeps_rows_with_a_vector(self):
        self.assertEqual(where(["embedding <=> [1,0,0]"]), ('WHERE "embedding" IS NOT NULL', []))
        self.assertEqual(where(["embedding is null"]), ('WHERE "embedding" IS NULL', []))

    def test_refused(self):
        for bad, message in ((["embedding = [1,0,0]"], "invalid operator"), (["embedding <=> [1,0]"], "takes 3"), (["embedding <=> words"], "list of numbers"), (["title <=> [1,0,0]"], "invalid operator")):
            with self.subTest(bad=bad), self.assertRaisesRegex(Exception, message): where(bad)


if __name__ == "__main__":
    unittest.main()
