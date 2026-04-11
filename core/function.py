#system & structure
def func_structure_create(directories_list: list, files_list: list) -> None:
    """Create directory and file structure if it doesn't exist."""
    import os
    for directory_path in directories_list:
        try:
            os.makedirs(directory_path, exist_ok=True)
        except OSError:
            pass
    for file_path in files_list:
        try:
            if not os.path.exists(file_path):
                open(file_path, "a").close()
        except OSError:
            pass

def func_structure_check(root_path: str, dirs: tuple = None, files: tuple = None) -> None:
    """Verify existence of required project directories and files."""
    from pathlib import Path
    dirs_list = dirs or ()
    files_list = files or ()
    try:
        root = Path(root_path)
        if not root.exists():
            return None
        missing_dirs = [directory_name for directory_name in dirs_list if not (root / directory_name).is_dir()]
        missing_files = [file_name for file_name in files_list if not (root / file_name).is_file()]
        if missing_dirs:
            print(f"Structure verification failed. Missing Dirs: {missing_dirs}")
        if missing_files:
            print(f"Structure verification failed. Missing Files: {missing_files}")
    except Exception:
        pass
    return None

#utils & converters
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

def func_password_hash(password_raw: any) -> str:
    """Generate SHA-256 hash of the provided password string."""
    import hashlib
    return hashlib.sha256(str(password_raw).encode()).hexdigest()

#api & middleware utilities
#api core logic
def func_logic_data_validate(obj_list: list, api_role: str, config_column_blocked: list, immutable_fields: list = None) -> None:
    """Centralized validation for platform constraints, blocked columns, and immutable fields across one pass."""
    immutable_fields = immutable_fields or ["created_at"]
    for item in obj_list:
        if not isinstance(item, dict):
            continue
        for key in item:
            if key in immutable_fields:
                raise Exception(f"restricted update to immutable field: {key}")
            if api_role != "admin" and key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")

async def func_logic_obj_create(api_role: str, obj_query: dict[str, any], obj_body: dict[str, any], user_id: any, config_table_create_my: list, config_table_create_public: list, config_column_blocked: list, client_postgres_pool: any, func_postgres_serialize: callable, config_table: dict, func_producer_logic: callable, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, config_channel_allowed: list, func_celery_producer: callable, func_kafka_producer: callable, func_rabbitmq_producer: callable, func_redis_producer: callable, func_postgres_object_create: callable, func_validate_identifier: callable, config_postgres_batch_limit: int = None) -> any:
    """Wrapper logic for object creation with role-based validation and optional queueing."""
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    config_postgres_batch_limit = config_postgres_batch_limit or 1000
    if len(obj_list) > config_postgres_batch_limit:
        raise Exception("batch size exceeded")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
    if api_role not in ("my", "public", "admin"):
        raise Exception(f"role not allowed for creation: {api_role}")
    if api_role == "my" and obj_query.get("table") not in config_table_create_my:
        raise Exception(f"""table not allowed for role 'my': {obj_query.get("table")}, allowed: {config_table_create_my}""")
    if api_role == "public" and obj_query.get("table") not in config_table_create_public:
        raise Exception(f"""table not allowed for role 'public': {obj_query.get("table")}, allowed: {config_table_create_public}""")
    func_logic_data_validate(obj_list, api_role, config_column_blocked)
    if user_id:
        for item in obj_list:
            item["created_by_id"] = user_id
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_object_create", "params": {"execution_mode": obj_query.get("mode"), "table_name": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "config_table": config_table.get(obj_query.get("table"), {}).get("buffer")}}
        producer_obj = {"celery": {"client": client_celery_producer, "func": func_celery_producer}, "kafka": {"client": client_kafka_producer, "func": func_kafka_producer}, "rabbitmq": {"client": client_rabbitmq_producer, "func": func_rabbitmq_producer}, "redis": {"client": client_redis_producer, "func": func_redis_producer}, "config_channel_allowed": config_channel_allowed}
        return await func_producer_logic(obj_query.get("queue"), task_obj, producer_obj)
    return await func_postgres_object_create(client_postgres_pool, func_postgres_serialize, obj_query.get("mode"), obj_query.get("table"), obj_list, func_validate_identifier, obj_query.get("is_serialize"), config_table.get(obj_query.get("table"), {}).get("buffer"))

async def func_logic_obj_update(api_role: str, obj_query: dict, obj_body: dict, user_id: any, config_column_blocked: list, config_column_single_update: list, client_postgres_pool: any, func_postgres_serialize: callable, func_producer_logic: callable, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, config_channel_allowed: list, func_celery_producer: callable, func_kafka_producer: callable, func_rabbitmq_producer: callable, func_redis_producer: callable, func_postgres_object_update: callable, func_validate_identifier: callable, func_otp_verify: callable, config_expiry_sec_otp: int, config_is_otp_users_update_admin: int = None, config_postgres_batch_limit: int = None) -> any:
    """Wrapper logic for object updates with owner validation, OTP checks, and optional queueing."""
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    created_by_id = user_id
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    config_postgres_batch_limit = config_postgres_batch_limit or 1000
    if len(obj_list) > config_postgres_batch_limit:
        raise Exception("batch size exceeded")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
        created_by_id = None
    if api_role not in ("my", "admin"):
        raise Exception(f"role not allowed for update: {api_role}")
    func_logic_data_validate(obj_list, api_role, config_column_blocked)
    async def func_logic_user_otp_check(item: dict) -> None:
        """Internal helper to enforce OTP verification and single-field update constraints for sensitive user data."""
        if any(key in item for key in ("email", "mobile")):
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            if len(item) != 2:
                raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await func_otp_verify(client_postgres_pool, obj_query.get("otp"), item.get("email"), item.get("mobile"), config_expiry_sec_otp)
    if api_role == "my":
        item = obj_list[0]
        if obj_query.get("table") == "users":
            if str(item.get("id")) != str(user_id):
                raise Exception("ownership issue: cannot update other users")
            await func_logic_user_otp_check(item)
    elif api_role == "admin":
        created_by_id = None
        if obj_query.get("table") == "users" and (config_is_otp_users_update_admin or 0) == 1:
            await func_logic_user_otp_check(obj_list[0])
    if user_id:
        for item in obj_list:
            item["updated_by_id"] = user_id
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_object_update", "params": {"table_name": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "created_by_id": created_by_id}}
        producer_obj = {"celery": {"client": client_celery_producer, "func": func_celery_producer}, "kafka": {"client": client_kafka_producer, "func": func_kafka_producer}, "rabbitmq": {"client": client_rabbitmq_producer, "func": func_rabbitmq_producer}, "redis": {"client": client_redis_producer, "func": func_redis_producer}, "config_channel_allowed": config_channel_allowed}
        return await func_producer_logic(obj_query.get("queue"), task_obj, producer_obj)
    return await func_postgres_object_update(client_postgres_pool, func_postgres_serialize, obj_query.get("table"), obj_list, func_validate_identifier, obj_query.get("is_serialize"), created_by_id)

