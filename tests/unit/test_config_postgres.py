import copy
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import config
from core.function import func_postgres_schema_init


class Row(dict):
    def __init__(self, values=None, **kwargs):
        super().__init__(kwargs)
        self.values_list = list(values or [])

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.values_list[key]
        return super().__getitem__(key)


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSchemaPool:
    def __init__(self, tables=None, meta=None, triggers=None):
        self.conn = FakeSchemaConn(tables=tables or {}, meta=meta or {}, triggers=triggers or {})

    def acquire(self):
        return FakeAcquire(self.conn)


class FakeSchemaConn:
    def __init__(self, tables, meta, triggers):
        self.tables = copy.deepcopy(tables)
        self.meta = {table: set(items) for table, items in meta.items()}
        self.triggers = {table: set(items) for table, items in triggers.items()}
        self.queries = []

    async def execute(self, sql, *args):
        self.queries.append((sql, args))
        self._apply(sql)
        return "OK"

    async def fetch(self, sql, *args):
        normalized = " ".join(sql.lower().split())
        if "from pg_attribute" in normalized:
            table = args[0]
            rows = []
            for name, info in self.tables.get(table, {}).items():
                rows.append(
                    Row(
                        [name, info["type"], info.get("notnull", False), info.get("default")],
                        attname=name,
                        type=info["type"],
                        notnull=info.get("notnull", False),
                        default=info.get("default"),
                    )
                )
            return rows
        if "from pg_indexes where tablename=$1" in normalized:
            table = args[0]
            return [Row([name], name=name) for name in sorted(self.meta.get(table, set()))]
        if "from information_schema.columns c join information_schema.tables" in normalized:
            rows = []
            for table, columns in self.tables.items():
                for column in columns:
                    rows.append(Row([table, column], table_name=table, column_name=column))
            return rows
        return []

    def _apply(self, sql):
        self._apply_cleanup(sql)

        create_table = re.search(r'CREATE TABLE IF NOT EXISTS (?:"([^"]+)"|(\w+)) \("id" bigserial PRIMARY KEY\)', sql)
        if create_table:
            table = create_table.group(1) or create_table.group(2)
            self.tables.setdefault(table, {}).setdefault(
                "id", {"type": "bigserial", "notnull": True, "default": None}
            )
            return

        add_col = re.search(r'ALTER TABLE (?:"([^"]+)"|(\w+)) ADD COLUMN (?:"([^"]+)"|(\w+)) ([^ ]+(?:\([^)]*\))?)', sql)
        if add_col:
            groups = add_col.groups()
            table = groups[0] or groups[1]
            column = groups[2] or groups[3]
            dtype = groups[4]
            self.tables.setdefault(table, {})[column] = {
                "type": dtype,
                "notnull": "NOT NULL" in sql,
                "default": sql.split("DEFAULT ", 1)[1].split(" ", 1)[0] if "DEFAULT " in sql else None,
            }
            return

        rename_col = re.search(r'ALTER TABLE "?(\w+)"? RENAME COLUMN "?(\w+)"? TO "?(\w+)"?', sql)
        if rename_col:
            table, old, new = rename_col.groups()
            self.tables[table][new] = self.tables[table].pop(old)
            return

        type_change = re.search(r'ALTER TABLE "?(\w+)"? ALTER COLUMN "?(\w+)"? TYPE ([^ ]+)', sql)
        if type_change:
            table, column, dtype = type_change.groups()
            self.tables[table][column]["type"] = dtype
            return

        set_not_null = re.search(r'ALTER TABLE "?(\w+)"? ALTER COLUMN "?(\w+)"? SET NOT NULL', sql)
        if set_not_null:
            table, column = set_not_null.groups()
            self.tables[table][column]["notnull"] = True
            return

        drop_not_null = re.search(r'ALTER TABLE "?(\w+)"? ALTER COLUMN "?(\w+)"? DROP NOT NULL', sql)
        if drop_not_null:
            table, column = drop_not_null.groups()
            self.tables[table][column]["notnull"] = False
            return

        set_default = re.search(r'ALTER TABLE "?(\w+)"? ALTER COLUMN "?(\w+)"? SET DEFAULT (.+)', sql)
        if set_default:
            table, column, default = set_default.groups()
            self.tables[table][column]["default"] = default
            return

        drop_default = re.search(r'ALTER TABLE "?(\w+)"? ALTER COLUMN "?(\w+)"? DROP DEFAULT', sql)
        if drop_default:
            table, column = drop_default.groups()
            self.tables[table][column]["default"] = None
            return

        drop_column = re.search(r'ALTER TABLE "?(\w+)"? DROP COLUMN "?(\w+)"?', sql)
        if drop_column:
            table, column = drop_column.groups()
            self.tables.get(table, {}).pop(column, None)
            return

        create_index = re.search(r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:"([^"]+)"|(\w+))\s+ON\s+(?:"([^"]+)"|(\w+))', sql, re.IGNORECASE)
        if create_index:
            groups = create_index.groups()
            name = groups[0] or groups[1]
            table = groups[2] or groups[3]
            self.meta.setdefault(table, set()).add(name)
            return

        add_constraint = re.search(r'ALTER TABLE "?(\w+)"? ADD CONSTRAINT "?(\w+)"?', sql)
        if add_constraint:
            table, name = add_constraint.groups()
            self.meta.setdefault(table, set()).add(name)
            return

        drop_trigger = re.search(r'DROP TRIGGER IF EXISTS "?(\w+)"? ON "?(\w+)"?', sql)
        if drop_trigger:
            trigger, table = drop_trigger.groups()
            self.triggers.setdefault(table, set()).discard(trigger)

        create_trigger = re.search(r'CREATE TRIGGER "?(\w+)"? .*? ON "?(\w+)"?', sql)
        if create_trigger:
            trigger, table = create_trigger.groups()
            self.triggers.setdefault(table, set()).add(trigger)

    def _apply_cleanup(self, sql):
        managed_tables = self._quoted_values_after(sql, "tablename IN") or self._quoted_values_after(sql, "relname IN")
        if "FROM pg_indexes" in sql and "IF NOT record.indexname IN" in sql:
            wants = set(self._quoted_values_after(sql, "IF NOT record.indexname IN"))
            for table in managed_tables:
                self.meta.setdefault(table, set()).difference_update(
                    item for item in set(self.meta.get(table, set())) if item.startswith(("idx_", "unique_", "check_")) and item not in wants
                )
        elif "FROM pg_constraint" in sql and "IF NOT record.conname IN" in sql:
            wants = set(self._quoted_values_after(sql, "IF NOT record.conname IN"))
            for table in managed_tables:
                self.meta.setdefault(table, set()).difference_update(
                    item for item in set(self.meta.get(table, set())) if item.startswith(("unique_", "check_")) and item not in wants
                )
        elif "FROM pg_trigger" in sql and "IF NOT record.tgname IN" in sql:
            wants = set(self._quoted_values_after(sql, "IF NOT record.tgname IN"))
            for table in managed_tables:
                self.triggers.setdefault(table, set()).difference_update(
                    item for item in set(self.triggers.get(table, set())) if item.startswith("trigger_") and item not in wants
                )

    def _quoted_values_after(self, text, marker):
        marker_index = text.find(marker)
        if marker_index == -1:
            return []
        after_marker = text[marker_index:]
        match = re.search(r"\(([^()]*)\)", after_marker)
        if not match:
            return []
        return re.findall(r"'([^']+)'", match.group(1))


class FakePasswordHasher:
    def hash(self, value):
        return f"hashed:{value}"


def all_sql(conn):
    return "\n".join(sql for sql, _args in conn.queries)


PRIMARY_ID = {"name": "id", "datatype": "bigserial", "is_primary": 1}


def control_pg_config(control=None, users_columns=None, demo_columns=None, extension=None):
    if users_columns is not None and (not users_columns or users_columns[0] != PRIMARY_ID):
        users_columns = [PRIMARY_ID, *users_columns]
    if demo_columns is not None and (not demo_columns or demo_columns[0] != PRIMARY_ID):
        demo_columns = [PRIMARY_ID, *demo_columns]
    users_columns = users_columns if users_columns is not None else [
        PRIMARY_ID,
        {"name": "type", "datatype": "smallint"},
        {"name": "username", "datatype": "text"},
        {"name": "password", "datatype": "text"},
        {"name": "role", "datatype": "smallint"},
        {"name": "deactivated_at", "datatype": "smallint"},
        {"name": "deleted_at", "datatype": "timestamptz"},
    ]
    demo_columns = demo_columns if demo_columns is not None else [
        PRIMARY_ID,
        {"name": "updated_at", "datatype": "timestamptz"},
        {"name": "is_protected", "datatype": "boolean"},
        {"name": "created_by_id", "datatype": "bigint"},
    ]
    pg_config = {
        "table": {
            "users": users_columns,
            "demo": demo_columns,
        },
        "control": control or {},
    }
    if extension is not None:
        pg_config["extension"] = extension
    return pg_config


def test_config_postgres_all_current_columns_have_required_keys_and_valid_references():
    for table, columns in config.config_postgres["table"].items():
        names = [column["name"] for column in columns]
        assert len(names) == len(set(names)), f"duplicate columns in {table}"
        for column in columns:
            assert column.get("name")
            assert column.get("datatype")
            for index_group in str(column.get("index", "")).split("|"):
                if not index_group:
                    continue
                index_type, index_columns = index_group[:-1].split("(", 1)
                assert index_type in {"btree", "gin", "gist"}
                for index_column in index_columns.split(","):
                    assert index_column.strip() in names
            for group in str(column.get("unique", "")).split("|"):
                if not group:
                    continue
                for unique_column in group.split(","):
                    assert unique_column.strip() in names


def test_func_check_rejects_missing_or_invalid_postgres_column_datatype():
    from core.function import func_check

    base_kwargs = {
        "app_routes": [],
        "config_config_path": None,
        "config_function_path": None,
        "config_api_namespace": ["/"],
        "config_router_path": None,
        "config_api": {},
        "config_allowed_user_storage_backends": [],
        "config_allowed_api_storage_backends": [],
    }

    invalid_configs = [
        ({"table": {"demo": [{"datatype": "text"}]}}, "column name"),
        ({"table": {"demo": [{"name": "title"}]}}, "datatype"),
        ({"table": {"demo": [{"name": "title", "datatype": "not_a_pg_type"}]}}, "invalid datatype"),
    ]

    for pg_config, message in invalid_configs:
        with pytest.raises(Exception, match=message):
            func_check(**base_kwargs, config_postgres=pg_config)

    func_check(**base_kwargs, config_postgres={"table": {"demo": [
        {"name": "title", "datatype": "text"},
        {"name": "tags", "datatype": "text[]"},
        {"name": "amount", "datatype": "numeric(10,2)"},
        {"name": "place", "datatype": "geography(Point, 4326)"},
    ]}})


@pytest.mark.asyncio
async def test_config_postgres_schema_init_builds_real_config_schema_and_controls():
    pool = FakeSchemaPool()

    result = await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=config.config_postgres,
        config_root_user_password=config.config_root_user_password,
    )

    sql = all_sql(pool.conn)
    assert result == "database init done"
    for table, columns in config.config_postgres["table"].items():
        assert table in pool.conn.tables
        for column in columns:
            assert column["name"] in pool.conn.tables[table]
    assert 'CREATE EXTENSION IF NOT EXISTS "postgis";' in sql
    assert 'CREATE INDEX IF NOT EXISTS "idx_test_tag_gin" ON "test" USING gin("tag");' in sql
    assert 'ALTER TABLE "test" ADD CONSTRAINT "unique_test_code_type" UNIQUE ("code","type");' in sql
    assert 'ALTER TABLE "test" ADD CONSTRAINT "unique_test_code_slug" UNIQUE ("code","slug");' in sql
    assert 'CHECK ("email" ~ \'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$\');' in sql
    assert 'ALTER TABLE "test" SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);' in sql
    is_enable_drop_column = config.config_postgres["control"].get("is_enable_drop_column", 0)
    if is_enable_drop_column:
        assert "CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE')" not in sql
    else:
        assert "CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE')" in sql
    assert "trigger_delete_disable_users" not in sql
    assert "trigger_delete_disable_bulk_users" not in sql
    


    assert "trigger_delete_disable_role_users" in sql
    assert "trigger_delete_disable_role_users_soft" in sql
    assert "trigger_protect_root_users" in sql
    assert "trigger_log_users_delete" in sql
    assert "INSERT INTO users (type, username, password, role)" in sql


