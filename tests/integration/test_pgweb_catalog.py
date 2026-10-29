"""pgweb Database info counts and catalogs against a real throwaway PostgreSQL database."""
import asyncio
import unittest

import asyncpg

from function.pgweb import func_pgweb_catalog
from function.pgweb import func_pgweb_info
from function.pgweb import func_pgweb_tree
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres


@requires_postgres
class PgwebCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        fetch(cls.url, "CREATE EXTENSION IF NOT EXISTS pg_trgm")
        fetch(cls.url, "CREATE TABLE parent (id bigserial PRIMARY KEY, name text UNIQUE)")
        fetch(cls.url, "CREATE TABLE child (id int PRIMARY KEY, parent_id bigint REFERENCES parent(id), note text)")
        fetch(cls.url, "CREATE VIEW child_view AS SELECT * FROM child")
        fetch(cls.url, "CREATE MATERIALIZED VIEW parent_mv AS SELECT * FROM parent")
        fetch(cls.url, "CREATE POLICY parent_all ON parent USING (true)")
        fetch(cls.url, "CREATE FUNCTION touch() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN NEW; END$$")
        fetch(cls.url, "CREATE TRIGGER child_touch BEFORE UPDATE ON child FOR EACH ROW EXECUTE FUNCTION touch()")
        fetch(cls.url, "CREATE PROCEDURE noop() LANGUAGE sql AS $$SELECT 1$$")

    @classmethod
    def tearDownClass(cls):
        drop_database(cls.db_name)

    def run_on_pool(self, coroutine_factory):
        async def run():
            pool = await asyncpg.create_pool(self.url, min_size=1, max_size=2)
            try: return await coroutine_factory(pool)
            finally: await pool.close()
        return asyncio.run(run())

    def test_info_counts_own_objects_and_extension_objects_apart(self):
        info = self.run_on_pool(lambda pool: func_pgweb_info(pool=pool, connection_url="postgresql://u:***@h/db"))
        self.assertEqual({key: info[key] for key in ("tables", "views", "materialized_views", "primary_keys", "foreign_keys", "unique_constraints", "policies", "functions", "procedures", "triggers")},
                         {"tables": 2, "views": 1, "materialized_views": 1, "primary_keys": 2, "foreign_keys": 1, "unique_constraints": 1, "policies": 1, "functions": 1, "procedures": 1, "triggers": 1})
        self.assertEqual(info["columns"], 5)
        self.assertGreater(info["internal_triggers"], 0)    # the foreign key's own triggers
        self.assertGreater(info["extension_routines"], 0)    # pg_trgm's functions, not counted in functions
        self.assertEqual((info["connection_url"], info["schema_scope"]), ("postgresql://u:***@h/db", "public"))

    def test_catalog_columns_come_from_the_query(self):
        tables = self.run_on_pool(lambda pool: func_pgweb_catalog(pool=pool, kind="tables"))
        self.assertEqual(tables["columns"], ["schema", "name", "type", "owner", "columns", "indexes", "constraints", "triggers", "policies", "size", "estimated_rows"])
        self.assertEqual([row["name"] for row in tables["rows"]], ["child", "parent"])
        views = self.run_on_pool(lambda pool: func_pgweb_catalog(pool=pool, kind="views"))    # no table-only counts for views
        self.assertEqual(views["columns"], ["schema", "name", "type", "owner", "size", "estimated_rows"])
        self.assertEqual([row["name"] for row in views["rows"]], ["child_view"])

    def test_extension_objects_are_kept_out_of_own_catalogs(self):
        functions = self.run_on_pool(lambda pool: func_pgweb_catalog(pool=pool, kind="functions"))
        self.assertEqual([row["name"] for row in functions["rows"]], ["touch"])
        routines = self.run_on_pool(lambda pool: func_pgweb_catalog(pool=pool, kind="extension_routines"))
        self.assertEqual({row["extension"] for row in routines["rows"]}, {"pg_trgm"})
        tree = self.run_on_pool(lambda pool: func_pgweb_tree(pool=pool))
        self.assertEqual(tree["public"], {"table": [{"name": "child"}, {"name": "parent"}], "view": [{"name": "child_view"}], "materialized_view": [{"name": "parent_mv"}]})

    def test_unknown_catalog_is_refused(self):
        with self.assertRaisesRegex(Exception, "invalid catalog"): self.run_on_pool(lambda pool: func_pgweb_catalog(pool=pool, kind="nope"))


if __name__ == "__main__":
    unittest.main()