async def func_producer_logic(queue: str, task_obj: dict, producer_obj: dict) -> any:
    """Ultra-standardized producer logic. Handles queue splitting, validation, and multi-tech dispatch in exactly 3 parameters."""
    if not queue:
        raise Exception("invalid queue format: queue name missing")
    if "_" not in queue:
        raise Exception(f"invalid queue format: '{queue}', expected tech_channel (e.g. redis_default)")
    tech, channel = queue.split("_", 1)
    if tech not in ["redis", "rabbitmq", "kafka", "celery"]:
        raise Exception(f"invalid queue technology: {tech}")
    if channel not in producer_obj.get("config_channel_allowed", []):
        raise Exception(f"unauthorized channel: {channel}, allowed: {producer_obj.get('config_channel_allowed')}")
    p = producer_obj.get(tech)
    if not p:
        raise Exception(f"producer not found for tech: {tech}")
    if tech == "celery":
        return p["func"](channel, task_obj["task_name"], p["client"], task_obj["params"])
    return await p["func"](channel, p["client"], task_obj)

async def func_api_file_to_obj_list(upload_file: any) -> list[dict[str, any]]:
    """Convert an uploaded CSV file into a list of dictionaries (all at once)."""
    import csv, io, asyncio
    def _parse_csv(file):
        return [row for row in csv.DictReader(io.TextIOWrapper(file, encoding="utf-8"))]
    obj_list = await asyncio.to_thread(_parse_csv, upload_file.file)
    await upload_file.close()
    return obj_list

async def func_api_file_to_chunks(upload_file: any, chunk_size: int = None) -> any:
    """Yield chunks of dictionaries from an uploaded CSV file for memory efficiency."""
    if chunk_size is None:
        chunk_size = 5000
    import csv, io, asyncio
    
    def _read_chunk(reader_iter, size):
        chunk = []
        try:
            for _ in range(size):
                chunk.append(next(reader_iter))
        except StopIteration:
            pass
        return chunk
    reader = csv.DictReader(io.TextIOWrapper(upload_file.file, encoding="utf-8"))
    reader_iter = iter(reader)
    while True:
        chunk = await asyncio.to_thread(_read_chunk, reader_iter, chunk_size)
        if not chunk:
            break
        yield chunk
    await upload_file.close()
    return

