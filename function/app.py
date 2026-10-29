# import
import ast
import functools
import importlib.util
import inspect
import os
import pathlib
import re
import shutil
import urllib.parse
from decimal import Decimal
from typing import Any
import orjson
from fastapi import FastAPI
from fastapi.encoders import decimal_encoder
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.routing import iter_route_contexts
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import State
from starlette.routing import Match

# function
async def func_admin_sync(*, app_state: State, app_routes: list = None) -> str:
    """Synchronize and refresh all application state caches, schemas, OpenAPI spec, and config maps."""
    postgres_master = app_state.client_postgres_dict.get("master")
    if postgres_master:
        await app_state.func_postgres_create(client_postgres=postgres_master, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=app_state.cache_postgres_schema_dict.get("master", {}), mode="flush", table=None, obj_list=None, buffer_limit=None, buffer_postgres=app_state.buffer_postgres_create, config_column_regex=None)
    app_state.cache_postgres_schema_dict = {name: await app_state.func_postgres_schema_read(client_postgres=pool) for name, pool in app_state.client_postgres_dict.items()}
    app_state.cache_clickhouse_schema_dict = {name: await app_state.func_clickhouse_schema_read(client_clickhouse=client) for name, client in (getattr(app_state, "client_clickhouse_dict", None) or {}).items()}
    if app_routes is not None:
        app_state.cache_openapi = app_state.func_openapi_spec_generate(app_routes=app_routes, app_state=app_state)
    app_state.cache_config = await app_state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app_state.config_sql.get("config"), is_json_value=True) if postgres_master and "config" in app_state.cache_postgres_schema_dict["master"] else {}
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app_state.config_sql.get("users_role")) if postgres_master else {}
    app_state.cache_users_deactivated = await app_state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app_state.config_sql.get("users_deactivated")) if postgres_master else {}
    app_state.cache_users_deleted = await app_state.func_postgres_map_column(client_postgres=postgres_master, config_sql=app_state.config_sql.get("users_deleted")) if postgres_master else {}
    return "done"

