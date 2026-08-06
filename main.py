# packages
import asyncio
import importlib.util
import os
import time
from contextlib import asynccontextmanager, suppress
import uvicorn

# custom
from function import *
from config import *
if importlib.util.find_spec("function_extend"): from function_extend import *
if importlib.util.find_spec("config_extend"): from config_extend import *

# lifespan
@asynccontextmanager
async def func_lifespan(app:"FastAPI"):
    try:
        # start
        start_journey = time.perf_counter()
        app.state.runtime_background_tasks = set()
        app.state.postgres_buffer_flush_task = None
        app.state.inmemory_cache_cleanup_task = None
        # check
        func_check(app=app)
        func_structure_init()
        # client init
        client_password_hasher = func_client_password_hasher()
        client_http = func_client_http()
        postgres_pool_kwargs = {"min_size": app.state.config_postgres_pool_min_size, "max_size": app.state.config_postgres_pool_max_size, "is_read_only": app.state.config_is_read_only}
        client_postgres = await func_client_postgres(dsn=app.state.config_postgres_url, **postgres_pool_kwargs)
        client_postgres_dict = {name: await func_client_postgres(dsn=url, **postgres_pool_kwargs) for name, url in (app.state.config_postgres_url_dict or {}).items() if url}
        client_redis = func_client_redis(url=app.state.config_redis_url)
        client_redis_user_state = func_client_redis(url=app.state.config_redis_url_user_state)
        client_redis_ratelimiter = func_client_redis(url=app.state.config_redis_url_ratelimiter)
        client_redis_producer = func_client_redis(url=app.state.config_redis_url_queue)
        client_mongodb = func_client_mongodb(url=app.state.config_mongodb_url)
        client_mssql = await func_client_mssql(dsn=app.state.config_mssql_url)
        client_clickhouse = await func_client_clickhouse(dsn=app.state.config_clickhouse_url)
        aws_kwargs = {"aws_access_key_id": app.state.config_aws_access_key_id, "aws_secret_access_key": app.state.config_aws_secret_access_key}
        client_s3_context, client_s3 = await func_client_s3(region_name=app.state.config_aws_s3_region_name, **aws_kwargs)
        client_s3_resource = func_client_s3_resource(region_name=app.state.config_aws_s3_region_name, **aws_kwargs)
        client_sns = func_client_sns(region_name=app.state.config_aws_sns_region_name, **aws_kwargs)
        client_ses = func_client_ses(region_name=app.state.config_aws_ses_region_name, **aws_kwargs)
        client_openai = func_client_openai(api_key=app.state.config_openai_key)
        client_gemini = func_client_gemini(api_key=app.state.config_gemini_key)
        client_posthog = func_client_posthog(project_key=app.state.config_posthog_project_key, host=app.state.config_posthog_project_host)
        client_celery_producer = func_client_celery(url=app.state.config_celery_url)
        client_kafka_producer = await func_client_kafka(url=app.state.config_kafka_url, username=app.state.config_kafka_username, password=app.state.config_kafka_password)
        client_rabbitmq, client_rabbitmq_producer = await func_client_rabbitmq(url=app.state.config_rabbitmq_url)
        client_sftp = await func_client_sftp(host=app.state.config_sftp_host, port=app.state.config_sftp_port, username=app.state.config_sftp_username, password=app.state.config_sftp_password)
        client_azure_email = func_client_azure_email(connection_string=app.state.config_azure_email_connection_string)
        client_azure_blob = func_client_azure_blob(account_name=app.state.config_azure_account_name, account_key=app.state.config_azure_account_key)
        # client helper
        if app.state.config_log_db is not None and app.state.config_log_db not in client_postgres_dict: raise Exception(f"config_log_db '{app.state.config_log_db}' not found in config_postgres_url_dict")
        client_postgres_log = client_postgres if app.state.config_log_db is None else client_postgres_dict[app.state.config_log_db]
        # postges schema init
        if client_postgres and not app.state.config_is_read_only and app.state.config_is_enable_postgres_schema_init: await app.state.func_postgres_schema_init(client_postgres=client_postgres, config_postgres=app.state.config_postgres, root_user_password_hash=client_password_hasher.hash(config_root_user_password) if config_root_user_password else None)
        # cache schema init
        cache_postgres_schema = await app.state.func_postgres_schema_read(client_postgres=client_postgres) if client_postgres else {}
        cache_postgres_schema_ai = await app.state.func_postgres_schema_read_ai(client_postgres=client_postgres) if client_postgres else {}
        cache_postgres_schema_dict = {name: await app.state.func_postgres_schema_read(client_postgres=client) for name, client in client_postgres_dict.items()}
        cache_postgres_schema_ai_dict = {name: await app.state.func_postgres_schema_read_ai(client_postgres=client) for name, client in client_postgres_dict.items()}
        cache_postgres_schema_table_list = list(cache_postgres_schema.keys())
        cache_postgres_schema_column_list = sorted(list(set(col for table in cache_postgres_schema.values() for col in table.keys())))
        #cache db names
        cache_postgres_db_name_list = list(client_postgres_dict)
        # cache data init
        cache_config = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("config"), is_json_value=1) if client_postgres and "config" in cache_postgres_schema else {}
        cache_users_role = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("users_role")) if client_postgres else {}
        cache_users_deactivated = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("users_deactivated")) if client_postgres else {}
        cache_users_deleted = await app.state.func_postgres_map_column(client_postgres=client_postgres, config_sql=app.state.config_sql.get("users_deleted")) if client_postgres else {}
        # caches in-memory
        cache_api_response = {}
        cache_ratelimiter = {}
        cache_postgres_buffer_create = {}
        cache_postgres_buffer_log_api = {}
        # app state add
        func_app_state_add(app=app, data_dict={**globals(), **locals()}, prefixes=("client_", "cache_"))
        # openapi spec generation
        app.state.cache_openapi = app.state.func_openapi_spec_generate(app_routes=app.routes, app_state=app.state)
        # start periodic tasks
        app.state.postgres_buffer_flush_lock = asyncio.Lock()
        if not app.state.config_is_read_only: app.state.postgres_buffer_flush_task = asyncio.create_task(app.state.func_postgres_buffers_flush_periodic(app_state=app.state, client_postgres=client_postgres, cache_postgres_buffer_create=cache_postgres_buffer_create, client_postgres_log=client_postgres_log, cache_postgres_buffer_log_api=cache_postgres_buffer_log_api, interval_sec=60))
        app.state.inmemory_cache_cleanup_task = asyncio.create_task(app.state.func_inmemory_cache_cleanup_periodic(cache_api_response=cache_api_response, cache_ratelimiter=cache_ratelimiter, interval_sec=300))
    except Exception as e:
        print(f"❌ startup error: {e}")
        raise
    # shutdown
    yield
    try:
        # stop runtime background tasks
        runtime_background_tasks = getattr(app.state, "runtime_background_tasks", set())
        if runtime_background_tasks:
            await app.state.func_async_tasks_cancel(task_list=list(runtime_background_tasks), timeout_sec=5)
        # stop periodic tasks
        postgres_buffer_flush_task = getattr(app.state, "postgres_buffer_flush_task", None)
        if postgres_buffer_flush_task: await app.state.func_async_tasks_cancel(task_list=[postgres_buffer_flush_task], timeout_sec=5)
        inmemory_cache_cleanup_task = getattr(app.state, "inmemory_cache_cleanup_task", None)
        if inmemory_cache_cleanup_task: await app.state.func_async_tasks_cancel(task_list=[inmemory_cache_cleanup_task], timeout_sec=5)
        # postgres buffer flush final
        if not app.state.config_is_read_only:
            try:
                await app.state.func_postgres_buffer_flush(app_state=app.state, client_postgres=client_postgres, cache_postgres_buffer=cache_postgres_buffer_create)
            except Exception as e: print(f"❌ final primary buffer flush error: {e}")
            try:
                await app.state.func_postgres_buffer_flush(app_state=app.state, client_postgres=client_postgres_log, cache_postgres_buffer=cache_postgres_buffer_log_api)
            except Exception as e: print(f"❌ final log api buffer flush error: {e}")
        # client disconnect
        await func_client_close(app_state=app.state)
    except Exception as e:
        print(f"❌ shutdown error: {e}")