#api metadata
def func_openapi_spec_generate(app_routes: list, config_api_roles_auth: list = None, app_state: any = None) -> dict:
    """Generate a standard OpenAPI 3.0.0 specification from FastAPI routes using source inspection."""
    import inspect, re, ast
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "API Documentation", "version": "1.0.0"},
        "paths": {},
        "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}}
    }
    for route in app_routes:
        if not hasattr(route, "path"):
            continue
        if not hasattr(route, "endpoint"):
            continue
        path = route.path
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        methods = list(getattr(route, "methods", []))
        if not methods and "WebSocket" in type(route).__name__:
            methods = ["WS"]
        for method in methods:
            m_lower = method.lower()
            path_parts = path.split("/")
            tag = path_parts[1] if len(path_parts) > 1 and path_parts[1] else "system"
            op = {"tags": [tag], "parameters": [], "responses": {"200": {"description": "Successful Response"}}}
            if any(path.startswith(x) for x in (config_api_roles_auth if config_api_roles_auth else [])):
                op["security"] = [{"BearerAuth": []}]
                op["parameters"].append({"name": "Authorization", "in": "header", "required": True, "schema": {"type": "string", "default": "Bearer {token}"}})
            for p in re.findall(r"\{(\w+)\}", path):
                op["parameters"].append({"name": p, "in": "path", "required": True, "schema": {"type": "string"}})
            try:
                sig = inspect.signature(route.endpoint)
                for name, par in sig.parameters.items():
                    p_type = par.annotation.__name__ if hasattr(par.annotation, "__name__") else str(par.annotation)
                    if name in ["request", "websocket", "req"]:
                        continue
                    if "Request" in p_type:
                        continue
                    if "Response" in p_type:
                        continue
                    if "WebSocket" in p_type:
                        continue
                    if "BackgroundTasks" in p_type:
                        continue
                    if any(x["name"] == name for x in op["parameters"]):
                        continue
                    param_def = {
                        "name": name,
                        "in": "query",
                        "required": par.default == inspect.Parameter.empty,
                        "schema": {
                            "type": "integer" if p_type == "int" else "string",
                            "default": None if par.default == inspect.Parameter.empty else par.default
                        }
                    }
                    op["parameters"].append(param_def)
                source = inspect.getsource(route.endpoint)
                tree = ast.parse(source)
                def eval_node(n):
                   if hasattr(ast, "Constant") and isinstance(n, ast.Constant):
                       return n.value
                   if hasattr(ast, "Str") and isinstance(n, ast.Str):
                       return n.s
                   if hasattr(ast, "Bytes") and isinstance(n, ast.Bytes):
                       return n.s
                   if hasattr(ast, "Num") and isinstance(n, ast.Num):
                       return n.n
                   if hasattr(ast, "NameConstant") and isinstance(n, ast.NameConstant):
                       return n.value
                   if isinstance(n, ast.List):
                       return [eval_node(e) for e in n.elts]
                   if isinstance(n, ast.Tuple):
                       return tuple(eval_node(e) for e in n.elts)
                   if hasattr(ast, "Attribute") and isinstance(n, ast.Attribute):
                       if hasattr(n.value, "id") and n.value.id == "st" and app_state:
                           return getattr(app_state, n.attr, None)
                   return None
                def ast_to_schema(n):
                    if isinstance(n, ast.Dict):
                        props = {}
                        for k, v in zip(n.keys, n.values):
                            k_name = eval_node(k)
                            if k_name:
                                props[k_name] = ast_to_schema(v)
                        return {"type": "object", "properties": props}
                    if isinstance(n, ast.List):
                        return {"type": "array", "items": ast_to_schema(n.elts[0]) if n.elts else {"type": "string"}}
                    if isinstance(n, ast.Tuple):
                        return {"type": "array", "items": ast_to_schema(n.elts[0]) if n.elts else {"type": "string"}}
                    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                        s1 = ast_to_schema(n.left)
                        s2 = ast_to_schema(n.right)
                        p = {**(s1.get("properties", {})), **(s2.get("properties", {}))}
                        return {"type": "object", "properties": p}
                    if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "dict":
                         return {"type": "object"}
                    v = eval_node(n)
                    if isinstance(v, int):
                        return {"type": "integer", "default": v}
                    if isinstance(v, float):
                        return {"type": "number", "default": v}
                    if isinstance(v, bool):
                        return {"type": "boolean", "default": v}
                    if isinstance(v, list):
                        return {"type": "array", "items": {"type": "string"}}
                    if isinstance(v, dict):
                        return {"type": "object", "properties": {k: {"type": "string", "default": str(val)} for k, val in v.items()}}
                    return {"type": "string", "default": str(v) if v is not None else "str"}
                for node in ast.walk(tree):
                    if isinstance(node, ast.Return):
                        try:
                            op["responses"]["200"]["content"] = {"application/json": {"schema": ast_to_schema(node.value)}}
                        except Exception:
                            pass
                    if not isinstance(node, ast.Call):
                        continue
                    func_id = getattr(node.func, "id", None)
                    if not func_id:
                        func_id = getattr(node.func, "attr", None)
                    if func_id != "func_request_param_read":
                        continue
                    try:
                        p_loc = eval_node(node.args[1])
                        p_list = eval_node(node.args[2])
                        if p_list is not None and p_loc in ["header", "query"]:
                            for p in p_list:
                                if not p or not isinstance(p, (list, tuple)) or len(p) < 1:
                                    continue
                                op["parameters"] = [x for x in op["parameters"] if x["name"] != p[0]]
                                tp = "string"
                                fmt = None
                                itms = None
                                if len(p) > 1:
                                    dt = p[1]
                                    if dt in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                        tp = "integer"
                                    elif dt in ["float", "number", "numeric"]:
                                        tp = "number"
                                    elif dt == "bool":
                                        tp = "boolean"
                                    elif dt in ["dict", "object"]:
                                        tp = "object"
                                    elif dt == "file":
                                        tp = "string"
                                        fmt = "binary"
                                    elif dt == "list" or dt.startswith("list:"):
                                        tp = "array"
                                        it_tp = "string"
                                        inner = dt.split(":")[1] if ":" in dt else "string"
                                        if inner in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                            it_tp = "integer"
                                        elif inner in ["float", "number", "numeric"]:
                                            it_tp = "number"
                                        elif inner == "bool":
                                            it_tp = "boolean"
                                        elif inner in ["dict", "object"]:
                                            it_tp = "object"
                                        itms = {"type": it_tp}
                                op["parameters"].append({
                                    "name": p[0],
                                    "in": p_loc,
                                    "required": bool(p[2]) if len(p) > 2 else False,
                                    "schema": {
                                        "type": tp,
                                        "format": fmt,
                                        "items": itms,
                                        "pattern": p[5] if len(p) > 5 else None,
                                        "description": f"{p[6]}" if len(p) > 6 and p[6] else None
                                    }
                                })
                        elif p_list is not None and p_loc in ["body", "form"]:
                            media_type = "application/json" if p_loc == "body" else "multipart/form-data"
                            if "requestBody" not in op:
                                op["requestBody"] = {"content": {media_type: {"schema": {"type": "object"}}}}
                            if p_list:
                                schema_obj = op["requestBody"]["content"][media_type]["schema"]
                                if "properties" not in schema_obj:
                                    schema_obj["properties"] = {}
                                if "required" not in schema_obj:
                                    schema_obj["required"] = []
                                props = schema_obj["properties"]
                                for p in p_list:
                                    if not p or not isinstance(p, (list, tuple)) or len(p) < 1:
                                        continue
                                    tp = "string"
                                    fmt = None
                                    itms = None
                                    if len(p) > 1:
                                        dt = p[1]
                                        if dt in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                            tp = "integer"
                                        elif dt in ["float", "number", "numeric"]:
                                            tp = "number"
                                        elif dt == "bool":
                                            tp = "boolean"
                                        elif dt in ["dict", "object"]:
                                            tp = "object"
                                        elif dt == "file":
                                            tp = "string"
                                            fmt = "binary"
                                        elif dt == "list" or dt.startswith("list:"):
                                            tp = "array"
                                            it_tp = "string"
                                            inner = dt.split(":")[1] if ":" in dt else "string"
                                            if inner in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                                it_tp = "integer"
                                            elif inner in ["float", "number", "numeric"]:
                                                it_tp = "number"
                                            elif inner == "bool":
                                                it_tp = "boolean"
                                            elif inner in ["dict", "object"]:
                                                it_tp = "object"
                                            itms = {"type": it_tp}
                                    props[p[0]] = {
                                        "type": tp,
                                        "format": fmt,
                                        "items": itms,
                                        "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None,
                                        "default": p[4] if len(p) > 4 else None,
                                        "pattern": p[5] if len(p) > 5 else None,
                                        "description": f"{p[6]}" if len(p) > 6 and p[6] else None
                                    }
                                    if len(p) > 2 and bool(p[2]):
                                        schema_obj["required"].append(p[0])
                    except Exception:
                        pass
            except Exception:
                pass

            spec["paths"][path][m_lower] = op
    return spec