@pytest.mark.asyncio
async def test_config_postgres_schema_init_renames_updates_defaults_and_notnull_state():
    pg_config = {
        "table": {
            "demo": [
                PRIMARY_ID,
                {"name": "title", "datatype": "text", "is_mandatory": 1, "default": "'new'"},
                {"name": "address", "old": "adress", "datatype": "text"},
                {"name": "count", "datatype": "bigint"},
            ]
        },
        "control": {},
    }
    pool = FakeSchemaPool(
        tables={
            "demo": {
                "id": {"type": "bigserial", "notnull": True, "default": None},
                "title": {"type": "varchar", "notnull": False, "default": "'old'::text"},
                "adress": {"type": "text", "notnull": False, "default": None},
                "count": {"type": "integer", "notnull": True, "default": "0"},
            }
        }
    )

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="",
    )

    sql = all_sql(pool.conn)
    assert 'ALTER TABLE "demo" RENAME COLUMN "adress" TO "address"' in sql
    assert 'ALTER TABLE "demo" ALTER COLUMN "title" TYPE text USING "title"::text' in sql
    assert 'ALTER TABLE "demo" ALTER COLUMN "title" SET NOT NULL' in sql
    assert 'ALTER TABLE "demo" ALTER COLUMN "title" SET DEFAULT \'new\'' in sql
    assert 'ALTER TABLE "demo" ALTER COLUMN "count" TYPE bigint USING "count"::bigint' in sql
    assert 'ALTER TABLE "demo" ALTER COLUMN "count" DROP NOT NULL' in sql
    assert 'ALTER TABLE "demo" ALTER COLUMN "count" DROP DEFAULT' in sql
    assert "address" in pool.conn.tables["demo"]
    assert "adress" not in pool.conn.tables["demo"]
    assert pool.conn.tables["demo"]["title"]["notnull"] is True
    assert pool.conn.tables["demo"]["count"]["notnull"] is False
    assert pool.conn.tables["demo"]["count"]["default"] is None


