# 🧩 Extending Atom

Atom is opinionated but not closed. You extend it **without editing core files**, so you can pull framework updates (via `sync.py`) at any time without losing your work.

## The Golden Rule

Atom owns all contents of `docs/`, `router/`, `function/`, `script/`, `static/`, and `files/`, plus `config.py` and selected core files. Sync replaces these folders completely, removing local-only files even on the first run. Keep your work in separate extension paths:

| Atom path | Developer path | Purpose |
|-----------|----------------|---------|
| `config.py` | `config_extend.py` | Configuration overrides |
| `router/` | `router_extend/` | Custom API endpoints |
| `function/` | `function_extend/` | Custom `func_*` business logic |
| `script/` | `script_extend/` | Standalone workers and jobs |
| `static/` | `static_extend/` | Web assets, served at `/static/<name>` together with Atom's `static/` |
| `docs/` | `docs_extend/` | Project documentation |
| `tests/` (Atom's, not synced) | `tests_extend/` | Project tests (`venv/bin/python -m unittest discover -s tests_extend -t .`) |
| `files/` | `files_extend/` | Anything extra: constants and reusable `param_specs`, sample JSON, AI prompts and contexts, templates, seed CSVs |

One rule: Atom owns every unsuffixed folder and sync fully replaces it, deleting any other file inside; the project owns every `<name>_extend` folder. A file with the same path in `static/` and `static_extend/` stops startup, so a project cannot shadow an Atom page.

Files in `static_extend/` are served at `/static/<file>`: `static_extend/logo.png` is `/static/logo.png`. `/static_extend/...` is not a URL, and no `.env` setting is needed. Restart the app after creating `static_extend/` for the first time; new files in an existing folder are served right away. Each `.html` file there, and each folder with an `index.html` (a page split into several files), gets a row on the home page at `/`.

Sync creates each missing `_extend` folder locally (empty; `tests_extend/` gets an `__init__.py`) and a starter `config_extend.py`; it never modifies existing ones. Git commits a folder only once it holds a file. `.env` is also preserved.

`files_extend/` holds anything extra the project needs. Python modules there are imported as `files_extend.<module>`; other files are opened by path from the project root, where Atom runs:

```python
# files_extend/specs.py
ORDER_ID = [{"name": "order_id", "type": "int", "required": True}]

# router_extend/order.py (inside a route)
from files_extend.specs import ORDER_ID
oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=ORDER_ID, strict=True, reject_unknown=True)
```

Imported `param_specs`, alone or combined (`param_specs=ORDER_ID + [{...}]`), appear in the API docs (`/openapi.json`) like inline ones, as long as they are plain lists and dicts.

```python
# function_extend/summary.py
import json
from pathlib import Path

def func_summary_prompt() -> str:
    return Path("files_extend/prompts/summary.txt").read_text()

def func_sample_orders() -> list:
    return json.loads(Path("files_extend/sample/orders.json").read_text())
```

For a project's own Redis, add `config_redis_url_<name>` to `.env` and use `request.app.state.client_redis_dict["<name>"]`; see [redis.md](redis.md#project-redis-connections).

Files in `files_extend/` are committed and included in the Docker image. Runtime output such as uploads and exports belongs in `tmp/` or blob storage, not `files_extend/`; keep secrets in `.env`.

Configuration extensions are loaded after the defaults in `main.py`:

```python
config_modules = [config] + ([importlib.import_module("config_extend")] if importlib.util.find_spec("config_extend") else [])
config_values = {key: value for module in config_modules for key, value in vars(module).items() if key.startswith("config_")}
```

`config_extend.py` is read after `config.py`, so its `config_*` values override the defaults. Only `config_*` names are taken from it: functions defined there are ignored, so they cannot replace core functions. It is kept out of the sync list. The `function` package discovers both Atom functions and modules directly inside the optional `function_extend/` folder; no `__init__.py` is required there.

## Startup and shutdown: `func_extend`

`main.py` is Atom's. To create your own clients or load data once at startup, define `func_extend` in any `function_extend/` module; Atom calls it after its own clients and caches are ready and stores the return value, whatever it is, in `app.state.extend` (`None` when `func_extend` is not defined). `func_extend_shutdown` runs on shutdown before Atom closes its clients, so it can still use them. Both are optional, take `app_state`, and may be sync or async.

```python
# function_extend/extend.py
async def func_extend(*, app_state):
    return {"stripe": StripeClient(api_key=app_state.config_stripe_key), "plans": await func_plans_load(app_state=app_state)}

async def func_extend_shutdown(*, app_state):
    await app_state.extend["stripe"].close()

# router_extend/billing.py (inside a route)
plans = app_state.extend["plans"]
```

An error in `func_extend` stops startup. An error in `func_extend_shutdown` is printed and Atom's own shutdown continues. With several workers, each worker runs both once. Restart the app to rebuild `extend`; `/admin/sync` does not touch it.

## Extend Atom's dictionaries

`config.py` has seven dictionary settings a project extends: `config_sql`, `config_table`, `config_column_regex`, `config_dropdown`, `config_column_int_mapping`, `config_postgres` and `config_api`. Define each one you change once in `config_extend.py`; `main.py` uses that value in place of Atom's and does not merge for you, so start from Atom's value and add or override keys:

- spread Atom's base at the top level only: `{**base_config_x, "key": value}`. To change one of Atom's keys, write that key's whole value (copy from `config.py` what you keep); never spread a nested base like `**base_config_x["users"]`, so every override shows its full value in one place;
- `config_postgres` is the one exception, because its tables sit one level down: `{**base_config_postgres, "table": {**base_config_postgres["table"], "task": [...]}}`.

Keep Atom's keys when you extend: a dict defined from scratch replaces Atom's completely. For three of them startup checks it: if `config_api`, `config_postgres` or `config_column_int_mapping` in `config_extend.py` is missing any of Atom's routes, Postgres setup (extensions, tables, switches, SQL) or mapped codes, it stops and names them. Changing their values (a route's policy, a table's columns) is fine; how you write the dict (`**base`, a copy) doesn't matter.

Lay the file out in three sections: `# base` (imports of Atom's values, `from config import config_api as base_config_api`), `# atom` (Atom's dicts you extend, each starting from its base) and `# misc` (everything else: plain values and your own `config_*` settings). When `config_extend.py` is missing, sync creates it in this layout, with `config_column_int_mapping`, `config_postgres` and `config_api` already defined from their bases and commented examples; add other Atom dicts to `# base` and `# atom` the same way.

```python
# config_extend.py
from config import config_column_int_mapping as base_config_column_int_mapping
from config import config_api as base_config_api
from config import config_postgres as base_config_postgres

# 1. Add the project's own mappings: task statuses and user role labels.
config_column_int_mapping = {
    **base_config_column_int_mapping,
    "task": {
        "status": {1: "To Do", 2: "In Progress", 3: "Done"},
        "priority": {1: "Low", 2: "Medium", 3: "High"},
    },
    "users": {    # the project's role labels (Atom ships none for users)
        "role": {1: "Admin", 10: "Editor", 11: "Viewer"},
    },
}

# 2. Add a route policy and turn off a core route (its whole policy, with is_active added).
config_api = {
    **base_config_api,
    "/custom/hello": {"id": 200, "is_token": False},
    "/my/object-read": {"id": 50, "is_token": True, "is_postgres_param": True, "is_active": False},
}

# 3. Add a table, and a column to Atom's users table (a new list: Atom's columns plus yours).
config_postgres = {
    **base_config_postgres,
    "table": {
        **base_config_postgres["table"],
        "task": [
            {"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True},
            {"name": "created_by_id", "datatype": "bigint"},
            {"name": "title", "datatype": "text"},
            {"name": "status", "datatype": "smallint", "default": 1},
            {"name": "priority", "datatype": "smallint"},
        ],
        "users": [*base_config_postgres["table"]["users"], {"name": "department", "datatype": "text"}],
    },
}
```

These examples are alternatives to existing definitions: merge the snippets into your current dictionaries rather than assigning the same configuration name again later. Choose an unused API ID. The custom route policy needs a matching router, as shown below. Integer mappings provide labels; they do not change role permissions or validate database values.

### What startup checks in `config_extend.py`

Three variables are checked, and only when `config_extend.py` defines them:

| Variable | Checked | Startup stops when |
|---|---|---|
| `config_api` | every route Atom defines is still a key | an Atom route is missing (e.g. `/health`) |
| `config_postgres` | Atom's parts (`extension`, `table`, `control`, `sql`) and, inside each, every extension, table, switch and SQL entry Atom defines | any of them is missing (e.g. `table.users`, `extension.pg_trgm`, `control.is_index_drop`) |
| `config_column_int_mapping` | every code Atom maps (`blob.type`, `log_users_delete.type`, `log_users_delete.worker_status`) is still there | an Atom code is missing (e.g. `blob.type 2`) |

Values are not checked: change a route's policy, a table's columns or a code's label, and add your own routes, tables, mappings and codes, freely. What counts as Atom's is read from `config.py` on every start, so entries Atom adds later are covered without changing the check. How the dict is written does not matter either: `{**base_config_api, ...}` or a copy both pass. The message names the missing entries and the fix, for example `config_postgres drops 3 of Atom's entries (table.users, extension.pg_trgm, control.is_index_drop); fix: {**base_config_postgres, "table": {**base_config_postgres["table"], ...}}`.

Not checked: `config_dropdown`, `config_sql`, `config_table`, `config_column_regex` and any `config_*` the project adds; a missing key there only removes that option.

One more check covers the whole file: a base imported under a name starting with `config_` (`config_api_base = ...` instead of `base_config_api`) stops startup, because every `config_*` name is read as a setting.

The final settings, whichever file set them, also go through Atom's general startup checks (route policies, database URLs, limits); see [config.md](config.md).

### Override one of Atom's keys

Dictionary unpacking (`**base`) copies Atom's entries into the new dictionary; a later duplicate key replaces Atom's value. Write that key's whole value, as in the `/my/object-read` entry above: start from the value in `config.py`, keep what you need and change the rest. For a route, include its `id` and `is_token`. This changes policy, not the route handler.

### Replace or modify a core table's columns

`**base_config_postgres["table"]` copies only the table map: Atom's column lists are shared with `config.py`, so never change them in place (`config_postgres["table"]["users"].append(...)` would change Atom's own list). Give the table a new list instead:

