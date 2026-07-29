# 🛣️ Routers & Adding APIs

This guide shows how Atom's endpoints are structured and how to add your own the idiomatic way.

Routers live in [`router/`](../router). Each file is auto-discovered and mounted at startup by `func_app_router_add` — the only hard requirement is a module-level `router = APIRouter()`. Files load in the order set by `router_order` in `main.py` (`index → auth → my → public → private → admin`); any file not listed loads afterward, alphabetically.

---

## Anatomy of an endpoint

Every existing handler follows the same shape. Here's `/my/api-usage` annotated:

```python
@router.get("/my/api-usage")                     # 1. path + method
async def func_api_my_api_usage(*, request: Request):   # 2. naming convention
    app_state = request.app.state                # 3. grab app.state once
    if not app_state.client_postgres_read_fallback:     # 4. guard needed clients
        raise Exception("postgres read client not initialized")
    oq = await app_state.func_request_param_read(       # 5. read & validate params
        request=request, mode="query", strict=0,
        config=[("days", "int", 1, None, None)])
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        records = await conn.fetch(sql, oq["days"], request.state.user["id"])  # 6. use request.state.user
        obj_list = [dict(r) for r in records]
    return {"status": 1, "message": obj_list}    # 7. standard response
```

---

## 1. Naming convention

| Thing | Convention | Example |
|-------|-----------|---------|
| Route path | `/<tier>/<action-kebab>` | `/my/object-create` |
| Handler function | `func_api_<tier>_<action_snake>` | `func_api_my_object_create` |
| Signature | keyword-only `request` | `async def func_api_...(*, request: Request)` |

Match the tier the route belongs to:

| Tier | Meaning |
|------|---------|
| `index` | Root/meta (health, info, openapi) |
| `auth` | Signup & login (no token) |
| `my` | The authenticated user's own data (`is_token=1`) |
| `public` | Open, unauthenticated endpoints |
| `private` | Authenticated server-side actions (email, blobs) |
| `admin` | Role-restricted privileged ops |

Put your endpoint in the file matching its tier (or a new file — see below).

---

## 2. Reading parameters — `func_request_param_read`

**Never** read `request.query_params` / `request.json()` by hand. Use `func_request_param_read` — it extracts, validates, type-casts, and applies defaults in one call.

```python
oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[
    #  key        dtype   mandatory  allowed_values                   default
    ("table",   "str",   1,         app_state.cache_postgres_schema_table_list, None),
    ("limit",   "int",   0,         None,                             100),
    ("mode",    "str",   0,         ["now", "buffer"],                "now"),
])
```

**`mode`** — where params come from: `"query"`, `"body"` (JSON), `"form"` (multipart, incl. file uploads), or `"header"`.

**`config`** — a list of 5-tuples: `(key, dtype, is_mandatory, allowed_values, default_value)`.
- `dtype` — `int` / `float` / `str` / `bool` / `dict` / `list` / `file` / `any`, or `list:int` etc. for typed lists. Booleans accept `1/true/yes/on/ok`; lists accept JSON or comma-separated strings.
- `is_mandatory` — `1` raises if missing/empty (default must then be `None`).
- `allowed_values` — a whitelist; the value must be one of these (great for validating table names against `cache_postgres_schema_table_list`, or a service against `config_*_services`).
- `default_value` — used when the param is absent.

**`strict`** — `0` keeps unrecognized params too; `1` returns only the keys you declared.

Convention: name the result `oq` (query), `ob` (body), `of` (form). For bulk writes the pattern is `obj_list = ob.get("obj_list", [ob])` so one endpoint accepts a single object or a list.

**Form / file upload** example (`/private/blob-upload-file`):
```python
of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[
    ("service",   "str",  1, app_state.config_blob_services, None),
    ("container", "str",  1, None, None),
    ("file",      "file", 1, None, None)])
```

---

## 3. `request.state` vs `request.app.state`

Two different scopes — don't confuse them:

| | Scope | Set by | Holds |
|---|-------|--------|-------|
| `request.app.state` | Application (shared, whole process) | The lifespan in `main.py` | All clients (`client_*`), caches (`cache_*`), config (`config_*`), and functions (`func_*`). |
| `request.state` | This request only | The middleware, per request | `request.state.user` — the decoded JWT claims (`{}` if unauthenticated). |