@pytest.mark.asyncio
async def test_config_postgres_schema_init_treats_none_and_empty_optional_column_settings_as_off():
    pg_config = {
        "table": {
            "demo": [
                PRIMARY_ID,
                {
                    "name": "title",
                    "datatype": "text",
                    "default": None,
                    "index": "",
                    "unique": "",
                    "check": None,
                    "regex": "",
                    "in": None,
                    "old": "",
                },
                {"name": "code", "datatype": "text", "default": ""},
            ],
        }
    }
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="",
    )

    sql = all_sql(pool.conn)
    assert 'ADD COLUMN "title" text  ' in sql
    assert 'ADD COLUMN "code" text  ' in sql
    assert "DEFAULT None" not in sql
    assert "SET DEFAULT None" not in sql
    assert "SET DEFAULT " not in sql
    assert "ADD CONSTRAINT" not in sql
    assert "CREATE INDEX" not in sql
    assert "RENAME COLUMN" not in sql


@pytest.mark.asyncio
async def test_config_postgres_schema_init_removes_stale_indexes_constraints_and_control_triggers_on_config_change():
    first_config = {
        "table": {
            "demo": [
                PRIMARY_ID,
                {"name": "created_at", "datatype": "timestamptz"},
                {"name": "updated_at", "datatype": "timestamptz"},
                {"name": "is_protected", "datatype": "boolean"},
                {"name": "status", "datatype": "smallint", "in": (0, 1), "index": "btree(status)"},
                {"name": "code", "datatype": "text", "unique": "code"},
            ]
        },
        "control": {"table_delete_disable_row": ["demo"], "table_delete_disable_row_bulk": [["demo", 1]]},
    }
    second_config = {
        "table": {
            "demo": [
                PRIMARY_ID,
                {"name": "created_at", "datatype": "timestamptz"},
                {"name": "updated_at", "datatype": "timestamptz"},
                {"name": "is_protected", "datatype": "boolean"},
                {"name": "status", "datatype": "smallint"},
                {"name": "code", "datatype": "text"},
            ]
        },
        "control": {},
    }
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=first_config,
        config_root_user_password="",
    )

    assert "idx_demo_status_btree" in pool.conn.meta["demo"]
    assert "unique_demo_code" in pool.conn.meta["demo"]
    assert any(name.startswith("check_demo_status_in_") for name in pool.conn.meta["demo"])
    assert "trigger_delete_disable_demo" in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_bulk_demo" in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_is_protected_demo" in pool.conn.triggers["demo"]
    assert "trigger_updated_at_set_demo" in pool.conn.triggers["demo"]

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=second_config,
        config_root_user_password="",
    )

    assert "idx_demo_status_btree" not in pool.conn.meta["demo"]
    assert "unique_demo_code" not in pool.conn.meta["demo"]
    assert not any(name.startswith("check_demo_status_in_") for name in pool.conn.meta["demo"])
    assert "trigger_delete_disable_demo" not in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_bulk_demo" not in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_is_protected_demo" in pool.conn.triggers["demo"]
    assert "trigger_updated_at_set_demo" in pool.conn.triggers["demo"]


