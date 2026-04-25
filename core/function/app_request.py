async def func_request_param_read(*, request: any, mode: str, strict: int, config: list) -> dict:
    """Extract, validate, and type-cast request parameters from query, form, body or headers."""
    params_dict = {}
    header_params = {k.lower(): v for k, v in request.headers.items()}
    if mode == "query":
        params_dict = dict(request.query_params)
    elif mode == "form":
        form_data = await request.form()
        params_dict = {key: val for key, val in form_data.items() if isinstance(val, str)}
        for key in form_data.keys():
            files = [x for x in form_data.getlist(key) if not isinstance(x, str)]
            if files:
                params_dict[key] = files
    elif mode == "body":
        try:
            json_payload = await request.json()
        except Exception:
            json_payload = None
        params_dict = json_payload if isinstance(json_payload, dict) else {"body": json_payload}
    elif mode == "header":
        params_dict = header_params
    else:
        raise Exception(f"invalid mode: {mode}")
    if config is None:
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
        "file": lambda v: [x for x in (v if isinstance(v, list) else [v] if v is not None else []) if hasattr(x, "file")],
        "list": lambda v: [] if v is None else v if isinstance(v, list) else [] if (isinstance(v, str) and not v.strip()) else [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else [v]
    }
    output_dict = params_dict.copy() if not strict else {}
    for param in config:
        if not isinstance(param, (list, tuple)):
            raise Exception(f"invalid configuration format: expected list or tuple, got {type(param)}")
        param_len = len(param)
        if param_len < 5:
            param_key = param[0] if param_len > 0 else "unknown"
            raise Exception(f"invalid config tuple length {param_len} for '{param_key}': (key, dtype, is_mandatory, allowed_values, default_value) are required")
        key, dtype, is_mandatory, allowed_values, default_value = param[0], param[1], int(param[2]), param[3], param[4]
        regex_info = param[5] if param_len > 5 else None
        regex_pattern = regex_info[0] if isinstance(regex_info, (list, tuple)) and len(regex_info) > 0 else None
        custom_error = regex_info[1] if isinstance(regex_info, (list, tuple)) and len(regex_info) > 1 else None
        if dtype not in TYPE_MAP and not dtype.startswith("list:"):
            raise Exception(f"parameter '{key}' has invalid dtype '{dtype}'")
        if is_mandatory == 1 and default_value is not None:
            raise Exception(f"parameter '{key}' is mandatory, default_value must be None")
        if default_value is not None and allowed_values and default_value not in allowed_values:
            raise Exception(f"parameter '{key}' default '{default_value}' violating allowed_values: {allowed_values}")
        if allowed_values is not None and not isinstance(allowed_values, (list, tuple)):
            raise Exception(f"parameter '{key}' allowed_values must be a list or tuple")
        val = params_dict.get(key)
        if val is None:
            val = header_params.get(key.lower())
        if val is None:
            val = default_value
        if isinstance(val, str) and val.lower() in ("null", "undefined"):
            val = default_value
        if is_mandatory == 1:
            if val is None:
                raise Exception(f"parameter '{key}' missing")
            if isinstance(val, str) and not val.strip():
                raise Exception(f"parameter '{key}' cannot be empty")
        if val is not None:
            try:
                if dtype.startswith("list:") and ":" in dtype:
                    inner_type = dtype.split(":")[1]
                    val_list = TYPE_MAP["list"](val)
                    val = [TYPE_MAP[inner_type](x) for x in val_list]
                else:
                    val = TYPE_MAP[dtype](val)
            except Exception:
                raise Exception(f"parameter '{key}' invalid type {dtype}")
        if is_mandatory == 1:
            if dtype == "file" and (not isinstance(val, list) or len(val) == 0):
                raise Exception(f"parameter '{key}' missing or invalid file upload")
            if dtype == "list" and (not isinstance(val, list) or len(val) == 0):
                 raise Exception(f"parameter '{key}' missing or empty list")
        if val is not None and allowed_values and val not in allowed_values:
            raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        if val is not None and regex_pattern:
            import re
            if not re.match(regex_pattern, str(val)):
                raise Exception(custom_error if custom_error else f"parameter '{key}' format invalid")
        output_dict[key] = val
    return output_dict
async def func_check_cache(*, mode: str, url_path: str, query_params: dict, config_api: dict, client_redis: any, user_id: int, response: any, cache_api_response: dict) -> any:
    """Retrieve from or store to cache API responses based on configuration."""
    from fastapi import Response
    import gzip, base64, time
    if mode not in ["get", "set"]:
        raise Exception(f"invalid cache mode: {mode}")
    uid = user_id if "my/" in url_path else 0
    cache_key = f"""cache:{url_path}?{"&".join(f"{k}={v}" for k, v in sorted(query_params.items()))}:{uid}"""
    api_cfg = config_api.get(url_path, {})
    cache_mode, expire_sec = api_cfg.get("api_cache_sec", (None, None))
    if not (expire_sec is not None and expire_sec > 0):
        return None if mode == "get" else response
    if mode == "get":
        cached_data = None
        if cache_mode == "redis":
            cached_data = await client_redis.get(cache_key)
        elif cache_mode == "inmemory":
            item = cache_api_response.get(cache_key)
            if item and item["expire_at"] > time.time():
                cached_data = item["data"]
        if cached_data:
            return Response(content=gzip.decompress(base64.b64decode(cached_data)).decode(), status_code=200, media_type="application/json", headers={"x-cache": "hit"})
        return None
    elif mode == "set":
        body_content = getattr(response, "body", None)
        if body_content is None:
            body_content = b"".join([chunk async for chunk in response.body_iterator])
        compressed_body = base64.b64encode(gzip.compress(body_content)).decode()
        if cache_mode == "redis":
            await client_redis.setex(cache_key, expire_sec, compressed_body)
        elif cache_mode == "inmemory":
            cache_api_response[cache_key] = {"data": compressed_body, "expire_at": time.time() + expire_sec}
        return Response(content=body_content, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))

async def func_api_response_background(*, scope: dict, body_bytes: bytes, api_function: callable) -> any:
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

async def func_api_response(*, request: any, api_function: callable, config_api: dict, client_redis: any, user_id: int, func_background: callable, func_cache: callable, cache_api_response: dict) -> tuple:
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
        response = await func_background(scope=request.scope, body_bytes=body_bytes, api_function=api_function)
        resp_type = 1
    elif cache_sec_config:
        response = await func_cache(mode="get", url_path=path, query_params=query_params, config_api=config_api, client_redis=client_redis, user_id=user_id, response=None, cache_api_response=cache_api_response)
        if response:
            resp_type = 2
    if not response:
        response = await api_function(request)
        resp_type = 3
        if cache_sec_config:
            response = await func_cache(mode="set", url_path=path, query_params=query_params, config_api=config_api, client_redis=client_redis, user_id=user_id, response=response, cache_api_response=cache_api_response)
            resp_type = 4
    return response, resp_type

async def func_api_response_error(*, exception: Exception, is_traceback: int, sentry_dsn: str) -> tuple:
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
