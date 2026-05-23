import sys
import time
from pathlib import Path

import pytest
from fastapi import Request, responses

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import config
from core.app import app, middleware
from core.function import (
    func_middleware_api_cache_get,
    func_middleware_api_cache_set,
    func_middleware_check_ratelimiter,
    func_middleware_check_user_deactivated,
    func_middleware_check_user_deleted,
    func_middleware_check_user_role,
    func_postgres_create,
    func_postgres_update,
    func_regex_check,
)


@pytest.fixture(autouse=True)
def restore_app_state():
    old_state = app.state._state.copy()
    yield
    app.state._state = old_state



class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeUserConn:
    def __init__(self, *, role=1, deactivated_at=None, deleted_at=None):
        self.role = role
        self.deactivated_at = deactivated_at
        self.deleted_at = deleted_at
        self.fetch_calls = []

    async def fetch(self, sql, *args):
        self.fetch_calls.append((sql, args))
        normalized = " ".join(sql.lower().split())
        if "select role from users" in normalized:
            return [{"role": self.role}]
        if "select id, deactivated_at from users" in normalized:
            return [{"id": args[0], "deactivated_at": self.deactivated_at}]
        if "select deleted_at from users" in normalized:
            return [{"id": args[0], "deleted_at": self.deleted_at}]
        return []


class FakeUserPool:
    def __init__(self, *, role=1, deactivated_at=None, deleted_at=None):
        self.conn = FakeUserConn(role=role, deactivated_at=deactivated_at, deleted_at=deleted_at)

    def acquire(self):
        return FakeAcquire(self.conn)


class FakeRedisPipeline:
    def __init__(self, redis):
        self.redis = redis
        self.ops = []

    def incr(self, key):
        self.ops.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self.ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        for op in self.ops:
            if op[0] == "incr":
                self.redis.store[op[1]] = str(int(self.redis.store.get(op[1], 0)) + 1)
            elif op[0] == "expire":
                self.redis.expires[op[1]] = op[2]


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.expires = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = str(value)
        self.expires[key] = ttl

    def pipeline(self):
        return FakeRedisPipeline(self)

    async def aclose(self):
        pass


def make_request(path, *, query_string=b"", method="GET", body=b"", app=None):
    async def receive():
        return {"type": "http.request", "body": body}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "app": app,
    }
    return Request(scope, receive=receive)


def test_config_api_paths_modes_ids_and_admin_roles_match_app_routes():
    app_paths = {route.path for route in app.routes if hasattr(route, "path")}
    allowed_modes = {
        "user_role_check": {"redis", "realtime", "inmemory", "token"},
        "user_active_check": {"redis", "realtime", "inmemory", "token"},
        "user_deleted_check": {"redis", "realtime", "inmemory", "token"},
        "api_cache_sec": {"redis", "inmemory"},
        "api_ratelimiting_times_sec": {"redis", "inmemory"},
    }

    missing = set(config.config_api) - app_paths
    assert missing == set()

    ids = [entry.get("id") for entry in config.config_api.values()]
    assert all(isinstance(api_id, int) for api_id in ids)
    assert len(ids) == len(set(ids))

    for path, entry in config.config_api.items():
        for key, modes in allowed_modes.items():
            if key in entry:
                setting = entry[key]
                assert isinstance(setting, list)
                if key != "user_role_check" and setting[0] in ("", None):
                    assert len(setting) >= 1
                    continue
                assert setting[0] in modes
                if key in {"user_active_check", "user_deleted_check"}:
                    assert len(setting) >= 1
                else:
                    assert len(setting) >= 2
        if path.startswith("/admin/"):
            assert "user_role_check" in entry
            assert 1 in entry["user_role_check"][1]


def test_config_namespaces_are_normalized_and_auth_scopes_are_nested():
    namespaces = config.config_api_namespace
    auth_namespaces = config.config_api_namespace_auth
    user_namespaces = config.config_api_namespace_user

    assert len(namespaces) == len(set(namespaces))
    assert all(item.startswith("/") and item.endswith("/") for item in namespaces)
    assert all(item in namespaces for item in auth_namespaces)
    assert all(item in auth_namespaces for item in user_namespaces)
    assert "/public/" in namespaces
    assert "/public/" not in auth_namespaces
    assert "/admin/" in auth_namespaces


