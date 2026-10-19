# import
import contextlib
import os
import orjson
from dotenv import load_dotenv

# function
def func_config_load_env(*, global_dict: dict) -> None:
    """Override config_* values in global_dict from .env and the environment; config_postgres_url_<name>, config_redis_url_<name>, config_clickhouse_url_<name>, and config_mssql_url_<name> fill the matching *_url_dict."""
    load_dotenv(".env")
    env = {k.lower(): v for k, v in os.environ.items()}
    env.update({k: v for k, v in os.environ.items() if k == k.lower()})
    for k, v in list(global_dict.items()):
        if k.startswith("config_") and (ev := env.get(k)) is not None:
            if isinstance(v, bool):
                bool_value = ev.strip().lower()
                if bool_value in ("true", "1", "yes", "on", "ok"):
                    global_dict[k] = True
                elif bool_value in ("false", "0", "no", "off"):
                    global_dict[k] = False
                else:
                    raise ValueError(f"invalid boolean value for {k}: {ev!r}; expected true or false")
            elif isinstance(v, (list, tuple, dict)):
                with contextlib.suppress(Exception): global_dict[k] = orjson.loads(ev)
            else: global_dict[k] = int(ev) if ev.lstrip("-").isdigit() else ev
            if isinstance(global_dict[k], list): global_dict[k] = tuple(global_dict[k])
    url_dicts = {"config_postgres_url_": "config_postgres_url_dict", "config_redis_url_": "config_redis_url_dict", "config_clickhouse_url_": "config_clickhouse_url_dict", "config_mssql_url_": "config_mssql_url_dict"}
    for k, ev in env.items():
        if k.startswith("config_") and not k.startswith(tuple(url_dicts)) and k not in global_dict:
            val = ev.strip()
            if val.lower() in ("true", "yes", "on"):
                global_dict[k] = True
            elif val.lower() in ("false", "no", "off"):
                global_dict[k] = False
            elif val.lstrip("-").isdigit():
                global_dict[k] = int(val)
            else:
                with contextlib.suppress(Exception):
                    loaded = orjson.loads(val)
                    global_dict[k] = tuple(loaded) if isinstance(loaded, list) else loaded
                if k not in global_dict:
                    global_dict[k] = ev
            if isinstance(global_dict.get(k), list):
                global_dict[k] = tuple(global_dict[k])
    for k, v in env.items():
        for prefix, dict_key in url_dicts.items():
            if k == prefix: raise ValueError(f"{prefix} needs a name, e.g. {prefix}master")
            if k.startswith(prefix) and k != dict_key:
                if not isinstance(global_dict.get(dict_key), dict):
                    global_dict[dict_key] = {}
                global_dict[dict_key][k.removeprefix(prefix)] = v
    return None
