# 🧩 Extending Atom

Atom is opinionated but not closed. You extend it **without editing core files**, so you can pull framework updates (via `sync.py`) at any time without losing your work.

## The Golden Rule

Core files — `main.py`, upstream Atom files in `function/`, `config.py`, and the shipped routers — are **overwritten by `sync.py`** on update. Put custom logic in uniquely named function modules or the drop-in extension files:

| Your file | Purpose | Survives `sync.py`? |
|-----------|---------|---------------------|
| `config_extend.py` | Override / add any config value | ✅ yes |
| `function/custom_<your>.py` | Add functions with unique names | ✅ yes, if the path is absent from upstream Atom |
| `router/<your>.py` | Add new API endpoints | ✅ yes, if the path is absent from upstream Atom |
| `.env` | Secrets & connection strings | ✅ yes |

Configuration extensions are loaded after the defaults in `main.py`:

```python
if importlib.util.find_spec("config_extend"): from config_extend import *
```

`config_extend.py` is imported after `config.py`, so its values override the defaults. It is kept out of the sync list. Custom function files are discovered by the `function` package.

## 1. Override or add config

Create `config_extend.py` in the project root. Any name you define replaces the core value; new names are simply added.

```python
# config_extend.py

# turn features on/off
config_signup_allowed_roles = [5]
config_is_prod = True

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

### Core module map

The shared `function/` folder groups helpers by responsibility:

| Module | Responsibility |
| --- | --- |
| `app.py` | App setup, state refresh, OpenAPI, and monitoring initialization |
| `auth.py` | Sign-up, login, JWTs, OTP generation/verification, and user lookup |
| `background.py` | Buffer flushing, cache cleanup, and task shutdown |
| `blob.py` | Cloud blob upload, preview, deletion, and container operations |
| `clients.py` | Service client creation and cleanup |
| `config.py` | Configuration checks |
| `data_import.py` | CSV import into databases |
| `files.py` | Local directories, temporary file streaming, and CSV parsing |
| `jira.py` | Jira worklog export |
| `messaging.py` | Email/OTP delivery and message ordering, pagination, and read tracking |
| `middleware.py` | Request authentication, access checks, caching, and responses |
| `pgweb.py` | PostgreSQL browser operations |
| `postgres_crud.py` | PostgreSQL CRUD, grouped reads, and distinct reads |
| `postgres_metadata.py` | Schema inspection, database selection, column mapping, and diagnostics |
| `postgres_schema.py` | Schema validation, initialization, and synchronization |
| `postgres_sql.py` | PostgreSQL filters, relations, and value serialization |
| `query_ai.py` | AI query generation and ClickHouse schema context |
| `query_runners.py` | PostgreSQL, SQL Server, and ClickHouse query execution and exports |
| `queues.py` | Queue publishing and broker workers |
| `request.py` | Request parameters, object extraction, audit fields, and numeric conversion |
| `validation.py` | Values, columns, batches, table access, and user mutation permissions |

`__init__.py` discovers these modules automatically. Keep route handlers in
`router/` and reusable helpers in `function/`. Add a module when a new use case
needs one; keep related operations together. Public `func_*` names remain
available through `from function import ...` and `app.state` regardless of their
module location. Sync discovers the files through its existing folder rules.

### Adding custom functions

To add functions, create a Python file directly inside the shared `function/` folder:

```python
# function/custom_payments.py
async def func_payment_create(*, amount: int):
    return {"amount": amount}
```

After restart, `from function import func_payment_create` and
`request.app.state.func_payment_create` are available automatically. No edits to
`main.py` or `function/__init__.py` are needed.

The loader imports modules alphabetically and exports the `func_*` functions
defined in each module. Files beginning with `_` and nested packages are not
auto-loaded. Imported helpers are not exported a second time. Duplicate function
names defined in different modules stop startup with an error naming both files.
Use distinctive filenames such as `custom_payments.py`: sync replaces any path
also present in upstream Atom, including `function/__init__.py`, but leaves
developer-only files untouched.

Inside a function module, import shared helpers from their defining module
(for example, `from .request import func_query_bool_parse`), rather than from
`function`, whose exports are still being assembled during loading. Keep module
dependencies acyclic. Only function names are exported by `from function import *`.

Keep custom functions in uniquely named files in `function/`. Function names must
also be unique across modules; duplicate definitions are not an override mechanism.

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

New standalone processes go in `script/` and are run as separate processes (they're not part of the API). Use them for queue consumers or batch jobs; they read the same `config.py` and can import from `function`.

## Updating the framework

When new Atom versions ship, pull the latest core files with `sync.py`:

```bash
venv/bin/python sync.py
```

The updater first fetches upstream `main`, pins that commit, validates its
`sync.py`, and replaces the local updater. It then starts that latest version in a
fresh process using the same Python interpreter. The latest version applies its
sync rules immediately, in this same invocation; there is no second manual run.
The child uses the pinned commit without re-fetching or restarting again, while
the parent holds the sync lock.

The latest updater prepares and validates the selected project files before
replacing them. Missing required files, invalid Python, failed Git commands, or
symlinked destinations stop the update. Files are written to the working tree;
the Git index is left unchanged. If the project sync fails, the newly installed
`sync.py` remains in place, while project write failures use in-memory rollback.
If the new process cannot be launched, the old updater is restored from memory.

- All upstream files in `function/` and `router/` are discovered automatically and
  created or replaced, including newly added Atom modules. Developer-only files in
  both folders and `.env` are preserved. A path also present in upstream belongs to Atom.
- Existing requirement entries are preserved; missing packages are appended.
  Existing configuration overrides are preserved; missing `config_postgres` and
  `config_api` assignments are seeded in `config_extend.py`.
- `.atom-sync/state.json` records the last synced Atom files. On later updates,
  unchanged Atom files removed upstream are also removed locally. If such a file
  has local edits, sync stops so you can move those edits to a custom module.
  On the first run, unknown files are preserved.
- Write failures trigger rollback using previous contents held in memory. No
  backup files are saved. No success message is printed on failure, and
  the command exits nonzero. A lock prevents overlapping updater runs.

Ownership state and the sync lock are excluded from Git and Docker builds. Keep the
state file for future ownership tracking. Re-run the dependency install if
`requirements.txt` changed, then restart the app:

```bash
venv/bin/pip install -r requirements.txt
```

### Recovering an interrupted update

Rollback is available only while the updater process is running. If rollback
cannot finish, or the process is forcibly killed, review the working tree and
recover affected files from your saved Git version. Uncommitted changes have no
persistent recovery copy. Remove `.atom-sync/lock` only after confirming no updater
is running. Review the diff and run your application tests before deploying;
syntax validation does not verify runtime compatibility.

## Summary

| Goal | Do this |
|------|---------|
| Change a setting | Set it in `config_extend.py` |
| Add functions | New `function/custom_<your>.py` with unique `func_*` names |
| Add an endpoint | New file in `router/` + entry in `config_api` |
| Add a table | Extend `config_postgres["table"]` in `config_extend.py` |
| Add a worker | New script in `script/` |
| Enable a service | Set its `config_*_url` / key (in `.env` or `config_extend.py`) |
| Update Atom | `python sync.py` — extensions are preserved |

---

📚 [Back to README](../readme.md)
