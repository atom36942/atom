import pytest
import re
from core.app import app
from core.function.app_check import func_check
from core import config

# ===========================================================================
# config_postgres: every table has columns
# ===========================================================================
def test_config_postgres_all_tables_have_columns():
    for table_name, cols in config.config_postgres["table"].items():
        assert isinstance(cols, list), f"{table_name} columns must be a list"
        assert len(cols) > 0, f"{table_name} has no columns"

def test_config_postgres_all_columns_have_name_and_datatype():
    for table_name, cols in config.config_postgres["table"].items():
        for col in cols:
            assert "name" in col, f"{table_name} column missing 'name': {col}"
            assert "datatype" in col, f"{table_name}.{col.get('name')} missing 'datatype'"

def test_config_postgres_no_duplicate_columns():
    for table_name, cols in config.config_postgres["table"].items():
        names = [c["name"] for c in cols]
        dupes = [n for n in set(names) if names.count(n) > 1]
        assert not dupes, f"duplicate columns in {table_name}: {dupes}"

def test_config_postgres_no_reserved_keywords():
    reserved = {"all", "select", "from", "where", "table", "column", "order", "group", "having", "limit", "offset", "create", "drop", "insert", "update", "delete", "index", "constraint", "primary", "foreign", "references", "user", "default", "check", "unique", "null", "not", "and", "or", "in", "is", "true", "false"}
    for table_name, cols in config.config_postgres["table"].items():
        for col in cols:
            assert col["name"].lower() not in reserved, f"{table_name}.{col['name']} is a reserved keyword"

# ===========================================================================
# config_postgres: control flags
# ===========================================================================
def test_config_control_flags_valid():
    control = config.config_postgres.get("control", {})
    bool_keys = ["is_extension", "is_drop_disable_schema", "is_drop_disable_table", "is_truncate_disable", "is_users_delete_child_soft", "is_users_delete_child_hard", "is_users_delete_disable_role", "is_autovacuum_optimize"]
    for key in bool_keys:
        if key in control:
            assert control[key] in (0, 1), f"control.{key} must be 0 or 1, got {control[key]}"

def test_config_control_table_delete_disable_row_valid():
    control = config.config_postgres.get("control", {})
    blocked = control.get("table_delete_disable_row", [])
    assert isinstance(blocked, list), "table_delete_disable_row must be a list"
    if blocked != ["*"]:
        tables = set(config.config_postgres["table"].keys())
        for t in blocked:
            assert t in tables, f"table_delete_disable_row references unknown table '{t}'"

def test_config_control_table_delete_disable_row_bulk_valid():
    control = config.config_postgres.get("control", {})
    bulk = control.get("table_delete_disable_row_bulk", [])
    assert isinstance(bulk, list), "table_delete_disable_row_bulk must be a list"
    for item in bulk:
        assert isinstance(item, (list, tuple)) and len(item) == 2, f"invalid bulk entry: {item}"
        assert isinstance(item[1], int) and item[1] > 0, f"bulk limit must be positive int: {item}"

# ===========================================================================
# config_postgres: index syntax validation
# ===========================================================================
def test_config_postgres_index_syntax():
    for table_name, cols in config.config_postgres["table"].items():
        col_names = {c["name"] for c in cols}
        for col in cols:
            if "index" not in col:
                continue
            for group in col["index"].split("|"):
                group = group.strip()
                assert "(" in group and group.endswith(")"), f"invalid index syntax '{group}' in {table_name}.{col['name']}"
                idx_type, cols_str = group[:-1].split("(", 1)
                idx_type = idx_type.strip().lower()
                assert idx_type in ("btree", "gin", "gist", "hash", "brin", "spgist"), f"unknown index type '{idx_type}' in {table_name}.{col['name']}"
                for ic in cols_str.split(","):
                    assert ic.strip() in col_names, f"index references unknown column '{ic.strip()}' in {table_name}"

