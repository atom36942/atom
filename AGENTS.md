# Atom agent guide
Rules Atom enforces at import, startup, sync, and CI. Follow exactly.

## Work
- Work autonomously; ask only for essential missing info or destructive actions outside the request.
- Match surrounding code: naming, density, one-line statements, comments. Never expose `.env` or credentials.

## Flow: build features only in project paths
- One rule: Atom owns every unsuffixed path; the project owns `<name>_extend` (`router_extend/`, `function_extend/`, `files_extend/`, `static_extend/`, `script_extend/`, `tests_extend/`, `docs_extend/`, `config_extend.py`). Shared: `.env` (project), `requirements.txt` (merged), `.github/` (per repo).
1. API → `router_extend/<feature>.py` (`router = APIRouter()`): read params, call a `func_*`, return. No business logic.
2. Logic → `function_extend/<feature>.py`: `func_*` business logic and helpers reused by several APIs; available as `app_state.func_*`.
3. Files → `files_extend/`: anything extra the project needs: constants and `param_specs` reused across APIs (Python modules imported as `files_extend.<module>`), JSON, prompts, templates, and other files (read by path from the project root). Web assets → `static_extend/`, served at `/static/<name>` with Atom's `static/` (same name in both stops startup). `/static_extend/...` is not a URL; no `.env` setting; restart after creating the folder.
4. Config → `config_extend.py`: `config_api` policy, new tables in `config_postgres["table"]` (column spec: `docs/extend.md` "Add or change database tables"; owner columns get `"index": "btree(created_by_id,id)"`), `config_*` settings.
5. Jobs → `script_extend/`, never `script/` (enqueue from a route with `app_state.func_producer`, `docs/queue.md`); tests → `tests_extend/` (with `__init__.py`; never `tests/`, which is Atom's); docs → `docs_extend/`; packages → append to `requirements.txt` pinned `==`.
- Request path: middleware applies `config_api` → route → `func_*` (with `files_extend/` and core helpers) → DB → `{"status": 1, "message": ...}`.
- Never edit core (`function/`, `router/`, `docs/`, `script/`, `static/`, `files/`, `config.py`, `main.py`, `sync.py`, `AGENTS.md`, `ruff.toml`, `.gitignore`, `.dockerignore`, `Dockerfile`, `readme.md`; `sync_files` and `sync_folders` in `sync.py` are the full list) unless asked for a framework change: `python sync.py` overwrites them and deletes any other file inside Atom folders.
- Refactors, renames, cleanups, formatting, and lint fixes touch only project files; leave core as is even if it looks wrong or inconsistent. If core blocks the work, solve it in project paths or report it; never patch core.
- `.gitignore` ignores unlisted paths and is synced: new top-level files/folders are never committed unless named `*_extend`. Sync resets Atom's package pins in `requirements.txt`.

## config_extend.py
- Extend, never replace; define each `config_*` once (no auto-merge); `deepcopy` nested dicts:
  `config_api = {**base_config_api, "/order/read": {"id": 200, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}}}` with `from config import config_api as base_config_api`. Import base values as `base_config_*`, never under another `config_*` name (every `config_*` is read as a setting; startup fails).
- Every route needs a `config_api` entry with a unique `id` (200+ for project routes); startup fails on a missing entry, an entry without a route, or a repeated ID.

## config_api: the middleware enforces it before the route runs; never code these checks in a route
- `is_token: True` → access token required (401). `user_check_*` also need `is_token: True`.
- `user_check_role: {"mode": m, "roles": [..]}` (403); `user_check_deactivated` / `user_check_deleted: {"mode": m}` block users with `deactivated_at` / `deleted_at` set.
- `m`: `token` (claims in token, fastest, stale until re-login), `redis` (cached DB lookup), `realtime` (DB every request; admin and destructive routes), `inmemory` (startup snapshot, single worker).
- `rate_limit: {"mode": "redis"|"inmemory", "limit": N, "window_sec": S}` per user or IP (429). `cache: {"mode": "redis"|"inmemory", "ttl_sec": S, "is_per_user": bool}` keyed by path and query; `is_per_user` for user-specific data.
- WebSocket routes: `config_api` entry takes only `id` and `is_active` (other keys fail startup); the socket function checks `is_active` and authenticates itself (token as first message, like `/my/message-socket`).
- `is_postgres_param: True` allows `?postgres=<name>` (sets `request.state.client_postgres`); `is_active: False` disables the route (404).
- Caller: `request.state.user` = decoded token (`config_column_token_encode` columns: `id`, `role`, …) or `{}`. Use `request.state.user["id"]` for ownership; never take user id or role from params. Rules `config_api` cannot express (e.g. row ownership) go in a `func_*`.

## Routes
- `async def func_api_<area>_<name>(*, request: Request):` then `app_state = request.app.state`. Use only `app_state.func_*`, `app_state.config_*`, `app_state.client_*`, `request.state.client_postgres`, `request.state.cache_postgres_schema`; no imports from `function`.
- Read every param with `await app_state.func_request_param_read(request=request, mode="query"|"body"|"form"|"header", param_specs=[...], strict=True, strict_types=True, reject_unknown=True)`; never `request.query_params`, `request.json()`, `request.form()`, `request.headers`. Spec keys: `name`, `type` (`str`, `int`, `float`, `bool`, `list`, `list:int`, `dict`, `file`, `any`), `required`, `default`, `allowed`, `minimum`, `maximum`, `min_length`, `max_length`. With `is_postgres_param`, add `{"name": "postgres", "type": "str"}`.
- Return `{"status": 1, "message": result}`. Errors: `raise app_state.func_api_error(message=..., status_code=...)`; plain `Exception` → 400.
- List routes with `app_state.func_app_route_list(app=request.app)`, not `app.routes`.

## Functions
- `func_*`, keyword-only (`*,`), unique across `function/` and `function_extend/` (duplicates fail at import; core cannot be overridden).
- Startup state: optional `func_extend(*, app_state)` in `function_extend/` runs once after Atom's clients are ready; its return value is `app_state.extend` (`None` if undefined). Optional `func_extend_shutdown(*, app_state)` runs before Atom's clients close. Never edit `main.py` for this.
- In `function_extend/` import from defining modules (`from function.request import func_query_bool_parse`), not `function`. `_*.py` files and subfolders are not loaded.

## Data and security
- Table access via `func_check_table_permission` and `func_postgres_create/read/update/delete`; ownership via `created_by_id` (`docs/crud.md`, `docs/ownership.md`).
- SQL: values as `$1, $2`, never in f-strings; identifiers only after `^[a-zA-Z_][a-zA-Z0-9_]*$` or an allow-list, quoted. Reviewed core f-string SQL carries `# noqa: S608 - <reason>`.
- Never `is_trusted=True` in `func_postgres_create` with request data.
- Connections: `.env` `config_<db>_url_<name>` → `app_state.client_postgres_dict` / `client_redis_dict` / `client_mssql_dict` / `client_clickhouse_dict["<name>"]`; Postgres, MSSQL, ClickHouse default to `master`. Redis roles `api_response`, `user_state`, `ratelimiter`, `queue` are Atom's; use your own name for project Redis. MongoDB and other services: one `client_*`.
- Production: `config_token_secret_key` 32+ bytes. `config_uvicorn_workers` > 1: every `inmemory` cache, rate limit, and user check must be `redis`.

## Style
- Headers, lowercase singular: routers `# import`/`# router`/`# api`; functions `# import`/`# function`; scripts `# import`/`# config`/`# logic`/`# main`. No module docstrings.

## Verify
- `venv/bin/ruff check .` (core strict; `*_extend/`, `config_extend.py` errors only), project tests with `venv/bin/python -m unittest discover -s tests_extend -t .`, then start the app with `venv/bin/python main.py` or `venv/bin/uvicorn main:app --reload`; startup checks catch `config_api`, duplicate `func_*`, and secret errors. Use `venv/bin/python main.py` when `config_uvicorn_workers` > 1.
- Examples: `docs/extend.md`, `docs/auth.md`, `docs/security.md`.

## Project rules
- Also read `docs_extend/AGENTS.md` if present: project-specific rules, written by the project and never synced. Atom's rules above win on conflict.
