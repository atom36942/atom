# Atom agent guide

Rules for AI coding agents working in an Atom project. Follow them exactly; they reflect checks Atom enforces at import, startup, sync, and CI.

## Main flow
Build every project feature from these layers; never change Atom core to add one:
1. **API** → `router_extend/<feature>.py`: the endpoint. Read and validate every param with `app_state.func_request_param_read`, call a `func_*`, return the result. No business logic here.
2. **Logic** → `function_extend/<feature>.py`: `func_*` functions with the feature's business logic, including helpers several APIs reuse. Each is available as `app_state.func_*`, alongside Atom's core helpers.
3. **Shared** → `shared/`: constants and data reused across APIs and functions, such as `param_specs`, sample JSON, prompts, and templates.
4. **Config** → `config_extend.py`: the route's `config_api` policy (auth, roles, rate limit, cache), new tables in `config_postgres`, and `config_*` settings.
5. **Jobs** → `script_extend/` for standalone workers. **Docs** → `docs_extend/`. **Packages** → `requirements.txt`.
6. **Verify** → run ruff, the tests, and `python main.py` (see the end of this file).

Request path: client → middleware (auth, role, rate limit, cache from `config_api`) → route in `router_extend/` → `func_*` in `function_extend/` (using `shared/` and core helpers) → database → `{"status": 1, "message": ...}`.

## Work style
- Complete the requested work autonomously. Ask only for essential missing information or before destructive actions outside the request.
- Read the surrounding code first and match it: naming, density, one-line statements, comment style.
- Never expose `.env` values or other credentials in code, output, or logs.

## Where code goes
| Change | Path |
|---|---|
| API endpoint | `router_extend/<feature>.py` with module-level `router = APIRouter()` |
| Business logic | `function_extend/<feature>.py`, functions named `func_*` |
| Config values and overrides | `config_extend.py`, names `config_*` |
| Constants and data used in several places (`param_specs`, sample JSON, prompts, templates) | `shared/` |
| Standalone worker or job | `script_extend/` |
| Project docs | `docs_extend/` |
| Project Python packages | append to `requirements.txt`, pinned with `==` |

- Do not edit Atom core: `function/`, `router/`, `docs/`, `config.py`, `main.py`, `sync.py`, `AGENTS.md`, `ruff.toml`, `.gitignore`, `Dockerfile`, `readme.md`, `static/api.html`, `static/pgweb.html`, and the scripts listed in `sync.py`. `python sync.py` overwrites them and deletes extra files in `function/`, `router/`, and `docs/`. Edit core only when the user explicitly asks for a framework change.
- `.gitignore` ignores everything not listed. New top-level files or folders are not committed and cannot be added there (sync overwrites it); use the paths above.
- Sync sets Atom's version for every package Atom lists in `requirements.txt`; never rely on a different pin for those.

## Adding an endpoint
1. Write the route in `router_extend/<feature>.py`; put logic in a `func_*` in `function_extend/`.
2. Add the path to `config_api` in `config_extend.py` with a unique `id` (use 200+), explicit `is_token`, and `user_check_role` where roles apply. Startup fails if any route lacks an entry, an entry has no route, or an ID repeats.
3. Extend, never replace, the base dictionaries:
   ```python
   from copy import deepcopy
   from config import config_api as base_config_api, config_postgres as base_config_postgres
   config_api = {**base_config_api, "/order/read": {"id": 200, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}}}
   config_postgres = deepcopy(base_config_postgres)
   ```
   Define each `config_*` name once; keys are not merged for you.

## Route rules
- Signature: `async def func_api_<area>_<name>(*, request: Request):`, then `app_state = request.app.state`.
- Reach helpers, config, and clients only through `app_state` (`app_state.func_x`, `app_state.config_x`, `app_state.client_x`); the per-request database is `request.state.client_postgres` and its schema `request.state.cache_postgres_schema`. Do not import from `function` in routers.
- Read every query, body, form, and header param with `func_request_param_read`; never use `request.query_params`, `request.json()`, `request.form()`, or `request.headers` for params directly. Call it as `await app_state.func_request_param_read(request=request, mode="query"|"body"|"form"|"header", param_specs=[...], strict=True, strict_types=True, reject_unknown=True)`. Specs: `name`, `type` (`str`, `int`, `float`, `bool`, `list`, `list:int`, `dict`, `file`, `any`), `required`, `default`, `allowed`, `minimum`, `maximum`, `min_length`, `max_length`. On routes with `is_postgres_param`, add `{"name": "postgres", "type": "str"}` to query specs.
- Return `{"status": 1, "message": result}`. Errors: `raise app_state.func_api_error(message="...", status_code=4xx|5xx)`; a plain `Exception` becomes 400.
- To list routes use `app_state.func_app_route_list(app=request.app)`; `app.routes` holds one nested entry per router.

## Functions
- Names start with `func_`, use keyword-only arguments (`*,`), and must be unique across `function/` and `function_extend/`; a duplicate fails at import, so a core function cannot be overridden.
- Inside `function_extend/`, import helpers from their defining module (`from function.request import func_query_bool_parse`), not from `function`. Files starting with `_` and subfolders are not loaded.

## Data and security
- Use existing helpers for table access: `func_check_table_permission`, `func_postgres_create/read/update/delete`, ownership via `created_by_id`. See `docs/crud.md` and `docs/ownership.md`.
- SQL: bind values as `$1, $2`; never put values in f-strings. Put identifiers in SQL only after checking `^[a-zA-Z_][a-zA-Z0-9_]*$` or an allow-list, and quote them. Core f-string SQL carries `# noqa: S608 - <reason>`.
- Never pass `is_trusted=True` to `func_postgres_create` with request data.
- Production requires `config_token_secret_key` of 32+ bytes. More than one worker (`config_uvicorn_workers`) requires `redis` instead of `inmemory` for every cache, rate limit, and user check in `config_api`.

## Style
- Section headers, lowercase and singular: routers `# import`, `# router`, `# api`; function modules `# import`, `# function`; scripts `# import`, `# config`, `# logic`, `# main`. No module docstrings.

## Verify before finishing
```bash
venv/bin/ruff check .
venv/bin/python -m unittest discover -s tests
python main.py
```
- Ruff runs strict security and bug rules on core; `*_extend/` and `config_extend.py` are checked for errors only.
- Integration tests run only with `ATOM_TEST_POSTGRES_URL` set; CI runs them and fails below 70% coverage.
- Start the app with `python main.py`, not `uvicorn main:app`, so startup checks run.
- See `docs/extend.md` for full examples, `docs/auth.md` for auth, and `docs/security.md` for security.
