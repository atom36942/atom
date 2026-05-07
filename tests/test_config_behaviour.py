import sys
import time
from pathlib import Path

import pytest
from fastapi import Request, responses

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import config
from core.app import app
from core.function import (
    func_middleware_api_response,
    func_middleware_check_is_active,
    func_middleware_check_ratelimiter,
    func_middleware_check_role,
    func_postgres_create,
    func_regex_check,
)


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeUserConn:
    def __init__(self, *, role=1, is_active=1):
        self.role = role
        self.is_active = is_active
        self.fetch_calls = []

    async def fetch(self, sql, *args):
        self.fetch_calls.append((sql, args))
        normalized = " ".join(sql.lower().split())
        if "select role from users" in normalized:
            return [{"role": self.role}]
        if "select id,is_active from users" in normalized:
            return [{"id": args[0], "is_active": self.is_active}]
        return []


class FakeUserPool:
    def __init__(self, *, role=1, is_active=1):
        self.conn = FakeUserConn(role=role, is_active=is_active)

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


def make_request(path, *, query_string=b"", method="GET", body=b""):
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
    }
    return Request(scope, receive=receive)


def test_config_api_paths_modes_ids_and_admin_roles_match_app_routes():
    app_paths = {route.path for route in app.routes if hasattr(route, "path")}
    allowed_modes = {
        "user_role_check": {"redis", "realtime", "inmemory", "token"},
        "user_is_active_check": {"redis", "realtime", "inmemory", "token"},
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
                assert setting[0] in modes
                assert len(setting) >= 2
        if path.startswith("/admin/"):
            assert "user_role_check" in entry
            assert 1 in entry["user_role_check"][1]


@pytest.mark.asyncio
async def test_config_api_cache_inmemory_sets_and_hits_cached_response():
    calls = []

    async def api_function(_request):
        calls.append("run")
        return responses.JSONResponse({"status": 1, "message": len(calls)})

    cache = {}
    cfg = {"/cached": {"api_cache_sec": ["inmemory", 30]}}

    first = await func_middleware_api_response(
        request=make_request("/cached", query_string=b"a=1"),
        api_function=api_function,
        config_api=cfg,
        client_redis=None,
        user_id=0,
        cache_api_response=cache,
    )
    second = await func_middleware_api_response(
        request=make_request("/cached", query_string=b"a=1"),
        api_function=api_function,
        config_api=cfg,
        client_redis=None,
        user_id=0,
        cache_api_response=cache,
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

    first = await func_middleware_api_response(
        request=make_request("/cached"),
        api_function=api_function,
        config_api=cfg,
        client_redis=redis,
        user_id=0,
        cache_api_response={},
    )
    second = await func_middleware_api_response(
        request=make_request("/cached"),
        api_function=api_function,
        config_api=cfg,
        client_redis=redis,
        user_id=0,
        cache_api_response={},
    )

    assert first.status_code == 200
    assert second.headers["x-cache"] == "hit"
    assert calls == ["run"]
    assert list(redis.expires.values()) == [15]


@pytest.mark.asyncio
async def test_config_api_ratelimiter_inmemory_allows_until_limit_then_blocks():
    cache = {}
    cfg = {"/limited": {"api_ratelimiting_times_sec": ["inmemory", 2, 60]}}

    await func_middleware_check_ratelimiter(
        client_redis_ratelimiter=None,
        config_api=cfg,
        url_path="/limited",
        identifier="user-1",
        cache_ratelimiter=cache,
    )
    await func_middleware_check_ratelimiter(
        client_redis_ratelimiter=None,
        config_api=cfg,
        url_path="/limited",
        identifier="user-1",
        cache_ratelimiter=cache,
    )
    with pytest.raises(Exception, match="ratelimiter exceeded"):
        await func_middleware_check_ratelimiter(
            client_redis_ratelimiter=None,
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
        client_redis_ratelimiter=redis,
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
            client_redis_ratelimiter=redis,
            config_api=cfg,
            url_path="/limited",
            identifier="user-1",
            cache_ratelimiter={},
        )


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

    await func_middleware_check_role(
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
        await func_middleware_check_role(user_dict={"id": 1}, url_path="/admin/protected", config_api=cfg, client_postgres_pool=None, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)
    with pytest.raises(Exception, match="invalid user role type"):
        await func_middleware_check_role(user_dict={"id": 1, "role": "abc"}, url_path="/admin/protected", config_api=cfg, client_postgres_pool=None, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)
    with pytest.raises(Exception, match="access denied"):
        await func_middleware_check_role(user_dict={"id": 1, "role": 2}, url_path="/admin/protected", config_api=cfg, client_postgres_pool=None, client_redis=None, cache_users_role={}, config_redis_cache_ttl_sec=60)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "kwargs"),
    [
        ("token", {"user_dict": {"id": 1, "is_active": 1}}),
        ("inmemory", {"user_dict": {"id": 1}, "cache_users_is_active": {1: 1}}),
        ("realtime", {"user_dict": {"id": 1}, "client_postgres_pool": FakeUserPool(is_active=1)}),
        ("redis", {"user_dict": {"id": 1}, "client_redis": FakeRedis(), "client_postgres_pool": FakeUserPool(is_active=1)}),
    ],
)
async def test_config_api_user_active_check_all_supported_modes_allow_active_user(mode, kwargs):
    cfg = {"/admin/protected": {"user_is_active_check": [mode, 1]}}

    await func_middleware_check_is_active(
        user_dict=kwargs["user_dict"],
        url_path="/admin/protected",
        config_api=cfg,
        client_postgres_pool=kwargs.get("client_postgres_pool"),
        client_redis=kwargs.get("client_redis"),
        cache_users_is_active=kwargs.get("cache_users_is_active", {}),
        config_redis_cache_ttl_sec=60,
    )


@pytest.mark.asyncio
async def test_config_api_user_active_check_rejects_inactive_and_can_be_disabled():
    enabled_cfg = {"/admin/protected": {"user_is_active_check": ["token", 1]}}
    disabled_cfg = {"/admin/protected": {"user_is_active_check": ["token", 0]}}

    with pytest.raises(Exception, match="user not active"):
        await func_middleware_check_is_active(user_dict={"id": 1, "is_active": 0}, url_path="/admin/protected", config_api=enabled_cfg, client_postgres_pool=None, client_redis=None, cache_users_is_active={}, config_redis_cache_ttl_sec=60)

    await func_middleware_check_is_active(user_dict={"id": 1, "is_active": 0}, url_path="/admin/protected", config_api=disabled_cfg, client_postgres_pool=None, client_redis=None, cache_users_is_active={}, config_redis_cache_ttl_sec=60)


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
        "is_serialize": 0,
        "buffer_limit": 0,
        "cache_postgres_buffer": {},
        "config_regex": config.config_regex,
        "func_regex_check": func_regex_check,
        "config_obj_list_limit": config.config_obj_list_limit,
    }

    with pytest.raises(Exception, match="object list required"):
        await func_postgres_create(obj_list=[], **common)
    with pytest.raises(Exception, match="object data required"):
        await func_postgres_create(obj_list=[{}], **common)


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
            is_serialize=0,
            buffer_limit=0,
            cache_postgres_buffer={},
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_obj_list_limit=1,
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
            is_serialize=0,
            buffer_limit=0,
            cache_postgres_buffer={},
            config_regex=config.config_regex,
            func_regex_check=func_regex_check,
            config_obj_list_limit=config.config_obj_list_limit,
        )


@pytest.mark.asyncio
async def test_postgres_create_forces_users_serialization():
    calls = {}

    async def fake_serialize(**kwargs):
        calls.update(kwargs)
        return [{"username": "user_1", "password": "secret1"}]

    await func_postgres_create(
        client_postgres_pool=None,
        client_postgres_conn=None,
        client_password_hasher=None,
        func_postgres_serialize=fake_serialize,
        cache_postgres_schema={},
        mode="buffer",
        table="users",
        obj_list=[{"username": "user_1", "password": "secret1"}],
        is_serialize=0,
        buffer_limit=10,
        cache_postgres_buffer={},
        config_regex=config.config_regex,
        func_regex_check=func_regex_check,
        config_obj_list_limit=config.config_obj_list_limit,
    )

    assert calls["table"] == "users"
    assert calls["obj_list"] == [{"username": "user_1", "password": "secret1"}]


def test_config_regex_error_messages_match_current_password_pattern():
    pattern, message = config.config_regex["password"]

    assert "6,30" in pattern
    assert "6-30" in message