def test_config_table_lists_reference_known_tables_and_sensitive_columns():
    table_names = set(config.config_postgres["table"]) | {"spatial_ref_sys"}
    user_columns = {"id"} | {column["name"] for column in config.config_postgres["table"]["users"]}
    all_columns = {
        column["name"]
        for columns in config.config_postgres["table"].values()
        for column in columns
    }

    assert set(config.config_table).issubset(table_names)
    assert all("buffer" not in table_config for table_config in config.config_table.values())
    assert all(
        table_config["buffer_limit"] > 0
        for table_config in config.config_table.values()
        if "buffer_limit" in table_config
    )
    assert set(config.config_table_create_disable_my).issubset(table_names)
    assert set(config.config_table_create_enable_public).issubset(table_names)
    assert set(config.config_table_read_enable_public) == {"*"} or set(config.config_table_read_enable_public).issubset(table_names)
    assert set(config.config_admin_columns).issubset(all_columns)
    assert set(config.config_column_enable_single_update).issubset(user_columns)
    assert set(config.config_token_key).issubset(user_columns)


def test_config_defaults_have_sane_bounds_and_required_security_settings():
    assert config.config_otp_length >= 4
    assert config.config_expiry_sec_otp > 0
    assert config.config_query_limit_default > 0
    assert config.config_buffer_limit > 0
    assert config.config_obj_list_limit >= config.config_buffer_limit
    assert config.config_blob_limit_kb > 0
    assert config.config_blob_upload_limit_count > 0
    assert config.config_upload_url_expire_sec > 0
    assert config.config_postgres_min_connection > 0
    assert config.config_postgres_max_connection >= config.config_postgres_min_connection
    assert len(config.config_token_secret_key) >= 32
    assert config.config_cors_expose_headers == list(dict.fromkeys(config.config_cors_expose_headers))
    assert "x-cache" in {header.lower() for header in config.config_cors_expose_headers}


def test_config_sql_queries_match_required_cache_and_profile_schema():
    table_columns = {
        table: {"id"} | {column["name"] for column in columns}
        for table, columns in config.config_postgres["table"].items()
    }

    assert {"users_role", "users_deactivated", "profile_metadata"} <= set(config.config_sql)
    assert {"id", "role", "deactivated_at"} <= table_columns["users"]
    assert {"id", "created_by_id"} <= table_columns["test"]
    assert isinstance(config.config_sql["profile_metadata"], dict)
    assert set(config.config_sql["profile_metadata"]) == {"test_count", "test_object"}
    assert "from users" in config.config_sql["users_role"].lower()
    assert "from users" in config.config_sql["users_deactivated"].lower()
    assert all("created_by_id=$1" in query for query in config.config_sql["profile_metadata"].values())


@pytest.mark.asyncio
async def test_config_api_cache_inmemory_sets_and_hits_cached_response():
    calls = []

    async def api_function(_request):
        calls.append("run")
        return responses.JSONResponse({"status": 1, "message": len(calls)})

    cache = {}
    cfg = {"/cached": {"api_cache_sec": ["inmemory", 30]}}

    app.state.config_api = cfg
    app.state.client_redis = None
    app.state.cache_api_response = cache
    app.state.config_is_enable_log_api = 0
    app.state.config_api_namespace_user = []
    app.state.config_api_namespace_auth = []

    first = await middleware(
        request=make_request("/cached", query_string=b"a=1", app=app),
        api_function=api_function,
    )
    second = await middleware(
        request=make_request("/cached", query_string=b"a=1", app=app),
        api_function=api_function,
    )

    assert first.status_code == 200
    assert second.headers["x-cache"] == "hit"
    assert second.body == first.body
    assert calls == ["run"]


@pytest.mark.asyncio
async def test_config_api_cache_redis_sets_and_hits_cached_response():
    calls = []
    redis = FakeRedis()

    async def api_function(_request):
        calls.append("run")
        return responses.JSONResponse({"status": 1, "message": len(calls)})

    cfg = {"/cached": {"api_cache_sec": ["redis", 15]}}

    app.state.config_api = cfg
    app.state.client_redis = redis
    app.state.cache_api_response = {}
    app.state.config_is_enable_log_api = 0
    app.state.config_api_namespace_user = []
    app.state.config_api_namespace_auth = []

    first = await middleware(
        request=make_request("/cached", app=app),
        api_function=api_function,
    )
    second = await middleware(
        request=make_request("/cached", app=app),
        api_function=api_function,
    )

    assert first.status_code == 200
    assert second.headers["x-cache"] == "hit"
    assert calls == ["run"]
    assert list(redis.expires.values()) == [15]


@pytest.mark.asyncio
async def test_config_api_cache_empty_or_missing_mode_is_off():
    for cfg in [
        {"/cached": {}},
        {"/cached": {"api_cache_sec": [""]}},
        {"/cached": {"api_cache_sec": ["", 30]}},
        {"/cached": {"api_cache_sec": [None]}},
        {"/cached": {"api_cache_sec": [None, 30]}},
    ]:
        cache = {"existing": "untouched"}
        response = responses.JSONResponse({"status": 1})

        assert await func_middleware_api_cache_get(path="/cached", query_params={}, config_api=cfg, client_redis=None, user_id=1, cache_api_response=cache, config_api_namespace_user=[]) is None
        returned = await func_middleware_api_cache_set(path="/cached", query_params={}, response=response, config_api=cfg, client_redis=None, user_id=1, cache_api_response=cache, config_api_namespace_user=[])

        assert returned is response
        assert cache == {"existing": "untouched"}


