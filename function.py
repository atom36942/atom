#system & structure
def func_structure_create(directories_list: list, files_list: list) -> None:
    """Create directory and file structure if it doesn't exist."""
    import os
    for directory_path in directories_list:
        try: os.makedirs(directory_path, exist_ok=True)
        except: pass
    for file_path in files_list:
        try:
            if not os.path.exists(file_path): open(file_path, "a").close()
        except: pass

def func_structure_check(root_path: str, dirs: tuple = (), files: tuple = ()) -> None:
    """Verify existence of required project directories and files."""
    from pathlib import Path
    try:
        root = Path(root_path)
        if not root.exists(): return None
        missing_dirs = [directory_name for directory_name in dirs if not (root / directory_name).is_dir()]
        missing_files = [file_name for file_name in files if not (root / file_name).is_file()]
        if missing_dirs or missing_files:
            print(f"Structure verification failed. Missing Dirs: {missing_dirs}, Missing Files: {missing_files}")
    except: pass
    return None


#utils & converters
async def func_table_tag_read(postgres_pool: any, table_name: str, column_name: str, filter_column: str = None, filter_value: any = None, limit_count: int = 100, page_number: int = 1) -> list:
    """Read unique tags/items from an array column with occurrence counts."""
    import re
    limit, page = min(max(int(limit_count or 100), 1), 500), max(int(page_number or 1), 1)
    regex_identifier = re.compile(r"^[a-z_][a-z0-9_]*$")
    if not all(regex_identifier.match(x) for x in (table_name, column_name) if x): raise Exception("bad table or column identifier")
    if filter_column and not regex_identifier.match(filter_column): raise Exception("bad filter column identifier")
    where_clause, query_args = (f"WHERE x.{filter_column}=$1", [filter_value]) if filter_column and filter_value is not None else ("", [])
    query = f"SELECT tag_item, count(*) FROM {table_name} x CROSS JOIN LATERAL unnest(x.{column_name}) tag_item {where_clause} GROUP BY tag_item ORDER BY count(*) DESC LIMIT {limit} OFFSET {(page-1)*limit}"
    async with postgres_pool.acquire() as conn: rows = await conn.fetch(query, *query_args)
    return [{"tag": row['tag_item'], "count": row['count']} for row in rows]

def func_gemini_client_read(gemini_api_key: str) -> any:
    """Initialize Google Gemini AI client."""
    try: from google import genai
    except: import genai
    return genai.Client(api_key=gemini_api_key)

async def func_html_serve(html_name: str) -> any:
    """Serve local HTML files from the static directory with search-fallback."""
    import os, aiofiles
    from pathlib import Path
    from fastapi import responses, HTTPException
    file_name = html_name if html_name.endswith(".html") else f"{html_name}.html"
    static_root, file_path = Path("static"), Path("static") / file_name
    if not file_path.is_file():
        for found_path in static_root.rglob(file_name):
            if found_path.is_file(): file_path = found_path; break
        else: raise HTTPException(404, "page not found")
    resolved_path = str(file_path)
    if ".." in resolved_path: raise HTTPException(400, "invalid name")
    absolute_path = os.path.abspath(resolved_path)
    if not absolute_path.endswith(".html") or not os.path.isfile(absolute_path): raise HTTPException(404, "file not found")
    try:
        async with aiofiles.open(absolute_path, "r", encoding="utf-8") as file_handle: html_content = await file_handle.read()
    except: raise HTTPException(500, "failed to read file")
    return responses.HTMLResponse(content=html_content)


#api & middleware utilities
async def func_api_response_error(exception: Exception, is_traceback: int, sentry_dsn: str) -> tuple[str, any]:
    """Central API error handler: formats database, client, and system exceptions into a standard JSON response."""
    import traceback, asyncpg, re, botocore.exceptions, redis.exceptions, httpx, jwt.exceptions
    from fastapi import responses
    if isinstance(exception, asyncpg.exceptions.UniqueViolationError): column = re.findall(r'\((.*?)\)=', exception.detail or ""); error_msg = (column[0].replace("_", " ") + " already exists") if column else "duplicate value"
    elif isinstance(exception, asyncpg.exceptions.CheckViolationError): constraint = exception.constraint_name or ""; error_msg = re.sub(r"^constraint_|_regex$", "", constraint).replace("_", " ") + " invalid"
    elif isinstance(exception, asyncpg.exceptions.ForeignKeyViolationError): column = re.findall(r'\((.*?)\)=', exception.detail or ""); error_msg = (column[0].replace("_", " ") + " invalid reference") if column else "invalid reference"
    elif isinstance(exception, asyncpg.exceptions.NotNullViolationError): column = re.findall(r'"(.*?)"', exception.message or ""); error_msg = (column[-1].replace("_", " ") + " required") if column else "missing required field"
    elif isinstance(exception, (asyncpg.exceptions.InvalidTextRepresentationError, asyncpg.exceptions.NumericValueOutOfRangeError, asyncpg.exceptions.StringDataRightTruncationError)): error_msg = "invalid database input"
    elif isinstance(exception, (asyncpg.exceptions.DeadlockDetectedError, asyncpg.exceptions.SerializationError)): error_msg = "database conflict retry"
    elif isinstance(exception, botocore.exceptions.ClientError): error_msg = f"cloud service error: {exception.response.get('Error', {}).get('Code', 'Unknown')}"
    elif isinstance(exception, redis.exceptions.RedisError): error_msg = "cache service error"
    elif isinstance(exception, jwt.exceptions.PyJWTError): error_msg = "authentication token invalid"
    elif isinstance(exception, httpx.HTTPStatusError): error_msg = f"external api error: {exception.response.status_code}"
    else: error_msg = str(exception)
    if is_traceback: print(traceback.format_exc())
    if sentry_dsn: import sentry_sdk; sentry_sdk.capture_exception(exception)
    return error_msg, responses.JSONResponse(status_code=400, content={"status": 0, "message": error_msg})

async def func_api_log_create(start_time: float, ip_address: str, user_id: any, api_path: str, http_method: str, query_params: str, status_code: int, log_type: int, error_description: str, is_log_api: int, api_id: int, func_postgres_obj_create: callable, postgres_pool: any, func_postgres_obj_serialize: callable, table_buffer: int) -> None:
    """Create an API execution log entry asynchronously."""
    import asyncio, time
    if is_log_api:
        log_obj = {"ip_address": ip_address, "created_by_id": user_id, "api": api_path, "api_id": api_id, "method": http_method, "query_param": query_params, "status_code": status_code, "response_time_ms": int((time.perf_counter() - start_time) * 1000), "type": log_type, "description": error_description}
        asyncio.create_task(func_postgres_obj_create(postgres_pool, func_postgres_obj_serialize, "buffer", "log_api", [log_obj], 0, table_buffer))
    return None

#api core logic
async def func_obj_create_logic(obj_query: dict, obj_body: dict, role: str, user_id: any, table_create_my_list: list, table_create_public_list: list, column_blocked_list: list, postgres_pool: any, func_postgres_obj_serialize: callable, table_config: dict, func_producer_logic: callable, celery_producer: any, kafka_producer: any, rabbitmq_producer: any, redis_producer: any, channel_name: str, func_celery_producer: callable, func_kafka_producer: callable, func_rabbitmq_producer: callable, func_redis_producer: callable, func_postgres_obj_create: callable) -> any:
    """Wrapper logic for object creation with role-based validation and optional queueing."""
    obj_list = obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
    if obj_query.get("table") == "users": obj_query["is_serialize"] = 1
    if role == "my":
        if obj_query.get("table") not in table_create_my_list: raise Exception("table not allowed")
        if any(any(key in column_blocked_list for key in item) for item in obj_list): raise Exception("key not allowed")
    if role == "public":
        if obj_query.get("table") not in table_create_public_list: raise Exception("table not allowed")
        if any(any(key in column_blocked_list for key in item) for item in obj_list): raise Exception("key not allowed")
    if user_id: [item.__setitem__("created_by_id", user_id) for item in obj_list]
    if not obj_query.get("queue"): return await func_postgres_obj_create(postgres_pool, func_postgres_obj_serialize, obj_query.get("mode"), obj_query.get("table"), obj_list, obj_query.get("is_serialize"), table_config.get(obj_query.get("table"), {}).get("buffer"))
    payload = {"func": "func_postgres_obj_create", "mode": obj_query.get("mode"), "table": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "buffer": table_config.get(obj_query.get("table"), {}).get("buffer")}
    return await func_producer_logic(payload, obj_query.get("queue"), celery_producer, kafka_producer, rabbitmq_producer, redis_producer, channel_name, func_celery_producer, func_kafka_producer, func_rabbitmq_producer, func_redis_producer)

async def func_obj_update_logic(obj_query: dict, obj_body: dict, role: str, user_id: any, column_blocked_list: list, column_single_update_list: list, postgres_pool: any, func_postgres_obj_serialize: callable, func_producer_logic: callable, celery_producer: any, kafka_producer: any, rabbitmq_producer: any, redis_producer: any, channel_name: str, func_celery_producer: callable, func_kafka_producer: callable, func_rabbitmq_producer: callable, func_redis_producer: callable, func_postgres_obj_update: callable, func_otp_verify: callable, expiry_sec_otp: int) -> any:
    """Wrapper logic for object updates with owner validation, OTP checks, and optional queueing."""
    obj_list, created_by_id = obj_body["obj_list"] if "obj_list" in obj_body else [obj_body], user_id
    if obj_query.get("table") == "users": obj_query["is_serialize"], created_by_id = 1, None
    if role == "my":
        if any(any(key in column_blocked_list for key in item) for item in obj_list): raise Exception("key not allowed")
        if obj_query.get("table") == "users":
            if len(obj_list) != 1: raise Exception("multi-object update not allowed")
            if obj_list[0].get("id") != user_id: raise Exception("ownership issue")
            if "is_deleted" in obj_list[0]: raise Exception("field is_deleted cannot be modified")
            csu = column_single_update_list.split(",") if isinstance(column_single_update_list, str) else column_single_update_list
            if any(key in obj_list[0] and len(obj_list[0]) != 2 for key in csu): raise Exception("obj length should be 2")
            if any(key in obj_list[0] for key in ("email", "mobile")): await func_otp_verify(postgres_pool, obj_query.get("otp"), obj_list[0].get("email"), obj_list[0].get("mobile"), expiry_sec_otp)
    elif role == "public": raise Exception("not allowed")
    elif role == "admin": created_by_id = None
    if user_id: [item.__setitem__("updated_by_id", user_id) for item in obj_list]
    if not obj_query.get("queue"): return await func_postgres_obj_update(postgres_pool, func_postgres_obj_serialize, obj_query.get("table"), obj_list, obj_query.get("is_serialize"), created_by_id)
    payload = {"func": "func_postgres_obj_update", "table": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "created_by_id": created_by_id}
    return await func_producer_logic(payload, obj_query.get("queue"), celery_producer, kafka_producer, rabbitmq_producer, redis_producer, channel_name, func_celery_producer, func_kafka_producer, func_rabbitmq_producer, func_redis_producer)

async def func_producer_logic(payload: dict, queue_name: str, celery_producer: any, kafka_producer: any, rabbitmq_producer: any, redis_producer: any, channel_name: str, func_celery_producer: callable, func_kafka_producer: callable, func_rabbitmq_producer: callable, func_redis_producer: callable) -> any:
    """Route payload to the appropriate message queue producer."""
    if queue_name == "celery": return func_celery_producer(celery_producer, payload["func"], [v for k, v in payload.items() if k != "func"])
    elif queue_name == "kafka": return await func_kafka_producer(kafka_producer, channel_name, payload)
    elif queue_name == "rabbitmq": return await func_rabbitmq_producer(rabbitmq_producer, channel_name, payload)
    elif queue_name == "redis": return await func_redis_producer(redis_producer, channel_name, payload)
    raise Exception("invalid queue")

