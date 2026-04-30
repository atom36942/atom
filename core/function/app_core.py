def func_structure_create(*, directories: list, files: list) -> None:
    """Ensure required directory structure and files exist on startup."""
    import os
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    for file in files:
        if not os.path.exists(file):
            with open(file, "w") as f:
                pass
    return None

def func_app_read(*, func_lifespan: any) -> any:
    """Initialize a FastAPI application with debug mode and lifespan handler, disabling default OpenAPI routes."""
    from fastapi import FastAPI
    return FastAPI(debug=True, lifespan=func_lifespan, openapi_url=None, docs_url=None, redoc_url=None)

def func_app_add_cors(*, app_obj: any, config_cors_origin: list, config_cors_method: list, config_cors_headers: list, config_is_cors_allow_credentials: int) -> None:
    """Add CORS middleware to the FastAPI application."""
    from fastapi.middleware.cors import CORSMiddleware
    app_obj.add_middleware(CORSMiddleware, allow_origins=config_cors_origin, allow_methods=config_cors_method, allow_headers=config_cors_headers, allow_credentials=bool(config_is_cors_allow_credentials))
    return None

def func_app_add_prometheus(*, app_obj: any) -> None:
    """Expose Prometheus metrics for the FastAPI application."""
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app_obj).expose(app_obj)
    return None

def func_app_state_add(*, app_obj: any, dict_context: dict, prefix_list: tuple) -> None:
    """Inject configuration values into the FastAPI application state based on a prefix list."""
    for key, val in dict_context.items():
        if key.startswith(prefix_list):
            setattr(app_obj.state, key, val)
    return None

def func_app_add_sentry(*, config_sentry_dsn: str) -> None:
    """Initialize Sentry SDK for error tracking and profiling."""
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(dsn=config_sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=True)
    return None

def func_app_add_static(*, app_obj: any, folder_path: str, route_path: str) -> None:
    """Mount a static directory to the FastAPI application."""
    from fastapi.staticfiles import StaticFiles
    app_obj.mount(route_path, StaticFiles(directory=folder_path), name="static")
    return None

def func_app_add_router(*, app_obj: any) -> None:
    """Dynamically discover and include all FastAPI routers from the router directory."""
    import sys, importlib.util
    from pathlib import Path
    from fastapi import APIRouter
    root_dir = Path("./core/router").resolve()
    if not root_dir.exists():
        return None
    for py_file in root_dir.rglob("*.py"):
        if py_file.name.startswith((".", "__")):
            continue
        rel_path = py_file.relative_to(root_dir)
        module_name = "core.router." + ".".join(rel_path.with_suffix("").parts)
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            router = getattr(module, "router", None)
            if not isinstance(router, APIRouter):
                raise Exception(f"invalid router file: {py_file} (missing 'router' attribute of type APIRouter)")
            app_obj.include_router(router)

def func_config_override_from_env(*, global_dict: dict) -> None:
    """Override configuration variables starting with 'config_' from environment variables and .env file."""
    import orjson, os, ast
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
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
    return None

async def func_api_log_create(*, config_is_log_api: int, api_id: int, request: any, response: any, time_ms: int, user_id: any, func_postgres_create: callable, client_postgres_pool: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, cache_postgres_buffer: dict, config_table: dict) -> None:
    """Log API request details asynchronously if enabled in config (identifier validated)."""
    if config_is_log_api == 0 or client_postgres_pool is None:
        return None
    log_obj = {
        "created_by_id": user_id,
        "type": 1,
        "ip_address": request.client.host if request.client else None,
        "api": request.url.path,
        "api_id": api_id,
        "method": request.method,
        "query_param": str(request.query_params),
        "status_code": response.status_code if hasattr(response, "status_code") else None,
        "response_time_ms": time_ms
    }
    await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="buffer", table="log_api", obj_list=[log_obj], is_serialize=0, buffer_limit=config_table.get("log_api", {}).get("buffer", 100), cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=None)
    return None