@pytest.mark.asyncio
async def test_config_api_cache_non_positive_ttl_is_off():
    for cfg in [
        {"/cached": {"api_cache_sec": ["inmemory", 0]}},
        {"/cached": {"api_cache_sec": ["inmemory", -1]}},
    ]:
        cache = {}
        response = responses.JSONResponse({"status": 1})

        returned = await func_middleware_api_cache_set(path="/cached", query_params={}, response=response, config_api=cfg, client_redis=None, user_id=1, cache_api_response=cache, config_api_namespace_user=[])

        assert returned is response
        assert cache == {}


@pytest.mark.asyncio
async def test_config_api_ratelimiter_inmemory_allows_until_limit_then_blocks():
    cache = {}
    cfg = {"/limited": {"api_ratelimiting_times_sec": ["inmemory", 2, 60]}}

    await func_middleware_check_ratelimiter(
        client_redis=None,
        config_api=cfg,
        url_path="/limited",
        identifier="user-1",
        cache_ratelimiter=cache,
    )
    await func_middleware_check_ratelimiter(
        client_redis=None,
        config_api=cfg,
        url_path="/limited",
        identifier="user-1",
        cache_ratelimiter=cache,
    )
    with pytest.raises(Exception, match="ratelimiter exceeded"):
        await func_middleware_check_ratelimiter(
            client_redis=None,
            config_api=cfg,
            url_path="/limited",
            identifier="user-1",
            cache_ratelimiter=cache,
        )


@pytest.mark.asyncio
async def test_config_api_ratelimiter_redis_uses_pipeline_and_blocks_on_existing_count():
    redis = FakeRedis()
    cfg = {"/limited": {"api_ratelimiting_times_sec": ["redis", 2, 60]}}

    await func_middleware_check_ratelimiter(
        client_redis=redis,
        config_api=cfg,
        url_path="/limited",
        identifier="user-1",
        cache_ratelimiter={},
    )
    assert redis.store["ratelimiter:/limited:user-1"] == "1"
    assert redis.expires["ratelimiter:/limited:user-1"] == 60

    redis.store["ratelimiter:/limited:user-1"] = "2"
    with pytest.raises(Exception, match="ratelimiter exceeded"):
        await func_middleware_check_ratelimiter(
            client_redis=redis,
            config_api=cfg,
            url_path="/limited",
            identifier="user-1",
            cache_ratelimiter={},
        )


@pytest.mark.asyncio
async def test_config_api_ratelimiter_empty_or_missing_mode_is_off():
    for cfg in [
        {"/limited": {}},
        {"/limited": {"api_ratelimiting_times_sec": [""]}},
        {"/limited": {"api_ratelimiting_times_sec": ["", 2, 60]}},
        {"/limited": {"api_ratelimiting_times_sec": [None]}},
        {"/limited": {"api_ratelimiting_times_sec": [None, 2, 60]}},
    ]:
        cache = {}

        await func_middleware_check_ratelimiter(
            client_redis=None,
            config_api=cfg,
            url_path="/limited",
            identifier="user-1",
            cache_ratelimiter=cache,
        )

        assert cache == {}


@pytest.mark.asyncio
async def test_config_api_ratelimiter_non_positive_numbers_are_off():
    for cfg in [
        {"/limited": {"api_ratelimiting_times_sec": ["inmemory", 0, 60]}},
        {"/limited": {"api_ratelimiting_times_sec": ["inmemory", -1, 60]}},
        {"/limited": {"api_ratelimiting_times_sec": ["inmemory", 10, 0]}},
        {"/limited": {"api_ratelimiting_times_sec": ["inmemory", 10, -1]}},
    ]:
        cache = {}

        await func_middleware_check_ratelimiter(
            client_redis=None,
            config_api=cfg,
            url_path="/limited",
            identifier="user-1",
            cache_ratelimiter=cache,
        )

        assert cache == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "kwargs"),
    [
        ("token", {"user_dict": {"id": 1, "role": 1}}),
        ("inmemory", {"user_dict": {"id": 1}, "cache_users_role": {1: 1}}),
        ("realtime", {"user_dict": {"id": 1}, "client_postgres_pool": FakeUserPool(role=1)}),
        ("redis", {"user_dict": {"id": 1}, "client_redis": FakeRedis(), "client_postgres_pool": FakeUserPool(role=1)}),
    ],
)
async def test_config_api_user_role_check_all_supported_modes_allow_role_one(mode, kwargs):
    cfg = {"/admin/protected": {"user_role_check": [mode, [1]]}}

    await func_middleware_check_user_role(
        user_dict=kwargs["user_dict"],
        url_path="/admin/protected",
        config_api=cfg,
        client_postgres_pool=kwargs.get("client_postgres_pool"),
        client_redis=kwargs.get("client_redis"),
        cache_users_role=kwargs.get("cache_users_role", {}),
        config_redis_cache_ttl_sec=60,
    )