async def func_consumer_logic(payload: dict, func_postgres_obj_create: callable, func_postgres_obj_update: callable, func_postgres_obj_serialize: callable, postgres_pool: any) -> any:
    """Execute background tasks received from message queues."""
    import asyncio
    from itertools import count
    if not hasattr(func_consumer_logic, "counter"): func_consumer_logic.counter = count(1)
    if payload["func"] == "func_postgres_obj_create": output = asyncio.create_task(func_postgres_obj_create(postgres_pool, func_postgres_obj_serialize, payload["mode"], payload["table"], payload["obj_list"], payload["is_serialize"], payload["buffer"]))
    elif payload["func"] == "func_postgres_obj_update": output = asyncio.create_task(func_postgres_obj_update(postgres_pool, func_postgres_obj_serialize, payload["table"], payload["obj_list"], payload["is_serialize"], payload["created_by_id"]))
    else: raise Exception("wrong consumer func")
    print(next(func_consumer_logic.counter)); return output

async def func_api_file_to_obj_list(upload_file: any) -> list:
    """Convert an uploaded CSV file into a list of dictionaries."""
    import csv, io
    reader = csv.DictReader(io.TextIOWrapper(upload_file.file, encoding="utf-8"))
    obj_list = [row for row in reader]; await upload_file.close(); return obj_list

#api metadata
def func_api_metadata_read(app_routes: list) -> list:
    """Extract API paths, methods, and parameter schemas from FastAPI routes using source inspection."""
    import inspect, re, ast
    metadata = []
    for route in app_routes:
        if not hasattr(route, "path") or not hasattr(route, "endpoint"): continue
        route_meta = {"path": route.path, "methods": list(getattr(route, "methods", [])), "params": {"header": [], "query": [], "form": [], "body": [], "path": []}}
        for p in re.findall(r"\{(\w+)\}", route.path): route_meta["params"]["path"].append({"name": p, "type": "str", "required": 1, "default": None})
        try:
            sig = inspect.signature(route.endpoint)
            for name, par in sig.parameters.items():
                p_type = par.annotation.__name__ if hasattr(par.annotation, "__name__") else str(par.annotation)
                if name in ["request", "websocket", "req"] or "Request" in p_type or "Response" in p_type or "WebSocket" in p_type or "BackgroundTasks" in p_type or any(x["name"] == name for x in route_meta["params"]["path"]): continue
                route_meta["params"]["query"].append({"name": name, "type": p_type, "required": 1 if par.default == inspect.Parameter.empty else 0, "default": None if par.default == inspect.Parameter.empty else par.default})
            source = inspect.getsource(route.endpoint)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and (getattr(node.func, "id", None) == "func_request_param_read" or (isinstance(node.func, ast.Name) and node.func.id == "func_request_param_read")):
                    try:
                        p_type = node.args[0].value if hasattr(node.args[0], "value") else node.args[0].s
                        p_list = ast.literal_eval(node.args[2])
                        for p in p_list:
                            route_meta["params"][p_type] = [x for x in route_meta["params"][p_type] if x["name"] != p[0]]
                            p_meta = {"name": p[0], "type": p[1], "required": p[2], "default": p[3], "allowed": p[4]}
                            route_meta["params"][p_type].append(p_meta)
                    except: pass
        except: pass
        p, h = route.path, route_meta["params"]["header"]
        is_auth, req = 0, 1
        if any(p.startswith(x) for x in ["/my/", "/private/", "/admin/"]): is_auth = 1
        elif not any(p.startswith(x) for x in ["/auth/", "/public/", "/openapi.json", "/docs", "/redoc"]) and p != "/": is_auth, req = 1, 0
        if is_auth and not any(x["name"].lower() == "authorization" for x in h): h.append({"name": "Authorization", "type": "str", "required": req, "default": None})
        metadata.append(route_meta)
    return metadata

def func_sync_routes_check(app_routes: list, current_config_api: dict) -> None:
    """Validate config_api consistency with app routes, ensuring all admin APIs have role 1 and all config entries exist."""
    missing, app_paths = [], {route.path for route in app_routes if hasattr(route, "path")}
    config_missing = [p for p in current_config_api if p not in app_paths]
    if config_missing: missing.append(f"config_api paths missing from app: {', '.join(config_missing)}")
    for route in app_routes:
        if hasattr(route, "path") and route.path.startswith("/admin/"):
            path = route.path
            if path not in current_config_api: missing.append(f"{path} missing from config_api")
            else:
                roles_cfg = current_config_api[path].get("roles", [])
                allowed_roles = roles_cfg[1] if roles_cfg and isinstance(roles_cfg[0], str) else roles_cfg
                if 1 not in (allowed_roles if isinstance(allowed_roles, (list, tuple, set)) else []): missing.append(f"{path} missing role 1")
    if missing: raise Exception("; ".join(missing))

def func_info_read(app_routes: list, cache_postgres_schema: dict, config_postgres: dict, config_table: dict, config_api: dict) -> dict:
    """Construct system discovery metadata including routes, schema, and configuration settings."""
    return {
        "api_list": [route.path for route in app_routes],
        "api_metadata": func_api_metadata_read(app_routes),
        "postgres_schema": cache_postgres_schema,
        "config_table_key": sorted(list(set(k for v in config_table.values() for k in v))),
        "config_api_key": sorted(list(set(k for v in config_api.values() for k in v))),
        "config_postgres_key": {k: (sorted(list(set(ck for cv in v.values() for item in cv for ck in item))) if k == "table" else sorted(list(v.keys())) if isinstance(v, dict) else []) for k, v in config_postgres.items()}
    }

def func_config_override_from_env(global_dict: dict) -> None:
    """Override configuration variables starting with 'config_' from environment variables and .env file."""
    import json, os, ast
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    for key, value in list(global_dict.items()):
        val_env = os.getenv(key)
        if key.startswith("config_") and val_env is not None:
            config_val = val_env
            if isinstance(global_dict[key], (list, tuple)): global_dict[key] = json.loads(config_val)
            elif isinstance(value, bool): global_dict[key] = config_val.lower() == "true"
            elif isinstance(value, int): global_dict[key] = int(config_val)
            elif isinstance(value, dict):
                try: global_dict[key] = json.loads(config_val)
                except: pass
            else:
                try: global_dict[key] = int(config_val)
                except: global_dict[key] = config_val
            if isinstance(global_dict[key], list): global_dict[key] = tuple(global_dict[key])
    try:
        with open("config.py", "r") as config_file:
            for node in ast.parse(config_file.read()).body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Name):
                    target_id = node.targets[0].id
                    value_id = node.value.id
                    if target_id.startswith("config_") and value_id.startswith("config_") and os.getenv(target_id) is None: global_dict[target_id] = global_dict[value_id]
    except: pass


#database - core operations
async def func_postgres_runner(postgres_pool: any, execution_mode: str, sql_query: str) -> any:
    """Execute raw SQL queries in 'read' or 'write' mode with basic DDL protection."""
    if execution_mode not in ("read", "write"): raise Exception("execution_mode should be 'read' or 'write'")
    if any(keyword in sql_query.lower() for keyword in ("drop", "truncate")): raise Exception("DDL keywords not allowed in runner")
    async with postgres_pool.acquire() as conn:
        if execution_mode == "read": return await conn.fetch(sql_query)
        return await conn.fetch(sql_query) if "returning" in sql_query.lower() else await conn.execute(sql_query)

async def func_postgres_ids_update(postgres_pool: any, table_name: str, record_ids: any, column_name: str, target_value: any, created_by_id: int = None, updated_by_id: int = None) -> None:
    """Update a specific column for a list of record IDs with ownership check."""
    if isinstance(record_ids, str): record_ids = ",".join([str(int(x.strip())) for x in record_ids.split(",") if x.strip()])
    elif isinstance(record_ids, (list, tuple)): record_ids = ",".join([str(int(x)) for x in record_ids])
    set_clause = f"{column_name}=$1" if updated_by_id is None else f"{column_name}=$1,updated_by_id=$2"
    update_query = f"UPDATE {table_name} SET {set_clause} WHERE id IN ({record_ids}) AND ($3::bigint IS NULL OR created_by_id=$3);"
    async with postgres_pool.acquire() as conn: await conn.execute(update_query, target_value, updated_by_id, created_by_id)

async def func_postgres_ids_delete(postgres_pool: any, table_name: str, record_ids: any, created_by_id: int = None) -> str:
    """Delete records by ID with optional ownership restriction."""
    if isinstance(record_ids, str): record_ids = ",".join([str(int(x.strip())) for x in record_ids.split(",") if x.strip()])
    elif isinstance(record_ids, (list, tuple)): record_ids = ",".join([str(int(x)) for x in record_ids])
    delete_query = f"DELETE FROM {table_name} WHERE id IN ({record_ids}) AND ($1::bigint IS NULL OR created_by_id=$1);"
    async with postgres_pool.acquire() as conn: await conn.execute(delete_query, created_by_id)
    return "ids deleted"

async def func_postgres_parent_read(postgres_pool: any, table_name: str, parent_column: str, parent_table: str, created_by_id: int = None, sort_order: str = "id desc", limit_count: int = 100, page_number: int = 1) -> list:
    """Read parent records based on child table's foreign key column."""
    limit, page = int(limit_count or 100), int(page_number or 1); order = sort_order or "id desc"
    query = f"WITH x AS (SELECT {parent_column} FROM {table_name} WHERE ($1::bigint IS NULL OR created_by_id=$1) ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit}) SELECT ct.* FROM x LEFT JOIN {parent_table} ct ON x.{parent_column}=ct.id;"
    async with postgres_pool.acquire() as conn: return [dict(r) for r in (await conn.fetch(query, created_by_id))]

async def func_sql_map_column(postgres_pool: any, sql_query: str) -> dict:
    """Execute a SQL query and map results into a dictionary, supporting grouping for duplicate keys."""
    import re, json
    if not sql_query: return {}
    match = re.search(r"select\s+(.*?)\s+from\s", sql_query, flags=re.I | re.S); columns = [c.strip() for c in match.group(1).split(",")]; key_col, other_cols, result_map = columns[0], columns[1:], {}
    async with postgres_pool.acquire() as conn:
        async with conn.transaction():
            async for record in conn.cursor(sql_query, prefetch=5000):
                key, val = record.get(key_col), (dict(record) if other_cols[0] == "*" else record.get(other_cols[0])) if len(other_cols) == 1 else {c: record.get(c) for c in other_cols}
                if isinstance(val, str) and val.lstrip().startswith(("{", "[")):
                    try: val = json.loads(val)
                    except: pass
                if key not in result_map: result_map[key] = val
                else:
                    if not isinstance(result_map[key], list): result_map[key] = [result_map[key]]
                    result_map[key].append(val)
    return result_map


#database - maintenance & schema
async def func_postgres_clean(postgres_pool: any, table_config: dict) -> None:
    """Delete old records from tables based on retention_day configuration."""
    from datetime import datetime, timedelta
    async with postgres_pool.acquire() as conn:
        for table, cfg in table_config.items():
            if (retention_days := cfg.get("retention_day")) is not None: await conn.execute(f"DELETE FROM {table} WHERE created_at < $1", datetime.utcnow() - timedelta(days=retention_days))
    return None

