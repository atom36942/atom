# FAQ

Short answers to common "how do I…" questions. Follow the links for detail.

### How do I check request logs?
Every request is logged to the **`log_api`** table (path, method, status, response time, user, error). Query it:
```sql
SELECT * FROM log_api ORDER BY id DESC LIMIT 50;
```

### How do I see all available APIs?
Hit `/info` (live route list + schema + config) or `/openapi.json` for the OpenAPI spec. The console at `/` renders them.

### What is `api.html` / the page at `/`?
`static/api.html` is Atom's **built-in API console** — a single HTML page served at `/` that lists every endpoint and lets you try requests (set a token, fill params, send) without any external tool. It's driven by `/info` + `/openapi.json`. Change which file is served with `config_root_html_path`, or customize the page by editing `static/api.html`.

### Why is my new endpoint public / ignoring auth?
A route with **no `config_api` entry** defaults to open (no token, no checks). Add an entry with `is_token`/`user_check_role`. See [config.md](config.md#config_api).

### How do I make an admin user?
Role **`1`** is admin. The root user is seeded at startup from `config_root_user_password`. Promote others by setting `role=1` via `/admin/object-update` on the `users` table.

### Why do I get "signup disabled"?
`config_is_enable_signup = 0`. Set it to `1` to allow new users. See [auth.md](auth.md).

### How do I change how long login tokens last?
`config_access_token_expires_sec` / `config_refresh_token_expires_sec`. Rotate with `POST /my/token-refresh`.

### An integration (Redis, S3, …) isn't working — why?
Its client is `None` unless the matching `config_*` is set. Provide it via `.env`. See the [README](../readme.md#configuration).

### How do I add a new table?
Add it to `config_postgres["table"]` (via `config_extend.py`) — created on startup. See [extend.md](extend.md#4-add-or-change-database-tables).

### How do I cache an endpoint's response?
Add `api_cache_sec` to its `config_api` entry, e.g. `["inmemory", 60, 0]`.

### How do I rate-limit an endpoint?
Add `api_ratelimiting_times_sec`, e.g. `["inmemory", 10, 60]` (10 requests / 60s).

### How do I run a raw SQL query?
`POST /admin/postgres-query-runner-read` (or `-write`, or `-read-export` for CSV). See [admin.md](admin.md).

### How do I refresh caches without restarting?
`GET /admin/sync` rebuilds schema/config/role caches and the OpenAPI spec live.

### Where do failed background jobs go?
Appended to `tmp/consumer_failed_payload.jsonl` with the payload + traceback. See [workers.md](workers.md).

### How do I increase the max upload size?
`config_blob_limit_size_kb` (per file) and `config_blob_limit_upload` (file count). See [blob.md](blob.md).

### How do I inspect the database schema or size?
`GET /admin/postgres-schema` and `GET /admin/postgres-info` (`db=main` or `external`).

### How do I update Atom to the latest version?
```bash
venv/bin/python sync.py
```
Your `.env`, `config_extend.py`, `function_extend.py`, and custom routers are preserved. See [extend.md](extend.md#updating-the-framework).

### How do I disable a user without deleting them?
Set `deactivated_at` on the `users` row; routes with a `user_check_deactivated` policy will reject them.

### How do I send a request's work to the background?
Add `?is_background=1` (in-process) or `?queue=redis` on create endpoints to hand off to a worker. See [workers.md](workers.md).

### I'm getting CORS errors in the browser — how do I fix them?
Add your frontend origin to `config_cors_allow_origins` (or set `config_cors_allow_origin_regex`). The default regex `.*` is permissive for dev; restrict it in production. See [security.md](security.md).

### Login returns "incorrect password" — what's wrong?
The identity + **role** pair must match an existing user, and the password must verify. Remember identities are unique *per role*, so the wrong `role` finds no user. See [auth.md](auth.md).

### How do I change the OTP length or expiry?
`config_otp_length` (digits) and `config_otp_expiry_sec` (validity window). See [config.md](config.md#otp).

### How do I run against a read replica?
Set `config_postgres_url_read`. Read endpoints use it automatically and fall back to the primary if unset.

### How do I read/write a second (external) database?
Set `config_postgres_url_external`, then pass `db=external` to the admin query runners / schema endpoints.

### Why is a config value from `.env` being ignored?
Names must start with `config_` and match exactly. Lists/dicts must be JSON; bools accept `true/1/yes/on`. See [config.md](config.md#how-config-is-loaded--overridden).

---

📚 [Back to README](../readme.md)