@pytest.mark.asyncio
async def test_config_api_user_role_check_rejects_missing_invalid_and_denied_roles():
    cfg = {"/admin/protected": {"user_role_check": ["token", [1]]}}

    with pytest.raises(Exception, match="user role missing"):
        await func_middleware_check_user_role(user_dict={"id": 1}, url_path="/admin/protected", config_api=cfg, client_postgres_pool=None, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)
    with pytest.raises(Exception, match="invalid user role type"):
        await func_middleware_check_user_role(user_dict={"id": 1, "role": "abc"}, url_path="/admin/protected", config_api=cfg, client_postgres_pool=None, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)
    with pytest.raises(Exception, match="access denied"):
        await func_middleware_check_user_role(user_dict={"id": 1, "role": 2}, url_path="/admin/protected", config_api=cfg, client_postgres_pool=None, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "kwargs"),
    [
        ("token", {"user_dict": {"id": 1, "deactivated_at": None}}),
        ("inmemory", {"user_dict": {"id": 1}, "cache_users_deactivated": {1: None}}),
        ("realtime", {"user_dict": {"id": 1}, "client_postgres_pool": FakeUserPool(deactivated_at=None)}),
        ("redis", {"user_dict": {"id": 1}, "client_redis": FakeRedis(), "client_postgres_pool": FakeUserPool(deactivated_at=None)}),
    ],
)
async def test_config_api_user_active_check_all_supported_modes_allow_active_user(mode, kwargs):
    cfg = {"/admin/protected": {"user_active_check": [mode, 1]}}

    await func_middleware_check_user_deactivated(
        user_dict=kwargs["user_dict"],
        url_path="/admin/protected",
        config_api=cfg,
        client_postgres_pool=kwargs.get("client_postgres_pool"),
        client_redis=kwargs.get("client_redis"),
        cache_users_deactivated=kwargs.get("cache_users_deactivated", {}),
        config_redis_cache_ttl_sec=60,
    )


@pytest.mark.asyncio
async def test_config_api_user_active_check_rejects_inactive_and_can_be_disabled():
    enabled_cfg = {"/admin/protected": {"user_active_check": ["token", 1]}}
    disabled_cfg = {"/admin/protected": {"user_active_check": ["token", 0]}}

    with pytest.raises(Exception, match="user not active"):
        await func_middleware_check_user_deactivated(user_dict={"id": 1, "deactivated_at": "2026-05-21"}, url_path="/admin/protected", config_api=enabled_cfg, client_postgres_pool=None, client_redis=None, cache_users_deactivated={}, config_redis_cache_ttl_sec=60)

    await func_middleware_check_user_deactivated(user_dict={"id": 1, "deactivated_at": "2026-05-21"}, url_path="/admin/protected", config_api=disabled_cfg, client_postgres_pool=None, client_redis=None, cache_users_deactivated={}, config_redis_cache_ttl_sec=60)


@pytest.mark.asyncio
async def test_config_api_user_active_check_accepts_mode_only_and_empty_mode_off():
    mode_only_cfg = {"/admin/protected": {"user_active_check": ["token"]}}
    empty_mode_cfg = {"/admin/protected": {"user_active_check": [""]}}
    none_mode_cfg = {"/admin/protected": {"user_active_check": [None]}}

    with pytest.raises(Exception, match="user not active"):
        await func_middleware_check_user_deactivated(user_dict={"id": 1, "deactivated_at": "2026-05-21"}, url_path="/admin/protected", config_api=mode_only_cfg, client_postgres_pool=None, client_redis=None, cache_users_deactivated={}, config_redis_cache_ttl_sec=60)

    await func_middleware_check_user_deactivated(user_dict={"id": 1, "deactivated_at": "2026-05-21"}, url_path="/admin/protected", config_api=empty_mode_cfg, client_postgres_pool=None, client_redis=None, cache_users_deactivated={}, config_redis_cache_ttl_sec=60)
    await func_middleware_check_user_deactivated(user_dict={"id": 1, "deactivated_at": "2026-05-21"}, url_path="/admin/protected", config_api=none_mode_cfg, client_postgres_pool=None, client_redis=None, cache_users_deactivated={}, config_redis_cache_ttl_sec=60)


