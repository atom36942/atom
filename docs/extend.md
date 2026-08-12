# 🧩 Extending Atom

Atom is opinionated but not closed. You extend it **without editing core files**, so you can pull framework updates (via `sync.py`) at any time without losing your work.

## The Golden Rule

Core files — `main.py`, `function.py`, `config.py`, and the shipped routers — are **overwritten by `sync.py`** on update. Put all your customizations in the drop-in extension files instead:

| Your file | Purpose | Survives `sync.py`? |
|-----------|---------|---------------------|
| `config_extend.py` | Override / add any config value | ✅ yes |
| `function_extend.py` | Override / add any function | ✅ yes |
| `router/<your>.py` | Add new API endpoints | ✅ yes |
| `.env` | Secrets & connection strings | ✅ yes |

Both extension modules are auto-loaded at import time in `main.py`:

```python
if importlib.util.find_spec("function_extend"): from function_extend import *
if importlib.util.find_spec("config_extend"): from config_extend import *
```

Because they're imported **after** the core modules with `import *`, anything they define with the same name **wins** (last import overrides). They're also git-ignored/kept out of the sync list, so updates never touch them.

## 1. Override or add config

Create `config_extend.py` in the project root. Any name you define replaces the core value; new names are simply added.

```python
# config_extend.py

# turn features on/off
config_is_signup = False
config_is_debug = False

# enable an integration just by setting its config
config_openai_key = "sk-..."

# extend a config map — import the base and merge
from config import config_api
config_api = {
    **config_api,
    "/custom/hello": {"id": 200, "is_token": False},
}
```

> Registering a route in `config_api` is what the middleware uses to enforce auth, roles, rate limits, and caching for that path. A route with no entry defaults to open/no-token.

## 2. Override or add logic

Create `function_extend.py`. Define a new function, or redefine an existing `func_*` to change core behavior.

```python
# function_extend.py

# add a new helper
async def func_my_business_logic(*, client_postgres, payload):
    ...
    return result

# override a shipped function (same name wins)
async def func_token_encode(*, user, config_token_secret_key, expiry_sec):
    ...  # your custom token logic
```

Everything set on `app.state` (all `func_*` and `config_*` names) is available to routers as `request.app.state.func_...` — so your new functions are reachable from endpoints just like core ones.

## 3. Add new API endpoints

Drop a `.py` file into `router/`. It's auto-discovered and mounted by `func_app_router_add` — the only requirement is a module-level `router = APIRouter()`.

```python
# router/custom.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/custom/hello")
async def func_api_custom_hello(*, request: Request):
    app_state = request.app.state
    res = await app_state.func_my_helper(user_id=1)
    return {"status": 1, "message": res}
```

Load order is controlled by `router_order` in `main.py` (files not listed load after the known tiers, alphabetically). Add the path to `config_api` (step 1) if it needs auth, rate-limiting, or caching.

## 4. Add or change database tables

Tables are declared as data in `config.py` under `config_postgres["table"]` and created automatically on startup when `config_is_postgres_schema_init = True`. To add your own table without editing `config.py`, extend the structure in `config_extend.py`:

```python
# config_extend.py
from config import config_postgres

config_postgres["table"]["product"] = [
    {"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True},
    {"name": "created_at", "datatype": "timestamptz", "default": "now()", "index": "btree(created_at)"},
    {"name": "created_by_id", "datatype": "bigint"},
    {"name": "title", "datatype": "text", "is_mandatory": True, "index": "gin_trgm(title)"},
    {"name": "price", "datatype": "numeric(10,2)"},
]
```

Column specs support `is_primary`, `is_mandatory`, `default`, `unique`, `check`, `regex`, `index` (btree / gin / gist / gin_trgm), array types, PostGIS geography, and `old` (for renames). Once a table has a `created_by_id` column it works with the generic `object-create` / `object-read` ownership flow out of the box.

## 5. Add background workers

New standalone processes go in `script/` and are run as separate processes (they're not part of the API). Use them for queue consumers or batch jobs; they read the same `config.py` and can import from `function.py` / `function_extend.py`.

## Updating the framework

When new Atom versions ship, pull the latest core files with `sync.py`:

```bash
venv/bin/python sync.py
```

It runs `git fetch` against the upstream repo and checks out the framework files (`main.py`, `function.py`, `config.py`, routers, `static/api.html`, `Dockerfile`, …). Your `config_extend.py`, `function_extend.py`, custom `router/` files, and `.env` are **not** in the sync list, so they're preserved. Re-run the dependency install if `requirements.txt` changed:

```bash
venv/bin/pip install -r requirements.txt
```

## Summary

| Goal | Do this |
|------|---------|
| Change a setting | Set it in `config_extend.py` |
| Change core behavior | Redefine the `func_*` in `function_extend.py` |
| Add an endpoint | New file in `router/` + entry in `config_api` |
| Add a table | Extend `config_postgres["table"]` in `config_extend.py` |
| Add a worker | New script in `script/` |
| Enable a service | Set its `config_*_url` / key (in `.env` or `config_extend.py`) |
| Update Atom | `python sync.py` — extensions are preserved |

---

📚 [Back to README](../readme.md)
