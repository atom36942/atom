"""The admin page stands alone (its own role 1 login and storage) and reaches the data only through /admin/* routes that exist and are admin only."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "static" / "admin.html").read_text()
ROUTER = (ROOT / "router" / "admin.py").read_text()
CONFIG = (ROOT / "config.py").read_text()


class AdminPageTests(unittest.TestCase):
    def test_every_element_the_script_looks_up_exists(self):
        used = set(re.findall(r'\$\("([\w-]+)"\)', PAGE))
        made = set(re.findall(r'\bid="([\w-]+)"', PAGE))
        self.assertEqual(sorted(used - made), [])

    def test_page_keeps_its_own_login_and_storage(self):
        # its own key "admin", a role 1 login and its reference data in IndexedDB, through the page standard's account block (tests/test_page_auth.py)
        self.assertIn('const PAGE = { key: "admin", title: "Admin", role: 1, loginRequired: true, idb: true', PAGE)

    def test_every_admin_route_the_page_calls_exists_and_is_admin_only(self):
        routes = set(re.findall(r'"(/admin/[\w-]+)', PAGE)) | set(re.findall(r"`(/admin/[\w-]+)", PAGE))
        self.assertTrue(routes)
        for route in sorted(routes):
            with self.subTest(route=route):
                self.assertRegex(ROUTER, rf'@router\.\w+\("{re.escape(route)}"\)')
                self.assertRegex(CONFIG, rf'"{re.escape(route)}": \{{[^\n]*"roles": \[1\]')

    def test_page_writes_only_through_admin_routes(self):
        # the page's own requests go to /admin/* only; the account block (the user, the password) is checked in tests/test_page_auth.py
        own = re.sub(r"/\* ==== atom page: account ==== \*/.*?/\* ==== end atom page: account ==== \*/", "", PAGE, flags=re.S)
        for path in re.findall(r'(?<![\w.])api\(`?"?([^`"?$]+)', own):
            with self.subTest(path=path): self.assertTrue(path.startswith("/admin/"), path)

    def test_settings_the_page_reads_exist_in_config(self):
        # the page takes Atom's rules from the running server by these names; a rename in config.py must change the page too
        for name in sorted(set(re.findall(r'"(config_[a-z_]+)"', PAGE)) - {"config_postgres"}):
            with self.subTest(name=name): self.assertRegex(CONFIG, re.compile(rf"^{name} = ", re.M))

    def test_server_set_columns_never_reach_a_form(self):
        self.assertIn('const AUDIT = ["created_at", "created_by_id", "updated_at", "updated_by_id"];', PAGE)
        form = re.search(r"const editableColumns = table => columns\(table\)\.filter\(c => \{(.*?)\n\}\);", PAGE, re.S).group(1)
        for rule in ("c.is_primary", "AUDIT.includes(n)", "STATE_COLS.includes(n)", "!readable(n)", 'kind(c) === "geo"', "RULES.users_blocked.includes(n)"):
            with self.subTest(rule=rule): self.assertIn(rule, form)

    def test_reference_data_is_one_indexeddb_record(self):
        # the schema, /info, row counts, settings, triggers and constraints: the record "reference", saved by the sync's download and read on open
        self.assertIn('Page.cacheSet("reference", fresh)', PAGE)
        self.assertIn('Page.cacheGet("reference")', PAGE)
        self.assertNotIn("store.username", PAGE)

    def test_check_constraints_are_read_from_pg_constraint(self):
        # Atom writes config_postgres in / regex / check as CHECK constraints; the page reads them in one query
        self.assertIn("where con.contype = 'c'", PAGE)
        self.assertIn("def.match(/= ANY", PAGE)

    def test_nullability_is_read_as_yes_or_no(self):
        # /admin/postgres-schema sends is_nullable as "YES"/"NO" (a string is always truthy): only isNotNull may read it
        uses = [line.strip() for line in PAGE.splitlines() if ".is_nullable" in line]
        self.assertEqual(len(uses), 1, uses)
        self.assertTrue(uses[0].startswith("const isNotNull = c =>"), uses)
        self.assertIn('"NO"', uses[0])

    def test_system_tables_the_page_names_are_atoms(self):
        # SYSTEM_TABLES (read-only in the panel) must be tables Atom's config_postgres creates
        atom = re.findall(r'^"(\w+)":\[$', CONFIG, re.M)
        system = re.findall(r"(\w+): \"", re.search(r"const SYSTEM_TABLES = \{([^}]+)\}", PAGE).group(1))
        self.assertTrue(system and set(system) <= set(atom), system)

    def test_trigger_names_the_page_reads_are_the_ones_atom_creates(self):
        functions = "\n".join(path.read_text() for path in (ROOT / "function").glob("*.py"))
        for prefix in sorted(set(re.findall(r"trigger_[a-z_]+?_(?=\$\{t\}|\b)", PAGE)) | set(re.findall(r"/\^(trigger_[a-z_]+)", PAGE))):
            with self.subTest(trigger=prefix): self.assertIn(prefix.rstrip("_"), functions)


if __name__ == "__main__":
    unittest.main()