@pytest.mark.asyncio
async def test_config_postgres_schema_init_recreates_changed_index_and_constraint_names():
    first_config = {
        "table": {
            "demo": [
                PRIMARY_ID,
                {"name": "status", "datatype": "smallint", "in": (0, 1), "index": "btree(status)"},
                {"name": "code", "datatype": "text", "unique": "code"},
            ]
        },
        "control": {},
    }
    second_config = {
        "table": {
            "demo": [
                PRIMARY_ID,
                {"name": "status", "datatype": "smallint", "in": (1, 2)},
                {"name": "status_text", "datatype": "text", "index": "gin(status_text)"},
                {"name": "code", "datatype": "text"},
                {"name": "scope", "datatype": "text"},
                {"name": "marker", "datatype": "text", "unique": "code,scope"},
            ]
        },
        "control": {},
    }
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=first_config,
        config_root_user_password="",
    )
    first_check = next(name for name in pool.conn.meta["demo"] if name.startswith("check_demo_status_in_"))
    assert "idx_demo_status_btree" in pool.conn.meta["demo"]
    assert "unique_demo_code" in pool.conn.meta["demo"]

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=second_config,
        config_root_user_password="",
    )

    second_checks = [name for name in pool.conn.meta["demo"] if name.startswith("check_demo_status_in_")]
    assert "idx_demo_status_btree" not in pool.conn.meta["demo"]
    assert "idx_demo_status_text_gin" in pool.conn.meta["demo"]
    assert "unique_demo_code" not in pool.conn.meta["demo"]
    assert "unique_demo_code_scope" in pool.conn.meta["demo"]
    assert first_check not in second_checks
    assert len(second_checks) == 1


@pytest.mark.asyncio
async def test_config_postgres_schema_init_control_toggles_are_reflected_in_generated_state():
    pg_config = control_pg_config(
        control={
            "is_enable_drop_schema": 0,
            "is_enable_drop_table": 0,
            "is_enable_truncate": 0,
            "is_enable_delete_disable_users_role": 1,
            "is_enable_delete_disable_users_role_soft": 1,

            "table_delete_disable_row": ["*"],
            "table_delete_disable_row_bulk": [["*", 3]],
        },
    )
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="root-secret",
    )

    sql = all_sql(pool.conn)
    assert "CREATE EVENT TRIGGER trigger_drop_disable ON ddl_command_start WHEN TAG IN ('DROP SCHEMA','DROP TABLE')" in sql
    assert "CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE')" in sql
    assert "trigger_protect_root_users" in pool.conn.triggers["users"]
    assert "trigger_delete_disable_role_users" in pool.conn.triggers["users"]
    assert "trigger_delete_disable_role_users_soft" in pool.conn.triggers["users"]

    assert "trigger_truncate_disable_users" in pool.conn.triggers["users"]
    assert "trigger_truncate_disable_demo" in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_users" in pool.conn.triggers["users"]
    assert "trigger_delete_disable_demo" in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_bulk_users" in pool.conn.triggers["users"]
    assert "trigger_delete_disable_bulk_demo" in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_is_protected_demo" in pool.conn.triggers["demo"]
    assert "trigger_updated_at_set_demo" in pool.conn.triggers["demo"]
    assert "func_delete_disable_bulk(3)" in sql


