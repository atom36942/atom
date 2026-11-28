# command: venv/bin/python main.py

# info: FastAPI app entry point: builds the app, wires Atom's clients, routers and middleware, and runs uvicorn with config_uvicorn_workers workers. For development use venv/bin/uvicorn main:app --reload.

# import
import importlib.util
import os
if __name__ == "__main__": os.chdir(os.path.dirname(os.path.abspath(__file__)))    # run as a file: .env, tmp/, secret/ and static/ are this folder's, wherever it is started from
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
import config
import function

# config
config_modules = [config] + ([importlib.import_module("config_extend")] if importlib.util.find_spec("config_extend") else [])
config_values = {key: value for module in config_modules for key, value in vars(module).items() if key.startswith("config_")}
function.func_config_load(global_dict=config_values)

# lifespan
@asynccontextmanager
async def func_lifespan(app: FastAPI):
    registry = {}
    try:
        # start
        start_journey = time.perf_counter()
        app.state.runtime_background_tasks = set()
        app.state.runtime_message_socket = {}
        app.state.runtime_error_count = {"log_api_write": 0, "buffer_flush": 0, "buffer_dropped": 0, "background_task": 0, "cleanup": 0, "schedule": 0}
        cache_api_response = {}
        cache_api_response_bytes = {"total": 0}    # stored size of cache_api_response, kept as entries come and go
        cache_ratelimiter = {}
        cache_oidc = {}    # each OIDC provider's discovery and signing keys, an hour
        buffer_postgres_create = {}
        buffer_postgres_log_api = {}
        cache_token = OrderedDict()
        cache_static_version = {}
        app.state.config_api = app.state.func_middleware_api_user_check_fill(config_api=app.state.config_api, config_api_global_user_check_deleted=app.state.config_api_global_user_check_deleted, config_api_global_user_check_deactivated=app.state.config_api_global_user_check_deactivated)    # every token route checks deleted and deactivated users unless it sets its own
        cache_config_api_template = app.state.func_middleware_api_template_read(config_api=app.state.config_api)    # routes with path parameters, matched when the exact path is not in config_api
        cache_atom_version = app.state.func_atom_version()
        print(f"Atom {cache_atom_version or 'version unknown'}", flush=True)
        app.state.func_check(app=app)
        # with several workers, main resets tmp once before they start; a worker resetting it would delete files others are using
        app.state.func_structure_init(is_tmp_reset=app.state.config_is_tmp_reset and app.state.config_uvicorn_workers == 1)
        # clients: Atom's (func_client_registry) and the project's (func_extend_client in function_extend/), opened at once; one failing closes the others and stops startup
        registry = app.state.func_client_registry_build(app_state=app.state)
        app.state.runtime_client_registry = registry
        clients = await app.state.func_client_registry_open(registry=registry)
        app.state.func_app_state_add(app=app, data_dict=clients, prefixes=("client_",))
        client_password_hasher, client_postgres_dict, client_clickhouse_dict = clients["client_password_hasher"], clients["client_postgres_dict"], clients["client_clickhouse_dict"]
        await app.state.func_check_postgres_connections(app_state=app.state, client_postgres_dict=client_postgres_dict)
        # postgres schemas: each config_postgres_schema_<name> on its own database, master first; its tables' rules (who may do what, buffer, labels) are read from it here
        postgres_schemas = app.state.func_postgres_schema_dict(values=getattr(app.state, "_state", None) or vars(app.state))
        cache_postgres_table_rule = app.state.func_postgres_table_rule_dict(schemas=postgres_schemas)
        cache_int_mapping = app.state.func_postgres_int_mapping(schemas=postgres_schemas, config_users_role_label=app.state.config_users_role_label, config_api=app.state.config_api)
        cache_column_regex = app.state.func_postgres_column_regex_dict(schemas=postgres_schemas)
        cache_users_access = app.state.func_postgres_users_access(config_users_token_column=app.state.config_users_token_column, config_users_private_read_column=app.state.config_users_private_read_column, config_users_update_alone_column=app.state.config_users_update_alone_column)
        cache_ownership_column = app.state.func_postgres_ownership_column_dict(rules=cache_postgres_table_rule)    # /my ownership_column choices per action (each table checks its own); flat names so the OpenAPI spec reads them as the dropdown
        cache_ownership_column_read, cache_ownership_column_update, cache_ownership_column_delete = cache_ownership_column["read"], cache_ownership_column["update"], cache_ownership_column["delete"]
        cache_log_api_database = app.state.func_postgres_log_database(schemas=postgres_schemas) if app.state.config_is_log_api else None
        if not app.state.config_is_read_only:
            root_user_password_hash = client_password_hasher.hash(str(app.state.config_root_user_password)) if app.state.config_root_user_password and app.state.config_is_postgres_schema_init else None
            for name, schema in postgres_schemas.items():
                if not (client_postgres := client_postgres_dict.get(name)): continue
                if not app.state.config_is_postgres_schema_init: await app.state.func_postgres_schema_check(app_state=app.state, client_postgres=client_postgres, config_postgres_schema=schema, name=name)
                else:
                    async with app.state.func_postgres_advisory_lock(client_postgres=client_postgres, lock_id=3): await app.state.func_postgres_schema_init(app_state=app.state, client_postgres=client_postgres, config_postgres_schema=schema, database=name, lock_timeout_sec=app.state.config_postgres_lock_timeout_sec, root_user_password_hash=root_user_password_hash)
        # postgres master
        postgres_master = client_postgres_dict.get("master")
        postgres_master_schema = await app.state.func_postgres_schema_read(client_postgres=postgres_master) if postgres_master else {}
        cache_startup = await app.state.func_postgres_cache_read(client_postgres=postgres_master, is_config_table="config" in postgres_master_schema, config_cache_row_limit_config=app.state.config_cache_row_limit_config, config_cache_row_limit_users_role=app.state.config_cache_row_limit_users_role, config_cache_row_limit_users_deactivated=app.state.config_cache_row_limit_users_deactivated, config_cache_row_limit_users_deleted=app.state.config_cache_row_limit_users_deleted)
        cache_config, cache_users_role, cache_users_deactivated, cache_users_deleted = cache_startup["cache_config"], cache_startup["cache_users_role"], cache_startup["cache_users_deactivated"], cache_startup["cache_users_deleted"]
        client_postgres_log_api = client_postgres_dict.get(cache_log_api_database) if cache_log_api_database else None
        # cache schema
        cache_postgres_schema_dict = {name: postgres_master_schema if name == "master" else await app.state.func_postgres_schema_read(client_postgres=pool) for name, pool in client_postgres_dict.items()}
        app.state.func_postgres_control_table_check(schemas=postgres_schemas, cache_postgres_schema_dict=cache_postgres_schema_dict)    # every table an access list names exists in its database
        if postgres_master and not app.state.config_is_read_only and app.state.config_is_root_user and "permissions" in postgres_master_schema.get("users", {}): await app.state.func_root_user_permissions_sync(client_postgres=postgres_master, config_api=app.state.config_api)    # root holds every /admin route id
        cache_clickhouse_schema_dict = {name: await app.state.func_clickhouse_schema_read(client_clickhouse=client) for name, client in client_clickhouse_dict.items()}
        # func calls
        app.state.func_app_state_add(app=app, data_dict=locals(), prefixes=("client_", "cache_", "buffer_"))
        app.state.func_check_log_api_table(app_state=app.state)
        app.state.cache_openapi = app.state.func_openapi_spec_generate(app_routes=app.state.func_app_route_list(app=app), app_state=app.state)
        # project startup: func_extend in function_extend/ returns app.state.extend
        app.state.extend = await app.state.func_app_extend_run(app_state=app.state, name="func_extend")
        # periodic tasks
        app.state.func_app_tasks_start(app_state=app.state)
    except BaseException as e:    # also a cancelled startup (Ctrl-C), which is not an Exception
        print(f"❌ startup error: {e}")
        await app.state.func_client_close(registry=registry, clients={name: getattr(app.state, name, None) for name in registry})    # close what opened before the failure
        raise
    # shutdown
    yield
    try:
        await app.state.func_app_tasks_stop(app_state=app.state)
        if not app.state.config_is_read_only: await app.state.func_postgres_buffer_flush_all(app_state=app.state)
        # project shutdown runs before Atom's clients close; its errors never block that
        try: await app.state.func_app_extend_run(app_state=app.state, name="func_extend_shutdown")
        except Exception as e: print(f"❌ func_extend_shutdown error: {e}")
        await app.state.func_client_close(registry=app.state.runtime_client_registry, clients={name: getattr(app.state, name, None) for name in app.state.runtime_client_registry})
    except Exception as e:
        print(f"❌ shutdown error: {e}")