@pytest.mark.parametrize("mode, kwargs", [
    ("token", {"user_dict": {"id": 1, "deleted_at": None}}),
    ("inmemory", {"user_dict": {"id": 1}, "cache_users_deleted": {1: None}}),
    ("realtime", {"user_dict": {"id": 1}, "client_postgres_pool": FakeUserPool(deleted_at=None)}),
    ("redis", {"user_dict": {"id": 1}, "client_redis": FakeRedis(), "client_postgres_pool": FakeUserPool(deleted_at=None)}),
])
@pytest.mark.asyncio
async def test_func_middleware_check_user_deleted_modes(mode, kwargs):
    """Test user_deleted_check configuration strictly applies the specified mode."""
    cfg = {"/admin/protected": {"user_deleted_check": [mode, 1]}}
    await func_middleware_check_user_deleted(
        user_dict=kwargs.get("user_dict"),
        url_path="/admin/protected",
        config_api=cfg,
        client_postgres_pool=kwargs.get("client_postgres_pool"),
        client_redis=kwargs.get("client_redis"),
        cache_users_deleted=kwargs.get("cache_users_deleted", {}),
        config_redis_cache_ttl_sec=60
    )

@pytest.mark.asyncio
async def test_func_middleware_check_user_deleted_flag():
    """Test user_deleted_check configuration flag respects 0 and 1."""
    enabled_cfg = {"/admin/protected": {"user_deleted_check": ["token", 1]}}
    disabled_cfg = {"/admin/protected": {"user_deleted_check": ["token", 0]}}
    with pytest.raises(Exception, match="user is deleted"):
        await func_middleware_check_user_deleted(user_dict={"id": 1, "deleted_at": "2026-05-21T12:00:00Z"}, url_path="/admin/protected", config_api=enabled_cfg, client_postgres_pool=None, client_redis=None, cache_users_deleted={}, config_redis_cache_ttl_sec=60)
    # Should not raise
    await func_middleware_check_user_deleted(user_dict={"id": 1, "deleted_at": "2026-05-21T12:00:00Z"}, url_path="/admin/protected", config_api=disabled_cfg, client_postgres_pool=None, client_redis=None, cache_users_deleted={}, config_redis_cache_ttl_sec=60)


@pytest.mark.asyncio
async def test_config_api_user_deleted_check_accepts_mode_only_and_empty_mode_off():
    mode_only_cfg = {"/admin/protected": {"user_deleted_check": ["token"]}}
    empty_mode_cfg = {"/admin/protected": {"user_deleted_check": [""]}}
    none_mode_cfg = {"/admin/protected": {"user_deleted_check": [None]}}

    with pytest.raises(Exception, match="user is deleted"):
        await func_middleware_check_user_deleted(user_dict={"id": 1, "deleted_at": "2026-05-21T12:00:00Z"}, url_path="/admin/protected", config_api=mode_only_cfg, client_postgres_pool=None, client_redis=None, cache_users_deleted={}, config_redis_cache_ttl_sec=60)

    await func_middleware_check_user_deleted(user_dict={"id": 1, "deleted_at": "2026-05-21T12:00:00Z"}, url_path="/admin/protected", config_api=empty_mode_cfg, client_postgres_pool=None, client_redis=None, cache_users_deleted={}, config_redis_cache_ttl_sec=60)
    await func_middleware_check_user_deleted(user_dict={"id": 1, "deleted_at": "2026-05-21T12:00:00Z"}, url_path="/admin/protected", config_api=none_mode_cfg, client_postgres_pool=None, client_redis=None, cache_users_deleted={}, config_redis_cache_ttl_sec=60)


@pytest.mark.asyncio
async def test_config_regex_accepts_valid_username_password_and_rejects_invalid_values():
    await func_regex_check(
        config_regex=config.config_regex,
        obj_list=[{"username": "user_1", "password": "secret1"}],
    )

    with pytest.raises(Exception, match="Username must be"):
        await func_regex_check(config_regex=config.config_regex, obj_list=[{"username": "BadUser"}])
    with pytest.raises(Exception, match="Password must be"):
        await func_regex_check(config_regex=config.config_regex, obj_list=[{"password": "bad pass"}])


@pytest.mark.asyncio
async def test_postgres_create_rejects_missing_or_empty_object_data():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    common = {
        "client_postgres_pool": None,
        "client_postgres_conn": None,
        "client_password_hasher": None,
        "func_postgres_serialize": passthrough_serialize,
        "cache_postgres_schema": {},
        "mode": "now",
        "table": "test",
        "config_buffer_limit": config.config_buffer_limit,
        "cache_postgres_buffer_create": {},
        "config_regex": config.config_regex,
        "func_regex_check": func_regex_check,
        "config_table": config.config_table,
        "config_obj_list_limit": config.config_obj_list_limit,
    }

    with pytest.raises(Exception, match="object list required"):
        await func_postgres_create(obj_list=[], cache_postgres_buffer_create=common["cache_postgres_buffer_create"], **{k: v for k, v in common.items() if k != "cache_postgres_buffer_create"})
    with pytest.raises(Exception, match="object data required"):
        await func_postgres_create(obj_list=[{}], cache_postgres_buffer_create=common["cache_postgres_buffer_create"], **{k: v for k, v in common.items() if k != "cache_postgres_buffer_create"})