@pytest.mark.asyncio
async def test_config_postgres_schema_init_accepts_legacy_disable_control_switch_names():
    pg_config = control_pg_config(
        control={
            "is_disable_drop_schema": 1,
            "is_disable_drop_table": 1,
            "is_disable_truncate": 1,
            "is_disable_users_delete_role": 1,
            "is_disable_drop_column": 0,
        },
    )
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="root-secret",
    )

    sql = all_sql(pool.conn)
    assert "CREATE EVENT TRIGGER trigger_drop_disable ON ddl_command_start WHEN TAG IN ('DROP SCHEMA','DROP TABLE')" in sql
    assert "CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE')" not in sql
    assert "trigger_truncate_disable_demo" in pool.conn.triggers["demo"]
    assert "trigger_delete_disable_role_users" in pool.conn.triggers["users"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "extension", "expected_sql", "unexpected_sql"),
    [
        ({"is_enable_extension": 1}, ["pg_trgm"], 'CREATE EXTENSION IF NOT EXISTS "pg_trgm";', None),
        ({}, ["pg_trgm"], None, 'CREATE EXTENSION IF NOT EXISTS "pg_trgm";'),
        ({"is_enable_autovacuum_optimize": 1}, None, 'ALTER TABLE "demo" SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);', None),
        ({}, None, None, 'ALTER TABLE "demo" SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);'),
    ],
)
async def test_config_postgres_schema_init_extension_and_autovacuum_controls(control, extension, expected_sql, unexpected_sql):
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=control_pg_config(control=control, extension=extension),
        config_root_user_password="",
    )

    sql = all_sql(pool.conn)
    if expected_sql:
        assert expected_sql in sql
    if unexpected_sql:
        assert unexpected_sql not in sql


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "expected_tags"),
    [
        ({}, None),
        ({"is_enable_drop_schema": 0}, "('DROP SCHEMA')"),
        ({"is_enable_drop_table": 0}, "('DROP TABLE')"),
        ({"is_enable_drop_schema": 0, "is_enable_drop_table": 0}, "('DROP SCHEMA','DROP TABLE')"),
    ],
)
async def test_config_postgres_schema_init_drop_schema_table_controls(control, expected_tags):
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=control_pg_config(control=control),
        config_root_user_password="",
    )

    sql = all_sql(pool.conn)
    if expected_tags:
        assert f"CREATE EVENT TRIGGER trigger_drop_disable ON ddl_command_start WHEN TAG IN {expected_tags}" in sql
    else:
        assert "CREATE EVENT TRIGGER trigger_drop_disable ON ddl_command_start" not in sql
        assert "DROP EVENT TRIGGER IF EXISTS trigger_drop_disable" in sql


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "creates_guard"),
    [
        ({}, True),
        ({"is_enable_drop_column": 0}, True),
        ({"is_enable_drop_column": 1}, False),
    ],
)
async def test_config_postgres_schema_init_drop_column_db_guard_control(control, creates_guard):
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=control_pg_config(control=control),
        config_root_user_password="",
    )

    sql = all_sql(pool.conn)
    assert "DROP EVENT TRIGGER IF EXISTS trigger_drop_column_disable" in sql
    if creates_guard:
        assert "CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE')" in sql
    else:
        assert "CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE')" not in sql


@pytest.mark.asyncio
async def test_config_postgres_schema_init_does_not_drop_omitted_columns_without_explicit_drop_control():
    pg_config = {"table": {"demo": [PRIMARY_ID, {"name": "kept", "datatype": "text"}]}, "control": {}}
    pool = FakeSchemaPool(
        tables={
            "demo": {
                "id": {"type": "bigserial", "notnull": True, "default": None},
                "kept": {"type": "text", "notnull": False, "default": None},
                "legacy_data": {"type": "text", "notnull": False, "default": None},
            }
        }
    )

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="",
    )

    assert "legacy_data" in pool.conn.tables["demo"]
    assert "DROP COLUMN" not in all_sql(pool.conn)
    assert "CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE')" in all_sql(pool.conn)


@pytest.mark.asyncio
async def test_config_postgres_schema_init_drops_omitted_columns_only_when_explicitly_enabled():
    pg_config = {
        "table": {"demo": [PRIMARY_ID, {"name": "kept", "datatype": "text"}]},
        "control": {"is_enable_drop_column": 1, "is_enable_drop_column_mismatch": 1},
    }
    pool = FakeSchemaPool(
        tables={
            "demo": {
                "id": {"type": "bigserial", "notnull": True, "default": None},
                "kept": {"type": "text", "notnull": False, "default": None},
                "legacy_data": {"type": "text", "notnull": False, "default": None},
            }
        }
    )

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="",
    )

    assert "legacy_data" not in pool.conn.tables["demo"]
    assert "DROP EVENT TRIGGER IF EXISTS trigger_drop_column_disable" in all_sql(pool.conn)
    assert 'ALTER TABLE "demo" DROP COLUMN "legacy_data"' in all_sql(pool.conn)


@pytest.mark.asyncio
async def test_config_postgres_schema_init_rejects_conflicting_drop_column_controls():
    pg_config = {
        "table": {"demo": [PRIMARY_ID, {"name": "kept", "datatype": "text"}]},
        "control": {"is_enable_drop_column": 0, "is_enable_drop_column_mismatch": 1},
    }

    with pytest.raises(Exception, match="is_enable_drop_column=0 blocks is_enable_drop_column_mismatch=1"):
        await func_postgres_schema_init(
            client_postgres_pool=FakeSchemaPool(),
            client_password_hasher=FakePasswordHasher(),
            config_postgres=pg_config,
            config_root_user_password="",
        )