# app
app = function.func_app_fastapi_create(config_is_prod=config_values["config_is_prod"], lifespan=func_lifespan, config_is_fastapi_telemetry=config_values["config_is_fastapi_telemetry"])
function.func_app_state_add(app=app, data_dict=vars(function), prefixes=("func_",))
function.func_app_state_add(app=app, data_dict=config_values, prefixes=("config_",))
app.state.func_app_router_add(app=app, router_dir=os.path.join(os.path.dirname(__file__), "router"), router_order={"index": 0, "auth": 1, "my": 2, "public": 3, "private": 4, "admin": 5})
app.state.func_app_static_add(app=app)
app.state.func_app_route_lookup_add(app=app)
app.state.func_sentry_init(config_sentry_dsn=app.state.config_sentry_dsn, config_sentry_traces_sample_rate=app.state.config_sentry_traces_sample_rate)

# middleware
def middleware(asgi_app):
    # plain ASGI: the route runs inline and the response is observed through a wrapped send (about a third faster than @app.middleware("http"))
    async def run(scope, receive, send):
        #start
        if scope["type"] != "http" or scope["method"] == "OPTIONS": return await asgi_app(scope, receive, send)
        app_state = scope["app"].state
        receive = app_state.func_middleware_body_limit(scope=scope, receive=receive, config_request_body_max_kb=app_state.config_request_body_max_kb, config_request_form_max_kb=app_state.config_request_form_max_kb)
        api_cfg = app_state.func_middleware_api_config(config_api=app_state.config_api, path=scope["path"], cache_config_api_template=app_state.cache_config_api_template)
        # api log: config_api routes (is_log_api: False skips one, e.g. /pgweb); other paths (static files, favicon, 404s) only with config_is_log_api_all; config_is_log_api_detail adds headers and JSON bodies
        is_log_api = api_cfg.get("is_log_api", True) if api_cfg else app_state.config_is_log_api_all
        receive, detail = app_state.func_middleware_log_detail_start(scope=scope, receive=receive, config_log_api_detail_max_kb=app_state.config_log_api_detail_max_kb, config_is_log_api_detail_mask=app_state.config_is_log_api_detail_mask) if is_log_api and app_state.config_is_log_api_detail else (receive, None)
        request = Request(scope, receive)
        start, error, response_type, request.state.user = time.perf_counter(), None, "direct_no_cache_set", {}
        request.state.request_id = app_state.func_middleware_request_id(headers=request.headers)
        sent, capture = {"status": None, "is_started": False}, None
        async def send_wrapped(message):
            if detail is not None: app_state.func_middleware_log_detail_send(message=message, detail=detail)
            if message["type"] == "http.response.start":
                sent["status"], sent["is_started"] = message["status"], True
                message["headers"] = [*app_state.func_middleware_security_headers(headers=message.get("headers", [])), (b"x-request-id", request.state.request_id.encode())]
                if api_cfg.get("cache"): message["headers"].append((b"vary", b"accept-encoding"))    # a cache hit may be sent gzipped, so shared caches must key on it
            elif message["type"] == "http.response.body" and capture is not None: capture.append(message.get("body", b""))
            await send(message)
        try:
            # config
            path = scope["path"]
            is_active = api_cfg.get("is_active", True)
            auth = api_cfg.get("auth")
            user_check_role = api_cfg.get("user_check_role")
            user_check_permission = api_cfg.get("user_check_permission")
            user_check_deactivated = api_cfg.get("user_check_deactivated")
            user_check_deleted = api_cfg.get("user_check_deleted")
            rate_limit = api_cfg.get("rate_limit")
            cache = api_cfg.get("cache")
            is_connection_param = api_cfg.get("is_connection_param", False)
            # active check
            await app_state.func_middleware_check_active(is_active=is_active)
            # caller ip and shared token: for a caller that can't sign (some device and IoT clouds), set per route; checked before the body is read
            if (ip_allow := api_cfg.get("ip_allow")) is not None: app_state.func_middleware_check_ip_allow(client_ip=app_state.func_middleware_client_ip(request=request), ip_allow=ip_allow)
            if token_verify := api_cfg.get("token_verify"): app_state.func_middleware_check_token_verify(request=request, token_verify=token_verify, secret=getattr(app_state, token_verify["secret"], None))
            # webhook signature: the route's caller is another service, proven by the HMAC of the raw body
            if webhook_verify := api_cfg.get("webhook_verify"): receive = await app_state.func_webhook_verify_request(request=request, receive=receive, webhook_verify=webhook_verify, config_webhook_verify_scheme=app_state.config_webhook_verify_scheme, secret=getattr(app_state, webhook_verify["secret"], None))
            # token
            request.state.user = await app_state.func_token_decode(headers=request.headers, config_token_secret_key=app_state.config_token_secret_key, cache_token=app_state.cache_token, config_token_cache_max=app_state.config_token_cache_max)
            if not request.state.user: request.state.user = await app_state.func_api_key_decode(headers=request.headers, client_postgres=app_state.client_postgres_dict.get("master"), cache_token=app_state.cache_token, config_token_cache_max=app_state.config_token_cache_max, config_api_key_cache_sec=app_state.config_api_key_cache_sec, token_column=app_state.cache_users_access["token"])
            # checks
            await app_state.func_middleware_check_auth(user_dict=request.state.user, url_path=path, auth=auth)
            user_row_read = app_state.func_middleware_user_row_reader(client_postgres=app_state.client_postgres_dict.get("master"), user_dict=request.state.user)    # one users query per request, whichever checks need it
            await app_state.func_middleware_check_role(user_dict=request.state.user, user_check_role=user_check_role, client_postgres=app_state.client_postgres_dict.get("master"), client_redis=app_state.client_redis_dict.get("user_state"), cache_users_role=app_state.cache_users_role, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec, user_row_read=user_row_read)
            await app_state.func_middleware_check_permission(user_dict=request.state.user, user_check_permission=user_check_permission, api_id=api_cfg.get("id"), user_row_read=user_row_read)
            await app_state.func_middleware_check_user_deleted(user_dict=request.state.user, user_check_deleted=user_check_deleted, client_postgres=app_state.client_postgres_dict.get("master"), client_redis=app_state.client_redis_dict.get("user_state"), cache_users_deleted=app_state.cache_users_deleted, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec, user_row_read=user_row_read)
            await app_state.func_middleware_check_user_deactivated(user_dict=request.state.user, user_check_deactivated=user_check_deactivated, client_postgres=app_state.client_postgres_dict.get("master"), client_redis=app_state.client_redis_dict.get("user_state"), cache_users_deactivated=app_state.cache_users_deactivated, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec, user_row_read=user_row_read)
            await app_state.func_middleware_check_ratelimiter(client_redis=app_state.client_redis_dict.get("ratelimiter"), rate_limit=rate_limit, url_path=path, identifier=request.state.user.get("id") if request.state.user else app_state.func_middleware_client_ip(request=request), cache_ratelimiter=app_state.cache_ratelimiter)
            # postgres select
            request.state.client_postgres, request.state.cache_postgres_schema = app_state.func_middleware_postgres_select(client_postgres_dict=app_state.client_postgres_dict, cache_postgres_schema_dict=app_state.cache_postgres_schema_dict, is_connection_param=is_connection_param, connection=request.query_params.get("connection"))
            request.state.connection = request.query_params.get("connection") or "master"    # the database's name: buffered rows and queued jobs keep it
            # cache
            user_id, query_params = (request.state.user.get("id") if request.state.user else 0), dict(request.query_params)
            response = await app_state.func_middleware_api_cache(mode="get", path=path, query_params=query_params, cache=cache, client_redis=app_state.client_redis_dict.get("api_response"), user_id=user_id, cache_api_response=app_state.cache_api_response, is_gzip_accepted="gzip" in request.headers.get("accept-encoding", ""))
            # execution
            if response:
                response_type = "cache_response"
                await response(scope, receive, send_wrapped)
            elif app_state.func_query_bool_parse(query_params.get("is_background"), default=False):
                response_type = "background_added"
                response = await app_state.func_middleware_api_background(scope=scope, body_bytes=await request.body())
                await response(scope, receive, send_wrapped)
            else:
                # copy the body only for routes with cache on; others (CSV exports) stream straight through
                capture = [] if cache and not app_state.func_query_bool_parse(query_params.get("is_disable_cache"), default=False) else None
                await asgi_app(scope, receive, send_wrapped)
                if capture is not None and sent["status"] == 200:
                    await app_state.func_middleware_api_cache(mode="set", path=path, query_params=query_params, response=Response(content=b"".join(capture), status_code=200), cache=cache, client_redis=app_state.client_redis_dict.get("api_response"), user_id=user_id, cache_api_response=app_state.cache_api_response, cache_api_response_bytes=app_state.cache_api_response_bytes, config_api_cache_inmemory_max_kb=app_state.config_api_cache_inmemory_max_kb)
                    response_type = "direct_cache_set"
        # error
        except Exception as e:
            response_type = "error"
            error, response = await app_state.func_middleware_api_response_error(exception=e, is_traceback=True, sentry_dsn=app_state.config_sentry_dsn, request_id=request.state.request_id)
            # an error after the response started cannot replace it; it is still logged below
            if not sent["is_started"]: await response(scope, receive, send_wrapped)
        # form close (a background request closes its own when the task ends)
        if response_type != "background_added": await app_state.func_request_form_close(request=request)
        # api log buffer, written after the response was sent
        if is_log_api: await app_state.func_middleware_log_api_write(app_state=app_state, request=request, response_type=response_type, status_code=sent["status"], start=start, error=error, detail=detail)
    return run
