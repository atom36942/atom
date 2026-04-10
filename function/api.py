async def func_table_tag_read(postgres_pool: any, table_name: str, column_name: str, filter_column: str = None, filter_value: any = None, limit_count: int = None, page_number: int = None) -> list:
    """Read unique tags/items from an array column with occurrence counts."""
    import re
    limit = min(max(int(limit_count or 100), 1), 500)
    page = max(int(page_number or 1), 1)
    regex_identifier = re.compile(r"^[a-z_][a-z0-9_]*$")
    if not regex_identifier.match(table_name):
        raise Exception("table identifier invalid")
    if not regex_identifier.match(column_name):
        raise Exception("column identifier invalid")
    if filter_column and not regex_identifier.match(filter_column):
        raise Exception("bad filter column identifier")
    where_clause = ""
    query_args = []
    if filter_column and filter_value is not None:
        where_clause = f"WHERE x.{filter_column}=$1"
        query_args = [filter_value]
    query = f"SELECT tag_item, count(*) FROM {table_name} x CROSS JOIN LATERAL unnest(x.{column_name}) tag_item {where_clause} GROUP BY tag_item ORDER BY count(*) DESC LIMIT {limit} OFFSET {(page-1)*limit}"
    async with postgres_pool.acquire() as conn:
        rows = await conn.fetch(query, *query_args)
    return [{"tag": row["tag_item"], "count": row["count"]} for row in rows]

async def func_api_response_error(exception: Exception, is_traceback: int, sentry_dsn: str) -> tuple[str, any]:
    """Central API error handler: formats database, client, and system exceptions into a standard JSON response."""
    import traceback, asyncpg, re, botocore.exceptions, redis.exceptions, httpx, jwt.exceptions
    from fastapi import responses
    if isinstance(exception, asyncpg.exceptions.UniqueViolationError):
        column = re.findall(r"\((.*?)\)=", exception.detail or "")
        error_msg = (column[0].replace("_", " ") + " already exists") if column else "duplicate value"
    elif isinstance(exception, asyncpg.exceptions.CheckViolationError):
        constraint = exception.constraint_name or ""
        error_msg = re.sub(r"^constraint_|_regex$", "", constraint).replace("_", " ") + " invalid"
    elif isinstance(exception, asyncpg.exceptions.ForeignKeyViolationError):
        column = re.findall(r"\((.*?)\)=", exception.detail or "")
        error_msg = (column[0].replace("_", " ") + " invalid reference") if column else "invalid reference"
    elif isinstance(exception, asyncpg.exceptions.NotNullViolationError):
        column = re.findall(r"\"(.*?)\"", exception.message or "")
        error_msg = (column[-1].replace("_", " ") + " required") if column else "missing required field"
    elif isinstance(exception, asyncpg.exceptions.InvalidTextRepresentationError):
        error_msg = "invalid database input text format"
    elif isinstance(exception, asyncpg.exceptions.NumericValueOutOfRangeError):
        error_msg = "invalid database input numeric range"
    elif isinstance(exception, asyncpg.exceptions.StringDataRightTruncationError):
        error_msg = "invalid database input string truncation"
    elif isinstance(exception, asyncpg.exceptions.DeadlockDetectedError):
        error_msg = "database conflict deadlock detected"
    elif isinstance(exception, asyncpg.exceptions.SerializationError):
        error_msg = "database conflict serialization error"
    elif isinstance(exception, botocore.exceptions.ClientError):
        error_msg = f"""cloud service error: {exception.response.get("Error", {}).get("Code", "Unknown")}"""
    elif isinstance(exception, redis.exceptions.RedisError):
        error_msg = "cache service error"
    elif isinstance(exception, jwt.exceptions.PyJWTError):
        error_msg = "authentication token invalid"
    elif isinstance(exception, httpx.HTTPStatusError):
        error_msg = f"external api error: {exception.response.status_code}"
    else:
        error_msg = str(exception)
    if is_traceback:
        print(traceback.format_exc())
    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.capture_exception(exception)
    return error_msg, responses.JSONResponse(status_code=400, content={"status": 0, "message": error_msg})

async def func_api_log_create(config_is_log_api: int, api_id: int, request_obj: any, response_obj: any, response_time_ms: int, user_id: any, func_postgres_create: callable, client_postgres_pool: any, func_postgres_obj_serialize: callable, config_table: dict) -> None:
    """Log API request details asynchronously if enabled in config."""
    if config_is_log_api == 0:
        return None
    log_obj = {
        "created_by_id": user_id,
        "type": 1,
        "ip_address": request_obj.client.host,
        "api": request_obj.url.path,
        "api_id": api_id,
        "method": request_obj.method,
        "query_param": str(request_obj.query_params),
        "status_code": response_obj.status_code,
        "response_time_ms": response_time_ms
    }
    await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "buffer", "log_api", [log_obj], is_serialize=0, config_table=config_table.get("log_api", {}).get("buffer", 100))
    return None

