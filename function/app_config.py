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
async def func_api_log_create(*, config_is_log_api: int, api_id: int, request: any, response: any, time_ms: int, user_id: any, func_postgres_create: callable, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, cache_postgres_buffer: dict, config_table: dict) -> None:
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
    await func_postgres_create(client_postgres_pool=client_postgres_pool, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="buffer", table="log_api", obj_list=[log_obj], is_serialize=0, buffer_limit=config_table.get("log_api", {}).get("buffer", 100), cache_postgres_buffer=cache_postgres_buffer)
    return None