```python
# Add columns: Atom's users columns plus yours, so later Atom columns are still inherited.
"users": [*base_config_postgres["table"]["users"], {"name": "department", "datatype": "text"}],

# Change a column: copy the list with that column replaced.
"users": [{**column, "datatype": "varchar(200)"} if column["name"] == "title" else column for column in base_config_postgres["table"]["users"]],
```

Writing the complete column list by hand also works, but then you maintain every column Atom's authentication and other features need. Do not add a column name that already exists; change its definition instead. These settings only describe the schema; PostgreSQL changes happen during schema initialization when enabled. Review schema changes before applying them to existing data.

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
from config import config_postgres as base_config_postgres

config_postgres = {
**base_config_postgres,
"table": {
**base_config_postgres["table"],
"product": [
    {"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True},
    {"name": "created_at", "datatype": "timestamptz", "default": "now()", "index": "btree(created_at)"},
    {"name": "created_by_id", "datatype": "bigint"},
    {"name": "title", "datatype": "text", "is_mandatory": True, "index": "gin_trgm(title)"},
    {"name": "price", "datatype": "numeric(10,2)"},
],
},
}
```

`config.py` holds Atom core tables; keep application tables in `config_extend.py`. Spreading the base keeps Atom's tables and leaves `config.py`'s own dictionaries unchanged (see [Replace or modify a core table's columns](#replace-or-modify-a-core-tables-columns) for Atom's tables).

Column specs support `is_primary`, `is_mandatory`, `default`, `unique`, `check`, `regex`, `index` (btree / gin / gist / gin_trgm), array types, PostGIS geography, and `old` (for renames). Once a table has a `created_by_id` column it works with the generic `object-create` / `object-read` ownership flow out of the box. Give the owner column an index on (owner, `id`), e.g. `"index": "btree(created_by_id,id)"` (and `btree(received_by_id,id)` etc. for other owner columns you read by): `/my/object-read` filters by owner and sorts by `id`, and without it Postgres scans the table, which gets slower as it grows (see [performance.md](performance.md#9-owner-index-and-json-encoding)).

## 5. Add background workers

New standalone processes go in `script_extend/` and are run as separate processes (they're not part of the API). Use them for queue consumers or batch jobs; they can load `config.py` and optional overrides from `config_extend.py`, and import from `function`. Run them from the project root with `python3 -m script_extend.<worker_name>` so project imports are available. Scripts and docs are not auto-loaded by the API.

Every script has the same sections, in this order, so anyone can see at a glance how to run it, what it reads from outside, and what is fixed:

```python
# command: venv/bin/python -m script_extend.order_sync --dry-run

# info: Copies new orders to the warehouse database every minute.

# import
import argparse
import asyncio
import os
from function import func_client_postgres

# config
from config import config_postgres_url_dict                         # Atom settings, from config.py / .env
WAREHOUSE_URL = os.getenv("WAREHOUSE_URL")                          # or the environment, for a script that stands alone
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")              # and command-line flags

# setting
BATCH_SIZE = 500
POLL_INTERVAL_SEC = 60

# logic
async def copy_batch(pool):
    ...

async def main():
    args = parser.parse_args()
    ...

# main
if __name__ == "__main__":
    asyncio.run(main())
```

`# config` is everything that can change without editing the file and is read only there; `# setting` is values fixed in the file (UPPER_CASE). Keep every section, even an empty one.

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