async def func_api_response_background(scope: dict, body_bytes: bytes, api_function: callable) -> any:
    """Execute an API function in the background and return a 200 response immediately."""
    from fastapi import Request, responses
    from starlette.background import BackgroundTask
    async def receive_provider(): return {"type": "http.request", "body": body_bytes}
    async def api_task_execution():
        new_request = Request(scope=scope, receive=receive_provider)
        await api_function(new_request)
    background_resp = responses.JSONResponse(status_code=200, content={"status": 1, "message": "added in background"})
    background_resp.background = BackgroundTask(api_task_execution)
    return background_resp

async def func_api_response(request: any, api_function: callable, config_api: dict, client_redis: any, user_id: int, func_background: callable, func_cache: callable) -> tuple:
    """Orchestrate API request handling, including background task delegation and cache management."""
    from fastapi import responses
    path = request.url.path
    query_params = dict(request.query_params)
    api_cfg = config_api.get(path, {})
    cache_sec_config = api_cfg.get("api_cache_sec")
    response = None
    resp_type = 0
    if query_params.get("is_background") == "1":
        body_bytes = await request.body()
        response = await func_background(request.scope, body_bytes, api_function)
        resp_type = 1
    elif cache_sec_config:
        response = await func_cache("get", path, query_params, config_api, client_redis, user_id, None)
        if response:
            resp_type = 2
    if not response:
        response = await api_function(request)
        resp_type = 3
        if cache_sec_config:
            response = await func_cache("set", path, query_params, config_api, client_redis, user_id, response)
            resp_type = 4
    return response, resp_type


async def func_client_download_file(file_path: str, is_delete_after: int = None, chunk_size: int = None) -> any:
    """Stream a file for client download with optional automatic cleanup after transmission."""
    if "tmp/" not in str(file_path):
        raise Exception("IO Boundary Violation: tmp/ path required")
    from fastapi import responses
    from starlette.background import BackgroundTask
    import os, mimetypes, aiofiles
    is_delete_after = is_delete_after if is_delete_after is not None else 1
    chunk_size = chunk_size or 1048576
    file_name = os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    async def file_iterator():
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    return responses.StreamingResponse(file_iterator(), media_type=content_type, headers={"Content-Disposition": f"attachment; filename=\"{file_name}\""}, background=BackgroundTask(os.remove, file_path) if is_delete_after == 1 else None)

async def func_request_param_read(request_obj: any, parsing_mode: str, param_config: list, is_strict: int = None) -> dict:
    """Extract, validate, and type-cast request parameters from query, form, body or headers."""
    is_strict = is_strict or 0
    params_dict = {}
    header_params = {k.lower(): v for k, v in request_obj.headers.items()}
    if parsing_mode == "query":
        params_dict = dict(request_obj.query_params)
    elif parsing_mode == "form":
        form_data = await request_obj.form()
        params_dict = {key: val for key, val in form_data.items() if isinstance(val, str)}
        for key in form_data.keys():
            files = [x for x in form_data.getlist(key) if getattr(x, "filename", None)]
            if files:
                params_dict[key] = files
    elif parsing_mode == "body":
        try:
            json_payload = await request_obj.json()
        except Exception:
            json_payload = None
        params_dict = json_payload if isinstance(json_payload, dict) else {"body": json_payload}
    elif parsing_mode == "header":
        params_dict = header_params
    else:
        raise Exception(f"invalid parsing mode: {parsing_mode}")
    if param_config is None:
        return params_dict
    import orjson
    def smart_dict(v):
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and v.strip():
            try:
                return orjson.loads(v)
            except Exception:
                pass
        return {}
    TYPE_MAP = {
        "int": int, "bigint": int, "smallint": int, "integer": int, "int4": int, "int8": int,
        "float": float, "number": float, "numeric": float,
        "str": str, "any": lambda v: v, 
        "bool": lambda v: 1 if str(v).strip().lower() in ("1", "true", "yes", "on", "ok") else 0, 
        "dict": smart_dict, "object": smart_dict,
        "file": lambda v: ([] if v is None else v if isinstance(v, list) else [v]),
        "list": lambda v: [] if v is None else v if isinstance(v, list) else [] if (isinstance(v, str) and not v.strip()) else [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else [v]
    }
    output_dict = params_dict.copy() if not is_strict else {}
    for param in param_config:
        key, data_type, is_mandatory, allowed_values, default_value = param[:5]
        val = params_dict.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            if is_mandatory:
                raise Exception(f"mandatory parameter missing: {key}")
            if default_value is not None:
                val = default_value
        if val is not None:
            caster = TYPE_MAP.get(data_type, lambda v: v)
            try:
                val = caster(val)
            except Exception:
                raise Exception(f"parameter type mismatch: {key} (expected {data_type})")
            if allowed_values and val not in allowed_values:
                raise Exception(f"parameter value not allowed: {key} (allowed: {allowed_values})")
        output_dict[key] = val
    return output_dict
