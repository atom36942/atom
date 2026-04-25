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