def func_openapi_spec_generate(*, app_routes: list, app_state: State) -> dict:
    """Generate a standard OpenAPI 3.0.0 specification from FastAPI routes using source inspection."""
    config_api = getattr(app_state, "config_api", {}) or {}
    TYPE_MAP = {
        "int": "integer", "bigint": "integer", "smallint": "integer", "integer": "integer", "int4": "integer", "int8": "integer",
        "float": "number", "number": "number", "numeric": "number",
        "bool": "boolean", "dict": "object", "object": "object", "file": "string", "list": "array"
    }
    route_globals = {}    # names visible in the route's module, so param_specs imported from e.g. files_extend/ resolve too
    def plain(v):
        if isinstance(v, (list, tuple)): return all(plain(x) for x in v)
        if isinstance(v, dict): return all(isinstance(k, str) and plain(x) for k, x in v.items())
        return v is None or isinstance(v, (str, int, float, bool))
    def eval_node(n):
        if hasattr(ast, "Constant") and isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.Name) and n.id in route_globals and plain(route_globals[n.id]): return route_globals[n.id]
        if hasattr(ast, "Str") and isinstance(n, ast.Str): return n.s
        if hasattr(ast, "Num") and isinstance(n, ast.Num): return n.n
        if hasattr(ast, "NameConstant") and isinstance(n, ast.NameConstant): return n.value
        if isinstance(n, (ast.List, ast.Tuple)): return [eval_node(e) for e in n.elts]
        if isinstance(n, ast.Dict): return {eval_node(k): eval_node(v) for k, v in zip(n.keys, n.values, strict=True)}
        if isinstance(n, ast.Attribute) and hasattr(n.value, "id") and n.value.id == "app_state" and app_state: return getattr(app_state, n.attr, None)
        if isinstance(n, ast.IfExp): return eval_node(n.body) if eval_node(n.test) else eval_node(n.orelse)
        if isinstance(n, ast.Compare):
            left = eval_node(n.left)
            for op, r_node in zip(n.ops, n.comparators, strict=True):
                right = eval_node(r_node)
                if isinstance(op, ast.NotEq) and left == right: return False
                if isinstance(op, ast.Eq) and left != right: return False
                if isinstance(op, ast.In) and not (left in right): return False
                if isinstance(op, ast.NotIn) and not (left not in right): return False
            return True
        if isinstance(n, ast.ListComp) and len(n.generators) == 1:
            gen = n.generators[0]
            items = eval_node(gen.iter)
            if items is None or not isinstance(items, list): return None
            if not gen.ifs: return items
            if len(gen.ifs) == 1 and isinstance(gen.ifs[0], ast.Compare):
                comp = gen.ifs[0]
                if isinstance(comp.left, ast.Name) and comp.left.id == gen.target.id:
                    if len(comp.ops) == 1 and len(comp.comparators) == 1:
                        other = eval_node(comp.comparators[0])
                        if other is not None and isinstance(other, (list, tuple, set)):
                            if isinstance(comp.ops[0], ast.NotIn): return [it for it in items if it not in other]
                            if isinstance(comp.ops[0], ast.In): return [it for it in items if it in other]
            return items
        if isinstance(n, ast.BoolOp):
            vals = [eval_node(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            l, r = eval_node(n.left), eval_node(n.right)
            if l is not None and r is not None: return l + r
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "list" and len(n.args) > 0:
            v = eval_node(n.args[0])
            if v is not None: return list(v)
        return None
    def ast_to_schema(n):
        if isinstance(n, ast.Dict):
            return {"type": "object", "properties": {eval_node(k): ast_to_schema(v) for k, v in zip(n.keys, n.values, strict=True) if eval_node(k)}}
        if isinstance(n, (ast.List, ast.Tuple)):
            return {"type": "array", "items": ast_to_schema(n.elts[0]) if n.elts else {"type": "string"}}
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            s1, s2 = ast_to_schema(n.left), ast_to_schema(n.right)
            return {"type": "object", "properties": {**(s1.get("properties", {})), **(s2.get("properties", {}))}}
        v = eval_node(n)
        if isinstance(v, (int, float, bool)): return {"type": "integer" if isinstance(v, int) else "number" if isinstance(v, float) else "boolean", "default": v}
        if isinstance(v, list): return {"type": "array", "items": {"type": "string"}}
        if isinstance(v, dict): return {"type": "object", "properties": {k: {"type": "string", "default": str(val)} for k, val in v.items()}}
        return {"type": "string", "default": str(v) if v is not None else None}
    def spec_schema(p, reg_info):
        dt = p.get("type", "str")
        schema = {"type": TYPE_MAP.get(dt.split(":")[0], "string"), "format": "binary" if dt == "file" else None, "default": p.get("default"), "pattern": reg_info[0] if reg_info and len(reg_info) > 0 else None}
        if ":" in dt: schema["items"] = {"type": TYPE_MAP.get(dt.split(":")[1], "string")}
        if isinstance(p.get("allowed"), (list, tuple)): schema["enum"] = list(p["allowed"])
        is_array = schema["type"] == "array"
        bounds = {"minimum": "minimum", "maximum": "maximum", "min_length": "minItems" if is_array else "minLength", "max_length": "maxItems" if is_array else "maxLength"}
        for key, name in bounds.items():
            if p.get(key) is not None: schema[name] = p[key]
        return {k: v for k, v in schema.items() if v is not None}
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "API Documentation", "version": "1.0.0"},
        "paths": {},
        "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}}
    }
    for route in app_routes:
        if not hasattr(route, "path") or not hasattr(route, "endpoint"): continue
        path = route.path
        if path not in spec["paths"]: spec["paths"][path] = {}
        methods = list(getattr(route, "methods", [])) or (["WS"] if "WebSocket" in type(route).__name__ else [])
        for method in methods:
            m_lower = method.lower()
            tag = path.split("/")[1] if len(path.split("/")) > 1 and path.split("/")[1] else "system"
            op = {"tags": [tag], "parameters": [], "responses": {"200": {"description": "Successful Response"}}}
            api_cfg = config_api.get(path, {})
            connection_param = {"name": "connection", "in": "query", "required": False, "description": "connection name from config_postgres_url_<name>; default master", "schema": {"type": "string", "default": "master"}}
            is_token_required = api_cfg.get("is_token", False) is True
            op["x-auth-required"] = is_token_required
            op["x-roles-allowed"] = api_cfg.get("user_check_role", None)
            op["x-check-deactivated"] = "user_check_deactivated" in api_cfg
            op["x-check-deleted"] = "user_check_deleted" in api_cfg
            op["x-cache"] = api_cfg.get("api_cache_sec", None)
            op["x-rate-limit"] = api_cfg.get("api_ratelimiting_times_sec", None)
            if is_token_required:
                op["security"] = [{"BearerAuth": []}]
                op["parameters"].append({"name": "Authorization", "in": "header", "required": True, "schema": {"type": "string", "default": "Bearer {token}"}})
            if api_cfg.get("is_connection_param"): op["parameters"].append(connection_param)
            for p in re.findall(r"\{(\w+)\}", path):
                op["parameters"].append({"name": p, "in": "path", "required": True, "schema": {"type": "string"}})
            try:
                sig = inspect.signature(route.endpoint)
                for name, par in sig.parameters.items():
                    p_type = par.annotation.__name__ if hasattr(par.annotation, "__name__") else str(par.annotation)
                    if name in ["request", "websocket", "req"] or any(x in p_type for x in ["Request", "Response", "WebSocket", "BackgroundTasks"]): continue
                    if any(x["name"] == name for x in op["parameters"]): continue
                    op["parameters"].append({"name": name, "in": "query", "required": par.default == inspect.Parameter.empty, "schema": {"type": "integer" if p_type == "int" else "string", "default": None if par.default == inspect.Parameter.empty else par.default}})
                route_globals = inspect.unwrap(route.endpoint).__globals__
                source = inspect.getsource(route.endpoint)
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Return):
                        try: op["responses"]["200"]["content"] = {"application/json": {"schema": ast_to_schema(node.value)}}
                        except Exception as e: print(f"⚠️ openapi {path}: response schema skipped: {e}")
                    if not isinstance(node, ast.Call): continue
                    func_id = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    if func_id == "func_extract_request_object_list":
                        body = op.setdefault("requestBody", {})
                        body["required"] = True
                        body["description"] = "A single record object, or an object with an obj_list array for batch operations. Record fields depend on the selected table."
                        content = body.setdefault("content", {})
                        json_body = content.setdefault("application/json", {})
                        schema = json_body.setdefault("schema", {"type": "object", "properties": {}, "required": []})
                        schema["additionalProperties"] = True
                        continue
                    if func_id != "func_request_param_read": continue
                    is_regex_enabled = any(isinstance(n, ast.Call) and (getattr(n.func, "id", None) == "func_regex_check" or getattr(n.func, "attr", None) == "func_regex_check") for n in ast.walk(tree))
                    try:
                        p_loc, p_list = None, None
                        for kw in node.keywords:
                            if kw.arg == "mode": p_loc = eval_node(kw.value)
                            elif kw.arg == "param_specs": p_list = eval_node(kw.value)
                        if p_loc is None and len(node.args) > 1: p_loc = eval_node(node.args[1])
                        if p_list is None and len(node.args) > 2: p_list = eval_node(node.args[2])
                        if p_list is not None and p_loc in ["header", "query"]:
                            for p in p_list:
                                if not isinstance(p, dict) or "name" not in p: continue
                                p_name = p["name"]
                                op["parameters"] = [x for x in op["parameters"] if x["name"] != p_name]
                                reg_info = getattr(app_state, "config_column_regex", {}).get(p_name) if is_regex_enabled else None
                                op["parameters"].append({
                                    "name": p_name, "in": p_loc, "required": bool(p.get("required", False)),
                                    **({"description": reg_info[1]} if reg_info and len(reg_info) > 1 else {}),
                                    "schema": spec_schema(p, reg_info)
                                })
                        elif p_list is not None and p_loc in ["body", "form"]:
                            media_type = "application/json" if p_loc == "body" else "multipart/form-data"
                            if "requestBody" not in op: op["requestBody"] = {"content": {media_type: {"schema": {"type": "object", "properties": {}, "required": []}}}}
                            props, reqs = op["requestBody"]["content"][media_type]["schema"]["properties"], op["requestBody"]["content"][media_type]["schema"]["required"]
                            if any(kw.arg == "reject_unknown" and eval_node(kw.value) is True for kw in node.keywords): op["requestBody"]["content"][media_type]["schema"]["additionalProperties"] = False
                            for p in p_list:
                                if not isinstance(p, dict) or "name" not in p: continue
                                p_name = p["name"]
                                reg_info = getattr(app_state, "config_column_regex", {}).get(p_name) if is_regex_enabled else None
                                props[p_name] = {**spec_schema(p, reg_info), **({"description": reg_info[1]} if reg_info and len(reg_info) > 1 else {})}
                                if bool(p.get("required", False)): reqs.append(p_name)
                    except Exception as e: print(f"⚠️ openapi {path}: parameters skipped: {e}")
            except Exception as e: print(f"⚠️ openapi {path}: route skipped: {e}")
            # the middleware picks master when ?connection= is left out; a route's own spec for the param must not hide that
            if api_cfg.get("is_connection_param"): op["parameters"] = [x for x in op["parameters"] if x["name"] != "connection"] + [connection_param]
            spec["paths"][path][m_lower] = op
    return spec