app.add_middleware(middleware)

# gzip (outside Atom's middleware: it compresses what the route and the cache sent)
app.state.func_app_gzip_add(app=app)

# cors
app.state.func_app_cors_add(app=app, allow_origins=app.state.config_cors_allow_origins, allow_origin_regex=app.state.config_cors_allow_origin_regex, allow_methods=app.state.config_cors_allow_methods, allow_headers=app.state.config_cors_allow_headers, expose_headers=app.state.config_cors_expose_headers, allow_credentials=app.state.config_cors_allow_credentials)

# main
if __name__ == "__main__":
    workers = app.state.config_uvicorn_workers
    host = "0.0.0.0"  # noqa: S104 - a server (and its container) must accept connections on every interface
    if workers == 1: uvicorn.run(app, host=host, port=int(os.environ.get("PORT", 8000)), access_log=app.state.config_is_uvicorn_access_log, timeout_keep_alive=app.state.config_uvicorn_timeout_keep_alive_sec)
    else:
        # check config once here: uvicorn restarts workers that fail startup, so a bad config would loop instead of exiting
        app.state.func_check(app=app)
        function.func_structure_init(is_tmp_reset=app.state.config_is_tmp_reset)
        uvicorn.run("main:app", host=host, port=int(os.environ.get("PORT", 8000)), workers=workers, app_dir=os.path.dirname(os.path.abspath(__file__)), access_log=app.state.config_is_uvicorn_access_log, timeout_keep_alive=app.state.config_uvicorn_timeout_keep_alive_sec)