@pytest.mark.asyncio
async def test_config_postgres_schema_init_accepts_legacy_drop_column_mismatch_control_names():
    for legacy_key in ("is_drop_column_mismatch_db", "is_drop_column_mismatch"):
        pg_config = {
            "table": {"demo": [PRIMARY_ID, {"name": "kept", "datatype": "text"}]},
            "control": {"is_enable_drop_column": 1, legacy_key: 1},
        }
        pool = FakeSchemaPool(
            tables={
                "demo": {
                    "id": {"type": "bigserial", "notnull": True, "default": None},
                    "kept": {"type": "text", "notnull": False, "default": None},
                    "legacy_data": {"type": "text", "notnull": False, "default": None},
                }
            }
        )

        await func_postgres_schema_init(
            client_postgres_pool=pool,
            client_password_hasher=FakePasswordHasher(),
            config_postgres=pg_config,
            config_root_user_password="",
        )

        assert "legacy_data" not in pool.conn.tables["demo"]
        assert 'ALTER TABLE "demo" DROP COLUMN "legacy_data"' in all_sql(pool.conn)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "users_columns", "expected", "unexpected"),
    [
        ({"is_enable_delete_disable_users_role": 1}, None, "trigger_delete_disable_role_users", None),
        ({}, None, None, "trigger_delete_disable_role_users"),
        (
            {"is_enable_delete_disable_users_role": 1},
            [
                {"name": "type", "datatype": "smallint"},
                {"name": "username", "datatype": "text"},
                {"name": "password", "datatype": "text"},
                {"name": "deactivated_at", "datatype": "smallint"},
            ],
            None,
            "trigger_delete_disable_role_users",
        ),

    ],
)
async def test_config_postgres_schema_init_users_delete_controls_require_switches_and_columns(control, users_columns, expected, unexpected):
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=control_pg_config(control=control, users_columns=users_columns),
        config_root_user_password="",
    )

    users_triggers = pool.conn.triggers.get("users", set())
    if expected:
        assert expected in users_triggers
    if unexpected:
        assert unexpected not in users_triggers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "users_columns", "expected", "unexpected"),
    [
        ({"is_enable_delete_disable_users_role_soft": 1}, None, "trigger_delete_disable_role_users_soft", None),
        ({}, None, None, "trigger_delete_disable_role_users_soft"),
        (
            {"is_enable_delete_disable_users_role_soft": 1},
            [
                {"name": "type", "datatype": "smallint"},
                {"name": "username", "datatype": "text"},
                {"name": "password", "datatype": "text"},
                {"name": "role", "datatype": "smallint"},
                {"name": "deactivated_at", "datatype": "smallint"},
            ],
            None,
            "trigger_delete_disable_role_users_soft",
        ),
        (
            {"is_enable_delete_disable_users_role_soft": 1},
            [
                {"name": "type", "datatype": "smallint"},
                {"name": "username", "datatype": "text"},
                {"name": "password", "datatype": "text"},
                {"name": "deleted_at", "datatype": "timestamptz"},
                {"name": "deactivated_at", "datatype": "smallint"},
            ],
            None,
            "trigger_delete_disable_role_users_soft",
        ),

    ],
)
async def test_config_postgres_schema_init_users_soft_delete_controls_require_switches_and_columns(control, users_columns, expected, unexpected):
    pool = FakeSchemaPool()

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=control_pg_config(control=control, users_columns=users_columns),
        config_root_user_password="",
    )

    users_triggers = pool.conn.triggers.get("users", set())
    if expected:
        assert expected in users_triggers
    if unexpected:
        assert unexpected not in users_triggers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "expected_sql", "unexpected_sql", "expected_trigger", "unexpected_trigger"),
    [
        ({"is_enable_delete_disable_users_root": 1}, "CREATE TRIGGER trigger_protect_root_users", None, "trigger_protect_root_users", None),
        ({"is_enable_delete_disable_users_root": 0}, None, "CREATE TRIGGER trigger_protect_root_users", None, "trigger_protect_root_users"),
        ({"is_enable_users_root_upsert": 1}, "INSERT INTO users (type, username, password, role)", None, None, None),
        ({"is_enable_users_root_upsert": 0}, None, "INSERT INTO users (type, username, password, role)", None, None),
    ],
)
async def test_config_postgres_schema_init_root_user_controls(control, expected_sql, unexpected_sql, expected_trigger, unexpected_trigger):
    pool = FakeSchemaPool(triggers={"users": {"trigger_protect_root_users"}})

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=control_pg_config(control=control),
        config_root_user_password="root-secret",
    )

    sql = all_sql(pool.conn)
    users_triggers = pool.conn.triggers.get("users", set())
    if expected_sql:
        assert expected_sql in sql
    if unexpected_sql:
        assert unexpected_sql not in sql
    if expected_trigger:
        assert expected_trigger in users_triggers
    if unexpected_trigger:
        assert unexpected_trigger not in users_triggers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "expected", "unexpected"),
    [
        ({"is_enable_log_users_password": 1}, "trigger_password_log_users", None),
        ({"is_enable_log_users_password": 0}, None, "trigger_password_log_users"),
    ],
)
async def test_config_postgres_schema_init_password_log_control(control, expected, unexpected):
    pg_config = control_pg_config(control=control)
    pg_config["table"]["log_users_password"] = [
        PRIMARY_ID,
        {"name": "user_id", "datatype": "bigint"},
        {"name": "password", "datatype": "text"},
    ]
    pool = FakeSchemaPool(triggers={"users": {"trigger_password_log_users"}})

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="",
    )

    users_triggers = pool.conn.triggers.get("users", set())
    if expected:
        assert expected in users_triggers
    if unexpected:
        assert unexpected not in users_triggers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "expected", "unexpected"),
    [
        ({"is_enable_log_users_delete": 1}, "trigger_log_users_delete", None),
        ({"is_enable_log_users_delete": 0}, None, "trigger_log_users_delete"),
    ],
)
async def test_config_postgres_schema_init_users_delete_log_control(control, expected, unexpected):
    pg_config = control_pg_config(
        control=control,
        users_columns=[
            {"name": "deleted_at", "datatype": "timestamptz"},
        ],
    )
    pg_config["table"]["log_users_delete"] = [
        PRIMARY_ID,
        {"name": "user_id", "datatype": "bigint"},
        {"name": "event", "datatype": "smallint"},
        {"name": "status", "datatype": "smallint"},
    ]
    pool = FakeSchemaPool(triggers={"users": {"trigger_log_users_delete"}})

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="",
    )

    users_triggers = pool.conn.triggers.get("users", set())
    if expected:
        assert expected in users_triggers
        assert "CREATE OR REPLACE FUNCTION func_log_users_delete" in all_sql(pool.conn)
        assert "CREATE TRIGGER trigger_log_users_delete AFTER UPDATE OF deleted_at OR DELETE ON users" in all_sql(pool.conn)
    if unexpected:
        assert unexpected not in users_triggers


