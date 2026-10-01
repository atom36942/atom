"""Atom configuration loading from .env and environment variables."""

import contextlib
import os
import orjson
from dotenv import load_dotenv

def func_config_load_env(*, global_dict: dict) -> None:
    """Override config_* values in global_dict from .env and the environment; config_postgres_url_<name> fills config_postgres_url_dict."""
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
    postgres_url_prefix = "config_postgres_url_"
    for k, ev in env.items():
        if k.startswith("config_") and not k.startswith(postgres_url_prefix) and k not in global_dict:
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
        if k.startswith(postgres_url_prefix) and k not in (postgres_url_prefix, "config_postgres_url_dict"):
            if not isinstance(global_dict["config_postgres_url_dict"], dict):
                global_dict["config_postgres_url_dict"] = {}
            global_dict["config_postgres_url_dict"][k.removeprefix(postgres_url_prefix)] = v
    return None