@pytest.mark.asyncio
async def test_postgres_create_rejects_obj_list_over_limit():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    with pytest.raises(Exception, match="maximum 1 objects allowed"):
        await func_postgres_create(
            client_postgres_pool=None,
            client_postgres_conn=None,
            client_password_hasher=None,
            func_postgres_serialize=passthrough_serialize,
            cache_postgres_schema={},
            mode="now",
            table="test",
            obj_list=[{"title": "one"}, {"title": "two"}],
            config_buffer_limit=0,
            cache_postgres_buffer_create={},
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_table=config.config_table,
            config_obj_list_limit=1,
        )


@pytest.mark.asyncio
async def test_postgres_create_serializes_before_buffering_and_releases_without_reserializing():
    calls = []

    async def fake_serialize(**kwargs):
        calls.append(kwargs)
        return [dict(item, title=f"serialized:{item['title']}") for item in kwargs["obj_list"]]

    class FakeConn:
        async def fetch(self, sql, *args):
            return [{"id": 1}, {"id": 2}]

    buffer = {}
    common = {
        "client_postgres_pool": None,
        "client_postgres_conn": FakeConn(),
        "client_password_hasher": None,
        "func_postgres_serialize": fake_serialize,
        "cache_postgres_schema": {},
        "mode": "buffer",
        "table": "test",
        "config_buffer_limit": 2,
        "cache_postgres_buffer_create": buffer,
        "config_regex": config.config_regex,
        "func_regex_check": func_regex_check,
        "config_table": config.config_table,
        "config_obj_list_limit": config.config_obj_list_limit,
    }

    assert await func_postgres_create(obj_list=[{"title": "one"}], **common) == "buffered"
    assert len(calls) == 1
    assert calls[0]["obj_list"] == [{"title": "one"}]
    assert buffer["test|title"] == [{"title": "serialized:one"}]

    assert await func_postgres_create(obj_list=[{"title": "two"}], **common) == "buffered released"
    assert len(calls) == 2
    assert calls[1]["obj_list"] == [{"title": "two"}]
    assert buffer["test|title"] == []


@pytest.mark.asyncio
async def test_postgres_update_rejects_missing_or_empty_object_data():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    common = {
        "client_postgres_pool": None,
        "client_postgres_conn": None,
        "client_password_hasher": None,
        "func_postgres_serialize": passthrough_serialize,
        "cache_postgres_schema": {},
        "table": "test",
        "created_by_id": None,
        "config_obj_list_limit": config.config_obj_list_limit,
        "config_regex": config.config_regex,
        "func_regex_check": func_regex_check,
        "config_table": config.config_table,
    }

    with pytest.raises(Exception, match="object list required"):
        await func_postgres_update(obj_list=[], **common)
    with pytest.raises(Exception, match="object data required"):
        await func_postgres_update(obj_list=[{}], **common)


@pytest.mark.asyncio
async def test_postgres_update_rejects_obj_list_over_limit():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    with pytest.raises(Exception, match="maximum 1 objects allowed"):
        await func_postgres_update(
            client_postgres_pool=None,
            client_postgres_conn=None,
            client_password_hasher=None,
            func_postgres_serialize=passthrough_serialize,
            cache_postgres_schema={},
            table="test",
            obj_list=[{"id": 1, "title": "one"}, {"id": 2, "title": "two"}],
            created_by_id=None,
            config_obj_list_limit=1,
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_table=config.config_table,
        )


@pytest.mark.asyncio
async def test_postgres_update_rejects_invalid_table_or_missing_update_fields():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    common = {
        "client_postgres_pool": None,
        "client_postgres_conn": None,
        "client_password_hasher": None,
        "func_postgres_serialize": passthrough_serialize,
        "cache_postgres_schema": {},
        "created_by_id": None,
        "config_obj_list_limit": config.config_obj_list_limit,
        "config_regex": config.config_regex,
        "func_regex_check": func_regex_check,
        "config_table": config.config_table,
    }

    with pytest.raises(Exception, match="invalid identifier"):
        await func_postgres_update(table="bad-table", obj_list=[{"id": 1, "title": "one"}], **common)
    with pytest.raises(Exception, match="object data invalid"):
        await func_postgres_update(table="test", obj_list=[{"id": 1, "title": "one"}, 2], **common)
    with pytest.raises(Exception, match="update field required"):
        await func_postgres_update(table="test", obj_list=[{"id": 1}], **common)