def func_check(app_routes: list, current_config_api: dict, allowed_roles: list = None, config_postgres: dict = None, api_roles_auth: list = None) -> None:
    """Validate config_api consistency with app routes, admin roles, valid modes, duplicate keys, and strict api roles."""
    import ast
    def get_duplicate_errors(file_path, var_name):
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == var_name:
                            if isinstance(node.value, ast.Dict):
                                keys = []
                                for k in node.value.keys:
                                    if isinstance(k, ast.Constant):
                                        keys.append(k.value)
                                    elif isinstance(k, ast.Str):
                                        keys.append(k.s)
                                duplicates = [str(k) for k in set(keys) if keys.count(k) > 1]
                                return [f"duplicate keys in {var_name}: {', '.join(duplicates)}"] if duplicates else []
        except Exception:
            pass
        return []
    app_paths = {route.path for route in app_routes if hasattr(route, "path")}
    def get_route_errors(paths, config):
        missing = [p for p in config if p not in paths]
        return [f"""config_api paths missing from app: {", ".join(missing)}"""] if missing else []
    def get_admin_errors(routes, config):
        errs = []
        for route in routes:
            if hasattr(route, "path") and route.path.startswith("/admin/"):
                if route.path not in config:
                    errs.append(f"{route.path} missing from config_api")
                else:
                    roles_cfg = config[route.path].get("user_role_check", [])
                    allowed_roles_cfg = roles_cfg[1] if roles_cfg and isinstance(roles_cfg[0], str) else roles_cfg
                    if 1 not in (allowed_roles_cfg if isinstance(allowed_roles_cfg, (list, tuple, set)) else []):
                        errs.append(f"{route.path} missing role 1")
        return errs
    def get_mode_errors(config):
        errs = []
        rules = {"user_role_check": ["redis", "realtime", "inmemory", "token"], "user_is_active_check": ["redis", "realtime", "inmemory", "token"], "api_cache_sec": ["redis", "inmemory"], "api_ratelimiting_times_sec": ["redis", "inmemory"]}
        for path, cfg in config.items():
            for key, allowed in rules.items():
                if key in cfg:
                    setting = cfg[key]
                    if not isinstance(setting, (list, tuple)) or len(setting) < 2 or setting[0] not in allowed:
                        errs.append(f"{path} invalid {key} mode (allowed: {allowed})")
        return errs
    def get_api_role_errors(routes, allowed):
        if not allowed:
            return []
        errs = []
        for route in routes:
            if hasattr(route, "path"):
                role = route.path.split("/")[1] if len(route.path.split("/")) > 2 else "index"
                if role not in allowed:
                    errs.append(f"invalid api role in path {route.path}: {role}")
        return errs
    def get_control_errors(config_pg):
        if not config_pg:
            return []
        if "control" not in config_pg:
            return []
        errs = []
        ctrl = config_pg["control"]
        for k, v in ctrl.items():
            if k.startswith("is_") and v not in (None, 0, 1):
                errs.append(f"invalid value for {k}: {v} (allowed: 0, 1, None)")
        tdd = ctrl.get("table_row_delete_disable")
        if not isinstance(tdd, list):
            errs.append("table_row_delete_disable must be a list")
        elif "*" in tdd and len(tdd) > 1:
            errs.append("exclusive wildcard violation: table_row_delete_disable cannot contain other tables if '*' is present")
        tddb = ctrl.get("table_row_delete_disable_bulk")
        if not isinstance(tddb, list):
            errs.append("table_row_delete_disable_bulk must be a list")
        else:
            is_star = any(isinstance(x, (list, tuple)) and x and x[0] == "*" for x in tddb)
            if is_star and len(tddb) > 1:
                errs.append("exclusive wildcard violation: table_row_delete_disable_bulk cannot contain other tables if '*' is present")
            for x in tddb:
                if not isinstance(x, (list, tuple)):
                    errs.append(f"invalid bulk delete format: {x} (expected array)")
                    continue
                if len(x) < 2:
                    errs.append(f"invalid bulk delete format: {x} (expected [table, limit])")
        return errs
    def get_cors_errors():
        from . import config
        errs = []
        for k in ("config_cors_origin", "config_cors_method", "config_cors_headers"):
            v = getattr(config, k, None)
            if not isinstance(v, list):
                errs.append(f"{k} must be a list")
            elif "*" in v and len(v) > 1:
                errs.append(f"exclusive wildcard violation: {k} cannot contain other values if '*' is present")
        return errs

    def get_switch_errors():
        from . import config
        errs = []
        for key, value in vars(config).items():
            if key.startswith("config_is_"):
                if value not in (None, 0, 1):
                    errs.append(f"invalid value for {key}: {value} (allowed: 0, 1, None)")
        return errs
    def get_table_integrity_errors(config_pg):
        from . import config
        if not config_pg:
            return []
        if "table" not in config_pg:
            return []
        errs = []
        db_tables = set(config_pg["table"].keys())
        for k in ("config_table_create_my", "config_table_create_public", "config_table_read_public", "config_table"):
            v = getattr(config, k, [] if k != "config_table" else {})
            v_list = v.keys() if k == "config_table" else v
            for table in v_list:
                if table not in db_tables:
                    errs.append(f"table reference integrity violation: {table} (referenced in {k}) does not exist in config_postgres")
        return errs
    def get_api_id_errors(config_api):
        missing = [p for p, v in config_api.items() if not isinstance(v, dict) or "id" not in v]
        if missing:
            return [f"missing mandatory API ID for: {', '.join(missing)}"]
        ids = [v["id"] for v in config_api.values()]
        dupes = [str(i) for i in set(ids) if ids.count(i) > 1]
        return [f"duplicate API IDs in config_api: {', '.join(dupes)}"] if dupes else []
    def get_enum_type_errors():
        from . import config
        errs = []
        checks = {"config_auth_type": int, "config_token_key": str, "config_api_roles": str}
        for k, t in checks.items():
            v = getattr(config, k, None)
            if not isinstance(v, list):
                errs.append(f"{k} must be a list")
            elif not all(isinstance(x, t) for x in v):
                errs.append(f"{k} must be a list of {t.__name__}s")
        return errs
    if api_roles_auth is not None and not isinstance(api_roles_auth, (list, tuple)):
        raise Exception("config_api_roles_auth must be a list")
    errors = get_duplicate_errors("config.py", "config_api") + get_route_errors(app_paths, current_config_api) + get_admin_errors(app_routes, current_config_api) + get_mode_errors(current_config_api) + get_api_role_errors(app_routes, allowed_roles) + get_switch_errors() + get_control_errors(config_postgres) + get_cors_errors() + get_table_integrity_errors(config_postgres) + get_api_id_errors(current_config_api) + get_enum_type_errors()
    if errors:
        raise Exception("; ".join(errors))