def func_app_route_list(*, app: FastAPI) -> list:
    """Every route the app serves. FastAPI 0.137+ keeps each included router as one nested entry in app.routes, so flatten them.

    Atom includes routers without an extra prefix, so each original route's path is the full request path.
    """
    return [context.original_route for context in iter_route_contexts(app.routes)]

def _response_json_default(value: Any) -> Any:
    """orjson fallback: Decimal as FastAPI writes it (int when whole, else float), anything else through jsonable_encoder."""
    return decimal_encoder(value) if isinstance(value, Decimal) else jsonable_encoder(value)

def func_response_json(*, content: Any, status_code: int = 200) -> Response:
    """Encode a route's return value with orjson, matching FastAPI's default JSON output.

    orjson writes dates itself (same ISO text as FastAPI, without a Python call per value); Decimal and types orjson lacks, plus dataclasses, go through _response_json_default.
    Anything orjson still refuses (e.g. integers above 64 bits) falls back to FastAPI's own encoding.
    """
    try: body = orjson.dumps(content, default=_response_json_default, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_PASSTHROUGH_DATACLASS)
    except (TypeError, orjson.JSONEncodeError): return JSONResponse(content=jsonable_encoder(content), status_code=status_code)
    return Response(content=body, status_code=status_code, media_type="application/json")

