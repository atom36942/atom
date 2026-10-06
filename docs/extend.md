# 🧩 Extending Atom

Atom is opinionated but not closed. You extend it **without editing core files**, so you can pull framework updates (via `sync.py`) at any time without losing your work.

## The Golden Rule

Atom owns all contents of `docs/`, `router/`, and `function/`, plus `config.py` and selected core files. Sync replaces these folders completely, removing local-only files even on the first run. Keep your work in separate extension paths:

| Atom path | Developer path | Purpose |
|-----------|----------------|---------|
| `config.py` | `config_extend.py` | Configuration overrides |
| `router/` | `router_extend/` | Custom API endpoints |
| `function/` | `function_extend/` | Custom `func_*` business logic |
| Two selected `script/consumer_postgres_*.py` files | `script_extend/` | Standalone workers and jobs |
| `docs/` | `docs_extend/` | Project documentation |

Only `script/consumer_postgres_create.py` and `script/consumer_postgres_update.py` are synced in `script/`; other scripts are left untouched. Keep new custom workers in `script_extend/` for a clear separation.

Create only the extension paths you need. Sync never creates or modifies them. `.env` is also preserved.

Configuration extensions are loaded after the defaults in `main.py`:

```python
config_modules = [config] + ([importlib.import_module("config_extend")] if importlib.util.find_spec("config_extend") else [])
config_values = {key: value for module in config_modules for key, value in vars(module).items() if key.startswith("config_")}
```

`config_extend.py` is read after `config.py`, so its `config_*` values override the defaults. Only `config_*` names are taken from it: functions defined there are ignored, so they cannot replace core functions. It is kept out of the sync list. The `function` package discovers both Atom functions and modules directly inside the optional `function_extend/` folder; no `__init__.py` is required there.

## Complete flow: config → router → function

For a custom endpoint, create these three files in order. This example adds `GET /custom/hello`, which returns a greeting. Finish all three steps before restarting Atom.

## 1. Add `config_extend.py`

Create this optional file in the project root. Merge the default route configuration so existing endpoints keep their policies:

```python
# config_extend.py
from config import config_api as base_config_api

config_custom_greeting = "Hello"
config_api = {
    **base_config_api,
    "/custom/hello": {"id": 200, "is_token": False},
}
```

Choose an unused API ID. The `config_api` entry defines the endpoint's auth, roles, rate limits, and caching; it does not create the endpoint. This example is public. Set `is_token` to `True` for a route that requires a token, and configure role checks as needed. A route without a policy entry defaults to no token requirement.

Only `config_*` names from this file are loaded. They override defaults from `config.py` and are available through `request.app.state`. Use `.env` for secrets and connection strings; see the [configuration guide](config.md).

## 2. Add the router file

Create a uniquely named Python file directly in `router_extend/`, with a module-level `router = APIRouter()`:

```python
# router_extend/custom_greeting.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/custom/hello")
async def func_api_custom_hello(*, request: Request):
    app_state = request.app.state
    name = request.query_params.get("name", "World")
    message = await app_state.func_custom_greeting(
        name=name,
        greeting=app_state.config_custom_greeting,
    )
    return {"status": 1, "message": message}
```

Use the same path in the router and `config_api`. Keep request handling in the router and business logic in `function_extend/`. Atom discovers router files automatically; no edits to `main.py` are needed. Files beginning with `_` or `.` are skipped. Extension routers load alphabetically after all core routers. Keep route paths unique; extensions do not replace existing core routes.

## 3. Add the function file

Create a uniquely named Python file directly in `function_extend/`:

```python
# function_extend/custom_greeting.py
async def func_custom_greeting(*, name: str, greeting: str):
    return f"{greeting}, {name}!"
```

Atom automatically exports functions defined in these modules whose names start with `func_`, then registers them on `app.state`. The router calls `request.app.state.func_custom_greeting`; no edits to `function/__init__.py` are needed.

The loader imports modules alphabetically. Files beginning with `_` and nested packages are not auto-loaded. Imported helpers are not exported a second time. Duplicate function names defined in different modules stop startup with an error naming both files, so use unique `func_*` names.

Inside a function module, import shared helpers from their defining module (for example, `from function.request import func_query_bool_parse`), rather than from `function`, whose exports are still being assembled during loading. Keep module dependencies acyclic.

### Restart and verify

Restart Atom after creating the three files:

```bash
venv/bin/uvicorn main:app --reload
```

Call the endpoint:

```bash
curl "http://localhost:8000/custom/hello?name=Atom"
```

Expected response:

```json
{"status": 1, "message": "Hello, Atom!"}
```

At runtime, Atom loads configuration and functions onto `app.state`, mounts the router, applies the route policy to the request, and runs the router handler. The handler reads the request, calls the business function, and returns the response. You can also inspect the endpoint in the API console at `/`.

## Migrating existing custom files

Before the first sync with this layout, move custom functions, routers, scripts, and docs out of Atom folders into their matching `*_extend/` folders. Update imports and worker commands to use the new paths. Keep `config_extend.py` in the project root. Restart and verify your endpoints before syncing. Files left inside Atom folders will be replaced or removed.

See the [sync guide](sync.md) for update behavior and recovery.

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

New standalone processes go in `script_extend/` and are run as separate processes (they're not part of the API). Use them for queue consumers or batch jobs; they can load `config.py` and optional overrides from `config_extend.py`, and import from `function`. Run them from the project root with `python3 -m script_extend.<worker_name>` so project imports are available. Scripts and docs are not auto-loaded by the API.

## Summary

| Goal | Do this |
|------|---------|
| Change a setting | Set it in `config_extend.py` |
| Add functions | New `function_extend/custom_<your>.py` with unique `func_*` names |
| Add an endpoint | New file in `router_extend/` + entry in `config_api` |
| Add a table | Extend `config_postgres["table"]` in `config_extend.py` |
| Add a worker | New script in `script_extend/` |
| Enable a service | Set its `config_*_url` / key (in `.env` or `config_extend.py`) |
| Update Atom | See the separate [sync guide](sync.md) |

---

📚 [Back to README](../readme.md)