def func_repo_info(app_routes: list, cache_postgres_schema: dict, config_postgres: dict, config_table: dict, config_api: dict) -> dict:
    """Construct system discovery metadata including routes, schema, and configuration settings."""
    import inspect, ast
    def get_postgres_keys(config_pg):
        postgres_key = {}
        for k, v in config_pg.items():
            if k == "table":
                table_keys = set()
                for cv in v.values():
                    for item in cv:
                        for ck in item:
                            table_keys.add(ck)
                postgres_key[k] = sorted(list(table_keys))
            elif isinstance(v, dict):
                postgres_key[k] = sorted(list(v.keys()))
            else:
                postgres_key[k] = []
        return postgres_key
    def get_api_param_count(routes):
        param_counts = {}
        for route in routes:
            if not hasattr(route, "endpoint"):
                continue
            try:
                for node in ast.walk(ast.parse(inspect.getsource(route.endpoint))):
                    if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) == "func_request_param_read":
                        if len(node.args) > 2 and isinstance(node.args[2], ast.List):
                            for elt in node.args[2].elts:
                                if isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) > 0:
                                    val = getattr(elt.elts[0], "value", getattr(elt.elts[0], "s", None))
                                    if isinstance(val, str):
                                        param_counts[val] = param_counts.get(val, 0) + 1
            except Exception:
                pass
        return dict(sorted(param_counts.items(), key=lambda x: x[1], reverse=True))
    def get_config_keys(cfg):
        return sorted(list(set(k for v in cfg.values() for k in v)))
    return {
        "api_list": [route.path for route in app_routes if hasattr(route, "path")],
        "api_param_count": get_api_param_count(app_routes),
        "postgres_schema": cache_postgres_schema,
        "config_table_key": get_config_keys(config_table),
        "config_api_key": get_config_keys(config_api),
        "config_postgres_key": get_postgres_keys(config_postgres)
    }

def func_config_override_from_env(global_dict: dict) -> None:
    """Override configuration variables starting with 'config_' from environment variables and .env file."""
    import orjson, os, ast
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    for key, value in list(global_dict.items()):
        val_env = os.getenv(key)
        if key.startswith("config_") and val_env is not None:
            config_val = val_env
            if isinstance(global_dict[key], (list, tuple)):
                global_dict[key] = orjson.loads(config_val)
            elif isinstance(value, bool):
                global_dict[key] = 1 if config_val.lower() in ("true", "1", "yes", "on", "ok") else 0
            elif isinstance(value, int):
                global_dict[key] = int(config_val)
            elif isinstance(value, dict):
                try:
                    global_dict[key] = orjson.loads(config_val)
                except Exception:
                    pass
            else:
                try:
                    global_dict[key] = int(config_val)
                except Exception:
                    global_dict[key] = config_val
            if isinstance(global_dict[key], list):
                global_dict[key] = tuple(global_dict[key])
    try:
        with open("core/config.py", "r") as config_file:
            for node in ast.parse(config_file.read()).body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Name):
                    target_id = node.targets[0].id
                    value_id = node.value.id
                    if target_id.startswith("config_") and value_id.startswith("config_") and os.getenv(target_id) is None:
                        global_dict[target_id] = global_dict[value_id]
    except Exception:
        pass

#database - core operations


#database - maintenance & schema
    



#external clients - messaging & cache (redis/rabbitmq/kafka/celery)


