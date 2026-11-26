"""The analytics page stands alone (its own role 1 login and storage), only reads (rows, SQL and exports are PgWeb's) and reaches the data only through /admin/* read routes that exist and are admin only."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "static" / "analytics.html").read_text()
ROUTER = (ROOT / "router" / "admin.py").read_text()
CONFIG = (ROOT / "config.py").read_text()
OWN = re.sub(r"/\* ==== atom page: account ==== \*/.*?/\* ==== end atom page: account ==== \*/", "", PAGE, flags=re.S)


class AnalyticsPageTests(unittest.TestCase):
    def test_every_element_the_script_looks_up_exists(self):
        used = set(re.findall(r'\$\("([\w-]+)"\)', PAGE))
        made = set(re.findall(r'\bid="([\w-]+)"', PAGE))
        dynamic = {name for name in used if re.search(rf'\b{re.escape(name)}: (async )?\(', PAGE) or f'"{name}"' in PAGE}    # card ids made by the sections
        self.assertEqual(sorted(used - made - dynamic), [])

    def test_page_keeps_its_own_login_and_storage(self):
        # its own key "analytics", a role 1 login and its data in IndexedDB, through the page standard's account block (tests/test_page_auth.py)
        self.assertIn('const PAGE = { key: "analytics", title: "Analytics", role: 1, loginRequired: true, idb: true', PAGE)

    def test_every_admin_route_the_page_calls_exists_and_is_admin_only(self):
        routes = set(re.findall(r'"(/admin/[\w-]+)', PAGE)) | set(re.findall(r"`(/admin/[\w-]+)", PAGE))
        self.assertTrue(routes)
        for route in sorted(routes):
            with self.subTest(route=route):
                self.assertRegex(ROUTER, rf'@router\.\w+\("{re.escape(route)}"\)')
                self.assertRegex(CONFIG, rf'"{re.escape(route)}": \{{[^\n]*("roles": \[1\]|"user_check_permission")')

    def test_page_only_reads(self):
        # its requests are /admin/* reads only: no create, update, delete or user routes, no write method; the account block is checked in tests/test_page_auth.py
        for path in re.findall(r'(?<![\w.])api\(`?"?([^`"?$]+)', OWN):
            with self.subTest(path=path): self.assertTrue(path.startswith("/admin/"), path)
        for route in re.findall(r"/admin/[\w-]+", OWN):
            with self.subTest(route=route): self.assertRegex(route, r"^/admin/(postgres-query-runner-read|table-column-groupby|object-read|postgres-schema|monitor)$")
        self.assertNotRegex(OWN, r'method: "(PUT|DELETE|PATCH)"')

    def test_raw_sql_is_never_typed_on_the_page(self):
        # no SQL box: every query is the page's own; PgWeb is the place to write SQL
        self.assertNotIn("<textarea", OWN)

    def test_settings_the_page_reads_exist_in_config(self):
        for name in sorted(set(re.findall(r'\bconfig_[a-z_]+', OWN)) - {"config_postgres_schema_master", "config_column_int_mapping"}):
            with self.subTest(name=name): self.assertRegex(CONFIG, re.compile(rf"^{name} = ", re.M))

    def test_saved_data_is_indexeddb_records(self):
        # the schema, /info, row estimates and settings: "reference"; each section's cards: "analytics"; a sync drops the cards
        for text in ('Page.cacheSet("reference", fresh)', 'Page.cacheGet("reference")', 'Page.cacheSet("analytics", {})', 'record: "analytics"'):
            with self.subTest(text=text): self.assertIn(text, PAGE)

    def test_nullability_is_read_as_yes_or_no(self):
        # /admin/postgres-schema sends is_nullable as "YES"/"NO" (a string is always truthy): only isNotNull may read it
        uses = [line.strip() for line in PAGE.splitlines() if ".is_nullable" in line]
        self.assertEqual(len(uses), 1, uses)
        self.assertTrue(uses[0].startswith("const isNotNull = c =>"), uses)
        self.assertIn('"NO"', uses[0])


if __name__ == "__main__":
    unittest.main()