async def func_postgres_obj_read(postgres_pool: any, func_postgres_obj_serialize: callable, table_name: str, query_params: dict) -> list:
    """Powerful generic PostgreSQL object reader with complex filtering, sorting, pagination, and relation fetching."""
    import re, json
    from datetime import datetime
    def validate_identifier(name):
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', str(name)): raise Exception(f"invalid identifier {name}")
        return name
    table, limit, page = validate_identifier(table_name), int(query_params.get("limit") or 100), int(query_params.get("page") or 1)
    order_clause = ", ".join([f"{validate_identifier(p[0])} {(p[1].upper() if len(p)>1 and p[1].lower() in ('asc','desc') else 'ASC')}" for p in [part.strip().split() for part in query_params.get("order", "id desc").split(",")] if p])
    column_list = "*" if query_params.get("column", "*") == "*" else ",".join([validate_identifier(c.strip()) for c in query_params.get("column").split(",")])
    creator_key, action_key, filters = query_params.get("creator_key"), query_params.get("action_key"), {k: v for k, v in query_params.items() if k not in ("table", "order", "limit", "page", "column", "creator_key", "action_key")}
    async def serialize_filter(col, val, is_base_type=False): return (None if str(val).lower() == "null" else (await func_postgres_obj_serialize(postgres_pool, table, [{col: val}], is_base=is_base_type))[0][col])
    conditions, values, bind_idx, v_ops, s_ops = [], [], 1, {"=":"=","==":"=","!=":"!=","<>":"<>",">":">","<":"<",">=":">=","<=":"<=","is":"IS","is not":"IS NOT","in":"IN","not in":"NOT IN","between":"BETWEEN","is distinct from":"IS DISTINCT FROM","is not distinct from":"IS NOT DISTINCT FROM"}, {"like":"LIKE","ilike":"ILIKE","~":"~","~*":"~*"}
    for filter_key, expression in filters.items():
        validate_identifier(filter_key)
        if expression.lower().startswith("point,"):
            _, coords = expression.split(",", 1); lon, lat, min_dist, max_dist = [float(x) for x in coords.split("|")]; conditions.append(f"ST_Distance({filter_key}, ST_Point(${bind_idx}, ${bind_idx+1})::geography) BETWEEN ${bind_idx+2} AND ${bind_idx+3}"); values.extend([lon, lat, min_dist, max_dist]); bind_idx += 4; continue
        if not hasattr(func_postgres_obj_serialize, "state") or table not in func_postgres_obj_serialize.state or filter_key not in func_postgres_obj_serialize.state[table]: await func_postgres_obj_serialize(postgres_pool, table, [{filter_key: None}])
        datatype = func_postgres_obj_serialize.state[table].get(filter_key, "text").lower(); is_json, is_array = "json" in datatype, ("[]" in datatype or "array" in datatype)
        if "," not in expression: raise Exception(f"invalid format for {filter_key}: {expression}")
        operator, raw_val = expression.split(",", 1); operator = operator.strip().lower(); allowed_ops = list(v_ops.keys()) + (list(s_ops.keys()) if any(x in datatype for x in ("text", "char", "varchar")) else []) + (["contains", "overlap", "any"] if is_array else []) + (["contains", "exists"] if is_json else [])
        if operator not in allowed_ops: raise Exception(f"invalid operator {operator} for {filter_key}")
        serialized_val = None
        if operator == "contains":
            if is_json:
                if "|" in raw_val and not (raw_val.startswith("{") or raw_val.startswith("[")):
                    parts = raw_val.split("|"); k, vr, t = parts[0], parts[1], (parts[2].lower() if len(parts) > 2 else "str"); v = int(vr) if t == "int" else (vr.lower() == "true" if t == "bool" else float(vr) if t == "float" else vr); serialized_val = json.dumps({k: v})
                else:
                    try: serialized_val = json.dumps(json.loads(raw_val))
                    except: serialized_val = raw_val
            elif is_array:
                parts = raw_val.split("|")
                dtype = func_postgres_obj_serialize.state[table].get(filter_key, "text").lower()
                elem_type = dtype.replace("[]", "").replace("array", "").replace("int4", "int").replace("_", "").strip()
                fake_schema = {**func_postgres_obj_serialize.state[table], filter_key: elem_type}
                async def serialize_element(v):
                    orig_state = func_postgres_obj_serialize.state[table]
                    func_postgres_obj_serialize.state[table] = fake_schema
                    res = (await func_postgres_obj_serialize(postgres_pool, table, [{filter_key: v}], is_base=True))[0][filter_key]
                    func_postgres_obj_serialize.state[table] = orig_state
                    return res
                serialized_val = [ (await serialize_element(x.strip())) for x in parts ]
            else: serialized_val = await serialize_filter(filter_key, raw_val)
        elif operator == "overlap":
            parts = raw_val.split("|")
            fake_schema = {**func_postgres_obj_serialize.state[table], filter_key: func_postgres_obj_serialize.state[table][filter_key].replace("[]", "").replace("array", "").strip()}
            async def serialize_element(v):
                orig_state = func_postgres_obj_serialize.state[table]
                func_postgres_obj_serialize.state[table] = fake_schema
                res = (await func_postgres_obj_serialize(postgres_pool, table, [{filter_key: v}], is_base=True))[0][filter_key]
                func_postgres_obj_serialize.state[table] = orig_state
                return res
            serialized_val = [ (await serialize_element(x.strip())) for x in parts ]
        elif operator in ("in", "not in", "between"): serialized_val = [await serialize_filter(filter_key, x.strip(), True if is_array else False) for x in raw_val.split("|")]
        elif operator == "any":
            fake_schema = {**func_postgres_obj_serialize.state[table], filter_key: func_postgres_obj_serialize.state[table][filter_key].replace("[]", "").replace("array", "").strip()}
            orig_state = func_postgres_obj_serialize.state[table]
            func_postgres_obj_serialize.state[table] = fake_schema
            serialized_val = (await func_postgres_obj_serialize(postgres_pool, table, [{filter_key: raw_val}], is_base=True))[0][filter_key]
            func_postgres_obj_serialize.state[table] = orig_state
        else: serialized_val = await serialize_filter(filter_key, raw_val, True if is_json and operator == "exists" else False)
        if serialized_val is None:
            if operator not in ("is", "is not", "is distinct from", "is not distinct from"): raise Exception(f"null requires is/distinct for {filter_key}")
            conditions.append(f"{filter_key} {v_ops[operator]} NULL")
        elif operator == "contains": values.append(serialized_val); conditions.append(f"{filter_key} @> ${bind_idx}{'::jsonb' if is_json else ''}"); bind_idx += 1
        elif operator == "exists": values.append(serialized_val); conditions.append(f"{filter_key} ? ${bind_idx}"); bind_idx += 1
        elif operator == "overlap": values.append(serialized_val); conditions.append(f"{filter_key} && ${bind_idx}"); bind_idx += 1
        elif operator == "any": values.append(serialized_val); conditions.append(f"${bind_idx} = ANY({filter_key})"); bind_idx += 1
        elif operator in ("in", "not in"): place_holders = [f"${bind_idx + i}" for i in range(len(serialized_val))]; values.extend(serialized_val); conditions.append(f"{filter_key} {v_ops[operator]} ({','.join(place_holders)})"); bind_idx += len(serialized_val)
        elif operator == "between": values.extend(serialized_val); conditions.append(f"{filter_key} BETWEEN ${bind_idx} AND ${bind_idx+1}"); bind_idx += 2
        else: conditions.append(f"{filter_key} {(v_ops.get(operator) or s_ops.get(operator))} ${bind_idx}"); values.append(serialized_val); bind_idx += 1
    where_statement = ("WHERE " + " AND ".join(conditions) if conditions else ""); final_query = f"SELECT {column_list} FROM {table} {where_statement} ORDER BY {order_clause} LIMIT ${bind_idx} OFFSET ${bind_idx+1}"; values.extend([limit, (page - 1) * limit])
    async with postgres_pool.acquire() as conn:
        records = await conn.fetch(final_query, *values); result_list = [dict(r) for r in records]
        if creator_key and result_list:
            keys_to_fetch = creator_key.split(",") if isinstance(creator_key, str) else creator_key
            user_ids = {str(r["created_by_id"]) for r in result_list if r.get("created_by_id")}
            user_map = {str(u["id"]): dict(u) for u in (await postgres_pool.fetch("SELECT * FROM users WHERE id = ANY($1);", list(map(int, user_ids))))} if user_ids else {}
            for res_row in result_list:
                uid = str(res_row.get("created_by_id"))
                for k in keys_to_fetch: res_row[f"creator_{k}"] = user_map[uid].get(k) if uid in user_map else None
        if action_key and result_list:
            action_parts = action_key.split(",") if isinstance(action_key, str) else action_key
            target_tbl, action_col, action_op, action_out_col = action_parts; object_ids = {r.get("id") for r in result_list if r.get("id")}
            action_map = {str(row["id"]): row["value"] for row in (await postgres_pool.fetch(f"SELECT {action_col} AS id, {action_op}({action_out_col}) AS value FROM {target_tbl} WHERE {action_col} = ANY($1) GROUP BY {action_col};", list(object_ids)))} if object_ids else {}
            for res_row in result_list: res_row[f"{target_tbl}_{action_op}"] = action_map.get(str(res_row.get("id")), 0 if action_op == "count" else None)
        return result_list