So:
- Get the authenticated user's id: `request.state.user["id"]` (safe on `is_token=1` routes; use `request.state.user.get("id")` on public routes where a token is optional).
- Get a DB client / config / helper: `request.app.state.client_postgres`, `app_state.config_batch_item_limit`, `app_state.func_postgres_read(...)`.

Idiom: bind `app_state = request.app.state` on the first line, then reference `app_state.*`.

---

## 4. Keep routes thin — push logic into `func_*`

Handlers should **orchestrate, not implement**. A route ideally does only: read params → guard clients/permissions → call one or more `func_*` → return. Heavy logic (queries, external calls, transforms) belongs in a function so it's testable and reusable.

- **Core** helpers live in `function.py` (`func_postgres_read`, `func_blob_upload_file`, `func_token_encode`, …).
- **Your** helpers go in `function_extend.py` — auto-loaded and merged onto `app.state`, so they're reachable exactly like core ones and survive `sync.py` updates. See [extend.md](extend.md).

```python
# function_extend.py
async def func_report_generate(*, client_postgres, user_id, days):
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch("SELECT ... WHERE created_by_id=$1 ...", user_id)
    return [dict(r) for r in rows]
```
```python
# router/report.py
@router.get("/my/report")
async def func_api_my_report(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0,
        config=[("days", "int", 0, None, 7)])
    data = await app_state.func_report_generate(
        client_postgres=app_state.client_postgres_read_fallback,
        user_id=request.state.user["id"], days=oq["days"])
    return {"status": 1, "message": data}
```

Note `func_*` are written as **pure functions** with keyword-only args and explicit dependencies passed in (client, config values) rather than reaching for globals — that's why routers pass `app_state.client_...` and `app_state.config_...` into them.

---

## 5. Response structure

Every endpoint returns the same envelope so clients can handle responses uniformly:

```python
{"status": 1, "message": <payload>}
```

- `status` — `1` means success. (Errors never reach your `return`: an exception is caught by the middleware, which produces the error response and logs it — so you just `raise Exception("...")` for any failure.)
- `message` — the payload: an object, a list, a token dict, or a nested shape.

Common payload shapes in the codebase:
```python
return {"status": 1, "message": user}                       # single object
return {"status": 1, "message": {"obj_list": rows,          # list + pagination
                                 "has_next_page": has_more}}
return {"status": 1, "message": token}                      # {access_token, refresh_token}
```
For non-JSON responses (files, streams), return a Starlette/FastAPI response directly — e.g. `responses.FileResponse(...)` as `/` does.

**Error handling:** don't try/except for control flow or build error dicts yourself. Just `raise Exception("clear message")`; the middleware sets `response_type="error"`, formats it, reports to Sentry (if configured), and still logs the request. See [middleware.md](middleware.md).

---

## 6. Register the endpoint's policy

Adding the route file makes it *reachable*, but auth/rate-limit/cache come from `config_api`. A path with no entry is **public** (no token, no checks). To protect or tune it, add an entry (via `config_extend.py` so it survives updates):

```python
# config_extend.py
from config import config_api
config_api = {**config_api,
    "/my/report": {"id": 210, "is_token": 1, "api_cache_sec": ["inmemory", 30, 0]},
}
```

See [config.md](config.md#config_api) for every field (`is_token`, `user_check_role`, `api_ratelimiting_times_sec`, `api_cache_sec`, and the `token`/`inmemory`/`realtime` modes).

> `func_check` runs at startup and validates `config_api` entries — a malformed policy fails the boot early.

---

## Checklist for a new API

1. Pick the tier; add the handler to `router/<tier>.py` (or a new `router/<name>.py`).
2. Name it `func_api_<tier>_<action>`, signature `(*, request: Request)`.
3. `app_state = request.app.state`; guard any client you rely on.
4. Read params with `func_request_param_read` (`oq`/`ob`/`of`).
5. Enforce ownership/permission (`request.state.user`, `config_column_admin`, table allow-lists).
6. Put real logic in a `func_*` (in `function_extend.py`); call it from the route.
7. `return {"status": 1, "message": ...}`; `raise` on any error.
8. Add a `config_api` entry if it needs a token, roles, rate-limit, or caching.

---

📚 [Back to README](../readme.md)
