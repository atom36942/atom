# 🛡️ Security Model

Atom's security is **layered and config-driven**. Each layer is enforced in one place and configured as data, so protections are uniform across every endpoint rather than re-implemented per handler.

```
Network       → CORS
Identity      → JWT token (signed, stateless)
Authorization → per-route policy: token → role → deactivated → deleted
Abuse         → rate-limiting
Data access   → table allow-lists · ownership scoping · restricted columns
Input safety  → schema validation · parameter binding · regex checks
Secrets       → env-injected keys
```

---

## 1. Identity — JWT

Requests carry `Authorization: Bearer <token>`. The middleware decodes it (`func_token_decode`) into `request.state.user`. Tokens are HS256-signed with **`config_token_secret_key`** and stateless (nothing stored server-side). Only the fields in `config_column_token_encode` are embedded. See [auth.md](auth.md).

## 2. Authorization — per-route policy

Every route's protection comes from its `config_api` entry, enforced in the middleware **in order**:

| Check | Config field | Rejects |
|-------|-------------|---------|
| Token required | `is_token` | Missing/invalid token. |
| Role | `user_check_role` | Role not in the allowed list. |
| Deactivated | `user_check_deactivated` | `deactivated_at` is set. |
| Deleted | `user_check_deleted` | `deleted_at` is set. |

Each check has a **`mode`** — `token` (trust the JWT claim), `inmemory` (Redis/in-memory cache, TTL `config_redis_cache_ttl_sec`), or `realtime` (live DB query). Use `realtime` for destructive admin ops so a revoked/deactivated user can't act on a stale token; `token`/`inmemory` for cheap, high-traffic reads. See [config.md](config.md#config_api) and [middleware.md](middleware.md).

> **Roles:** role `1` is root/admin. It can't be created via public auth endpoints, and admin routes restrict to `[1]` or `[1,2]`.

## 3. Abuse — rate limiting

Routes with `api_ratelimiting_times_sec` cap requests per window, keyed by **user id** (authenticated) or **client IP** (anonymous). Applied before the handler runs.

## 4. Data access control

Three independent gates protect the generic CRUD layer (see [crud.md](crud.md)):

- **Table allow-lists** — `config_table_public_create_enable` / `_read_enable` (public), `config_table_my_create_disable`, `config_table_my_delete_all_enable`. `"*"` = all, `[]` = none.
- **Ownership scoping** — `config_column_ownership` (`created_by_id`, `user_id`). The `my/*` endpoints filter and stamp by ownership so a user only ever touches their own rows; `admin/*` is unrestricted behind role checks.
- **Restricted columns** — a client can't set server-managed fields in `config_column_admin` (`created_at`, `role`, `verified_at`, …); on `users`, `config_column_admin_users` blocks `role`; and `config_column_single_update` forces sensitive fields (`password`, `email`, `mobile`) to be changed one at a time.
- **Sensitive tables** — `config_table_sensitive` shields core tables (`users`, `log_*`, …) from bulk-cleanup scripts.

## 5. Input safety

- **Schema validation** — table/column names are checked against `cache_postgres_schema`; unknown names are rejected before any SQL runs.
- **Parameter binding** — all values go through `func_postgres_serialize` / `func_postgres_where_build` and are bound as query parameters. User input is never string-interpolated into SQL, so the flexible filter syntax is **not** an injection vector.
- **Regex checks** — `func_regex_check` enforces `config_regex` patterns (e.g. username/password rules) on write.
- **Passwords** — hashed with **Argon2** (`argon2-cffi`); never stored or logged in plaintext.

## 6. Delete safeguards

- `is_protected` rows can't be deleted (`is_enable_is_protected_delete_disable`).
- The root user is protected (`is_enable_root_user_delete_disable`).
- Per-table delete guards: `table_row_delete_disable_all` / `_bulk`.
- Optional role-based delete blocks: `is_enable_users_role_delete_disable_hard` / `_soft`.

See [config.md](config.md#control).

## 7. Secrets & transport

- **Never commit secrets.** `config_token_secret_key` and `config_root_user_password` ship with insecure defaults — override them (and all connection strings) via `.env`, which is git-ignored. See the [README](../readme.md#-secrets-to-override-in-production).
- **CORS** — `config_cors_*`. The default `allow_origin_regex = ".*"` with credentials is permissive for development; **restrict origins in production**.
- **Debug** — set `config_is_debug=0` in production to avoid leaking internals.
- **Error reporting** — configure `config_sentry_dsn` to capture exceptions with `send_default_pii=False`.

---

## Production hardening checklist

- [ ] Set a strong random `config_token_secret_key`.
- [ ] Change `config_root_user_password`.
- [ ] Restrict `config_cors_allow_origins` / `config_cors_allow_origin_regex`.
- [ ] Set `config_is_debug=0`.
- [ ] Use `realtime` mode for role checks on destructive admin routes.
- [ ] Review `config_table_public_*_enable` — expose only what's intended.
- [ ] Set rate limits on auth and write endpoints.
- [ ] Configure `config_sentry_dsn` for monitoring.
- [ ] Point `config_postgres_url` at the primary database used for all reads and writes.

---

📚 [Back to README](../readme.md)