# ===========================================================================
# config_postgres: unique constraint syntax
# ===========================================================================
def test_config_postgres_unique_syntax():
    for table_name, cols in config.config_postgres["table"].items():
        col_names = {c["name"] for c in cols}
        for col in cols:
            if "unique" not in col:
                continue
            for group in col["unique"].split("|"):
                for u_col in group.split(","):
                    assert u_col.strip() in col_names, f"unique constraint references unknown column '{u_col.strip()}' in {table_name}"

# ===========================================================================
# config_postgres: check constraint validity
# ===========================================================================
def test_config_postgres_check_valid():
    for table_name, cols in config.config_postgres["table"].items():
        for col in cols:
            if "check" in col:
                assert isinstance(col["check"], str) and len(col["check"]) > 0, f"empty check in {table_name}.{col['name']}"
            if "in" in col:
                assert isinstance(col["in"], (tuple, list)), f"'in' must be tuple in {table_name}.{col['name']}"
                assert len(col["in"]) >= 2, f"'in' needs at least 2 values in {table_name}.{col['name']}"

# ===========================================================================
# config_postgres: regex constraint validation
# ===========================================================================
def test_config_postgres_regex_compiles():
    for table_name, cols in config.config_postgres["table"].items():
        for col in cols:
            if "regex" not in col:
                continue
            try:
                re.compile(col["regex"])
            except re.error as e:
                pytest.fail(f"invalid regex in {table_name}.{col['name']}: {e}")

def test_config_postgres_regex_not_on_arrays():
    for table_name, cols in config.config_postgres["table"].items():
        for col in cols:
            if "regex" in col and "[]" in col.get("datatype", ""):
                pytest.fail(f"regex on array column not supported: {table_name}.{col['name']}")

# ===========================================================================
# config_postgres: mandatory columns
# ===========================================================================
def test_config_postgres_mandatory_columns():
    for table_name, cols in config.config_postgres["table"].items():
        for col in cols:
            if col.get("is_mandatory") == 1 and "default" in col:
                pytest.fail(f"column {table_name}.{col['name']} is mandatory but has default — choose one")

# ===========================================================================
# config_api: comprehensive validation
# ===========================================================================
def test_config_api_all_have_ids():
    for path, cfg in config.config_api.items():
        assert isinstance(cfg, dict), f"{path} config must be dict"
        assert "id" in cfg, f"{path} missing 'id'"
        assert isinstance(cfg["id"], int), f"{path} id must be int"

def test_config_api_ids_unique():
    ids = [cfg["id"] for cfg in config.config_api.values()]
    dupes = [i for i in set(ids) if ids.count(i) > 1]
    assert not dupes, f"duplicate API IDs: {dupes}"

def test_config_api_modes_valid():
    valid_modes = {
        "user_role_check": ["redis", "realtime", "inmemory", "token"],
        "user_is_active_check": ["redis", "realtime", "inmemory", "token"],
        "api_cache_sec": ["redis", "inmemory"],
        "api_ratelimiting_times_sec": ["redis", "inmemory"],
    }
    for path, cfg in config.config_api.items():
        for key, allowed in valid_modes.items():
            if key in cfg:
                setting = cfg[key]
                assert isinstance(setting, (list, tuple)), f"{path}.{key} must be list/tuple"
                assert len(setting) >= 2, f"{path}.{key} too short"
                assert setting[0] in allowed, f"{path}.{key} mode '{setting[0]}' not in {allowed}"

def test_config_api_admin_all_have_role_1():
    for path, cfg in config.config_api.items():
        if path.startswith("/admin/"):
            roles_cfg = cfg.get("user_role_check", [])
            if roles_cfg:
                roles = roles_cfg[1] if isinstance(roles_cfg[0], str) else roles_cfg
                assert 1 in roles, f"{path} missing role 1 in user_role_check"

