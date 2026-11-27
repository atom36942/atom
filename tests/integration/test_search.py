"""Full-text search end to end on Atom's test table, given a search column here: the generated search column, the @@ filter, ranking with cursor paging, the column never returned, export, and the column rebuilt when its expression changes.

Same real-app boot as test_http.py (support.app_start), against a throwaway database.
"""
import copy
import functools
import json
import unittest

from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres

ROWS = [
    ("Printer stopped working", "Pune warehouse, since the update"),
    ("Login fails", "The printer page shows an error"),
    ("Toner empty", "Printer not working"),
    ("Scanner offline", "Mumbai office"),
    ("Pune: the printer works only on Wi-Fi", None),
]

SEARCH_ON_TEST = """from config import config_postgres_schema_master as base_config_postgres_schema_master
config_postgres_schema_master = {**base_config_postgres_schema_master, "table": {**base_config_postgres_schema_master["table"], "test": {**base_config_postgres_schema_master["table"]["test"], "column": [*base_config_postgres_schema_master["table"]["test"]["column"], {"name": "search", "datatype": "tsvector", "generated": "setweight(to_tsvector('english', coalesce(title, '')), 'A') || setweight(to_tsvector('english', coalesce(description, '')), 'B')", "index": "gin(search)"}]}}}
"""    # a project's searchable table: test gets a weighted search column (title A, description B), read through /admin/object-read (root holds its id)


@requires_postgres
class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.handle = app_start(env={"config_postgres_url_master": cls.url}, config_extend=SEARCH_ON_TEST)
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        for path in ("/admin/object-read", "/admin/object-read-export"): cls.app.state.config_api[path]["rate_limit"] = None
        cls.admin = {"Authorization": "Bearer " + app_login(cls.client, path="/auth/login-username-password", body={"username": "admin", "password": "root-test-password"})}
        cls.ids = [fetch(cls.url, "INSERT INTO test (title, description) VALUES ($1, $2) RETURNING id", title, description)[0]["id"] for title, description in ROWS]

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    def read(self, status=200, **params):
        query = {"table": "test", **{k: json.dumps(v) if isinstance(v, list) else v for k, v in params.items()}}
        response = self.client.get("/admin/object-read", params=query, headers=self.admin)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    def found(self, words, **params):
        return [row["id"] for row in self.read(filter=[f"search @@ {words}"], **params)["obj_list"]]

    def test_the_column_is_generated_with_its_index(self):
        [column] = fetch(self.url, "SELECT attgenerated, col_description(attrelid, attnum) AS comment FROM pg_attribute WHERE attrelid = 'test'::regclass AND attname = 'search'")
        self.assertEqual(column["attgenerated"], b"s")
        self.assertTrue(column["comment"].startswith("atom generated "))
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM pg_indexes WHERE tablename = 'test' AND indexname = 'idx_test_search_gin'"), [{"n": 1}])

    def test_words_in_any_order_word_forms_and_excluded_words(self):
        printer_work = {self.ids[0], self.ids[2], self.ids[4]}
        self.assertEqual(set(self.found("printer working")), printer_work, "works and working are one word")
        self.assertEqual(set(self.found("working printer")), printer_work)
        self.assertEqual(set(self.found("printer working -toner")), printer_work - {self.ids[2]})
        self.assertEqual(set(self.found("scanner or toner")), {self.ids[2], self.ids[3]}, "a search's own or")
        self.assertEqual(set(self.found('"printer stopped"')), {self.ids[0]}, "a phrase")
        self.assertEqual(self.found("nothing-like-this"), [])

    def test_ranked_best_first_and_paged_after_a_cursor(self):
        ranked = [row["id"] for row in self.read(filter=["search @@ printer working"], order="search desc")["obj_list"]]
        self.assertEqual((set(ranked[:2]), ranked[2]), ({self.ids[0], self.ids[4]}, self.ids[2]), "both words in the title rank above both in the description")
        first = self.read(filter=["search @@ printer working"], order="search desc", limit=1)
        self.assertNotIn("search", first["obj_list"][0])
        rest = [row["id"] for row in first["obj_list"]]
        after = first["after"]
        while after:
            page = self.read(filter=["search @@ printer working"], order="search desc", limit=1, after=after)
            rest += [row["id"] for row in page["obj_list"]]
            after = page["after"]
        self.assertEqual(rest, ranked, "page by page, the same order, every match once")
        self.assertIn("needs its search", self.read(400, order="search desc"))

    def test_the_column_is_never_returned_and_takes_only_words(self):
        self.assertTrue(all("search" not in row for row in self.read()["obj_list"]))
        self.assertIn("for search only", self.read(400, column="id,search"))
        self.assertIn("invalid operator", self.read(400, filter=["search = printer"]))
        response = self.client.get("/admin/object-read-export", params={"table": "test", "filter": json.dumps(["search @@ scanner"])}, headers=self.admin)
        self.assertEqual(response.status_code, 200, response.text)
        header, *rows = [line for line in response.content.decode().splitlines() if line]
        self.assertNotIn("search", header.split(","))
        self.assertEqual(len(rows), 1)

    def test_a_changed_expression_rebuilds_the_column_and_an_unchanged_one_changes_nothing(self):
        state = self.app.state
        plan = lambda config: self.client.portal.call(functools.partial(state.func_postgres_schema_plan, app_state=state, client_postgres=state.client_postgres_dict["master"], config_postgres_schema=config))
        self.assertEqual([step["sql"] for step in plan(state.config_postgres_schema_master) if not step["is_routine"]], [], "nothing to change")
        changed = copy.deepcopy(state.config_postgres_schema_master)
        column = next(c for c in changed["table"]["test"]["column"] if c["name"] == "search")
        column["generated"] = "to_tsvector('simple', coalesce(title, ''))"
        sql = [step["sql"] for step in plan(changed)]
        self.assertTrue(any('DROP COLUMN "search"' in s for s in sql) and any("GENERATED ALWAYS AS (to_tsvector('simple'" in s for s in sql), sql)


if __name__ == "__main__":
    unittest.main()