async def func_postgres_obj_update(postgres_pool: any, func_postgres_obj_serialize: callable, table_name: str, obj_list: list, is_serialize: int = 0, created_by_id: int = None, batch_size: int = 5000, return_ids: bool = False) -> str:
    """Update PostgreSQL records with support for owner validation, batch processing, and dynamic serialization."""
    import re, json
    def validate_identifier(name):
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', str(name)): raise Exception(f"invalid identifier {name}")
        return name
    if not obj_list: return "0 rows updated"
    if not all("id" in obj for obj in obj_list): raise Exception("id field required")
    validate_identifier(table_name)
    if is_serialize: obj_list = await func_postgres_obj_serialize(postgres_pool, table_name, obj_list)
    update_cols = [validate_identifier(c) for c in obj_list[0] if c != "id"]; total_updated = 0
    if not update_cols: return "0 rows updated"
    actual_batch_size = min(batch_size or 5000, 65535 // (len(update_cols) + (2 if created_by_id else 1)))
    async with postgres_pool.acquire() as conn:
        if len(obj_list) == 1:
            obj = obj_list[0]; params = [obj[c] for c in update_cols] + [obj["id"]]; where_clause = f"id=${len(params)}" + (f" AND created_by_id=${len(params)+1}" if created_by_id else ""); (params.append(created_by_id) if created_by_id else None)
            if return_ids:
                records = await conn.fetch(f"UPDATE {table_name} SET {','.join(f'{c}=${i+1}' for i,c in enumerate(update_cols))} WHERE {where_clause} RETURNING id;", *params)
                return f"{len(records)} rows updated"
            else:
                status = await conn.execute(f"UPDATE {table_name} SET {','.join(f'{c}=${i+1}' for i,c in enumerate(update_cols))} WHERE {where_clause};", *params)
                return f"{int(status.split()[-1])} rows updated"
        async with conn.transaction():
            returned_ids = []
            for i in range(0, len(obj_list), actual_batch_size):
                batch, batch_vals, set_clauses = obj_list[i:i+actual_batch_size], [], []
                for col in update_cols:
                    case_statements = []
                    for obj in batch:
                        batch_vals.extend([obj["id"], obj[col]]); (batch_vals.append(created_by_id) if created_by_id else None); case_statements.append(f"WHEN id=${len(batch_vals)-(1 if created_by_id else 1)} {(f'AND created_by_id=${len(batch_vals)}' if created_by_id else '')} THEN ${len(batch_vals)-(0 if created_by_id else 0)}")
                    set_clauses.append(f"{col} = CASE {' '.join(case_statements)} ELSE {col} END")
                id_list = [obj["id"] for obj in batch]; where_clause = f"id IN ({','.join(f'${len(batch_vals)+j+1}' for j in range(len(id_list)))})" + (f" AND created_by_id=${len(batch_vals)+len(id_list)+1}" if created_by_id else ""); batch_vals.extend(id_list); (batch_vals.append(created_by_id) if created_by_id else None)
                if return_ids: returned_ids.extend([r["id"] for r in (await conn.fetch(f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {where_clause} RETURNING id;", *batch_vals))])
                else: total_updated += int((await conn.execute(f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {where_clause};", *batch_vals)).split()[-1])
            return f"{len(returned_ids) if return_ids else total_updated} rows updated"


async def func_postgres_obj_create(postgres_pool: any, func_postgres_obj_serialize: callable, execution_mode: str, table_name: str = None, object_list: list = None, is_serialize: int = 0, table_buffer: int = 0) -> any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization."""
    if not hasattr(func_postgres_obj_create, "buffer"): func_postgres_obj_create.buffer = {}
    if execution_mode == "flush":
        for table, items in func_postgres_obj_create.buffer.items():
            if items:
                columns = items[0].keys(); query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join([f'${i+1}' for i in range(len(columns))])})"
                async with postgres_pool.acquire() as conn: await conn.executemany(query, [tuple(i.values()) for i in items])
                func_postgres_obj_create.buffer[table] = []
        return "flushed"
    if not object_list: return None
    serialized_list = await func_postgres_obj_serialize(postgres_pool, table_name, object_list) if is_serialize else object_list
    if execution_mode == "buffer":
        if table_name not in func_postgres_obj_create.buffer: func_postgres_obj_create.buffer[table_name] = []
        func_postgres_obj_create.buffer[table_name].extend(serialized_list)
        if len(func_postgres_obj_create.buffer[table_name]) >= (table_buffer or 500):
            items = func_postgres_obj_create.buffer[table_name]; columns = items[0].keys(); query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({','.join([f'${i+1}' for i in range(len(columns))])})"
            async with postgres_pool.acquire() as conn: await conn.executemany(query, [tuple(i.values()) for i in items])
            func_postgres_obj_create.buffer[table_name] = []
        return "buffered"
    columns = serialized_list[0].keys()
    query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({','.join([f'${i+1}' for i in range(len(columns))])}) RETURNING id"
    async with postgres_pool.acquire() as conn:
        if len(serialized_list) == 1: ids = await conn.fetch(query, *serialized_list[0].values())
        else:
            import json
            schema = func_postgres_obj_serialize.state.get(table_name, {})
            col_list = ",".join(columns)
            def_list = ",".join([f"{c} jsonb" for c in columns])
            cast_list = ",".join([f"(SELECT ARRAY(SELECT jsonb_array_elements_text({c})))::{schema.get(c, 'text')}" if '[]' in schema.get(c, '') else (f"{c}::{schema.get(c, 'text')}" if 'jsonb' in schema.get(c, '') else f"({c}->>0)::{schema.get(c, 'text')}") for c in columns])
            ids = await conn.fetch(f"INSERT INTO {table_name} ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id", json.dumps(serialized_list, default=str))
        return [r['id'] for r in ids] if len(ids) > 0 and isinstance(ids[0], dict) and 'id' in ids[0] else "bulk created"

async def func_postgres_obj_serialize(postgres_pool: any, table_name: str, object_list: list, is_base: bool = False) -> list:
    """Serialize Python objects (JSON, Arrays, Geog) to PostgreSQL compatible formats using schema-aware caching."""
    import json
    if not hasattr(func_postgres_obj_serialize, "state"): func_postgres_obj_serialize.state = {}
    if table_name not in func_postgres_obj_serialize.state:
        async with postgres_pool.acquire() as conn:
            rows = await conn.fetch("SELECT column_name, CASE WHEN data_type = 'ARRAY' THEN ltrim(udt_name, '_') || '[]' WHEN data_type = 'USER-DEFINED' THEN udt_name ELSE data_type END AS data_type FROM information_schema.columns WHERE table_name = $1", table_name)
            if not rows: return object_list
            func_postgres_obj_serialize.state[table_name] = {r["column_name"]: r["data_type"] for r in rows}
    schema, output_list = func_postgres_obj_serialize.state[table_name], []
    for item in object_list:
        new_item = {}
        for col, val in item.items():
            if col not in schema:
                async with postgres_pool.acquire() as conn:
                    rows = await conn.fetch("SELECT column_name, CASE WHEN data_type = 'ARRAY' THEN ltrim(udt_name, '_') || '[]' WHEN data_type = 'USER-DEFINED' THEN udt_name ELSE data_type END AS data_type FROM information_schema.columns WHERE table_name = $1", table_name)
                    func_postgres_obj_serialize.state[table_name] = {r["column_name"]: r["data_type"] for r in rows}; schema = func_postgres_obj_serialize.state[table_name]
            if col not in schema or val is None: new_item[col] = val; continue
            dtype, val_str = schema[col].lower(), str(val).strip()
            base_dtype = dtype.replace("[]", "").replace("array", "").strip()
            def cast_val(v, t):
                vs = str(v).strip()
                if not vs or vs.lower() == "null": return None
                if any(x in t for x in ("int", "serial", "bigint")): return int(vs)
                if "bool" in t: return vs.lower() == "true"
                if any(x in t for x in ("numeric", "float", "double")): return float(vs)
                if "timestamp" in t:
                    from datetime import datetime
                    return datetime.fromisoformat(vs.replace("Z", "+00:00")) if isinstance(v, str) else v
                if "date" in t:
                    from datetime import date
                    return date.fromisoformat(vs) if isinstance(v, str) else v
                return v
            if is_base:
                if "json" in dtype: new_item[col] = json.dumps(val) if not isinstance(val, str) else val
                elif "[]" in dtype or "array" in dtype:
                    v_arr = val_str.strip("{}")
                    arr = val if isinstance(val, (list, tuple)) else ([x.strip() for x in v_arr.split(",")] if v_arr else [])
                    new_item[col] = [cast_val(x, base_dtype) for x in arr]
                else: new_item[col] = cast_val(val, dtype)
            else:
                if "json" in dtype: new_item[col] = json.dumps(val) if not isinstance(val, str) else (json.loads(val_str) if val_str.startswith(("{", "[")) else val_str)
                elif "[]" in dtype or "array" in dtype:
                    v_arr = val_str.strip("{}")
                    arr = val if isinstance(val, (list, tuple)) else ([x.strip() for x in v_arr.split(",")] if v_arr else [])
                    new_item[col] = [cast_val(x, base_dtype) for x in arr]
                elif "bytea" in dtype: new_item[col] = val.encode() if isinstance(val, str) else val
                else: new_item[col] = cast_val(val, dtype)
        output_list.append(new_item)
    return output_list

async def func_postgres_stream(postgres_pool: any, sql_query: str) -> any:
    """Stream PostgreSQL query results as a CSV Iterative Response."""
    from fastapi.responses import StreamingResponse
    async def generate():
        async with postgres_pool.acquire() as conn:
            async with conn.transaction():
                first = True
                async for record in conn.cursor(sql_query):
                    if first: yield ",".join(record.keys()) + "\n"; first = False
                    yield ",".join([f'"{str(v).replace(chr(34), chr(34)*2)}"' if v is not None else "" for v in record.values()]) + "\n"
    return StreamingResponse(generate(), media_type="text/csv")

async def func_postgres_init_root_user(postgres_pool: any) -> str:
    """Ensure the users table, root user, and root protection triggers exist in PostgreSQL."""
    async with postgres_pool.acquire() as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS users (id BIGSERIAL PRIMARY KEY);")
        for col, dtype in [("type", "INTEGER"), ("username", "TEXT"), ("password", "TEXT"), ("role", "INTEGER"), ("is_active", "INTEGER")]:
            await conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {dtype};")
        await conn.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'unique_users_username_type' AND table_name = 'users') THEN 
                    ALTER TABLE users ADD CONSTRAINT unique_users_username_type UNIQUE (username, type); 
                END IF; 
            END $$;
        """)
        await conn.execute("INSERT INTO users (type, username, password, role, is_active) VALUES (1, 'atom', 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3', 1, 1) ON CONFLICT (username, type) DO UPDATE SET password = EXCLUDED.password, role = EXCLUDED.role, is_active = EXCLUDED.is_active;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_users_root_no_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; END; $$; DROP TRIGGER IF EXISTS trigger_users_root_no_delete ON users; CREATE TRIGGER trigger_users_root_no_delete BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_users_root_no_delete();")
    return "users init done"

async def func_postgres_init(postgres_pool: any, postgres_config: dict) -> str:
    """Initialize PostgreSQL database schema, tables, indexes, constraints, and triggers based on configuration."""
    if not postgres_config: raise Exception("postgres_config missing")
    if "table" not in postgres_config: raise Exception("postgres_config.table missing")
    control = postgres_config.get("control", {}); is_ext, is_match, disable_drop, disable_trunc = control.get("is_extension", 0), control.get("is_match_column", 0), control.get("is_drop_disable_table", 0), control.get("is_truncate_disable", 0)
    is_soft, is_hard, role_dis = control.get("is_child_delete_soft", 0), control.get("is_child_delete_hard", 0), control.get("is_delete_disable_role", 0)
    bulk_blocked, table_blocked, catalog = control.get("delete_disable_bulk", []), control.get("delete_disable_table", []), {"idx":set(),"uni":set(),"chk":set(),"tg":set()}
    for table_name, column_configs in postgres_config["table"].items():
        if len(set(col["name"] for col in column_configs)) != len(column_configs): raise Exception(f"Duplicate column in {table_name}")
    async with postgres_pool.acquire() as conn:
        if is_ext:
            for extension in ("postgis", "pg_trgm", "btree_gin"): await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {extension};")
        for table_name, column_configs in postgres_config["table"].items():
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id BIGSERIAL PRIMARY KEY); ALTER TABLE {table_name} SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);")
            current_cols = {row[0]: row[1] for row in await conn.fetch("SELECT a.attname, format_type(a.atttypid, a.atttypmod) FROM pg_attribute a JOIN pg_class t ON a.attrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid WHERE t.relname = $1 AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped", table_name)}
            for col_cfg in column_configs:
                col_name, col_type = col_cfg["name"], col_cfg["datatype"]
                if col_name not in current_cols:
                    if col_cfg.get("old") and col_cfg["old"] in current_cols: await conn.execute(f"ALTER TABLE {table_name} RENAME COLUMN {col_cfg['old']} TO {col_name}"); current_cols[col_name] = current_cols.pop(col_cfg["old"])
                    else: default_val = f"DEFAULT {col_cfg['default']}" if "default" in col_cfg else ""; await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {default_val}"); current_cols[col_name] = col_type.split('(')[0].lower()
                else:
                    type_mapping = {"timestamp with time zone":"timestamptz", "character varying":"varchar", "integer":"int", "boolean":"bool"}; current_type, target_type = type_mapping.get(current_cols[col_name].lower().split('(')[0], current_cols[col_name].lower().split('(')[0]), type_mapping.get(col_type.lower().split('(')[0], col_type.lower().split('(')[0])
                    if current_type != target_type:
                        if is_match: await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {col_type} USING {col_name}::{col_type}")
                        else: raise Exception(f"Type mismatch {table_name}.{col_name}: {current_cols[col_name]} vs {col_type}")
            for col_cfg in column_configs:
                col_name, col_type = col_cfg["name"], col_cfg["datatype"]
                if col_cfg.get("index"):
                    for index_type in (x.strip() for x in col_cfg["index"].split(",")):
                        idx_name = f"idx_{table_name}_{col_name}_{index_type}"; catalog["idx"].add(idx_name)
                        if idx_name not in [r[0] for r in await conn.fetch("SELECT indexname FROM pg_indexes WHERE tablename=$1", table_name)]: await conn.execute(f"CREATE INDEX {idx_name} ON {table_name} USING {index_type}({col_name} {( 'gin_trgm_ops' if index_type=='gin' and 'text' in col_type.lower() and '[]' not in col_type.lower() else '')});")
                if "in" in col_cfg:
                    chk_name = f"check_{table_name}_{col_name}_in"; catalog["chk"].add(chk_name)
                    await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {chk_name}; ALTER TABLE {table_name} ADD CONSTRAINT {chk_name} CHECK ({col_name} IN {col_cfg['in']});")
                if col_cfg.get("unique"):
                    for group in col_cfg["unique"].split("|"):
                        unique_cols = [x.strip() for x in group.split(",")]; uni_name = f"unique_{table_name}_{'_'.join(unique_cols)}"; catalog["uni"].add(uni_name)
                        await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {uni_name}; ALTER TABLE {table_name} ADD CONSTRAINT {uni_name} UNIQUE ({','.join(unique_cols)});")
            if is_match:
                for col_to_drop in set(current_cols.keys()) - ({cfg["name"] for cfg in column_configs} | {"id"}): await conn.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_to_drop} CASCADE;")
        db_schema_rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
        db_tables = {}; [db_tables.setdefault(row[0], []).append(row[1]) for row in db_schema_rows]; users_cols = db_tables.get("users", [])
        if users_cols:
            if "password" in users_cols and "log_users_password" in db_tables:
                catalog["tg"].add("trigger_users_password_log")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_password_log() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.password IS DISTINCT FROM NEW.password THEN INSERT INTO log_users_password (user_id, password) VALUES (NEW.id, NEW.password); END IF; RETURN NEW; END; $$; DROP TRIGGER IF EXISTS trigger_users_password_log ON users; CREATE TRIGGER trigger_users_password_log AFTER UPDATE ON users FOR EACH ROW EXECUTE FUNCTION func_users_password_log();")
            if is_soft and "is_deleted" in users_cols:
                catalog["tg"].add("trigger_users_soft_delete")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_soft_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; v INTEGER; BEGIN v := (CASE WHEN NEW.is_deleted=1 THEN 1 ELSE NULL END); FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'is_deleted') THEN EXECUTE format('UPDATE %I.%I SET is_deleted = $1 WHERE %I = $2', r.table_schema, r.table_name, r.column_name) USING v, NEW.id; END IF; END LOOP; RETURN NEW; END; $$; DROP TRIGGER IF EXISTS trigger_users_soft_delete ON users; CREATE TRIGGER trigger_users_soft_delete AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.is_deleted IS DISTINCT FROM NEW.is_deleted) EXECUTE FUNCTION func_users_soft_delete();")
            if is_hard:
                catalog["tg"].add("trigger_users_hard_delete")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_hard_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; BEGIN FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP EXECUTE format('DELETE FROM %I.%I WHERE %I = $1', r.table_schema, r.table_name, r.column_name) USING OLD.id; END LOOP; RETURN OLD; END; $$; DROP TRIGGER IF EXISTS trigger_users_hard_delete ON users; CREATE TRIGGER trigger_users_hard_delete AFTER DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_users_hard_delete();")
            if role_dis and "role" in users_cols:
                catalog["tg"].add("trigger_delete_disable_users_role")
                await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_users_role() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL THEN RAISE EXCEPTION 'DELETE not allowed for user with role'; END IF; RETURN OLD; END; $$; DROP TRIGGER IF EXISTS trigger_delete_disable_users_role ON users; CREATE TRIGGER trigger_delete_disable_users_role BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_users_role();")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected=1 THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %', TG_TABLE_NAME; END IF; RETURN OLD; END; $$; CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$; CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$; CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'delete not allowed on %', TG_TABLE_NAME; END; $$;")
        for table, cols in db_tables.items():
            if table == "spatial_ref_sys": continue
            if "is_protected" in cols:
                prot_tg_name = f"trigger_delete_disable_is_protected_{table}"; catalog["tg"].add(prot_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {prot_tg_name} ON {table}; CREATE TRIGGER {prot_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected();")
            if "updated_at" in cols:
                upd_tg_name = f"trigger_set_updated_at_{table}"; catalog["tg"].add(upd_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {upd_tg_name} ON {table}; CREATE TRIGGER {upd_tg_name} BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION func_set_updated_at();")
        for table, limit in bulk_blocked:
            if table in db_tables:
                bulk_tg_name = f"trigger_delete_disable_bulk_{table}"; catalog["tg"].add(bulk_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {bulk_tg_name} ON {table}; CREATE TRIGGER {bulk_tg_name} AFTER DELETE ON {table} REFERENCING OLD TABLE AS deleted_rows FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_bulk({limit});")
        for table in table_blocked:
            if table in db_tables:
                tab_tg_name = f"trigger_delete_disable_{table}"; catalog["tg"].add(tab_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {tab_tg_name} ON {table}; CREATE TRIGGER {tab_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table();")
        for prefix, col, info_tbl in (("tg", "tgname", "pg_trigger"), ("uni_chk", "conname", "pg_constraint"), ("idx", "indexname", "pg_indexes")):
            wants = catalog[prefix] if prefix != "uni_chk" else catalog["uni"] | catalog["chk"]
            if prefix == "idx": wants |= catalog["uni"] | catalog["chk"]
            wants_str = ",".join(f"'{i}'" for i in wants) if wants else "NULL"
            selection = col + (", relname" if prefix != "idx" else "")
            join_clause = ("JOIN pg_class ON pg_constraint.conrelid = pg_class.oid" if prefix == "uni_chk" else "JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid" if prefix == "tg" else "")
            drop_fmt, drop_vars = ("DROP INDEX IF EXISTS %I" if prefix == "idx" else "DROP TRIGGER IF EXISTS %I ON %I" if prefix == "tg" else "ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I"), ("record." + col if prefix == "idx" else "record.tgname, record.relname" if prefix == "tg" else "record.relname, record.conname")
            await conn.execute(f"DO $$ DECLARE record RECORD; BEGIN FOR record IN SELECT {selection} FROM {info_tbl} {join_clause} WHERE {col} LIKE 'idx_%%' OR {col} LIKE 'trigger_%%' OR {col} LIKE 'unique_%%' OR {col} LIKE 'check_%%' LOOP IF NOT record.{col} IN ({wants_str}) THEN EXECUTE format('{drop_fmt} ', {drop_vars}); END IF; END LOOP; END $$;")
        await conn.execute("ANALYZE;")
    return "database init done"

async def func_postgres_schema_read(postgres_pool: any) -> dict:
    """Read full database schema as a nested dictionary."""
    async with postgres_pool.acquire() as conn:
        rows = await conn.fetch("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public'")
        schema = {}
        for r in rows: schema.setdefault(r["table_name"], {})[r["column_name"]] = {"datatype": r["data_type"]}
    return schema

async def func_postgres_client_read(config_postgres: dict) -> any:
    """Initialize PostgreSQL connection pool."""
    import asyncpg
    return await asyncpg.create_pool(dsn=config_postgres["dsn"], min_size=config_postgres["min_size"], max_size=config_postgres["max_size"])


#external clients - messaging & cache (redis/rabbitmq/kafka/celery)
async def func_redis_client_read(redis_url: str) -> any:
    """Initialize Redis client using connection pooling."""
    import redis.asyncio as redis
    return redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_url))

async def func_redis_client_read_consumer(redis_client: any, channel_name: str) -> any:
    """Initialize Redis PubSub consumer and subscribe to a channel."""
    pubsub = redis_client.pubsub(); await pubsub.subscribe(channel_name); return pubsub

async def func_redis_producer(redis_client: any, channel_name: str, payload: dict) -> int:
    """Publish a JSON-serialized payload to a Redis channel."""
    import json
    return await redis_client.publish(channel_name, json.dumps(payload))

async def func_redis_object_create(redis_client: any, keys: list, objects: list, expiry_sec: int) -> None:
    """Batch create/update objects in Redis with optional expiration in a pipeline transaction."""
    import json
    async with redis_client.pipeline(transaction=True) as pipe:
        for key, obj in zip(keys, objects): (pipe.setex(key, expiry_sec, json.dumps(obj)) if expiry_sec else pipe.set(key, json.dumps(obj)))
        await pipe.execute()
    return None

def func_ses_client_read(aws_access_key: str, aws_secret_key: str, region: str) -> any:
    """Initialize AWS SES client."""
    import boto3
    return boto3.client("ses", region_name=region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)

def func_ses_send_email(ses_client: any, from_email: str, to_emails: list, subject: str, body: str) -> None:
    """Send a transactional email via AWS SES."""
    ses_client.send_email(Source=from_email, Destination={"ToAddresses": to_emails}, Message={"Subject": {"Charset": "UTF-8", "Data": subject}, "Body": {"Text": {"Charset": "UTF-8", "Data": body}}}); return None

def func_sns_send_mobile_message(sns_client: any, mobile_number: str, message_text: str) -> None:
    """Send a direct SMS message via AWS SNS."""
    sns_client.publish(PhoneNumber=mobile_number, Message=message_text); return None

def func_sns_send_mobile_message_template(sns_client: any, mobile_number: str, message_text: str, template_id: str, entity_id: str, sender_id: str) -> None:
    """Send a templated transactional SMS message via AWS SNS with custom metadata."""
    sns_client.publish(PhoneNumber=mobile_number, Message=message_text, MessageAttributes={"AWS.MM.SMS.EntityId": {"DataType": "String", "StringValue": entity_id}, "AWS.MM.SMS.TemplateId": {"DataType": "String", "StringValue": template_id}, "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": sender_id}, "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}}); return None

def func_sns_client_read(aws_access_key: str, aws_secret_key: str, region: str) -> any:
    """Initialize AWS SNS client."""
    import boto3
    return boto3.client("sns", region_name=region, aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)


#external clients - cloud (aws/s3/sns/ses)
async def func_s3_client_read(config_s3: dict) -> any:
    """Initialize AWS S3 client and resource."""
    import aiobotocore.session, boto3
    client = aiobotocore.session.get_session().create_client("s3", region_name=config_s3["region_name"], aws_access_key_id=config_s3["aws_access_key_id"], aws_secret_access_key=config_s3["aws_secret_access_key"])
    resource = boto3.resource("s3", region_name=config_s3["region_name"], aws_access_key_id=config_s3["aws_access_key_id"], aws_secret_access_key=config_s3["aws_secret_access_key"])
    return client, resource

async def func_s3_bucket_create(s3_client: any, region: str, bucket_name: str) -> any:
    """Create a new AWS S3 bucket in a specific region."""
    return await s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})

async def func_s3_bucket_public(s3_client: any, bucket_name: str) -> any:
    """Expose an AWS S3 bucket for public read access."""
    await s3_client.put_public_access_block(Bucket=bucket_name, PublicAccessBlockConfiguration={'BlockPublicAcls': False, 'IgnorePublicAcls': False, 'BlockPublicPolicy': False, 'RestrictPublicBuckets': False}); return await s3_client.put_bucket_policy(Bucket=bucket_name, Policy='''{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}'''.replace("bucket_name", bucket_name))

def func_s3_bucket_empty(s3_resource: any, bucket_name: str) -> any:
    """Purge all objects from an AWS S3 bucket."""
    return s3_resource.Bucket(bucket_name).objects.all().delete()

async def func_s3_bucket_delete(s3_client: any, bucket_name: str) -> any:
    """Delete an AWS S3 bucket."""
    return await s3_client.delete_bucket(Bucket=bucket_name)

def func_s3_url_delete(s3_resource: any, file_url: str) -> any:
    """Delete an object from AWS S3 given its public URL."""
    bucket, key = file_url.split("//", 1)[1].split(".", 1)[0], file_url.rsplit("/", 1)[1]; return s3_resource.Object(bucket, key).delete()

async def func_s3_upload(s3_client: any, bucket_name: str, file_obj: any, file_key: str) -> str:
    """Upload a file to AWS S3 bucket."""
    await s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=await file_obj.read())
    return f"https://{bucket_name}.s3.amazonaws.com/{file_key}"

def func_s3_upload_presigned(s3_client: any, region: str, bucket_name: str, file_key: str = None, size_limit_kb: int = 100, expiry_sec: int = 100) -> dict:
    """Generate a presigned POST URL for secure client-side binary uploads to S3."""
    import uuid
    if not file_key: file_key = f"{uuid.uuid4().hex}.bin"
    if "." not in file_key: raise Exception("missing extension")
    presigned_post = s3_client.generate_presigned_post(Bucket=bucket_name, Key=file_key, ExpiresIn=expiry_sec, Conditions=[['content-length-range', 1, size_limit_kb * 1024]]); return {**presigned_post["fields"], "url_final": f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_key}"}

def func_celery_client_read_producer(broker_url: str, backend_url: str) -> any:
    """Initialize Celery producer client."""
    from celery import Celery
    return Celery("producer", broker=broker_url, backend=backend_url)

def func_celery_client_read_consumer(broker_url: str, backend_url: str) -> any:
    """Initialize Celery worker client."""
    from celery import Celery
    return Celery("worker", broker=broker_url, backend=backend_url)

def func_celery_producer(celery_app: any, task_name: str, payload_list: list) -> str:
    """Dispatch a task to Celery worker and return task ID."""
    return celery_app.send_task(task_name, args=payload_list).id

async def func_rabbitmq_client_read_producer(rabbitmq_url: str) -> tuple:
    """Initialize RabbitMQ robust connection and channel for producer."""
    import aio_pika
    connection = await aio_pika.connect_robust(rabbitmq_url); return connection, await connection.channel()

async def func_rabbitmq_client_read_consumer(rabbitmq_url: str, channel_name: str) -> tuple:
    """Initialize RabbitMQ robust connection and queue for consumer."""
    import aio_pika
    connection = await aio_pika.connect_robust(rabbitmq_url); channel = await connection.channel(); return connection, await channel.declare_queue(channel_name, auto_delete=False)

async def func_rabbitmq_producer(rabbitmq_channel: any, channel_name: str, payload: dict) -> any:
    """Publish a JSON payload to a RabbitMQ queue."""
    import aio_pika, json
    return await rabbitmq_channel.default_exchange.publish(aio_pika.Message(body=json.dumps(payload).encode()), routing_key=channel_name)

async def func_kafka_client_read_producer(kafka_url: str, username: str, password: str) -> any:
    """Initialize AIOKafkaProducer with SASL authentication."""
    from aiokafka import AIOKafkaProducer
    kp = AIOKafkaProducer(bootstrap_servers=kafka_url, security_protocol="SASL_PLAINTEXT", sasl_mechanism="PLAIN", sasl_plain_username=username, sasl_plain_password=password); await kp.start(); return kp

async def func_kafka_client_read_consumer(kafka_url: str, username: str, password: str, channel_name: str, group_id: str, auto_commit: bool) -> any:
    """Initialize AIOKafkaConsumer with SASL authentication and specific group ID."""
    from aiokafka import AIOKafkaConsumer
    kc = AIOKafkaConsumer(channel_name, bootstrap_servers=kafka_url, group_id=group_id, security_protocol="SASL_PLAINTEXT", sasl_mechanism="PLAIN", sasl_plain_username=username, sasl_plain_password=password, auto_offset_reset="earliest", enable_auto_commit=auto_commit); await kc.start(); return kc

async def func_kafka_producer(kafka_producer: any, channel_name: str, payload: dict) -> any:
    """Send a JSON-formatted payload to a Kafka topic."""
    import json
    return await kafka_producer.send_and_wait(channel_name, json.dumps(payload, indent=2).encode('utf-8'), partition=0)


#api cache & rate limiting
async def func_check_ratelimiter(redis_client: any, config_api: dict, url_path: str, identifier: str) -> None:
    """Check and enforce API rate limits using either Redis or in-memory storage."""
    import time
    if not hasattr(func_check_ratelimiter, "state"): func_check_ratelimiter.state = {}
    if not (rl_config := config_api.get(url_path, {}).get("ratelimiter_times_sec")): return None
    mode, limit, window = rl_config; cache_key = f"ratelimiter:{url_path}:{identifier}"
    if mode == "redis":
        if not redis_client: raise Exception("redis client missing")
        current_count = await redis_client.get(cache_key)
        if current_count and int(current_count) + 1 > limit: raise Exception("ratelimiter exceeded")
        pipeline = redis_client.pipeline(); pipeline.incr(cache_key); (pipeline.expire(cache_key, window) if not current_count else None); await pipeline.execute()
    elif mode == "inmemory":
        now = time.time(); item = func_check_ratelimiter.state.get(cache_key)
        if item and item["expire_at"] > now:
            if item["count"] + 1 > limit: raise Exception("ratelimiter exceeded")
            item["count"] += 1
        else: func_check_ratelimiter.state[cache_key] = {"count": 1, "expire_at": now + window}
    else: raise Exception("invalid ratelimiter mode")
    return None

async def func_check_is_active(user_dict: dict, url_path: str, api_config: dict, postgres_pool: any, redis_client: any, cache_map: dict) -> None:
    """Check if the user is active using a strictly configured mode from api_config."""
    cfg = api_config.get(url_path, {}).get("is_active_check")
    if not cfg or not user_dict: return None
    mode, active_flag = cfg
    if active_flag == 0: return None
    async def fetch_is_active(uid):
        async with postgres_pool.acquire() as conn: rows = await conn.fetch("select id,is_active from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["is_active"]
    if mode == "redis":
        if not redis_client: raise Exception("redis client missing")
        cache_key, active_status = f"cache:user:active:{user_dict['id']}", None
        cached_val = await redis_client.get(cache_key)
        if cached_val is not None: active_status = int(cached_val)
        else:
            active_status = await fetch_is_active(user_dict["id"])
            await redis_client.setex(cache_key, 3600, str(active_status))
    else: active_status = (await fetch_is_active(user_dict["id"]) if mode == "realtime" else cache_map.get(user_dict["id"], await fetch_is_active(user_dict["id"])) if mode == "cache" else user_dict.get("is_active", "absent"))
    if active_status == "absent": raise Exception("missing is_active")
    if active_status == 0: raise Exception("user not active")

async def func_check_admin(user_dict: dict, url_path: str, api_config: dict, postgres_pool: any, redis_client: any, cache_map: dict) -> None:
    """Ensure sufficient roles to access admin endpoints using a strictly configured mode from api_config."""
    if not url_path.startswith("/admin") or not (cfg := api_config.get(url_path)) or "roles" not in cfg: return None
    mode, roles = cfg["roles"][0], set(cfg["roles"][1])
    async def fetch_role(uid):
        async with postgres_pool.acquire() as conn: rows = await conn.fetch("select role from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["role"]
    if mode == "redis":
        if not redis_client: raise Exception("redis client missing")
        cache_key, user_role = f"cache:user:role:{user_dict['id']}", None
        cached_val = await redis_client.get(cache_key)
        if cached_val is not None: user_role = int(cached_val)
        else:
            user_role = await fetch_role(user_dict["id"])
            await redis_client.setex(cache_key, 3600, str(user_role if user_role is not None else ""))
    else: user_role = (await fetch_role(user_dict["id"]) if mode == "realtime" else cache_map.get(user_dict["id"], await fetch_role(user_dict["id"])) if mode == "cache" else user_dict.get("role", "absent"))
    if user_role == "absent": raise Exception("user role missing")
    if user_role is None or user_role == "": raise Exception("user role is null")
    if user_role == "role": raise Exception("user role is invalid")
    if not isinstance(user_role, int):
        try: user_role = int(user_role)
        except: raise Exception("invalid user role type")
    if user_role not in roles: raise Exception("access denied")

async def func_check_cache(mode: str, url_path: str, query_params: dict, api_config: dict, redis_client: any, user_id: int, response_obj: any) -> any:
    """Retrieve from or store to cache API responses based on configuration."""
    from fastapi import Response
    import gzip, base64, time
    if not hasattr(func_check_cache, "state"): func_check_cache.state = {}
    def should_cache(expire_sec): return expire_sec is not None and expire_sec > 0
    def build_cache_key(path, qp, uid): return f"cache:{path}?{'&'.join(f'{k}={v}' for k, v in sorted(qp.items()))}:{uid}"
    def compress_data(body): return base64.b64encode(gzip.compress(body)).decode()
    def decompress_data(data): return gzip.decompress(base64.b64decode(data)).decode()
    if mode not in ["get", "set"]: raise Exception("cache mode should be 'get' or 'set'")
    uid = user_id if "my/" in url_path else 0; cache_key = build_cache_key(url_path, query_params, uid)
    cache_mode, expire_sec = api_config.get(url_path, {}).get("cache_sec", (None, None))
    if not should_cache(expire_sec): return None if mode == "get" else response_obj
    if mode == "get":
        cached_data = None
        if cache_mode == "redis": cached_data = await redis_client.get(cache_key)
        elif cache_mode == "inmemory":
            item = func_check_cache.state.get(cache_key)
            if item and item["expire_at"] > time.time(): cached_data = item["data"]
        if cached_data: return Response(decompress_data(cached_data), status_code=200, media_type="application/json", headers={"x-cache": "hit"})
        return None
    elif mode == "set":
        body_content = getattr(response_obj, "body", None)
        if body_content is None: body_content = b"".join([chunk async for chunk in response_obj.body_iterator])
        compressed_body = compress_data(body_content)
        if cache_mode == "redis": await redis_client.setex(cache_key, expire_sec, compressed_body)
        elif cache_mode == "inmemory": func_check_cache.state[cache_key] = {"data": compressed_body, "expire_at": time.time() + expire_sec}
        return Response(content=body_content, status_code=response_obj.status_code, media_type=response_obj.media_type, headers=dict(response_obj.headers))

async def func_api_response_background(scope: dict, body_bytes: bytes, api_function: callable) -> any:
    """Execute an API function in the background and return a 200 response immediately."""
    from fastapi import Request, responses
    from starlette.background import BackgroundTask
    async def receive_provider(): return {"type": "http.request", "body": body_bytes}
    async def api_task_execution():
        new_request = Request(scope=scope, receive=receive_provider)
        await api_function(new_request)
    background_resp = responses.JSONResponse(status_code=200, content={"status": 1, "message": "added in background"})
    background_resp.background = BackgroundTask(api_task_execution); return background_resp

async def func_api_response(request: any, api_function: callable, api_config: dict, redis_client: any, user_id: int, func_background: callable, func_cache: callable) -> tuple:
    """Orchestrate API request handling, including background task delegation and cache management."""
    from fastapi import responses
    cache_sec = api_config.get(request.url.path, {}).get("cache_sec")
    response, resp_type, query_params = None, 0, dict(request.query_params)
    if query_params.get("is_background") == "1":
        body_bytes = await request.body()
        response = await func_background(request.scope, body_bytes, api_function); resp_type = 1
    elif cache_sec:
        response = await func_cache("get", request.url.path, query_params, api_config, redis_client, user_id, None); resp_type = 2
    if not response:
        response = await api_function(request); resp_type = 3
        if cache_sec: response = await func_cache("set", request.url.path, query_params, api_config, redis_client, user_id, response); resp_type = 4
    return response, resp_type

async def func_authenticate(headers: dict, url_path: str, jwt_secret_key: str, api_config: dict) -> dict:
    """Unified authentication: extracts Bearer token, validates presence for protected routes, and decodes JWT.
    Returns the decoded user dict or an empty dict.
    """
    auth_header = headers.get("Authorization")
    token = auth_header.split("Bearer ", 1)[1] if auth_header and auth_header.startswith("Bearer ") else None
    if token:
        import jwt, json
        decoded_payload = jwt.decode(token, jwt_secret_key, algorithms="HS256")
        user_obj = json.loads(decoded_payload["data"])
    else:
        user_obj = {}
        if url_path.startswith(("/my", "/private", "/admin")):
            raise Exception("authorization token missing")
    return user_obj

async def func_token_encode(user_obj: dict, jwt_secret_key: str, token_expiry_sec: int, token_refresh_expiry_sec: int, key_list: list = None) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    import jwt, json, time
    if user_obj is None: return None
    payload_dict = {k: user_obj.get(k) for k in key_list} if key_list else (dict(user_obj) if not isinstance(user_obj, dict) else user_obj)
    serialized_payload = json.dumps(payload_dict, default=str)
    now_ts = int(time.time()); access_exp = now_ts + token_expiry_sec; refresh_exp = now_ts + token_refresh_expiry_sec
    access_token = jwt.encode({"exp": access_exp, "data": serialized_payload, "type": "access"}, jwt_secret_key)
    refresh_token = jwt.encode({"exp": refresh_exp, "data": serialized_payload, "type": "refresh"}, jwt_secret_key)
    return {"token": access_token, "token_refresh": refresh_token, "token_expiry_sec": token_expiry_sec, "token_refresh_expiry_sec": token_refresh_expiry_sec}

def func_fastapi_app_read(lifespan_handler: any, is_debug_mode: bool) -> any:
    """Initialize a FastAPI application with debug mode and lifespan handler."""
    from fastapi import FastAPI
    return FastAPI(debug=is_debug_mode, lifespan=lifespan_handler)

async def func_server_start(fastapi_app: any) -> None:
    """Start the Uvicorn server for the FastAPI application."""
    import uvicorn
    server_config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    await uvicorn.Server(server_config).serve()

def func_app_add_cors(fastapi_app: any, origins: list, methods: list, headers: list, allow_credentials: bool) -> None:
    """Add CORS middleware to the FastAPI application."""
    from fastapi.middleware.cors import CORSMiddleware
    fastapi_app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=methods, allow_headers=headers, allow_credentials=allow_credentials)

def func_app_add_prometheus(fastapi_app: any) -> None:
    """Expose Prometheus metrics for the FastAPI application."""
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(fastapi_app).expose(fastapi_app)

def func_app_state_add(fastapi_app: any, config_dict: dict, prefix: str) -> None:
    """Inject configuration values into the FastAPI application state based on a prefix."""
    for key, val in config_dict.items():
        if key.startswith(prefix): setattr(fastapi_app.state, key, val)

def func_app_add_sentry(sentry_dsn: str) -> None:
    """Initialize Sentry SDK for error tracking and profiling."""
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(dsn=sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=True)

def func_app_add_static(fastapi_app: any, folder_path: str, mount_path: str) -> None:
    """Mount a static directory to the FastAPI application."""
    from fastapi.staticfiles import StaticFiles
    fastapi_app.mount(mount_path, StaticFiles(directory=folder_path), name="static")

def func_add_router(fastapi_app: any) -> None:
    """Dynamically discover and include all FastAPI routers from the project directory."""
    import sys, importlib.util, traceback
    from pathlib import Path
    def load_router(root, file_path):
        try:
            rel_path = file_path.relative_to(root); module_name = "routers." + ".".join(rel_path.with_suffix("").parts)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec); sys.modules[module_name] = module; spec.loader.exec_module(module); fastapi_app.include_router(getattr(module, "router"))
        except: traceback.print_exc()
    root_dir = Path(".").resolve()
    for py_file in root_dir.rglob("*.py"):
        if py_file.name.startswith((".", "__")) or any(p.startswith(".") or p in ("venv", "env", "__pycache__") for p in py_file.parts): continue
        rel = py_file.relative_to(root_dir); ( load_router(root_dir, py_file) if (len(rel.parts) == 1 and py_file.name.startswith("router")) or ("router" in rel.parts[:-1]) else None )


#admin & analytics
async def func_user_sql_read(postgres_pool: any, config_sql: dict, user_id: int) -> dict:
    """Execute pre-defined analytics queries for a specific user profile."""
    queries_metadata = config_sql.get("profile_metadata", {}); result_data = {}
    async with postgres_pool.acquire() as conn:
        for key, sql_query in queries_metadata.items(): result_data[key] = [dict(record) for record in await conn.fetch(sql_query, user_id)]
    return result_data

async def func_api_usage_read(postgres_pool: any, days_limit: int, user_id: int = None) -> list:
    """Read API usage logs for a specific user or globally within a day limit."""
    async with postgres_pool.acquire() as conn: return await conn.fetch("SELECT api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND ($2::bigint IS NULL OR created_by_id=$2) GROUP BY api LIMIT 1000;", days_limit, user_id)

async def func_account_delete(delete_mode: str, postgres_pool: any, user_id: int) -> str:
    """Delete a user account either softly (flag) or hardly (row removal)."""
    query = ("UPDATE users SET is_deleted=1 WHERE id=$1" if delete_mode == "soft" else "DELETE FROM users WHERE id=$1" if delete_mode == "hard" else None)
    if not query: raise Exception("invalid delete mode")
    async with postgres_pool.acquire() as conn: await conn.execute(query, user_id); return "account deleted"


#user & message operations
async def func_user_single_read(postgres_pool: any, user_id: int) -> dict:
    """Read a single user's full record by their ID."""
    async with postgres_pool.acquire() as conn: record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
    if not record: raise Exception("user not found")
    return dict(record)


#auth & otp
async def func_otp_generate(postgres_pool: any, email_address: str = None, mobile_number: str = None) -> int:
    """Generate and store a numeric OTP for email or mobile verification."""
    import random
    if not email_address and not mobile_number: raise Exception("email or mobile missing")
    if email_address and mobile_number: raise Exception("provide only one identifier")
    otp_code = random.randint(100000, 999999)
    query, values = (("INSERT INTO otp (otp, email) VALUES ($1, $2)", (otp_code, email_address.strip().lower())) if email_address else ("INSERT INTO otp (otp, mobile) VALUES ($1, $2)", (otp_code, mobile_number.strip())))
    async with postgres_pool.acquire() as conn: await conn.execute(query, *values)
    return otp_code

async def func_otp_verify(postgres_pool: any, otp_code: int, email_address: str = None, mobile_number: str = None, expiry_sec: int = 600) -> None:
    """Verify an OTP for email or mobile within its expiration window."""
    if not otp_code: raise Exception("otp code missing")
    if not email_address and not mobile_number: raise Exception("email or mobile missing")
    if email_address and mobile_number: raise Exception("provide only one identifier")
    query, identifier = ((f"SELECT otp FROM otp WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '{expiry_sec}s' AND email=$1 ORDER BY id DESC LIMIT 1", email_address.strip().lower()) if email_address else (f"SELECT otp FROM otp WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '{expiry_sec}s' AND mobile=$1 ORDER BY id DESC LIMIT 1", mobile_number.strip()))
    async with postgres_pool.acquire() as conn: records = await conn.fetch(query, identifier)
    if not records: raise Exception("otp expired or not found")
    if int(records[0]["otp"]) != int(otp_code): raise Exception("invalid otp code")

async def func_message_inbox(postgres_pool: any, user_id: int, is_unread: int = None, sort_order: str = "id desc", limit_count: int = 100, page_number: int = 1) -> list:
    """Read a conversation-summarized inbox for a user with unread filtering."""
    limit, page, order = int(limit_count or 100), int(page_number or 1), (sort_order or "id desc")
    where_clause = ('user_id=$1 AND is_read' + ('=1' if is_unread == 0 else ' IS DISTINCT FROM 1') if is_unread in (0, 1) else '1=1')
    query = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - user_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR user_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with postgres_pool.acquire() as conn: return [dict(r) for r in (await conn.fetch(query, user_id))]

async def func_message_received(postgres_pool: any, user_id: int, is_unread: int = None, sort_order: str = "id desc", limit_count: int = 100, page_number: int = 1) -> list:
    """Read all messages received by a specific user."""
    limit, page, order = int(limit_count or 100), int(page_number or 1), (sort_order or "id desc")
    unread_filter = ('AND is_read' + ('=1' if is_unread == 0 else ' IS DISTINCT FROM 1') if is_unread in (0, 1) else '')
    query = f"SELECT * FROM message WHERE user_id=$1 {unread_filter} ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with postgres_pool.acquire() as conn: return [dict(r) for r in (await conn.fetch(query, user_id))]

async def func_message_thread(postgres_pool: any, user_one_id: int, user_two_id: int, sort_order: str = "id desc", limit_count: int = 100, page_number: int = 1) -> list:
    """Read the full message thread between two users."""
    limit, page, order = int(limit_count or 100), int(page_number or 1), (sort_order or "id desc")
    async with postgres_pool.acquire() as conn: return [dict(r) for r in (await conn.fetch(f"SELECT * FROM message WHERE ((created_by_id=$1 AND user_id=$2) OR (created_by_id=$2 AND user_id=$1)) ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};", user_one_id, user_two_id))]

async def func_message_thread_mark_read(postgres_pool: any, current_user_id: int, partner_id: int) -> None:
    """Mark all messages in a thread as read for the current user."""
    async with postgres_pool.acquire() as conn: await conn.execute("UPDATE message SET is_read=1 WHERE created_by_id=$1 AND user_id=$2;", partner_id, current_user_id)

async def func_message_delete(delete_mode: str, postgres_pool: any, user_id: int, message_id: int = None) -> str:
    """Delete messages based on mode: single, created, received, or all."""
    query, query_args = (("DELETE FROM message WHERE id=$1 AND (created_by_id=$2 OR user_id=$2)", (message_id, user_id)) if delete_mode == "single" else ("DELETE FROM message WHERE created_by_id=$1", (user_id,)) if delete_mode == "sent" else ("DELETE FROM message WHERE user_id=$1", (user_id,)) if delete_mode == "received" else ("DELETE FROM message WHERE (created_by_id=$1 OR user_id=$1)", (user_id,)) if delete_mode == "all" else (None, None))
    if not query: raise Exception("invalid delete mode")
    async with postgres_pool.acquire() as conn: await conn.execute(query, *query_args); return "messages deleted"

async def func_auth_signup_username_password(postgres_pool: any, user_type: int, username: str, password_raw: str) -> dict:
    """Register a new user with username and password."""
    import hashlib
    async with postgres_pool.acquire() as conn: records = await conn.fetch("INSERT INTO users (type, username, password) VALUES ($1, $2, $3) RETURNING *;", user_type, username, hashlib.sha256(str(password_raw).encode()).hexdigest())
    return records[0]

async def func_auth_signup_username_password_bigint(postgres_pool: any, user_type: int, username_bigint: int, password_bigint: int) -> dict:
    """Register a new user with bigint identifier and bigint password (for specialized devices)."""
    async with postgres_pool.acquire() as conn: records = await conn.fetch("INSERT INTO users (type, username_bigint, password_bigint) VALUES ($1, $2, $3) RETURNING *;", user_type, username_bigint, password_bigint)
    return records[0]

async def func_auth_login_password_username(postgres_pool: any, user_type: int, password_raw: str, username: str) -> dict:
    """Authenticate a user using username and password."""
    import hashlib
    async with postgres_pool.acquire() as conn: records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username=$2 AND password=$3 ORDER BY id DESC LIMIT 1;", user_type, username, hashlib.sha256(str(password_raw).encode()).hexdigest())
    if not records: raise Exception("invalid username or password")
    return records[0]

async def func_auth_login_password_username_bigint(postgres_pool: any, user_type: int, password_bigint: int, username_bigint: int) -> dict:
    """Authenticate a user using bigint identifier and bigint password."""
    async with postgres_pool.acquire() as conn: records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username_bigint=$2 AND password_bigint=$3 ORDER BY id DESC LIMIT 1;", user_type, username_bigint, password_bigint)
    if not records: raise Exception("invalid credentials")
    return records[0]

async def func_auth_login_password_email(postgres_pool: any, user_type: int, password_raw: str, email_address: str) -> dict:
    """Authenticate a user using email address and password."""
    import hashlib
    async with postgres_pool.acquire() as conn: records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 AND password=$3 ORDER BY id DESC LIMIT 1;", user_type, email_address, hashlib.sha256(str(password_raw).encode()).hexdigest())
    if not records: raise Exception("invalid email or password")
    return records[0]

async def func_auth_login_password_mobile(postgres_pool: any, user_type: int, password_raw: str, mobile_number: str) -> dict:
    """Authenticate a user using mobile number and password."""
    import hashlib
    async with postgres_pool.acquire() as conn: records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 AND password=$3 ORDER BY id DESC LIMIT 1;", user_type, mobile_number, hashlib.sha256(str(password_raw).encode()).hexdigest())
    if not records: raise Exception("invalid mobile or password")
    return records[0]

async def func_auth_login_otp_email(postgres_pool: any, user_type: int, email_address: str) -> dict:
    """Authenticate or register a user using email OTP."""
    async with postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", user_type, email_address); user = records[0] if records else (await conn.fetch("INSERT INTO users (type, email) VALUES ($1, $2) RETURNING *;", user_type, email_address))[0]
    return user

async def func_auth_login_otp_mobile(postgres_pool: any, user_type: int, mobile_number: str) -> dict:
    """Authenticate or register a user using mobile OTP."""
    async with postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", user_type, mobile_number); user = records[0] if records else (await conn.fetch("INSERT INTO users (type, mobile) VALUES ($1, $2) RETURNING *;", user_type, mobile_number))[0]
    return user

async def func_auth_login_google(postgres_pool: any, google_client_id: str, user_type: int, google_token: str) -> dict:
    """Authenticate or register a user using Google OAuth ID token."""
    import json, time; from google.oauth2 import id_token; from google.auth.transport import requests as google_requests
    token_info = id_token.verify_oauth2_token(google_token, google_requests.Request(), google_client_id)
    if token_info.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]: raise Exception("invalid google token issuer")
    if not token_info.get("email_verified"): raise Exception("google email not verified")
    if token_info.get("exp", 0) < time.time(): raise Exception("google token expired")
    email_address = token_info.get("email").lower(); google_metadata = {"sub": token_info.get("sub"), "email": email_address, "name": token_info.get("name"), "picture": token_info.get("picture"), "email_verified": 1}
    async with postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1", user_type, email_address); user = records[0] if records else (await conn.fetch("INSERT INTO users (type, email, google_login_id, google_login_metadata) VALUES ($1, $2, $3, $4::jsonb) RETURNING *", user_type, email_address, google_metadata["sub"], json.dumps(google_metadata)))[0]
        if not user.get("google_login_id"): await conn.execute("UPDATE users SET google_login_id=$1, google_login_metadata=$2::jsonb WHERE id=$3", google_metadata["sub"], json.dumps(google_metadata), user["id"])
    return user

def func_openai_client_read(api_key: str) -> any:
    """Initialize OpenAI client."""
    from openai import OpenAI
    return OpenAI(api_key=api_key)

async def func_resend_send_email(endpoint_url: str, api_key: str, from_email: str, to_email: str, email_subject: str, email_content: str) -> None:
    """Send an email via Resend API."""
    import httpx
    async with httpx.AsyncClient() as client: response = await client.post(endpoint_url, json={"from": from_email, "to": to_email, "subject": email_subject, "html": email_content}, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    if response.status_code != 200: raise Exception(f"email sending failed: {response.text}")

def func_fast2sms_send_otp_mobile(api_url: str, api_key: str, mobile_number: str, otp_code: str) -> dict:
    """Send an OTP via Fast2SMS API."""
    import requests
    response = requests.get(api_url, params={"authorization": api_key, "numbers": mobile_number, "variables_values": otp_code, "route": "otp"}).json()
    if not response.get("return"): raise Exception(response.get("message"))
    return response

def func_posthog_client_read(host_url: str, api_key: str) -> any:
    """Initialize Posthog client."""
    from posthog import Posthog
    return Posthog(api_key, host=host_url)

def func_gsheet_client_read(credentials_path: str, auth_scopes: list) -> any:
    """Initialize Google Sheets client using service account credentials."""
    import gspread; from google.oauth2.service_account import Credentials
    return gspread.authorize(Credentials.from_service_account_file(credentials_path, scopes=auth_scopes))

def func_gsheet_object_create(gs_client: any, sheet_url: str, object_list: list) -> any:
    """Append records to a Google Sheet."""
    from urllib.parse import urlparse, parse_qs
    if not object_list: return None
    parsed_url = urlparse(sheet_url); spreadsheet_id = parsed_url.path.split("/")[3]; grid_id = int(parse_qs(parsed_url.query).get("gid", [""])[0])
    spreadsheet = gs_client.open_by_key(spreadsheet_id); worksheet = next((ws for ws in spreadsheet.worksheets() if ws.id == grid_id), None)
    if not worksheet: raise Exception("worksheet not found")
    column_headers = list(object_list[0].keys()); return worksheet.append_rows([[obj.get(col, "") for col in column_headers] for obj in object_list], value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")

async def func_gsheet_object_read(sheet_url: str) -> list:
    """Read records from a public Google Sheet as a list of dictionaries."""
    from urllib.parse import urlparse, parse_qs
    import pandas as pd, aiohttp, io
    parsed_url = urlparse(sheet_url); spreadsheet_id = parsed_url.path.split("/d/")[1].split("/")[0]; grid_id = parse_qs(parsed_url.query).get("gid", ["0"])[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={grid_id}") as response:
            if response.status != 200: raise Exception(f"fetch failed: {response.status}")
            csv_content = await response.text()
    data_frame = pd.read_csv(io.StringIO(csv_content)); return data_frame.where(pd.notnull(data_frame), None).to_dict(orient="records")

def func_mongodb_client_read(connection_url: str) -> any:
    """Initialize MongoDB client."""
    import motor.motor_asyncio
    return motor.motor_asyncio.AsyncIOMotorClient(connection_url)

async def func_mongodb_object_create(mongo_client: any, db_name: str, collection_name: str, object_list: list) -> str:
    """Insert multiple records into a MongoDB collection."""
    if not mongo_client: raise Exception("mongo client missing")
    return str(await mongo_client[db_name][collection_name].insert_many(object_list))

def func_jira_worklog_export(jira_url: str, email_address: str, api_token: str, start_date: str = None, end_date: str = None, output_path: str = None) -> str:
    """Export Jira worklogs for a specific period to a CSV file."""
    from jira import JIRA; from pathlib import Path; import pandas as pd, uuid, calendar; from datetime import date
    if not output_path: output_path = f"tmp/{uuid.uuid4().hex}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True); current_date = date.today(); start_date = start_date or current_date.replace(day=1).strftime("%Y-%m-%d"); end_date = end_date or current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1]).strftime("%Y-%m-%d")
    jira_client = JIRA(server=jira_url, basic_auth=(email_address, api_token)); log_rows, assignees = [], set()
    for issue in jira_client.search_issues(f"worklogDate >= {start_date} AND worklogDate <= {end_date}", maxResults=0, expand="worklog"):
        if issue.fields.assignee: assignees.add(issue.fields.assignee.displayName)
        for worklog in issue.fields.worklog.worklogs:
            started_at = worklog.started[:10]
            if start_date <= started_at <= end_date: log_rows.append((worklog.author.displayName, started_at, worklog.timeSpentSeconds / 3600))
    pd.DataFrame(log_rows, columns=["author", "date", "hours"]).pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0).reindex(assignees, fill_value=0).round(0).astype(int).to_csv(output_path); return output_path

#utils & converters
def func_folder_reset(folder_path: str) -> str:
    """Purge all files and subdirectories within a specified directory."""
    import os, shutil
    absolute_path = folder_path if os.path.isabs(folder_path) else os.path.join(os.getcwd(), folder_path)
    if not os.path.isdir(absolute_path): return "folder not found"
    for item in os.listdir(absolute_path): (shutil.rmtree(item_path) if os.path.isdir(item_path := os.path.join(absolute_path, item)) else os.remove(item_path))
    return "folder reset done"

async def func_client_download_file(file_path: str, delete_after: bool = True, chunk_size: int = 1048576) -> any:
    """Stream a file for client download with optional automatic cleanup after transmission."""
    from fastapi import responses; from starlette.background import BackgroundTask
    import os, mimetypes, aiofiles
    file_name = os.path.basename(file_path); content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    async def file_iterator():
        async with aiofiles.open(file_path, "rb") as f:
            while (chunk := await f.read(chunk_size)): yield chunk
    return responses.StreamingResponse(file_iterator(), media_type=content_type, headers={"Content-Disposition": f'attachment; filename="{file_name}"'}, background=BackgroundTask(os.remove, file_path) if delete_after else None)

async def func_request_param_read(parsing_mode: str, request_obj: any, param_config: list, is_strict: int = 0) -> dict:
    """Extract, validate, and type-cast request parameters from query, form, or body payload."""
    if parsing_mode == "query": params_dict = dict(request_obj.query_params)
    elif parsing_mode == "form":
        form_data = await request_obj.form(); params_dict = {key: val for key, val in form_data.items() if isinstance(val, str)}
        for key in form_data.keys(): (params_dict.update({key: files}) if (files := [x for x in form_data.getlist(key) if getattr(x, "filename", None)]) else None)
    elif parsing_mode == "body":
        try: json_payload = await request_obj.json()
        except: json_payload = None
        params_dict = json_payload if isinstance(json_payload, dict) else {"body": json_payload}
    elif parsing_mode == "header": params_dict = {k.lower(): v for k, v in request_obj.headers.items()}
    else: raise Exception("invalid parsing mode")
    if param_config is None: return params_dict
    TYPE_MAP = {
        "int": int, "float": float, "str": str, "any": lambda v: v, "file": lambda v: ([] if v is None else v if isinstance(v, list) else [v]),
        "bool": lambda v: (v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "yes", "on", "ok")),
        "list": lambda v: ([] if v is None else v if isinstance(v, list) else [] if (isinstance(v, str) and not v.strip()) else [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else [v]),
    }
    output_dict = {} if is_strict else params_dict
    for key, data_type, is_mandatory, default_value, allowed_values in param_config:
        if is_mandatory and key not in params_dict: raise Exception(f"parameter '{key}' missing")
        val = params_dict.get(key, default_value)
        if is_mandatory:
            if val is None: raise Exception(f"parameter '{key}' missing")
            if isinstance(val, str) and not val.strip(): raise Exception(f"parameter '{key}' cannot be empty")
        if val is not None:
            try:
                if data_type.startswith("list:") and ":" in data_type:
                    inner_type = data_type.split(":")[1]
                    val = TYPE_MAP["list"](val)
                    val = [TYPE_MAP[inner_type](x) for x in val]
                else: val = TYPE_MAP[data_type](val)
            except: raise Exception(f"parameter '{key}' invalid type {data_type}")
        if allowed_values:
            if val not in allowed_values: raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        output_dict[key] = val
    return output_dict

def func_converter_number(data_type: str, process_mode: str, value: any) -> any:
    """Encode strings into specific-size integers or decode them back using a custom charset."""
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}
    if data_type not in type_limits: raise ValueError(f"invalid data type {data_type}")
    charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"; base = len(charset); max_len = type_limits[data_type]
    if process_mode == "encode":
        val_str = str(value); val_len = len(val_str); result_num = val_len
        if val_len > max_len: raise ValueError(f"input too long {val_len} > {max_len}")
        for char in val_str:
            char_idx = charset.find(char)
            if char_idx == -1: raise ValueError("invalid character in input")
            result_num = result_num * base + char_idx
        return result_num
    if process_mode == "decode":
        try: num_val = int(value); decoded_chars = []
        except: raise ValueError("invalid integer for decoding")
        while num_val > 0: num_val, reminder = divmod(num_val, base); decoded_chars.append(charset[reminder])
        return "".join(decoded_chars[::-1][1:]) if decoded_chars else ""

async def func_sftp_client_read(host: str, port: int, username: str, password: str, key_path: str, auth_mode: str) -> any:
    """Initialize SFTP connection using asyncssh."""
    import asyncssh
    if auth_mode not in ("key", "password"): raise Exception("invalid sftp auth mode")
    if auth_mode == "key" and not key_path: raise Exception("ssh key path missing")
    if auth_mode == "password" and not password: raise Exception("password missing")
    return await asyncssh.connect(host=host, port=int(port), username=username, client_keys=([key_path] if auth_mode == "key" else None), password=(password if auth_mode == "password" else None), known_hosts=None)

