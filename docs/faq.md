# ❓ FAQ

Short answers to common "how do I…" questions. Follow the links for detail.

<details>
<summary><strong>How do I check request logs?</strong></summary>

Every request is logged to the **`log_api`** table (path, method, status, response time, user, error). Query it:
```sql
SELECT * FROM log_api ORDER BY id DESC LIMIT 50;
```

</details>

<details>
<summary><strong>How do I see all available APIs?</strong></summary>

Hit `/info` (live route list + schema + config) or `/openapi.json` for the OpenAPI spec. The console at `/` renders them.

</details>

<details>
<summary><strong>What is `api.html` / the page at `/`?</strong></summary>

`static/api.html` is Atom's **built-in API console** — a single HTML page served at `/` that lists every endpoint and lets you try requests (set a token, fill params, send) without any external tool. It's driven by `/info` + `/openapi.json`. Change which file is served with `config_root_html_path`, or customize the page by editing `static/api.html`.

</details>

<details>
<summary><strong>Why is my new endpoint public / ignoring auth?</strong></summary>

A route with **no `config_api` entry** defaults to open (no token, no checks). Add an entry with `is_token`/`user_check_role`. See [config.md](config.md#config_api).

</details>

<details>
<summary><strong>How do I make an admin user?</strong></summary>

Role **`1`** is admin. The root user is seeded at startup from `config_root_user_password`. Promote others by setting `role=1` via `/admin/object-update` on the `users` table.

</details>

<details>
<summary><strong>Why do I get "signup disabled"?</strong></summary>

`config_is_enable_signup = 0`. Set it to `1` to allow new users. See [auth.md](auth.md).

</details>

<details>
<summary><strong>How do I change how long login tokens last?</strong></summary>

`config_access_token_expires_sec` / `config_refresh_token_expires_sec`. Rotate with `POST /my/token-refresh`.

</details>

<details>
<summary><strong>How do I keep a user's activity timestamp current?</strong></summary>

Send an authenticated ping whenever the user is active. This updates the user's `last_active_at`:
```bash
curl -X POST http://localhost:8000/my/ping \
  -H "Authorization: Bearer <access_token>"
```

</details>

<details>
<summary><strong>An integration (Redis, S3, …) isn't working — why?</strong></summary>

Its client is `None` unless the matching `config_*` is set. Provide it via `.env`. See the [README](../readme.md#configuration).

</details>

<details>
<summary><strong>How do I add a new table?</strong></summary>

Add it to `config_postgres["table"]` (via `config_extend.py`) — created on startup. See [extend.md](extend.md#4-add-or-change-database-tables).

</details>

<details>
<summary><strong>How do I cache an endpoint's response?</strong></summary>

Add `api_cache_sec` to its `config_api` entry, e.g. `["inmemory", 60, 0]`.

</details>

<details>
<summary><strong>How do I rate-limit an endpoint?</strong></summary>

Add `api_ratelimiting_times_sec`, e.g. `["inmemory", 10, 60]` (10 requests / 60s).

</details>

<details>
<summary><strong>How do I run a raw SQL query?</strong></summary>

`POST /admin/postgres-query-runner-read` (or `-write`, or `-read-export` for CSV). See [admin.md](admin.md).

</details>

<details>
<summary><strong>How do I refresh caches without restarting?</strong></summary>

`GET /admin/sync` rebuilds schema/config/role caches and the OpenAPI spec live.

</details>

<details>
<summary><strong>Where do failed background jobs go?</strong></summary>

Appended to `tmp/consumer_failed_payload.jsonl` with the payload + traceback. See [workers.md](workers.md).

</details>

<details>
<summary><strong>How do I increase the max upload size?</strong></summary>

`config_blob_limit_size_kb` (per file) and `config_blob_limit_upload` (file count). See [blob.md](blob.md).

</details>

<details>
<summary><strong>How do I inspect the database schema or size?</strong></summary>

`GET /admin/postgres-schema` and `GET /admin/postgres-info`.

</details>

<details>
<summary><strong>How do I update Atom to the latest version?</strong></summary>

```bash
venv/bin/python sync.py
```
Your `.env`, `config_extend.py`, `function_extend.py`, and custom routers are preserved. See [extend.md](extend.md#updating-the-framework).

</details>

<details>
<summary><strong>How do I disable a user without deleting them?</strong></summary>

Set `deactivated_at` on the `users` row; routes with a `user_check_deactivated` policy will reject them.

</details>

<details>
<summary><strong>How do I send a request's work to the background?</strong></summary>

Add `?is_background=1` (in-process) or `?queue=redis` on create endpoints to hand off to a worker. See [workers.md](workers.md).

</details>

<details>
<summary><strong>I'm getting CORS errors in the browser — how do I fix them?</strong></summary>

Add your frontend origin to `config_cors_allow_origins` (or set `config_cors_allow_origin_regex`). The default regex `.*` is permissive for dev; restrict it in production. See [security.md](security.md).

</details>

<details>
<summary><strong>Login returns "incorrect password" — what's wrong?</strong></summary>

The identity + **role** pair must match an existing user, and the password must verify. Remember identities are unique *per role*, so the wrong `role` finds no user. See [auth.md](auth.md).

</details>

<details>
<summary><strong>How do I change the OTP length or expiry?</strong></summary>

`config_otp_length` (digits) and `config_otp_expiry_sec` (validity window). See [config.md](config.md#otp).

</details>

<details>
<summary><strong>How do I read/write a second (external) database?</strong></summary>

Admin query runners and schema endpoints use `config_postgres_url`.

</details>

<details>
<summary><strong>Why is a config value from `.env` being ignored?</strong></summary>

Names must start with `config_` and match exactly. Lists/dicts must be JSON; bools accept `true/1/yes/on`. See [config.md](config.md#how-config-is-loaded--overridden).

</details>

---

📚 [Back to README](../readme.md)
