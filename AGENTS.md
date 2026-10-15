# Atom coding guide

- Complete requested work autonomously; ask only for essential missing information or destructive actions outside the request.
- For project APIs, use `router_extend/<feature>.py` (export `router = APIRouter()`), `function_extend/<feature>.py` (define `func_*` helpers), and `config_extend.py` (define `config_*` overrides). Modules load automatically; see `docs/extend.md` for examples and discovery rules.
- Put project constants and data used in several places in `shared/`: reusable values such as `param_specs` as Python modules (`from shared.specs import ...`), and files such as sample JSON, prompts, contexts, and templates (read by path from the project root, e.g. `Path("shared/prompts/x.txt")`). Sync never touches `shared/`; keep runtime output in `tmp/` or blob storage and secrets in `.env`.
- Keep project changes out of synced core files and folders listed in `sync.py`, including this file. Edit core only for requested framework changes.
- Add each route's policy to `config_api` with an unused ID and explicit authentication/role requirements. Preserve base dictionary entries; deep-copy nested schema dictionaries before extending. See `docs/extend.md` and `docs/auth.md`.
- Access helpers, config, and shared clients through `request.app.state`; use request-selected database/schema from `request.state` where applicable. Follow `router/private.py` and `router/my.py`.
- Validate input with `func_request_param_read`; use strict types and reject unknown fields for new APIs. Return `{"status": 1, "message": result}`; raise `func_api_error` with an appropriate HTTP status.
- Enforce table permissions and ownership; use existing CRUD helpers or parameterized SQL. See `docs/crud.md`, `docs/ownership.md`, and `docs/security.md`.
- Keep credentials in environment variables; never expose `.env` values.
