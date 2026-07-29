# 🚦 HTTP Middleware

Every request to Atom passes through **one** HTTP middleware defined in [`main.py`](../main.py) (`@app.middleware("http")`) before it reaches a route handler. The middleware only **orchestrates** — the actual logic for each step lives in `func_middleware_*` functions in [`function.py`](../function.py). A separate `CORSMiddleware` wraps it for cross-origin handling.

```
Request
  → (OPTIONS? short-circuit)
  → init request state
  → look up per-route policy (config_api)
  → decode token
  → check: auth → role → deactivated → deleted
  → rate-limit
  → cache GET ──(hit)──▶ response
       │(miss)
  → background dispatch  OR  run handler → cache SET
  → (on error) build error response
  → buffer API log row
  → Response
```

---

## Step-by-step

### 0. OPTIONS short-circuit
`if request.method == "OPTIONS": return await api_function(request)` — CORS preflight requests skip all checks and pass straight through (the CORS middleware handles them).

### 1. Initialize request state
Sets a timer (`start`) for response-time measurement, and defaults `error = None`, `response_type = "direct_no_cache_set"`, and `request.state.user = {}`. `response_type` is a label that ends up in the API log describing how the request was served.

### 2. Resolve the route policy
Reads the matched route's path and looks up its entry in `config_api`:

```python
api_cfg = app_state.config_api.get(route_path, {})
```

From it, pulls `is_token`, `user_check_role`, `user_check_deactivated`, `user_check_deleted`, `api_ratelimiting_times_sec`, and `api_cache_sec`. A path with **no entry** gets an empty dict → all checks default to off/public. See [config.md](config.md#config_api) for the shape of these fields.

### 3. Decode token (`func_token_decode`)
Parses the `Authorization` header and verifies the JWT with `config_token_secret_key`. On success `request.state.user` becomes the decoded claims (id, role, …); otherwise it stays empty. This never rejects on its own — enforcement happens next.

### 4. Auth & user-state checks
Four checks run in order, each a no-op unless the route's policy asks for it:

| Step | Function | Rejects when |
|------|----------|--------------|
| Auth | `func_middleware_check_auth` | `is_token=1` but no valid user. |
| Role | `func_middleware_check_role` | User's role isn't in the allowed list. |
| Deactivated | `func_middleware_check_user_deactivated` | User's `deactivated_at` is set. |
| Deleted | `func_middleware_check_user_deleted` | User's `deleted_at` is set. |

The role/deactivated/deleted checks honor the policy's `mode` (`token` / `inmemory` / `realtime`) to decide whether to trust the JWT, read the in-memory/Redis cache (TTL `config_redis_cache_ttl_sec`), or query Postgres live. Any failure raises and jumps to the error handler (step 8).

### 5. Rate-limit (`func_middleware_check_ratelimiter`)
If the route defines `api_ratelimiting_times_sec`, enforces "at most N requests per window" keyed by the **user id** (if authenticated) or **client IP** (if not). Over-limit raises.

### 6. Cache lookup (`func_middleware_api_cache`, `mode="get"`)
If the route is cacheable, builds a key from path + query params + user id and checks for a stored response. **On hit**, that response is returned immediately (`response_type = "cache_response"`) — the handler never runs.

### 7. Handle the request (on cache miss)
Two paths:

- **Background** — if the query string has `is_background=1`, the request is handed to `func_middleware_api_background` (reads the body + scope, schedules the work) and returns right away with `response_type = "background_added"`.
- **Direct** — otherwise the actual route handler runs (`await api_function(request)`), then `func_middleware_api_cache(mode="set")` stores the response if the route is cacheable (`response_type = "direct_cache_set"` when it does).

### 8. Error handling (`func_middleware_api_response_error`)
Any exception from steps 2–7 is caught here: `response_type = "error"`, and the function builds a safe error response (with traceback capture and Sentry reporting when `config_sentry_dsn` is set). The request is never left unhandled.

### 9. API logging (always)
Finally — success or error — if Postgres is configured, one `log_api` row is **buffered** (not written synchronously) via `func_postgres_create(mode="buffer")`, capturing: user id, `response_type`, IP, path, method, query params, status code, `response_time_ms`, and any error. Wrapped in `suppress(Exception)` so logging can never break the response. The buffer is drained by the `pulse_flush` loop — see [lifespan.md](lifespan.md).

### 10. Return
The response (cached, background ack, handler output, or error) is returned to the client.

---

## CORS

After the main middleware, `CORSMiddleware` is added using the `config_cors_*` settings (allowed origins/regex, methods, headers, credentials). Because it's added last, it runs outermost — handling preflight and attaching CORS headers around every response.

---

## Why one middleware

Centralizing auth, rate-limiting, caching, background dispatch, error handling, and logging in a single pipeline means:
- **Uniform enforcement** — every endpoint gets the same guarantees, driven by `config_api` data rather than per-handler code.
- **Thin handlers** — route functions focus on business logic; cross-cutting concerns live here.
- **Fast path** — cache hits and rejections short-circuit before the handler; logging is buffered off the hot path.

---

📚 [Back to README](../readme.md)