async def func_redis_producer(channel_name: str, client_redis: any, payload: dict) -> int:
    """Publish a JSON-serialized payload to a Redis channel."""
    import orjson
    return await client_redis.publish(channel_name, orjson.dumps(payload).decode('utf-8'))

async def func_redis_object_create(client_redis: any, keys: list, objects: list, config_redis_cache_ttl_sec: int) -> None:
    """Batch create/update objects in Redis with optional expiration in a pipeline transaction."""
    import orjson
    async with client_redis.pipeline(transaction=True) as pipe:
        for key, obj in zip(keys, objects):
            val = orjson.dumps(obj).decode('utf-8')
            if config_redis_cache_ttl_sec:
                pipe.setex(key, config_redis_cache_ttl_sec, val)
            else:
                pipe.set(key, val)
        await pipe.execute()
    return None

async def func_redis_object_delete(client_redis: any, keys: list) -> None:
    """Batch delete objects in Redis using a pipeline transaction."""
    async with client_redis.pipeline(transaction=True) as pipe:
        for key in keys:
            pipe.delete(key)
        await pipe.execute()
    return None


def func_celery_producer(channel_name: str, task_name: str, client_celery_producer: any, params: dict) -> any:
    """Send a task to a Celery worker."""
    return client_celery_producer.send_task(task_name, kwargs=params, queue=channel_name).id



async def func_rabbitmq_producer(channel_name: str, client_rabbitmq_producer: any, payload: dict) -> any:
    """Publish a JSON payload to a RabbitMQ queue."""
    import aio_pika, orjson
    return await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(payload), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel_name)



async def func_kafka_producer(channel_name: str, client_kafka_producer: any, payload: dict) -> any:
    """Publish a JSON payload to a Kafka topic."""
    import orjson
    return await client_kafka_producer.send_and_wait(channel_name, orjson.dumps(payload))


#api cache & rate limiting
async def func_token_encode(user_obj: dict, config_token_secret_key: str, config_token_expiry_sec: int, config_token_refresh_expiry_sec: int, config_token_key: list = None) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    import jwt, orjson, time
    if user_obj is None:
        return None
    payload_dict = {k: user_obj.get(k) for k in config_token_key} if config_token_key else dict(user_obj) if isinstance(user_obj, dict) else user_obj
    serialized_payload = orjson.dumps(payload_dict, default=str).decode('utf-8')
    now_ts = int(time.time())
    access_token = jwt.encode({"exp": now_ts + config_token_expiry_sec, "data": serialized_payload, "type": "access"}, config_token_secret_key)
    refresh_token = jwt.encode({"exp": now_ts + config_token_refresh_expiry_sec, "data": serialized_payload, "type": "refresh"}, config_token_secret_key)
    return {"token": access_token, "token_refresh": refresh_token, "token_expiry_sec": config_token_expiry_sec, "token_refresh_expiry_sec": config_token_refresh_expiry_sec}

def func_fastapi_app_read(lifespan_handler: any, is_debug_mode: int) -> any:
    """Initialize a FastAPI application with debug mode and lifespan handler, disabling default OpenAPI routes."""
    from fastapi import FastAPI
    return FastAPI(debug=bool(is_debug_mode), lifespan=lifespan_handler, openapi_url=None, docs_url=None, redoc_url=None)

def func_app_add_cors(fastapi_app: any, origins: list, methods: list, headers: list, is_allow_credentials: int) -> None:
    """Add CORS middleware to the FastAPI application."""
    from fastapi.middleware.cors import CORSMiddleware
    fastapi_app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=methods, allow_headers=headers, allow_credentials=bool(is_allow_credentials))

def func_app_add_prometheus(fastapi_app: any) -> None:
    """Expose Prometheus metrics for the FastAPI application."""
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(fastapi_app).expose(fastapi_app)

def func_app_state_add(fastapi_app: any, config_dict: dict, prefix: str) -> None:
    """Inject configuration values into the FastAPI application state based on a prefix."""
    for key, val in config_dict.items():
        if key.startswith(prefix):
            setattr(fastapi_app.state, key, val)

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
    """Dynamically discover and include all FastAPI routers from the router directory."""
    import sys, importlib.util
    from pathlib import Path
    from fastapi import APIRouter
    root_dir = Path("./router").resolve()
    if not root_dir.exists():
        return None
    for py_file in root_dir.rglob("*.py"):
        if py_file.name.startswith((".", "__")):
            continue
        rel_path = py_file.relative_to(root_dir)
        module_name = "router." + ".".join(rel_path.with_suffix("").parts)
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            router = getattr(module, "router", None)
            if not isinstance(router, APIRouter):
                raise Exception(f"invalid router file: {py_file} (missing 'router' attribute of type APIRouter)")
            fastapi_app.include_router(router)

#admin & analytics

async def func_api_usage_read(client_postgres_pool: any, days_limit: int, user_id: int = None) -> list:
    """Read API usage logs for a specific user or globally within a day limit."""
    query = "SELECT api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND ($2::bigint IS NULL OR created_by_id=$2) GROUP BY api LIMIT 1000;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, days_limit, user_id)
        return [dict(r) for r in records]

async def func_account_delete(delete_mode: str, client_postgres_pool: any, user_id: int) -> str:
    """Delete a user account either softly (flag) or hardly (row removal)."""
    async with client_postgres_pool.acquire() as conn:
        user=await conn.fetchrow("SELECT role FROM users WHERE id=$1", user_id)
        if not user:
            raise Exception("user not found")
        if user["role"] is not None:
            raise Exception("account with role cannot be deleted")
        if delete_mode == "soft":
            query = "UPDATE users SET is_deleted=1 WHERE id=$1"
        elif delete_mode == "hard":
            query = "DELETE FROM users WHERE id=$1"
        else:
            raise Exception(f"invalid delete mode: {delete_mode}, allowed: soft, hard")
        await conn.execute(query, user_id)
    return "account deleted"