@pytest.mark.asyncio
async def test_postgres_update_rejects_mismatched_object_keys():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    with pytest.raises(Exception, match="object keys mismatch"):
        await func_postgres_update(
            client_postgres_pool=None,
            client_postgres_conn=None,
            client_password_hasher=None,
            func_postgres_serialize=passthrough_serialize,
            cache_postgres_schema={},
            table="test",
            obj_list=[{"id": 1, "title": "one"}, {"id": 2, "name": "two"}],
            created_by_id=None,
            config_obj_list_limit=config.config_obj_list_limit,
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_table=config.config_table,
        )


@pytest.mark.asyncio
async def test_postgres_update_uses_zero_created_by_id_for_owner_filter():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    class FakeConn:
        def __init__(self):
            self.sql = None
            self.args = None

        async def fetch(self, sql, *args):
            self.sql = sql
            self.args = args
            return [{"id": 1}]

    conn = FakeConn()
    output = await func_postgres_update(
        client_postgres_pool=None,
        client_postgres_conn=conn,
        client_password_hasher=None,
        func_postgres_serialize=passthrough_serialize,
        cache_postgres_schema={},
        table="test",
        obj_list=[{"id": 1, "title": "one"}],
        created_by_id=0,
        config_obj_list_limit=config.config_obj_list_limit,
        config_regex=config.config_regex,
        func_regex_check=func_regex_check,
        config_table=config.config_table,
    )

    assert output == [1]
    assert '"created_by_id"=$3' in conn.sql
    assert conn.args == ("one", 1, 0)


@pytest.mark.asyncio
async def test_postgres_update_bulk_owner_filter_uses_correct_case_placeholders():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    class FakeTransaction:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeConn:
        def __init__(self):
            self.sql = None
            self.args = None

        def transaction(self):
            return FakeTransaction()

        async def fetch(self, sql, *args):
            self.sql = sql
            self.args = args
            return [{"id": 1}, {"id": 2}]

    conn = FakeConn()
    output = await func_postgres_update(
        client_postgres_pool=None,
        client_postgres_conn=conn,
        client_password_hasher=None,
        func_postgres_serialize=passthrough_serialize,
        cache_postgres_schema={},
        table="test",
        obj_list=[{"id": 1, "title": "one"}, {"id": 2, "title": "two"}],
        created_by_id=10,
        config_obj_list_limit=config.config_obj_list_limit,
        config_regex=config.config_regex,
        func_regex_check=func_regex_check,
        config_table=config.config_table,
    )

    assert output == [1, 2]
    assert 'WHEN "id"=$1::bigint AND "created_by_id"=$3::bigint THEN $2' in conn.sql
    assert 'WHEN "id"=$4::bigint AND "created_by_id"=$6::bigint THEN $5' in conn.sql
    assert conn.args == (1, "one", 10, 2, "two", 10, 1, 2, 10)


@pytest.mark.asyncio
async def test_postgres_update_validates_users_with_regex():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    with pytest.raises(Exception, match="Username must be"):
        await func_postgres_update(
            client_postgres_pool=None,
            client_postgres_conn=None,
            client_password_hasher=None,
            func_postgres_serialize=passthrough_serialize,
            cache_postgres_schema={},
            table="users",
            obj_list=[{"id": 1, "username": "BadUser"}],
            created_by_id=None,
            config_obj_list_limit=config.config_obj_list_limit,
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_table=config.config_table,
        )


@pytest.mark.asyncio
async def test_postgres_create_validates_users_with_regex():
    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    with pytest.raises(Exception, match="Username must be"):
        await func_postgres_create(
            client_postgres_pool=None,
            client_postgres_conn=None,
            client_password_hasher=None,
            func_postgres_serialize=passthrough_serialize,
            cache_postgres_schema={},
            mode="now",
            table="users",
            obj_list=[{"username": "BadUser"}],
            config_buffer_limit=0,
            cache_postgres_buffer_create={},
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_obj_list_limit=config.config_obj_list_limit,
            config_table=config.config_table,
        )


@pytest.mark.asyncio
async def test_postgres_create_forces_users_serialization():
    calls = {}

    async def fake_serialize(**kwargs):
        calls.update(kwargs)
        return [{"username": "user_1", "password": "secret1"}]

    class FakeConn:
        async def fetch(self, sql, *args):
            return [{"id": 1}]

    await func_postgres_create(
        client_postgres_pool=None,
        client_postgres_conn=FakeConn(),
        client_password_hasher=None,
        func_postgres_serialize=fake_serialize,
        cache_postgres_schema={},
        mode="now",
        table="users",
        obj_list=[{"username": "user_1", "password": "secret1"}],
        config_buffer_limit=10,
        cache_postgres_buffer_create={},
        config_regex=config.config_regex,
        func_regex_check=func_regex_check,
        config_obj_list_limit=config.config_obj_list_limit,
        config_table=config.config_table,
    )

    assert calls["table"] == "users"
    assert calls["obj_list"] == [{"username": "user_1", "password": "secret1"}]