# app
app = func_app_fastapi_create(config_is_debug=config_is_debug, lifespan=func_lifespan)
# state
func_app_state_add(app=app, data_dict=globals(), prefixes=("func_", "config_"))
func_app_router_add(app=app, router_dir=os.path.join(os.path.dirname(__file__), "router"), router_order={"index": 0, "auth": 1, "my": 2, "public": 3, "private": 4, "admin": 5})
func_app_static_add(app=app)
func_sentry_init(config_sentry_dsn=config_sentry_dsn)

# middleware
@app.middleware("http")
async def middleware(request, api_function):
    #request init
    if request.method == "OPTIONS": return await api_function(request)
    start, error, response_type, request.state.user = time.perf_counter(), None, "direct_no_cache_set", {}
    app_state = request.app.state
    try:
        # route config
        route = request.scope.get("route")
        path = request.url.path
        route_path = getattr(route, "path", None) or path
        api_cfg = app_state.config_api.get(route_path, {})
        is_token_check = api_cfg.get("is_token_check", 0)
        user_check_role = api_cfg.get("user_check_role")
        user_check_deactivated = api_cfg.get("user_check_deactivated")
        user_check_deleted = api_cfg.get("user_check_deleted")
        rate_limit = api_cfg.get("rate_limit")
        cache = api_cfg.get("cache")
        # authentication
        request.state.user = await app_state.func_token_decode(headers=request.headers, config_token_secret_key=app_state.config_token_secret_key)
        await app_state.func_middleware_check_token(user_dict=request.state.user, url_path=path, is_token_check=is_token_check, user_check_role=user_check_role, user_check_deactivated=user_check_deactivated, user_check_deleted=user_check_deleted)
        # authorization
        await app_state.func_middleware_check_role(user_dict=request.state.user, user_check_role=user_check_role, client_postgres=app_state.client_postgres, client_redis=app_state.client_redis_user_state, cache_users_role=app_state.cache_users_role, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_middleware_check_user_deactivated(user_dict=request.state.user, user_check_deactivated=user_check_deactivated, client_postgres=app_state.client_postgres, client_redis=app_state.client_redis_user_state, cache_users_deactivated=app_state.cache_users_deactivated, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        await app_state.func_middleware_check_user_deleted(user_dict=request.state.user, user_check_deleted=user_check_deleted, client_postgres=app_state.client_postgres, client_redis=app_state.client_redis_user_state, cache_users_deleted=app_state.cache_users_deleted, config_redis_cache_ttl_sec=app_state.config_redis_cache_ttl_sec)
        # rate limiting
        await app_state.func_middleware_check_ratelimiter(client_redis=app_state.client_redis_ratelimiter, rate_limit=rate_limit, url_path=path, identifier=request.state.user.get("id") if request.state.user else request.client.host, cache_ratelimiter=app_state.cache_ratelimiter)
        # api cache
        user_id, query_params = (request.state.user.get("id") if request.state.user else 0), dict(request.query_params)
        response = await app_state.func_middleware_api_cache(mode="get", path=path, query_params=query_params, cache=cache, client_redis=app_state.client_redis, user_id=user_id, cache_api_response=app_state.cache_api_response)
        # api execution
        if not response:
            if query_params.get("is_background") == "1":
                response_type = "background_added"
                response = await app_state.func_middleware_api_background(scope=request.scope, body_bytes=await request.body(), api_function=api_function)
            else:
                response = await api_function(request)
                response = await app_state.func_middleware_api_cache(mode="set", path=path, query_params=query_params, response=response, cache=cache, client_redis=app_state.client_redis, user_id=user_id, cache_api_response=app_state.cache_api_response)
                if getattr(response, "is_cache_set", False): response_type = "direct_cache_set"
        else:
            response_type = "cache_response"
    # error response
    except Exception as e:
        response_type = "error"
        error, response = await app_state.func_middleware_api_response_error(exception=e, is_traceback=1, sentry_dsn=app_state.config_sentry_dsn)
    # api log buffer
    if not app_state.config_is_read_only and app_state.client_postgres_log:
        with suppress(Exception): await app_state.func_postgres_create(client_postgres=app_state.client_postgres_log, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_log_api, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get("log_api", {}).get("buffer_limit", app_state.config_buffer_limit_default), mode="buffer", table="log_api", obj_list=[{"created_by_id": request.state.user.get("id") if getattr(request.state, "user", None) else None, "response_type": response_type, "ip_address": request.client.host if request.client else None, "path": request.url.path, "method": request.method, "query_param": str(request.query_params), "status_code": response.status_code if hasattr(response, "status_code") else None, "response_time_ms": int((time.perf_counter() - start) * 1000), "error": error}])
    return response

# cors
func_app_cors_add(app=app, allow_origins=config_cors_allow_origins, allow_origin_regex=config_cors_allow_origin_regex, allow_methods=config_cors_allow_methods, allow_headers=config_cors_allow_headers, expose_headers=config_cors_expose_headers, allow_credentials=config_cors_allow_credentials)

# main
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
