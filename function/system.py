def func_repo_info(routes: list, schema: dict, config_postgres: dict, config_table: dict, config_api: dict) -> str:
    """Generate a summary report of the repository's configuration state, including routes, tables, and service status."""
    import os
    info = []
    info.append(f"Project: {os.path.basename(os.getcwd())}")
    info.append(f"Routes: {len(routes)}")
    info.append(f"Tables (Postgres): {len(schema)}")
    info.append(f"Configured Tables: {len(config_table)}")
    info.append(f"Configured APIs: {len(config_api)}")
    info.append(f"Postgres URL: {'Set' if config_postgres.get('dsn') else 'Not Set'}")
    return "\n".join(info)

def func_openapi_spec_generate(routes: list, config_api_roles_auth: list, app_state: any) -> dict:
    """Generate an OpenAPI 3.0.0 specification by inspecting FastAPI route signatures and configurations."""
    import inspect, orjson
    spec = {"openapi": "3.0.0", "info": {"title": "Atom API", "version": "1.0.0"}, "paths": {}, "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}}}
    for route in routes:
        if not hasattr(route, "endpoint") or not hasattr(route, "path"):
             continue
        path = route.path
        if path.startswith(("/static", "/openapi.json", "/docs", "/redoc")):
            continue
        method = "get"
        if hasattr(route, "methods"):
            method = list(route.methods)[0].lower() if route.methods else "get"
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        is_auth = any(path.startswith(prefix) for prefix in config_api_roles_auth)
        sig = inspect.signature(route.endpoint)
        params = []
        for name, param in sig.parameters.items():
            if name in ("request", "websocket", "api_function"):
                continue
            params.append({"name": name, "in": "query", "required": param.default == inspect.Parameter.empty, "schema": {"type": "string"}})
        spec["paths"][path][method] = {"parameters": params, "responses": {"200": {"description": "OK"}}, "description": route.endpoint.__doc__ or ""}
        if is_auth:
            spec["paths"][path][method]["security"] = [{"bearerAuth": []}]
    return spec

def func_check(routes: list, config_api: dict, config_api_roles: list, config_postgres: dict, config_api_roles_auth: list) -> None:
    """Startup validation: verifies role configurations, route definitions, and critical system dependencies."""
    import config
    import sys
    print("starting system check...")
    for route in routes:
        if not hasattr(route, "path"):
            continue
        path = route.path
        if any(path.startswith(p) for p in config_api_roles_auth) and path not in config_api:
            print(f"Warning: {path} is in auth zone but has no entry in config_api")
    if not config_postgres.get("dsn") and "client_postgres_pool" in dir(config):
        print("Error: Postgres DSN not configured")
    print("system check completed successfully")