def test_config_api_ratelimiter_has_3_values():
    for path, cfg in config.config_api.items():
        rl = cfg.get("api_ratelimiting_times_sec")
        if rl:
            assert len(rl) == 3, f"{path} ratelimiter needs (mode, limit, window_sec)"
            assert isinstance(rl[1], int) and rl[1] > 0, f"{path} ratelimiter limit must be positive int"
            assert isinstance(rl[2], int) and rl[2] > 0, f"{path} ratelimiter window must be positive int"

def test_config_api_cache_has_2_values():
    for path, cfg in config.config_api.items():
        cache = cfg.get("api_cache_sec")
        if cache:
            assert len(cache) == 2, f"{path} cache needs (mode, expire_sec)"
            assert isinstance(cache[1], (int, float)) and cache[1] > 0, f"{path} cache expire must be positive"

# ===========================================================================
# config_api: paths match actual routes
# ===========================================================================
def test_config_api_paths_match_routes(state):
    app_paths = {route.path for route in app.routes if hasattr(route, "path")}
    for path in config.config_api:
        assert path in app_paths, f"config_api path '{path}' has no route"

# ===========================================================================
# config switches (config_is_*)
# ===========================================================================
def test_all_switches_binary():
    for key, value in vars(config).items():
        if key.startswith("config_is_"):
            assert value in (None, 0, 1), f"{key} must be 0, 1, or None — got {value}"

# ===========================================================================
# config_cors
# ===========================================================================
def test_cors_origin_valid():
    assert isinstance(config.config_cors_origin, list)
    if "*" in config.config_cors_origin:
        assert len(config.config_cors_origin) == 1, "wildcard cannot coexist with other origins"

def test_cors_method_valid():
    assert isinstance(config.config_cors_method, list)

def test_cors_headers_valid():
    assert isinstance(config.config_cors_headers, list)

def test_cors_credentials_valid():
    assert config.config_is_cors_allow_credentials in (0, 1)
    if config.config_is_cors_allow_credentials == 1:
        assert "*" not in config.config_cors_origin, "credentials=1 with origin=* is insecure"

# ===========================================================================
# config_token
# ===========================================================================
def test_token_secret_key_exists():
    assert config.config_token_secret_key is not None
    assert len(str(config.config_token_secret_key)) > 0

def test_token_expiry_positive():
    assert config.config_token_expiry_sec > 0
    assert config.config_token_refresh_expiry_sec > 0
    assert config.config_token_refresh_expiry_sec > config.config_token_expiry_sec

def test_token_key_valid():
    assert isinstance(config.config_token_key, list)
    assert "id" in config.config_token_key

# ===========================================================================
# config_auth_type
# ===========================================================================
def test_auth_type_valid():
    assert isinstance(config.config_auth_type, list)
    assert len(config.config_auth_type) > 0
    for t in config.config_auth_type:
        assert isinstance(t, int), f"auth_type must be int: {t}"

# ===========================================================================
# config_table (buffer, retention)
# ===========================================================================
def test_config_table_buffer_valid():
    for table, cfg in config.config_table.items():
        if "buffer" in cfg:
            assert isinstance(cfg["buffer"], int) and cfg["buffer"] > 0, f"{table} buffer must be positive"

def test_config_table_retention_valid():
    for table, cfg in config.config_table.items():
        if "retention_day" in cfg:
            assert isinstance(cfg["retention_day"], int) and cfg["retention_day"] > 0, f"{table} retention_day must be positive"

# ===========================================================================
# config_table_create_my / public / read_public
# ===========================================================================
def test_table_create_my_no_users():
    assert "users" not in config.config_table_create_my, "users table must not be in config_table_create_my"

def test_table_create_public_no_users():
    assert "users" not in config.config_table_create_public, "users table must not be in config_table_create_public"

def test_table_create_public_subset_of_my():
    """Public should generally be a subset or equal to my."""
    for t in config.config_table_create_public:
        assert t in config.config_table_create_my, f"'{t}' in public but not in my"

# ===========================================================================
# config_column_blocked
# ===========================================================================
def test_column_blocked_is_list():
    assert isinstance(config.config_column_blocked, list)
    assert len(config.config_column_blocked) > 0