@pytest.mark.asyncio
async def test_postgres_update_forces_users_serialization():
    calls = {}

    async def fake_serialize(**kwargs):
        calls.update(kwargs)
        return [{"id": 1, "username": "user_1"}]

    with pytest.raises(AttributeError):
        await func_postgres_update(
            client_postgres_pool=None,
            client_postgres_conn=None,
            client_password_hasher=None,
            func_postgres_serialize=fake_serialize,
            cache_postgres_schema={},
            table="users",
            obj_list=[{"id": 1, "username": "user_1"}],
            created_by_id=None,
            config_obj_list_limit=config.config_obj_list_limit,
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_table=config.config_table,
        )

    assert calls["table"] == "users"
    assert calls["obj_list"] == [{"id": 1, "username": "user_1"}]


def test_config_regex_error_messages_match_current_password_pattern():
    pattern, message = config.config_regex["password"]

    assert "6,30" in pattern
    assert "6-30" in message


class DummyRoute:
    def __init__(self, path):
        self.path = path


def test_func_check_allows_empty_modes_for_optional_config_api_settings():
    from core.function import func_check

    func_check(
        app_routes=[DummyRoute("/public/disabled-empty"), DummyRoute("/public/disabled-none")],
        config_config_path=None,
        config_function_path=None,
        config_api_namespace=["/", "/auth/", "/my/", "/public/", "/private/", "/admin/"],
        config_router_path=None,
        config_api={
            "/public/disabled-empty": {
                "user_active_check": [""],
                "user_deleted_check": [""],
                "api_cache_sec": [""],
                "api_ratelimiting_times_sec": [""],
            },
            "/public/disabled-none": {
                "user_active_check": [None],
                "user_deleted_check": [None],
                "api_cache_sec": [None],
                "api_ratelimiting_times_sec": [None],
            },
        },
        config_allowed_user_storage_backends=["redis", "realtime", "inmemory", "token"],
        config_allowed_api_storage_backends=["redis", "inmemory"],
        config_postgres={"table": {}, "extension": []},
    )


def test_func_check_requires_valid_admin_user_role_check():
    from core.function import func_check

    def func_api_admin_protected():
        pass

    admin_route = DummyRoute("/admin/protected")
    admin_route.endpoint = func_api_admin_protected

    def run(config_api):
        func_check(
            app_routes=[admin_route],
            config_config_path=None,
            config_function_path=None,
            config_api_namespace=["/", "/auth/", "/my/", "/public/", "/private/", "/admin/"],
            config_router_path=None,
            config_api=config_api,
            config_allowed_user_storage_backends=["redis", "realtime", "inmemory", "token"],
            config_allowed_api_storage_backends=["redis", "inmemory"],
            config_postgres={"table": {}, "extension": []},
        )

    with pytest.raises(Exception, match="missing in config_api"):
        run({})
    with pytest.raises(Exception, match="missing 'user_role_check'"):
        run({"/admin/protected": {}})
    with pytest.raises(Exception, match="invalid mode"):
        run({"/admin/protected": {"user_role_check": ["", [1]]}})
    with pytest.raises(Exception, match="must allow role 1"):
        run({"/admin/protected": {"user_role_check": ["token", [2]]}})

    run({"/admin/protected": {"user_role_check": ["token", [1]]}})


def test_func_check_routing_namespace_rules():
    from core.function import func_check
    
    valid_routes = [
        DummyRoute("/"),
        DummyRoute("/test"),
        DummyRoute("/info"),
        DummyRoute("/auth/login"),
        DummyRoute("/my/profile"),
    ]
    
    func_check(
        app_routes=valid_routes,
        config_config_path=None,
        config_function_path=None,
        config_api_namespace=["/", "/auth/", "/my/", "/public/", "/private/", "/admin/"],
        config_router_path=None,
        config_api={},
        config_allowed_user_storage_backends=[],
        config_allowed_api_storage_backends=[],
        config_postgres={"table": {}, "extension": []},
    )
    
    invalid_routes = [
        DummyRoute("/invalid/login"),
    ]
    
    with pytest.raises(Exception, match="invalid route: /invalid/login"):
        func_check(
            app_routes=invalid_routes,
            config_config_path=None,
            config_function_path=None,
            config_api_namespace=["/", "/auth/", "/my/", "/public/", "/private/", "/admin/"],
            config_router_path=None,
            config_api={},
            config_allowed_user_storage_backends=[],
            config_allowed_api_storage_backends=[],
            config_postgres={"table": {}, "extension": []},
        )
