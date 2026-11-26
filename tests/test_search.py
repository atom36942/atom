"""Full-text search building blocks: generated column rules, the search language read from the column, and the @@ filter's SQL (no database)."""
import asyncio
import unittest

from function import func_postgres_schema_config_validate
from function import func_postgres_search_language
from function import func_postgres_where_build

ID = {"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True}
SEARCH = {"datatype": "tsvector", "default": "(setweight(to_tsvector('english'::regconfig, COALESCE(title, ''::text)), 'A'::\"char\"))"}
SCHEMA = {"note": {"id": {"datatype": "bigint"}, "title": {"datatype": "text"}, "search": SEARCH}}


def where(filters):
    return asyncio.run(func_postgres_where_build(client_postgres=None, client_password_hasher=None, cache_postgres_schema=SCHEMA, table="note", filter=filters))


class GeneratedColumnTests(unittest.TestCase):
    def test_a_generated_column_takes_no_value_rules(self):
        column = {"name": "search", "datatype": "tsvector", "generated": "to_tsvector('simple', title)", "index": "gin(search)"}
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"note": [ID, {"name": "title", "datatype": "text"}, column]}})
        for key, value in (("default", "''"), ("is_mandatory", True), ("unique", "search")):
            with self.subTest(key=key), self.assertRaisesRegex(Exception, "is generated"):
                func_postgres_schema_config_validate(config_postgres_schema={"table": {"note": [ID, {**column, key: value}]}})
        with self.assertRaisesRegex(Exception, "SQL expression"): func_postgres_schema_config_validate(config_postgres_schema={"table": {"note": [ID, {**column, "generated": " "}]}})


class SearchFilterTests(unittest.TestCase):
    def test_language_comes_from_the_column(self):
        self.assertEqual(func_postgres_search_language(column=SEARCH), "english")
        self.assertEqual(func_postgres_search_language(column={"default": None}), "simple")

    def test_the_words_are_bound_as_typed(self):
        sql, values = where(['search @@ "printer stopped" or scanner -toner'])
        self.assertEqual(sql, """WHERE "search" @@ websearch_to_tsquery('english', $1)""")
        self.assertEqual(values, ['"printer stopped" or scanner -toner'], "quotes and a search's own or stay in it")

    def test_with_other_filters_and_only_words(self):
        sql, values = where(["search @@ printer", "id > 5"])
        self.assertIn("@@ websearch_to_tsquery('english', $1)", sql)
        self.assertEqual(values[0], "printer")
        with self.assertRaisesRegex(Exception, "invalid operator"): where(["search = printer"])
        with self.assertRaisesRegex(Exception, "invalid operator"): where(["title @@ printer"])


if __name__ == "__main__":
    unittest.main()
