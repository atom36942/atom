# Atom agent guide
Rules Atom enforces at import, startup, sync, and CI. Follow exactly.

## Work
- Work autonomously; ask only for essential missing info or destructive actions outside the request.
- Match surrounding code: naming, density, one-line statements, comments. Never expose `.env` or credentials.

## Ownership
- Atom owns every unsuffixed path; the project owns `<name>_extend` (`router_extend/`, `function_extend/`, `files_extend/`, `static_extend/`, `script_extend/`, `tests_extend/`, `docs_extend/`, `config_extend.py`). Shared: `.env` (project), `requirements.txt` (merged), `.github/` (per repo).
- Never edit core (`function/`, `router/`, `docs/`, `script/`, `static/`, `files/`, `config.py`, `main.py`, `sync.py`, `AGENTS.md`, `ruff.toml`, `.gitignore`, `.dockerignore`, `Dockerfile`, `readme.md`; full list: `SYNC_FILES`/`SYNC_FOLDERS` in `sync.py`) unless asked for a framework change: `python3 sync.py` overwrites them and deletes other files in Atom folders. Refactors, renames, cleanups and lint fixes touch project files only; if core blocks the work, solve it in project paths or report it.
- `.gitignore` is synced and ignores unlisted paths: new top-level paths are committed only if named `*_extend`.
- Sync never modifies existing `*_extend` files; it creates missing ones (a starter `config_extend.py`), resets the `# atom` section of `requirements.txt`, and rebuilds `venv/` to match `requirements.txt` exactly (`--no-venv` skips).

## Where code goes
1. API → `router_extend/<feature>.py` (`router = APIRouter()`): read params, call a `func_*`, return; no business logic.
2. Logic → `function_extend/<feature>.py`: `func_*`, available as `app_state.func_*`.
3. Files → `files_extend/`: shared constants and `param_specs` (import `files_extend.<module>`), JSON, prompts, templates (read by path from the project root).
4. Web pages → `static_extend/`, served at `/static/<name>` with Atom's `static/` (same name in both stops startup; `/static_extend/...` is not a URL; restart after creating the folder). A top-level `.html` file, or a folder with `index.html`, is listed on the home page at `/`. A page is standalone: its own login and its own `localStorage` key.
5. Config → `config_extend.py` (below). Jobs → `script_extend/` (enqueue with `app_state.func_producer`, `docs/queue.md`). Tests → `tests_extend/` (with `__init__.py`). Docs → `docs_extend/`. Packages → `requirements.txt` under `# extend`, pinned `==`.
- Temporary and generated files (exports, scratch, compile or download folders, logs) → `tmp/<feature>/` in the project root (gitignored), never tracked folders or the system temp folder; `tmp/` is wiped at app start while `config_is_tmp_reset` is true, so keep data that must survive in the database.
- Request path: middleware applies `config_api` → route → `func_*` → DB → `{"status": 1, "message": ...}`.

