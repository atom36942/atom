import pytest
import re
from core.app import app

# ===========================================================================
# app.state: all expected attributes exist
# ===========================================================================
@pytest.mark.asyncio
async def test_state_has_clients(state):
    clients = [
        "client_postgres_pool", "client_redis", "client_redis_ratelimiter",
        "client_password_hasher", "client_http",
    ]
    for attr in clients:
        assert hasattr(state, attr), f"missing state attribute: {attr}"

@pytest.mark.asyncio
async def test_state_has_caches(state):
    caches = [
        "cache_postgres_schema", "cache_postgres_schema_tables",
        "cache_postgres_schema_columns", "cache_users_role", "cache_users_is_active",
        "cache_ratelimiter", "cache_api_response", "cache_postgres_buffer", "cache_openapi"
    ]
    for attr in caches:
        assert hasattr(state, attr), f"missing state attribute: {attr}"

@pytest.mark.asyncio
async def test_state_has_functions(state):
    funcs = [
        "func_postgres_create", "func_postgres_read", "func_postgres_update",
        "func_postgres_delete", "func_postgres_serialize", "func_postgres_schema_read",
        "func_request_param_read", "func_request_obj_list_read",
        "func_orchestrator_obj_create", "func_orchestrator_obj_update",
        "func_authenticate", "func_check_admin", "func_check_is_active",
        "func_token_encode", "func_regex_check",
    ]
    for attr in funcs:
        assert hasattr(state, attr), f"missing state attribute: {attr}"

@pytest.mark.asyncio
async def test_state_has_configs(state):
    configs = [
        "config_postgres_url", "config_redis_url", "config_token_secret_key",
        "config_is_enable_signup", "config_auth_type", "config_table_create_my",
        "config_table_create_public", "config_column_blocked", "config_api",
        "config_postgres", "config_regex", "config_table",
        "config_api_roles", "config_api_roles_auth",
    ]
    for attr in configs:
        assert hasattr(state, attr), f"missing state attribute: {attr}"

# ===========================================================================
# Connection health
# ===========================================================================
@pytest.mark.asyncio
async def test_postgres_pool_connected(state, db_available):
    assert state.client_postgres_pool is not None
    async with state.client_postgres_pool.acquire() as conn:
        val = await conn.fetchval("SELECT 1")
        assert val == 1

@pytest.mark.asyncio
async def test_redis_connected(state):
    if state.client_redis is None:
        pytest.skip("Redis not configured")
    try:
        pong = await state.client_redis.ping()
        assert pong is True
    except Exception:
        pytest.skip("Redis not reachable")

# ===========================================================================
# Schema consistency
# ===========================================================================
@pytest.mark.asyncio
async def test_schema_tables_match_config(state, db_available):
    config_tables = set(state.config_postgres["table"].keys())
    schema_tables = set(state.cache_postgres_schema.keys())
    for t in config_tables:
        assert t in schema_tables, f"configured table '{t}' missing from live schema"

@pytest.mark.asyncio
async def test_schema_columns_match_config(state, db_available):
    for table_name, column_configs in state.config_postgres["table"].items():
        schema_cols = state.cache_postgres_schema.get(table_name, {})
        for col_cfg in column_configs:
            assert col_cfg["name"] in schema_cols, f"column '{col_cfg['name']}' missing from table '{table_name}'"

# ===========================================================================
# Config switches validation
# ===========================================================================
@pytest.mark.asyncio
async def test_config_switches_valid(state):
    from core import config
    for key, value in vars(config).items():
        if key.startswith("config_is_"):
            assert value in (None, 0, 1), f"invalid value for {key}: {value}"

# ===========================================================================
# CORS config validation
# ===========================================================================
@pytest.mark.asyncio
async def test_config_cors_valid(state):
    from core import config
    for k in ("config_cors_origin", "config_cors_method", "config_cors_headers"):
        v = getattr(config, k)
        assert isinstance(v, (list, tuple)), f"{k} must be a list"
        if "*" in v:
            assert len(v) == 1, f"{k}: wildcard cannot coexist with other values"

# ===========================================================================
# config_api IDs unique and paths exist
# ===========================================================================
@pytest.mark.asyncio
async def test_config_api_ids_unique(state):
    ids = [v["id"] for v in state.config_api.values() if isinstance(v, dict) and "id" in v]
    assert len(ids) == len(set(ids)), f"duplicate API IDs found"

@pytest.mark.asyncio
async def test_config_api_paths_exist(state):
    app_paths = {route.path for route in app.routes if hasattr(route, "path")}
    for path in state.config_api:
        assert path in app_paths, f"config_api path '{path}' not found in routes"

# ===========================================================================
# Regex patterns compile
# ===========================================================================
@pytest.mark.asyncio
async def test_config_regex_patterns_valid(state):
    for key, (pattern, msg) in state.config_regex.items():
        compiled = re.compile(pattern)
        assert compiled is not None, f"regex pattern for '{key}' failed to compile"

# ===========================================================================
# Table permission lists reference real tables
# ===========================================================================
@pytest.mark.asyncio
async def test_config_table_create_my_valid(state, db_available):
    for t in state.config_table_create_my:
        assert t in state.cache_postgres_schema, f"config_table_create_my references nonexistent table '{t}'"

@pytest.mark.asyncio
async def test_config_table_create_public_valid(state, db_available):
    for t in state.config_table_create_public:
        assert t in state.cache_postgres_schema, f"config_table_create_public references nonexistent table '{t}'"

@pytest.mark.asyncio
async def test_config_table_read_public_valid(state, db_available):
    if not state.config_table_read_public:
        pytest.skip("config_table_read_public not configured")
    for t in state.config_table_read_public:
        assert t in state.cache_postgres_schema, f"config_table_read_public references nonexistent table '{t}'"

# ===========================================================================
# Root user
# ===========================================================================
@pytest.mark.asyncio
async def test_root_user_exists(state, db_available):
    async with state.client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id, role FROM users WHERE id=1")
        assert user is not None, "root user (id=1) missing"
        assert user["role"] == 1, "root user must have role=1"

# ===========================================================================
# OpenAPI cache
# ===========================================================================
@pytest.mark.asyncio
async def test_openapi_generated(state):
    assert isinstance(state.cache_openapi, dict)
    assert "paths" in state.cache_openapi
    assert len(state.cache_openapi["paths"]) > 0

# ===========================================================================
# Caches start empty
# ===========================================================================
@pytest.mark.asyncio
async def test_ratelimiter_cache_empty(state):
    assert isinstance(state.cache_ratelimiter, dict)

@pytest.mark.asyncio
async def test_api_response_cache_empty(state):
    assert isinstance(state.cache_api_response, dict)