def test_column_blocked_essential_fields():
    essentials = ["is_active", "role", "created_at"]
    for f in essentials:
        assert f in config.config_column_blocked, f"'{f}' should be in column_blocked"

# ===========================================================================
# config_column_single_update
# ===========================================================================
def test_column_single_update_is_list():
    assert isinstance(config.config_column_single_update, list)

def test_column_single_update_sensitive_fields():
    sensitive = ["password", "email", "mobile"]
    for f in sensitive:
        assert f in config.config_column_single_update, f"'{f}' should be in column_single_update"

# ===========================================================================
# config_api_roles / config_api_roles_auth
# ===========================================================================
def test_api_roles_valid():
    assert isinstance(config.config_api_roles, list)
    assert "admin" in config.config_api_roles
    assert "auth" in config.config_api_roles
    assert "my" in config.config_api_roles
    assert "public" in config.config_api_roles

def test_api_roles_auth_valid():
    assert isinstance(config.config_api_roles_auth, list)
    assert "/admin/" in config.config_api_roles_auth
    assert "/my/" in config.config_api_roles_auth

# ===========================================================================
# config_regex
# ===========================================================================
def test_regex_config_compiles():
    for key, (pattern, msg) in config.config_regex.items():
        compiled = re.compile(pattern)
        assert compiled, f"regex for '{key}' failed to compile"
        assert isinstance(msg, str) and len(msg) > 0, f"regex '{key}' message must be non-empty"

def test_regex_username_samples():
    pattern = re.compile(config.config_regex["username"][0])
    assert pattern.match("valid_user")
    assert pattern.match("abc123")
    assert not pattern.match("AB")
    assert not pattern.match("a")
    assert not pattern.match("has space")
    assert not pattern.match("_leading")
    assert not pattern.match("trailing_")

def test_regex_password_samples():
    pattern = re.compile(config.config_regex["password"][0])
    assert pattern.match("password123")
    assert pattern.match("12345678")
    assert not pattern.match("short")
    assert not pattern.match("has space")

# ===========================================================================
# config_sql
# ===========================================================================
def test_config_sql_valid():
    assert isinstance(config.config_sql, dict)
    for key, val in config.config_sql.items():
        if isinstance(val, str):
            assert len(val) > 0, f"config_sql.{key} is empty"
            assert "select" in val.lower(), f"config_sql.{key} must be a SELECT query"

# ===========================================================================
# config_expiry_sec_otp
# ===========================================================================
def test_otp_expiry_valid():
    assert isinstance(config.config_expiry_sec_otp, int)
    assert config.config_expiry_sec_otp > 0

# ===========================================================================
# config_s3 limits
# ===========================================================================
def test_s3_limits_valid():
    assert isinstance(config.config_s3_limit_kb, (int, float)) and config.config_s3_limit_kb > 0
    assert isinstance(config.config_s3_upload_limit_count, int) and config.config_s3_upload_limit_count > 0
    assert isinstance(config.config_s3_presigned_expire_sec, int) and config.config_s3_presigned_expire_sec > 0

# ===========================================================================
# func_check (full application checks)
# ===========================================================================
@pytest.mark.asyncio
async def test_func_check_passes(state):
    """The full application consistency check should pass on a healthy config."""
    await func_check(
        app_routes=list(app.routes),
        current_config_api=state.config_api,
        allowed_roles=state.config_api_roles,
        api_roles_auth=state.config_api_roles_auth,
        client_postgres_pool=state.client_postgres_pool
    )

@pytest.mark.asyncio
async def test_func_check_invalid_roles_auth_type(state):
    with pytest.raises(Exception, match="config_api_roles_auth must be a list"):
        await func_check(
            app_routes=list(app.routes),
            current_config_api=state.config_api,
            allowed_roles=state.config_api_roles,
            api_roles_auth="invalid",
            client_postgres_pool=state.client_postgres_pool
        )