## Settings
- Every `config_*` from `config.py`, then `config_extend.py`, then `.env`/environment (wins), ends up on `app_state.config_*`; new names work too. Env values are typed by the existing default (else true/false, int, JSON, string); lists become tuples. `config_<db>_url_<name>` fills `config_<db>_url_dict[name]`.
- `config_extend.py` layout: `# base` (`from config import config_x as base_config_x`), `# atom` (Atom's dicts extended), `# misc` (plain values, project settings). Define each `config_*` once; never name a base import `config_*` (startup fails).
- Extend, never replace: `config_x = {**base_config_x, "key": value}`; spread only at the top level; to change one of Atom's keys write its whole value (never `**base_config_x[key]`). Exception, `config_postgres`: `{**base_config_postgres, "table": {**base_config_postgres["table"], "task": [...]}}`; add columns to an Atom table with a new list (`[*base_config_postgres["table"]["users"], {...}]`), never `.append` to Atom's.
- Startup fails if `config_extend.py` drops Atom's entries from `config_api` (routes), `config_postgres` (`extension`, `table`, `control`, `sql` and their entries) or `config_column_int_mapping` (codes); values and labels may change, additions are free. Atom's entries are read from `config.py` at startup.
- New tables: column spec in `docs/extend.md` "Add or change database tables"; owner columns get `"index": "btree(created_by_id,id)"`.

## config_api (enforced by the middleware before the route; never re-check in a route)
- Every route needs an entry with a unique `id` (200+ for project routes) and `is_token`; startup fails on a missing entry, an entry without a route, or a repeated `id`.
- `is_token: True` → access token required (401); `user_check_*` need it too.
- `user_check_role: {"mode": m, "roles": [..]}` (403); `user_check_deactivated`/`user_check_deleted: {"mode": m}`. `m`: `token` (fastest, stale until re-login), `redis` (cached), `realtime` (DB each request; admin and destructive routes), `inmemory` (startup snapshot, single worker).
- `rate_limit: {"mode": "redis"|"inmemory", "limit": N, "window_sec": S}` (429); `cache: {"mode": "redis"|"inmemory", "ttl_sec": S, "is_per_user": bool}`.
- `is_postgres_param: True` allows `?postgres=<name>`; `is_active: False` → 404; `is_log_api: False` keeps requests out of `log_api`.
- WebSocket entries take only `id` and `is_active`; the socket function checks both and authenticates itself (token as first message).
- `request.state.user` = decoded token (`config_column_token_encode` columns) or `{}`; take user id and role only from it, never from params. Row ownership and other rules `config_api` can't express go in a `func_*`.

## Routes
- `async def func_api_<area>_<name>(*, request: Request):`, then `app_state = request.app.state`; use only `app_state.func_*/config_*/client_*`, `request.state.client_postgres`, `request.state.cache_postgres_schema`; never import from `function`.
- Params only via `await app_state.func_request_param_read(request=request, mode="query"|"body"|"form"|"header", param_specs=[...], strict=True, strict_types=True, reject_unknown=True)`. Spec keys: `name`, `type` (`str`, `int`, `float`, `bool`, `list`, `list:int`, `dict`, `file`, `any`), `required`, `default`, `allowed`, `minimum`, `maximum`, `min_length`, `max_length`; with `is_postgres_param` add `{"name": "postgres", "type": "str"}`.
- Return `{"status": 1, "message": result}`; errors `raise app_state.func_api_error(message=..., status_code=...)` (plain `Exception` → 400). List routes with `app_state.func_app_route_list(app=request.app)`.

## Functions
- `func_*`, keyword-only, unique across `function/` and `function_extend/` (duplicates fail at import). `_*.py` and subfolders are not loaded; import from defining modules (`from function.request import ...`).
- Optional `func_extend(*, app_state)` runs once after Atom's clients are ready (its return is `app_state.extend`); `func_extend_shutdown(*, app_state)` runs before they close. Never edit `main.py` for this.

## Data and security
- Tables via `func_check_table_permission` and `func_postgres_create/read/update/delete`; ownership via `created_by_id` (`docs/crud.md`, `docs/ownership.md`). Never `is_trusted=True` with request data.
- SQL values as `$1, $2`, never in f-strings; identifiers only after `^[a-zA-Z_][a-zA-Z0-9_]*$` or an allow-list, quoted.
- Clients: `app_state.client_postgres_dict`/`client_redis_dict`/`client_mssql_dict`/`client_clickhouse_dict["<name>"]` (default `master`). Redis names `api_response`, `user_state`, `ratelimiter`, `queue` are Atom's.
- Production: `config_token_secret_key` 32+ bytes. With `config_uvicorn_workers` > 1, no `inmemory` mode for caches, rate limits or user checks, and `/my/message-socket` stays inactive (startup fails).

## Style
- Headers, lowercase singular, no module docstrings: routers `# import`/`# router`/`# api`; functions `# import`/`# function`.
- Scripts (and `sync.py`): `# command: <how to run>`, `# info: <one line>`, then `# import`, `# config` (every outside value, read only here: `from config import ...`, `os.getenv("NAME", default)`, CLI flags), `# setting` (fixed values, UPPER_CASE), `# logic` (helpers, then `main()`), `# main` (only `if __name__ == "__main__":` calling `main()`). Every section present, even empty; no blank lines inside `# config`/`# setting`.
- Script `# logic`: one top-level helper per named step (`noun_verb`: `task_claim`, `batch_fetch`), keyword-only, getting `# config` values as arguments (`# setting` constants may be read directly); `main()` is last, at most 30 lines, defines no functions, reads like steps (read config, open clients, call helpers, close in `finally`). Exception: `func_run_broker` callbacks take its positional arguments.
- Atom's `script/` holds only scripts that work in every project: imports are stdlib, packages, `config` and `function` (never `files`, `router` or `*_extend`; `sync.py` stdlib only); outside values are read only in `# config`; writes go only to `tmp/`. Scripts tied to a project's tables go in `script_extend/`.

## Verify
- `venv/bin/ruff check .`; `venv/bin/python -m unittest discover -s tests_extend -t .`; start with `venv/bin/python main.py` (startup checks catch config, duplicate `func_*` and secret errors).
- Also read `docs_extend/AGENTS.md` if present (project rules, never synced); these rules win on conflict.