#user & message operations
async def func_user_single_read(client_postgres_pool: any, user_id: int) -> dict:
    """Read a single user's full record by their ID."""
    async with client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
        if not record:
            raise Exception("user not found")
        return dict(record)

async def func_my_profile_read(client_postgres_pool: any, user_id: int, config_sql: dict) -> dict:
    """Read full user profile and update last activity status."""
    import asyncio
    user = await func_user_single_read(client_postgres_pool, user_id)
    metadata = {}
    queries_metadata = config_sql.get("profile_metadata")
    if queries_metadata:
        async with client_postgres_pool.acquire() as conn:
            for key, sql_query in queries_metadata.items():
                records = await conn.fetch(sql_query, user_id)
                metadata[key] = [dict(record) for record in records]
    asyncio.create_task(client_postgres_pool.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", user_id))
    return {**user, **metadata}

#auth & otp
async def func_otp_generate(client_postgres_pool: any, email_address: str = None, mobile_number: str = None) -> int:
    """Generate a random 6-digit OTP and store it in PostgreSQL for a given email or mobile."""
    import random
    otp_code = random.randint(100000, 999999)
    query = "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3);"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, otp_code, email_address.strip().lower() if email_address else None, mobile_number.strip() if mobile_number else None)
    return otp_code

async def func_otp_verify(client_postgres_pool: any, otp_code: int, email_address: str = None, mobile_number: str = None, config_expiry_sec_otp: int = None) -> None:
    """Verify an OTP for email or mobile within its expiration window."""
    config_expiry_sec_otp = config_expiry_sec_otp or 600
    if not otp_code:
        raise Exception("otp code missing")
    if not email_address and not mobile_number:
        raise Exception("missing both email and mobile")
    if email_address and mobile_number:
        raise Exception("provide only one identifier")
    if email_address:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email_address.strip().lower()
    else:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile_number.strip()
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, identifier)
        if not records:
            raise Exception("otp not found")
        if records[0]["otp"] != otp_code:
            raise Exception("invalid otp code")
        if not records[0]["is_active"]:
            raise Exception("otp code expired")
    return None






async def func_resend_send_email(config_resend_url: str, config_resend_key: str, from_email: str, to_email: str, email_subject: str, email_content: str) -> None:
    """Send an email using the Resend API."""
    import httpx, orjson
    headers = {"Authorization": f"Bearer {config_resend_key}", "Content-Type": "application/json"}
    payload = {"from": from_email, "to": [to_email], "subject": email_subject, "html": email_content}
    async with httpx.AsyncClient() as client:
        response = await client.post(config_resend_url, headers=headers, data=orjson.dumps(payload).decode('utf-8'))
        if response.status_code != 200:
            raise Exception(f"failed to send email: {response.text}")
    return None

def func_fast2sms_send_otp_mobile(config_fast2sms_url: str, config_fast2sms_key: str, mobile_number: str, otp_code: str) -> dict:
    """Send an OTP via Fast2SMS API."""
    import requests
    response = requests.get(config_fast2sms_url, params={"authorization": config_fast2sms_key, "numbers": mobile_number, "variables_values": otp_code, "route": "otp"}).json()
    if not response.get("return"):
        raise Exception(response.get("message"))
    return response



def func_gsheet_object_create(client_gsheet: any, sheet_url: str, object_list: list) -> any:
    """Append records to a Google Sheet."""
    from urllib.parse import urlparse, parse_qs
    if not object_list:
        return None
    parsed_url = urlparse(sheet_url)
    spreadsheet_id = parsed_url.path.split("/")[3]
    query_params = parse_qs(parsed_url.query)
    grid_id = int(query_params.get("gid", [""])[0])
    spreadsheet = client_gsheet.open_by_key(spreadsheet_id)
    worksheet = next((ws for ws in spreadsheet.worksheets() if ws.id == grid_id), None)
    if not worksheet:
        raise Exception("worksheet not found")
    column_headers = list(object_list[0].keys())
    rows_to_insert = [[obj.get(col, "") for col in column_headers] for obj in object_list]
    return worksheet.append_rows(rows_to_insert, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")

async def func_gsheet_object_read(sheet_url: str) -> list:
    """Read records from a public Google Sheet as a list of dictionaries."""
    from urllib.parse import urlparse, parse_qs
    import pandas as pd, aiohttp, io
    parsed_url = urlparse(sheet_url)
    spreadsheet_id = parsed_url.path.split("/d/")[1].split("/")[0]
    grid_id = parse_qs(parsed_url.query).get("gid", ["0"])[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={grid_id}") as response:
            if response.status != 200:
                raise Exception(f"fetch failed: {response.status}")
            csv_content = await response.text()
    data_frame = pd.read_csv(io.StringIO(csv_content))
    return data_frame.where(pd.notnull(data_frame), None).to_dict(orient="records")


async def func_mongodb_object_create(client_mongodb: any, db_name: str, collection_name: str, object_list: list) -> str:
    """Insert multiple records into a MongoDB collection."""
    if not client_mongodb:
        raise Exception("mongo client missing")
    result = await client_mongodb[db_name][collection_name].insert_many(object_list)
    return str(result.inserted_ids)

async def func_mongodb_object_delete(client_mongodb: any, db_name: str, collection_name: str, object_list: list) -> str:
    """Delete multiple records from a MongoDB collection using ID matching from a list of objects."""
    if not client_mongodb:
        raise Exception("mongo client missing")
    from bson.objectid import ObjectId
    id_list = []
    for obj in object_list:
        obj_id = obj.get("_id") or obj.get("id")
        if not obj_id:
            continue
        try:
            id_list.append(ObjectId(obj_id)) if len(str(obj_id)) == 24 else id_list.append(obj_id)
        except Exception:
            id_list.append(obj_id)
    if not id_list:
        return "0 rows deleted"
    result = await client_mongodb[db_name][collection_name].delete_many({"_id": {"$in": id_list}})
    return f"{result.deleted_count} rows deleted"

def func_jira_worklog_export(url: str, email_address: str, api_token: str, start_date: str = None, end_date: str = None, output_path: str = None) -> str:
    """Export Jira worklogs for a specific period to a CSV file."""
    try:
        from jira import JIRA
        from pathlib import Path
        import pandas as pd, uuid, calendar
        from datetime import date
        output_path = output_path or f"tmp/{uuid.uuid4().hex}.csv"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        current_date = date.today()
        start_date = start_date or current_date.replace(day=1).strftime("%Y-%m-%d")
        end_date = end_date or current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1]).strftime("%Y-%m-%d")
        jira_client = JIRA(server=url, basic_auth=(email_address, api_token))
        log_rows = []
        people = set()
        jql = f"worklogDate >= '{start_date}' AND worklogDate <= '{end_date}'"
        all_issues = jira_client.enhanced_search_issues(jql, maxResults=0)
        for issue in all_issues:
            if getattr(issue.fields, "assignee", None):
                people.add(issue.fields.assignee.displayName)
            for worklog in jira_client.worklogs(issue.id):
                started_at = worklog.started[:10]
                if start_date <= started_at <= end_date:
                    author_name = worklog.author.displayName
                    people.add(author_name)
                    log_rows.append((author_name, started_at, worklog.timeSpentSeconds / 3600))
        date_range = pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()
        if not log_rows:
            if people:
                pd.DataFrame(index=sorted(list(people)), columns=date_range).fillna(0).astype(int).to_csv(output_path)
                return output_path
            pd.DataFrame(columns=date_range).to_csv(output_path)
            return output_path
        df = pd.DataFrame(log_rows, columns=["author", "date", "hours"])
        pivot = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0).reindex(index=sorted(list(people)), columns=date_range, fill_value=0).round(0).astype(int)
        pivot.to_csv(output_path)
        return output_path
    except Exception as e:
        raise Exception(f"jira config exception: {str(e)}")