def func_endpoint_json_wrap(*, endpoint: Any, status_code: int | None) -> Any:
    """Wrap a route so a returned dict or list is encoded by func_response_json; FastAPI skips its slower encoding for a returned Response."""
    if getattr(endpoint, "__atom_json_wrapped__", False): return endpoint
    def to_response(result):
        return result if isinstance(result, Response) else func_response_json(content=result, status_code=status_code or 200)
    if inspect.iscoroutinefunction(endpoint):
        @functools.wraps(endpoint)
        async def wrapper(*args, **kwargs): return to_response(await endpoint(*args, **kwargs))
    else:
        @functools.wraps(endpoint)
        def wrapper(*args, **kwargs): return to_response(endpoint(*args, **kwargs))
    wrapper.__atom_json_wrapped__ = True
    return wrapper

def func_app_router_add(*, app: FastAPI, router_dir: Any, router_order: dict) -> None:
    """Load core routers in configured order, then optional sibling router_extend modules."""
    router_dir = pathlib.Path(router_dir)
    directories = [(router_dir, router_order)]
    if router_dir.name == "router":
        directories.append((router_dir.with_name("router_extend"), {}))
    for directory, order in directories:
        router_paths = sorted(directory.glob("*.py"), key=lambda path: (order.get(path.stem, 100), path.stem))
        for router_path in router_paths:
            if router_path.name.startswith(("_", ".")): continue
            spec = importlib.util.spec_from_file_location(f"{directory.name}.{router_path.stem}", router_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not hasattr(module, "router"): continue
            for route in module.router.routes:
                if isinstance(route, APIRoute) and route.response_model is None: route.endpoint = func_endpoint_json_wrap(endpoint=route.endpoint, status_code=route.status_code)
            app.include_router(module.router)
    return

def func_sentry_init(*, config_sentry_dsn: str, config_sentry_traces_sample_rate: float = 0.05):
    """Initialize Sentry SDK monitoring if DSN is configured: every error is sent; config_sentry_traces_sample_rate of requests are traced (and profiled)."""
    if not config_sentry_dsn: return None
    if isinstance(config_sentry_traces_sample_rate, bool) or not isinstance(config_sentry_traces_sample_rate, (int, float)) or not 0 <= config_sentry_traces_sample_rate <= 1: raise Exception("config_sentry_traces_sample_rate must be a number from 0 to 1")
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    return sentry_sdk.init(dsn=config_sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=config_sentry_traces_sample_rate, profiles_sample_rate=1.0, send_default_pii=False)

async def func_app_extend_run(*, app_state: State, name: str) -> Any:
    """Call the project's optional func_extend or func_extend_shutdown (function_extend/) with app_state; sync or async; None when not defined."""
    extend_function = getattr(app_state, name, None)
    if extend_function is None: return None
    result = extend_function(app_state=app_state)
    return await result if inspect.isawaitable(result) else result

def func_app_static_add(*, app: FastAPI, path: str = "/static", directories: tuple = ("static", "static_extend")) -> None:
    """Serve Atom's static/ and the project's static_extend/ at one path; a file in both, or two pages with one name (<name>.html and <name>/index.html), stops startup. Names compare ignoring case (one project behaves the same on Linux, macOS and Windows); hidden files such as .DS_Store are ignored."""
    existing, owner = [d for d in directories if os.path.isdir(d)], {}
    for directory in existing:
        for parent, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.startswith(".") or filename.lower() in ("thumbs.db", "desktop.ini"): continue    # OS files (.DS_Store, Thumbs.db) appear in any folder and are not the project's
                name = os.path.relpath(os.path.join(parent, filename), directory)
                if name.lower() in owner: raise Exception(f"{directory}/{name} clashes with {owner[name.lower()]}")
                owner[name.lower()] = f"{directory}/{name}"
    pages = {}
    for page in func_app_static_page_list(directories=directories):
        if page["url"].lower() in pages: raise Exception(f"{page['path']} clashes with {pages[page['url'].lower()]}: both are {page['url'].lower()}")
        pages[page["url"].lower()] = page["path"]
    static_files = StaticFiles(directory=directories[0], check_dir=False)
    static_files.all_directories = existing
    async def static_no_cache(scope, receive, send):
        # Revalidate every load (a 304 when unchanged), so a deploy never leaves a page running old and new files together.
        async def send_with_header(message):
            if message["type"] == "http.response.start": message["headers"] = [*message.get("headers", []), (b"cache-control", b"no-cache")]
            await send(message)
        await static_files(scope, receive, send_with_header)
    app.mount(path, static_no_cache, name="static")

def func_app_static_page_list(*, directories: tuple = ("static", "static_extend")) -> list:
    """Every page, home page included: each top-level <name>.html and <name>/index.html in static/ or static_extend/, whatever the name; other files are skipped. Each opens at /page/<name>.

    Each is {"name" (the file name without .html, or the folder name, first letter capital and the rest lowercase), "url", "folder" (the directory it is in), "path" (the file served)}, sorted by name.
    """
    pages = []
    for directory in directories:
        if not os.path.isdir(directory): continue
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.endswith(".html"): name, path = entry.name.removesuffix(".html"), entry.path
            elif entry.is_dir() and os.path.isfile(os.path.join(entry.path, "index.html")): name, path = entry.name, os.path.join(entry.path, "index.html")
            else: continue
            pages.append({"name": name.capitalize(), "url": f"/page/{urllib.parse.quote(name, safe='')}", "folder": os.path.basename(os.path.normpath(directory)), "path": path})
    return sorted(pages, key=lambda page: page["name"])

def func_app_static_page_path(*, name: str, directories: tuple = ("static", "static_extend")) -> str | None:
    """The file GET /page/{name} serves: the listed page at /page/<name>, so /page and the home page share one rule; None for any other name. Only scanned files are served, so no name reaches outside the two folders."""
    return next((page["path"] for page in func_app_static_page_list(directories=directories) if page["url"] == f"/page/{urllib.parse.quote(name or '', safe='')}"), None)

def func_app_cors_add(*, app: FastAPI, allow_origins: list = None, allow_origin_regex: str = None, allow_methods: list = None, allow_headers: list = None, expose_headers: list = None, allow_credentials: bool = True) -> None:
    """Configure CORS middleware on FastAPI application if origins are provided."""
    if not allow_origins and not allow_origin_regex: return
    app.add_middleware(CORSMiddleware, allow_origins=allow_origins or [], allow_origin_regex=allow_origin_regex, allow_methods=allow_methods or ["*"], allow_headers=allow_headers or ["*"], expose_headers=expose_headers or ["*"], allow_credentials=allow_credentials)

def func_app_fastapi_create(*, config_is_prod: bool = True, lifespan: Any = None, config_is_fastapi_telemetry: bool = False):
    """Create the FastAPI app; FastAPI's native OpenTelemetry stays off unless config_is_fastapi_telemetry, so requests skip its per-request provider lookup.

    When on, exporters are also set up from the OTEL_* environment variables (opt-in since FastAPI 0.143)."""
    telemetry = {"auto_configure": True} if config_is_fastapi_telemetry else {"tracing": False, "metrics": False, "logs": False}
    return FastAPI(debug=not config_is_prod, lifespan=lifespan, openapi_url=None, docs_url=None, redoc_url=None, telemetry=telemetry)

def func_atom_version(*, path: str = "sync.py") -> str | None:
    """Atom's version: ATOM_VERSION in the project's sync.py (the file sync updates), or None when it is missing or from before versions."""
    try: match = re.search(r'^ATOM_VERSION = "([^"]+)"$', pathlib.Path(path).read_text(), re.MULTILINE)
    except OSError: return None
    return match[1] if match else None

def func_structure_init(*, dir_list: tuple = ("tmp", "secret"), is_tmp_reset: bool = True) -> None:
    """Optionally reset working tmp/ directory and ensure required application directories exist."""
    if is_tmp_reset:
        if os.path.isdir("tmp") and not os.path.islink("tmp"): shutil.rmtree("tmp")
        elif os.path.exists("tmp"): os.remove("tmp")
    for d in dir_list: os.makedirs(d, exist_ok=True)

def func_app_state_add(*, app: FastAPI, data_dict: dict, prefixes: tuple) -> None:
    """Bulk register objects matching specific key prefixes onto app.state."""
    for k, v in data_dict.items():
        if k.startswith(prefixes):
            setattr(app.state, k, v)

def func_app_route_lookup_add(*, app: FastAPI) -> int:
    """Find fixed-path HTTP routes with one dict lookup instead of FastAPI checking every route in order.

    Only (method, path) pairs that FastAPI's own matching resolves to the same route at startup go in the table; anything else
    (static files, websockets, path parameters, 404, 405) runs FastAPI's normal matching. Returns the number of entries.
    """
    try:
        from fastapi.routing import _FASTAPI_EFFECTIVE_ROUTE_CONTEXT_KEY
        from fastapi.routing import _FASTAPI_INCLUDED_ROUTER_KEY
        from fastapi.routing import _IncludedRouter
        from fastapi.routing import _get_fastapi_scope
    except ImportError: return 0    # FastAPI internals moved: keep normal matching
    router = app.router
    if router.middleware_stack != router.app: return 0    # router-level middleware present: keep normal matching
    def normal_match(method, path):
        scope = {"type": "http", "method": method, "path": path, "root_path": "", "app": app, "headers": [], "query_string": b""}
        for top in router.routes:
            match, _ = top.matches(scope)
            if match == Match.FULL: return top, (top._match(scope)[3] if isinstance(top, _IncludedRouter) else None)
        return None, None
    table = {}
    for top in router.routes:
        if not isinstance(top, _IncludedRouter): continue
        for context in top.effective_candidates():
            route = getattr(context, "original_route", None)
            if not isinstance(route, APIRoute) or route.param_convertors or context.starlette_route is not None: continue
            for method in route.methods:
                key = (method, route.path)
                if key in table: continue
                winner, winner_context = normal_match(method, route.path)
                if winner is top and winner_context is context: table[key] = (top, context, route)
    normal_app = router.middleware_stack
    async def lookup_app(scope, receive, send):
        entry = table.get((scope.get("method"), scope.get("path"))) if scope["type"] == "http" and not scope.get("root_path") else None
        if entry is None: return await normal_app(scope, receive, send)
        top, context, route = entry
        match, child_scope = route.matches(scope)
        if match != Match.FULL: return await normal_app(scope, receive, send)
        if "router" not in scope: scope["router"] = router
        scope.update(child_scope)
        fastapi_scope = _get_fastapi_scope(scope)
        fastapi_scope[_FASTAPI_INCLUDED_ROUTER_KEY] = top
        fastapi_scope[_FASTAPI_EFFECTIVE_ROUTE_CONTEXT_KEY] = context
        scope["route"] = route
        await route.handle(scope, receive, send)
    router.middleware_stack = lookup_app
    return len(table)