@pytest.mark.asyncio
async def test_config_postgres_schema_init_users_delete_log_trigger_requires_log_table():
    pg_config = control_pg_config(
        control={"is_enable_log_users_delete": 1},
        users_columns=[
            {"name": "deleted_at", "datatype": "timestamptz"},
        ],
    )
    pool = FakeSchemaPool(triggers={"users": {"trigger_log_users_delete"}})

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=pg_config,
        config_root_user_password="",
    )

    assert "trigger_log_users_delete" not in pool.conn.triggers.get("users", set())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("control", "expected", "unexpected"),
    [
        ({"is_enable_truncate": 0}, {"trigger_truncate_disable_users", "trigger_truncate_disable_demo"}, set()),
        ({}, set(), {"trigger_truncate_disable_users", "trigger_truncate_disable_demo"}),
        ({"table_delete_disable_row": ["demo"]}, {"trigger_delete_disable_demo"}, {"trigger_delete_disable_users"}),
        ({"table_delete_disable_row": ["*"]}, {"trigger_delete_disable_demo", "trigger_delete_disable_users"}, set()),
        ({"table_delete_disable_row": ["missing"]}, set(), {"trigger_delete_disable_demo", "trigger_delete_disable_users"}),
        ({"table_delete_disable_row_bulk": [["demo", 2]]}, {"trigger_delete_disable_bulk_demo"}, {"trigger_delete_disable_bulk_users"}),
        ({"table_delete_disable_row_bulk": [["*", 4]]}, {"trigger_delete_disable_bulk_demo", "trigger_delete_disable_bulk_users"}, set()),
        ({"table_delete_disable_row_bulk": [["missing", 2]]}, set(), {"trigger_delete_disable_bulk_demo", "trigger_delete_disable_bulk_users"}),
        ({"is_enable_delete_disable_is_protected": 0}, set(), {"trigger_delete_disable_is_protected_demo"}),
        ({"is_enable_updated_at_set": 0}, set(), {"trigger_updated_at_set_demo"}),
    ],
)
async def test_config_postgres_schema_init_table_operation_controls(control, expected, unexpected):
    pool = FakeSchemaPool(
        triggers={
            "demo": {
                "trigger_delete_disable_is_protected_demo",
                "trigger_updated_at_set_demo",
            }
        }
    )

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=control_pg_config(control=control),
        config_root_user_password="",
    )

    actual = set().union(*pool.conn.triggers.values())
    assert expected <= actual
    assert actual.isdisjoint(unexpected)
    if control.get("table_delete_disable_row_bulk") == [["*", 4]]:
        assert "func_delete_disable_bulk(4)" in all_sql(pool.conn)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pg_config", "message"),
    [
        ({}, "config_postgres missing"),
        ({"extension": []}, "config_postgres.table missing"),
        ({"table": {"bad": [PRIMARY_ID, {"name": "select", "datatype": "text"}]}}, "reserved keyword"),
        ({"table": {"bad": [PRIMARY_ID, {"name": "tags", "datatype": "text[]", "regex": "x"}]}}, "Regex constraint is not supported"),
        ({"table": {"bad": [PRIMARY_ID, {"name": "title", "datatype": "text", "index": "gin(missing)"}]}}, "references non-existent column"),
        ({"table": {"bad": [PRIMARY_ID, {"name": "rating", "datatype": "integer", "index": "gin(rating)"}]}}, "GIN index is not compatible"),
        ({"table": {"bad": [PRIMARY_ID, {"name": "coordinate", "datatype": "geography(Point, 4326)", "index": "btree(coordinate)"}]}}, "Spatial column"),
        ({"table": {"bad": [PRIMARY_ID, {"name": "code", "datatype": "text", "unique": "missing"}]}}, "Unique constraint"),
    ],
)
async def test_config_postgres_schema_init_rejects_invalid_configurations(pg_config, message):
    with pytest.raises(Exception, match=message):
        await func_postgres_schema_init(
            client_postgres_pool=FakeSchemaPool(),
            client_password_hasher=FakePasswordHasher(),
            config_postgres=pg_config,
            config_root_user_password="",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("columns", "message"),
    [
        ([{"name": "title", "datatype": "text"}], "first column must be exactly"),
        ([{"name": "id", "datatype": "bigserial", "is_primary": 1, "index": "btree\\(id\\)"}], "cannot have more than 3 keys"),
        ([PRIMARY_ID, {"name": "row_id", "datatype": "bigserial", "is_primary": 1}], "can only define one primary column"),
        ([PRIMARY_ID, {"name": "id", "datatype": "bigint"}], "id must only be defined as the first primary column"),
    ],
)
async def test_config_postgres_schema_init_requires_explicit_primary_id(columns, message):
    with pytest.raises(Exception, match=message):
        await func_postgres_schema_init(
            client_postgres_pool=FakeSchemaPool(),
            client_password_hasher=FakePasswordHasher(),
            config_postgres={"table": {"demo": columns}},
            config_root_user_password="",
        )