#utils & converters

def func_folder_reset(folder_path: str) -> str:
    """Purge all files and subdirectories within a specified directory."""
    import os, shutil
    absolute_path = folder_path if os.path.isabs(folder_path) else os.path.join(os.getcwd(), folder_path)
    if not os.path.isdir(absolute_path):
        return "folder not found"
    for item in os.listdir(absolute_path):
        item_path = os.path.join(absolute_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    return "folder reset done"

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
        regex_pattern = param[5] if len(param) > 5 else None
        custom_error = param[6] if len(param) > 6 else None
        if data_type not in TYPE_MAP and not data_type.startswith("list:"):
            raise Exception(f"parameter '{key}' has invalid data_type '{data_type}'")
        if is_mandatory == 1 and default_value is not None:
            raise Exception(f"parameter '{key}' is mandatory, default_value must be None")
        if default_value is not None and allowed_values and default_value not in allowed_values:
            raise Exception(f"parameter '{key}' default '{default_value}' violating allowed_values: {allowed_values}")
        if allowed_values is not None and not isinstance(allowed_values, (list, tuple)):
            raise Exception(f"parameter '{key}' allowed_values must be a list or tuple")
        if is_mandatory and key not in params_dict:
            raise Exception(f"parameter '{key}' missing")
        val = params_dict.get(key)
        if val is None:
            val = header_params.get(key.lower())
        if val is None:
            val = default_value
        if isinstance(val, str) and val.lower() in ("null", "undefined"):
            val = default_value
        if is_mandatory:
            if val is None:
                raise Exception(f"parameter '{key}' missing")
            if isinstance(val, str) and not val.strip():
                raise Exception(f"parameter '{key}' cannot be empty")
        if val is not None:
            try:
                if data_type.startswith("list:") and ":" in data_type:
                    inner_type = data_type.split(":")[1]
                    val_list = TYPE_MAP["list"](val)
                    val = [TYPE_MAP[inner_type](x) for x in val_list]
                else:
                    val = TYPE_MAP[data_type](val)
            except Exception:
                raise Exception(f"parameter '{key}' invalid type {data_type}")
        if val is not None and allowed_values and val not in allowed_values:
            raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        if val is not None and regex_pattern:
            import re
            if not re.match(regex_pattern, str(val)):
                raise Exception(custom_error if custom_error else f"parameter '{key}' format invalid")
        output_dict[key] = val
    return output_dict

def func_converter_number(data_type: str, process_mode: str, value: any) -> any:
    """Encode strings into specific-size integers or decode them back using a custom charset."""
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}
    charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"
    if data_type not in type_limits:
        raise ValueError(f"invalid data type: {data_type}, allowed: {list(type_limits.keys())}")
    base = len(charset)
    max_len = type_limits[data_type]
    if process_mode == "encode":
        val_str = str(value)
        val_len = len(val_str)
        if val_len > max_len:
            raise ValueError(f"input too long {val_len} > {max_len}")
        result_num = val_len
        for char in val_str:
            char_idx = charset.find(char)
            if char_idx == -1:
                raise ValueError("invalid character in input")
            result_num = result_num * base + char_idx
        return result_num
    if process_mode == "decode":
        try:
            num_val = int(value)
        except Exception:
            raise ValueError("invalid integer for decoding")
        decoded_chars = []
        while num_val > 0:
            num_val, reminder = divmod(num_val, base)
            decoded_chars.append(charset[reminder])
        return "".join(decoded_chars[::-1][1:]) if decoded_chars else ""
        


# celery init moved to consumer.py

# notify moved to consumer.py

