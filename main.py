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
    try:
        # start
        start_journey = time.perf_counter()
        app.state.runtime_background_tasks = set()
        app.state.runtime_message_socket = {}
        app.state.runtime_error_count = {"log_api_write": 0, "buffer_flush": 0, "buffer_dropped": 0, "background_task": 0, "cleanup": 0}
        postgres_pool_kwargs = {"min_size": app.state.config_postgres_pool_min_size, "max_size": app.state.config_postgres_pool_max_size, "is_read_only": app.state.config_is_read_only}
        aws_kwargs = {"aws_access_key_id": app.state.config_aws_access_key_id, "aws_secret_access_key": app.state.config_aws_secret_access_key}
        cache_api_response = {}
        cache_ratelimiter = {}
        buffer_postgres_create = {}
        buffer_postgres_log_api = {}
        cache_token = OrderedDict()
        cache_atom_version = app.state.func_atom_version()
        print(f"Atom {cache_atom_version or 'version unknown'}", flush=True)
        app.state.func_check(app=app)
        # with several workers, main resets tmp once before they start; a worker resetting it would delete files others are using
        app.state.func_structure_init(is_tmp_reset=app.state.config_is_tmp_reset and app.state.config_uvicorn_workers == 1)
        # client init
        client_password_hasher = app.state.func_client_password_hasher()
        client_http = app.state.func_client_http()
        client_postgres_dict = {name: await app.state.func_client_postgres(dsn=url, **postgres_pool_kwargs) for name, url in (app.state.config_postgres_url_dict or {}).items() if url}
        client_redis_dict = {name: app.state.func_client_redis(url=url) for name, url in (app.state.config_redis_url_dict or {}).items() if url}
        client_mongodb = app.state.func_client_mongodb(url=app.state.config_mongodb_url)
        client_mssql_dict = {name: await app.state.func_client_mssql(dsn=url, min_size=app.state.config_mssql_pool_min_size, max_size=app.state.config_mssql_pool_max_size, recycle_sec=app.state.config_mssql_pool_recycle_sec) for name, url in (app.state.config_mssql_url_dict or {}).items() if url}
        client_clickhouse_dict = {name: await app.state.func_client_clickhouse(dsn=url) for name, url in (app.state.config_clickhouse_url_dict or {}).items() if url}
        client_s3 = await app.state.func_client_s3(region_name=app.state.config_aws_s3_region_name, **aws_kwargs)
        client_s3_resource = app.state.func_client_s3_resource(region_name=app.state.config_aws_s3_region_name, **aws_kwargs)
        client_sns = app.state.func_client_sns(region_name=app.state.config_aws_sns_region_name, **aws_kwargs)
        client_ses = app.state.func_client_ses(region_name=app.state.config_aws_ses_region_name, **aws_kwargs)
        client_openai = app.state.func_client_openai(api_key=app.state.config_openai_key)
        client_gemini = app.state.func_client_gemini(api_key=app.state.config_gemini_key)
        client_posthog = app.state.func_client_posthog(project_key=app.state.config_posthog_project_key, host=app.state.config_posthog_project_host)
        client_celery_producer = app.state.func_client_celery(url=app.state.config_celery_url)
        client_kafka_producer = await app.state.func_client_kafka(url=app.state.config_kafka_url, username=app.state.config_kafka_username, password=app.state.config_kafka_password)
        client_rabbitmq, client_rabbitmq_producer = await app.state.func_client_rabbitmq(url=app.state.config_rabbitmq_url)
        client_sftp = await app.state.func_client_sftp(host=app.state.config_sftp_host, port=app.state.config_sftp_port, username=app.state.config_sftp_username, password=app.state.config_sftp_password)
        client_azure_email = app.state.func_client_azure_email(connection_string=app.state.config_azure_email_connection_string)
        client_azure_sms = app.state.func_client_azure_sms(connection_string=app.state.config_azure_sms_connection_string)
        client_azure_blob = app.state.func_client_azure_blob(account_name=app.state.config_azure_account_name, account_key=app.state.config_azure_account_key)
        client_msgraph = app.state.func_client_msgraph(tenant_id=app.state.config_msgraph_tenant_id, client_id=app.state.config_msgraph_client_id, client_secret=app.state.config_msgraph_client_secret)
        client_postgres_pgweb = {}
        await app.state.func_check_postgres_connections(app_state=app.state, client_postgres_dict=client_postgres_dict)
        # postgres master
        postgres_master = client_postgres_dict.get("master")
        if postgres_master and not app.state.config_is_read_only and app.state.config_is_postgres_schema_init:
            async with app.state.func_postgres_advisory_lock(client_postgres=postgres_master, lock_id=3): await app.state.func_postgres_schema_init(app_state=app.state, client_postgres=postgres_master, config_postgres=app.state.config_postgres, root_user_password_hash=client_password_hasher.hash(str(app.state.config_root_user_password)) if app.state.config_root_user_password else None)
        postgres_master_schema = await app.state.func_postgres_schema_read(client_postgres=postgres_master) if postgres_master else {}
        cache_config = await app.state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app.state.config_sql.get("config"), is_json_value=True) if postgres_master and "config" in postgres_master_schema else {}
        cache_users_role = await app.state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app.state.config_sql.get("users_role")) if postgres_master else {}
        cache_users_deactivated = await app.state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app.state.config_sql.get("users_deactivated")) if postgres_master else {}
        cache_users_deleted = await app.state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app.state.config_sql.get("users_deleted")) if postgres_master else {}
        # postgres log
        client_postgres_log_api = client_postgres_dict.get(app.state.config_postgres_db_log_api)
        if client_postgres_log_api and app.state.config_postgres_db_log_api != "master" and not app.state.config_is_read_only and app.state.config_is_postgres_schema_init:
            async with app.state.func_postgres_advisory_lock(client_postgres=client_postgres_log_api, lock_id=3): await app.state.func_postgres_schema_tables_init(app_state=app.state, client_postgres=client_postgres_log_api, tables={"log_api": app.state.config_postgres["table"]["log_api"]})
        # cache schema
        cache_postgres_schema_dict = {name: postgres_master_schema if name == "master" else await app.state.func_postgres_schema_read(client_postgres=pool) for name, pool in client_postgres_dict.items()}
        cache_clickhouse_schema_dict = {name: await app.state.func_clickhouse_schema_read(client_clickhouse=client) for name, client in client_clickhouse_dict.items()}
        # func calls
        app.state.func_app_state_add(app=app, data_dict=locals(), prefixes=("client_", "cache_", "buffer_"))
        app.state.func_check_log_api_table(app_state=app.state)
        app.state.cache_openapi = app.state.func_openapi_spec_generate(app_routes=app.state.func_app_route_list(app=app), app_state=app.state)
        # project startup: func_extend in function_extend/ returns app.state.extend
        app.state.extend = await app.state.func_app_extend_run(app_state=app.state, name="func_extend")
        # periodic tasks
        app.state.func_app_tasks_start(app_state=app.state)
    except Exception as e:
        print(f"❌ startup error: {e}")
        raise
    # shutdown
    yield
    try:
        await app.state.func_app_tasks_stop(app_state=app.state)
        if not app.state.config_is_read_only:await app.state.func_postgres_buffer_flush_all(app_state=app.state, client_postgres=postgres_master, buffer_postgres_create=buffer_postgres_create, client_postgres_log_api=client_postgres_log_api, buffer_postgres_log_api=buffer_postgres_log_api)
        # project shutdown runs before Atom's clients close; its errors never block that
        try: await app.state.func_app_extend_run(app_state=app.state, name="func_extend_shutdown")
        except Exception as e: print(f"❌ func_extend_shutdown error: {e}")
        await app.state.func_client_close(app_state=app.state)
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
        request = Request(scope, receive)
        start, error, response_type, request.state.user = time.perf_counter(), None, "direct_no_cache_set", {}
        app_state = scope["app"].state
        sent, capture = {"status": None, "is_started": False}, None
        api_cfg = app_state.config_api.get(scope["path"], {})
        async def send_wrapped(message):
            if message["type"] == "http.response.start":
                sent["status"], sent["is_started"] = message["status"], True
                message["headers"] = app_state.func_middleware_security_headers(headers=message.get("headers", []))
                if api_cfg.get("cache"): message["headers"].append((b"vary", b"accept-encoding"))    # a cache hit may be sent gzipped, so shared caches must key on it
            elif message["type"] == "http.response.body" and capture is not None: capture.append(message.get("body", b""))
            await send(message)
        try:
            # config
            path = scope["path"]
            is_active = api_cfg.get("is_active", True)
            is_token = api_cfg.get("is_token", False)
            user_check_role = api_cfg.get("user_check_role")
            user_check_deactivated = api_cfg.get("user_check_deactivated")
            user_check_deleted = api_cfg.get("user_check_deleted")
            rate_limit = api_cfg.get("rate_limit")
            cache = api_cfg.get("cache")
            is_connection_param = api_cfg.get("is_connection_param", False)
            # active check
            await app_state.func_middleware_check_active(is_active=is_active)
            # token
            request.state.user = await app_state.func_token_decode(headers=request.headers, config_token_secret_key=app_state.config_token_secret_key, cache_token=app_state.cache_token, config_token_cache_max=app_state.config_token_cache_max)
            # checks
            await app_state.func_middleware_check_token(user_dict=request.state.user, url_path=path, is_token=is_token, user_check_role=user_check_role, user_check_deactivated=user_check_deactivated, user_check_deleted=user_check_deleted)
            await app_state.func_middleware_check_role(user_dict=request.state.user, user_check_role=user_check_role, client_postgres=app_state.client_postgres_dict.get("master"), client_redis=app_state.client_redis_dict.get("user_state"), cache_users_role=app_state.cache_users_role, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
            await app_state.func_middleware_check_user_deactivated(user_dict=request.state.user, user_check_deactivated=user_check_deactivated, client_postgres=app_state.client_postgres_dict.get("master"), client_redis=app_state.client_redis_dict.get("user_state"), cache_users_deactivated=app_state.cache_users_deactivated, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
            await app_state.func_middleware_check_user_deleted(user_dict=request.state.user, user_check_deleted=user_check_deleted, client_postgres=app_state.client_postgres_dict.get("master"), client_redis=app_state.client_redis_dict.get("user_state"), cache_users_deleted=app_state.cache_users_deleted, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
            await app_state.func_middleware_check_ratelimiter(client_redis=app_state.client_redis_dict.get("ratelimiter"), rate_limit=rate_limit, url_path=path, identifier=request.state.user.get("id") if request.state.user else app_state.func_middleware_client_ip(request=request), cache_ratelimiter=app_state.cache_ratelimiter)
            # postgres select
            request.state.client_postgres, request.state.cache_postgres_schema = app_state.func_middleware_postgres_select(client_postgres_dict=app_state.client_postgres_dict, cache_postgres_schema_dict=app_state.cache_postgres_schema_dict, is_connection_param=is_connection_param, connection=request.query_params.get("connection"))
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
                    await app_state.func_middleware_api_cache(mode="set", path=path, query_params=query_params, response=Response(content=b"".join(capture), status_code=200), cache=cache, client_redis=app_state.client_redis_dict.get("api_response"), user_id=user_id, cache_api_response=app_state.cache_api_response)
                    response_type = "direct_cache_set"
        # error
        except Exception as e:
            response_type = "error"
            error, response = await app_state.func_middleware_api_response_error(exception=e, is_traceback=True, sentry_dsn=app_state.config_sentry_dsn)
            # an error after the response started cannot replace it; it is still logged below
            if not sent["is_started"]: await response(scope, receive, send_wrapped)
        # form close (a background request closes its own when the task ends)
        if response_type != "background_added": await app_state.func_request_form_close(request=request)
        # api log buffer, written after the response was sent (config_api is_log_api: False skips it, e.g. /pgweb)
        if api_cfg.get("is_log_api", True): await app_state.func_middleware_log_api_write(app_state=app_state, request=request, response_type=response_type, status_code=sent["status"], start=start, error=error)
    return run
app.add_middleware(middleware)

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