def test_func_check_allows_owner_columns_without_soft_delete_column():
    from core.function import func_check

    config_postgres = {
        "table": {
            "child_tbl": [
                {"name": "id", "datatype": "bigserial"},
                {"name": "created_by_id", "datatype": "bigint"}
            ]
        }
    }
    func_check(
        app_routes=[],
        config_config_path=None,
        config_function_path=None,
        config_api_namespace=[],
        config_router_path=None,
        config_api={},
        config_allowed_user_storage_backends=[],
        config_allowed_api_storage_backends=[],
        config_postgres=config_postgres
    )



@pytest.mark.asyncio
async def test_config_postgres_custom_sql_index_lifecycle():
    initial_config = {
        "table": {
            "users": [
                PRIMARY_ID,
                {"name": "deactivated_at", "datatype": "smallint", "default": 1}
            ]
        },
        "sql": {
            "index_idx_users_inactive": "CREATE INDEX IF NOT EXISTS idx_users_inactive ON users (id) WHERE deactivated_at = 0",
            "other_custom_query": "SELECT 1"
        }
    }

    pool = FakeSchemaPool(
        tables={"users": {"id": {"type": "bigserial"}, "deactivated_at": {"type": "smallint"}}},
        meta={"users": set()},
        triggers={}
    )

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=initial_config,
        config_root_user_password="",
    )

    assert "idx_users_inactive" in pool.conn.meta["users"]
    assert any("idx_users_inactive" in q[0] for q in pool.conn.queries)
    assert any("SELECT 1" in q[0] for q in pool.conn.queries)

    second_config = {
        "table": {
            "users": [
                PRIMARY_ID,
                {"name": "deactivated_at", "datatype": "smallint", "default": 1}
            ]
        },
        "sql": {
            "other_custom_query": "SELECT 1"
        }
    }

    pool.conn.queries = []

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=second_config,
        config_root_user_password="",
    )

    assert "idx_users_inactive" not in pool.conn.meta["users"]


@pytest.mark.asyncio
async def test_config_postgres_nested_sql_index_lifecycle():
    initial_config = {
        "table": {
            "users": [
                PRIMARY_ID,
                {"name": "deactivated_at", "datatype": "smallint", "default": 1}
            ]
        },
        "sql": {
            "index": {
                "idx_users_inactive": "CREATE INDEX IF NOT EXISTS idx_users_inactive ON users (id) WHERE deactivated_at = 0"
            },
            "other_custom_query": "SELECT 1"
        }
    }

    pool = FakeSchemaPool(
        tables={"users": {"id": {"type": "bigserial"}, "deactivated_at": {"type": "smallint"}}},
        meta={"users": set()},
        triggers={}
    )

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=initial_config,
        config_root_user_password="",
    )

    assert "idx_users_inactive" in pool.conn.meta["users"]
    assert any("idx_users_inactive" in q[0] for q in pool.conn.queries)
    assert any("SELECT 1" in q[0] for q in pool.conn.queries)

    second_config = {
        "table": {
            "users": [
                PRIMARY_ID,
                {"name": "deactivated_at", "datatype": "smallint", "default": 1}
            ]
        },
        "sql": {
            "other_custom_query": "SELECT 1"
        }
    }

    pool.conn.queries = []

    await func_postgres_schema_init(
        client_postgres_pool=pool,
        client_password_hasher=FakePasswordHasher(),
        config_postgres=second_config,
        config_root_user_password="",
    )

    assert "idx_users_inactive" not in pool.conn.meta["users"]


def test_func_check_validates_postgres_duplicate_columns():
    from core.function import func_check

    config_fail = {
        "table": {
            "child_tbl": [
                {"name": "id", "datatype": "bigserial"},
                {"name": "title", "datatype": "text"},
                {"name": "title", "datatype": "text"}
            ]
        }
    }
    with pytest.raises(Exception, match="duplicate column name 'title'"):
        func_check(
            app_routes=[],
            config_config_path=None,
            config_function_path=None,
            config_api_namespace=[],
            config_router_path=None,
            config_api={},
            config_allowed_user_storage_backends=[],
            config_allowed_api_storage_backends=[],
            config_postgres=config_fail
        )
