# ❓ FAQ

Practical answers to common "how do I…" questions. Open a question for the steps, examples, and links to the full documentation.

<details>
<summary><strong>How do I check request logs?</strong></summary>

Every request is recorded in the **`log_api`** table. The row includes the path, HTTP method, response status, execution time, authenticated user, and any captured error, making it the first place to look when an endpoint behaves unexpectedly.

Use an admin SQL read query to inspect the newest requests:

```sql
SELECT * FROM log_api ORDER BY id DESC LIMIT 50;
```

Filter by fields such as `path`, `status`, or `user_id` when investigating a specific route or user. For ongoing production monitoring, forward application errors to Sentry and use `log_api` for request-level detail.

</details>

<details>
<summary><strong>How do I see all available APIs?</strong></summary>

Atom exposes the API in three useful formats:

- Open `/` for the interactive API console. It lists routes and lets you send requests from the browser.
- Request `GET /info` for Atom's live route list, database schema, and safe configuration metadata.
- Request `GET /openapi.json` when you need the standard OpenAPI document for a client generator, API tool, or frontend integration.

The console reads `/info` and `/openapi.json`, so restart the app after changing routes. If only cached schema or policy information is stale, run `GET /admin/sync`.

</details>

<details>
<summary><strong>What is `api.html` / the page at `/`?</strong></summary>

`static/api.html` is Atom's **built-in API console**, served at `/`. It discovers endpoints from `/info` and `/openapi.json`, then provides fields for path/query parameters, request bodies, and bearer tokens so you can test the API without Postman or another external tool.

To brand or extend the console, edit `static/api.html`. To serve a different root page entirely, point `config_root_html_path` at another HTML file. This affects the browser UI only; the API routes and OpenAPI document continue to work independently.

</details>

<details>
<summary><strong>Why is my new endpoint public / ignoring auth?</strong></summary>

Atom applies authentication and authorization from `config_api`, not from the router filename. A route with **no matching `config_api` entry** receives an empty policy and is public by default.

Add the exact route path and enable the checks you need:

```python
config_api["/my/report"] = {
    "id": 210,
    "is_token": 1,
    "user_check_role": ["token", [1, 2]],
    "user_check_deactivated": ["realtime"],
}
```

Make sure the path exactly matches the registered route, then restart the app so startup validation can check the policy. See [config.md](config.md#config_api) and [middleware.md](middleware.md).

</details>

<details>
<summary><strong>How do I make an admin user?</strong></summary>

Role **`1`** is the administrator role. On startup, Atom seeds the root administrator using `config_root_user_password`; override that value with a strong secret in `.env` before deploying.

To promote an existing user, authenticate as an administrator and update that user's `role` to `1` through `/admin/object-update` on the `users` table. Confirm the target user ID first—admin routes can access and modify data across users.

Public signup cannot create role `1` users, which prevents callers from granting themselves administrator access.

</details>

<details>
<summary><strong>Why do I get "signup disabled"?</strong></summary>

The application is running with `config_is_enable_signup = 0`. In that mode, password signup is rejected, and OTP or Google login cannot automatically create a user on their first login.

Set the value in `.env` or `config_extend.py`, then restart Atom:

```python
config_is_enable_signup = 1
```

If signup should remain closed, create the user through an administrator workflow instead; existing users can still log in. See [auth.md](auth.md).

</details>

<details>
<summary><strong>How do I change how long login tokens last?</strong></summary>

Set the lifetimes in seconds with `config_access_token_expires_sec` and `config_refresh_token_expires_sec`. For example, this gives access tokens a 15-minute lifetime and refresh tokens a 30-day lifetime:

```python
config_access_token_expires_sec = 900
config_refresh_token_expires_sec = 2592000
```

The values apply when a token pair is issued, so changing them does not rewrite tokens that already exist. Before the access token expires, the client can send its refresh token to `POST /my/token-refresh` to receive a new pair. Keep access tokens relatively short-lived and store refresh tokens more carefully.

</details>

<details>
<summary><strong>How do I keep a user's activity timestamp current?</strong></summary>

Send an authenticated ping while the user is active. `POST /my/ping` updates the current user's `last_active_at` timestamp and is useful for presence indicators, inactivity rules, and basic activity reporting.

```bash
curl -X POST http://localhost:8000/my/ping \
  -H "Authorization: Bearer <access_token>"
```

Call it on a reasonable interval—such as every few minutes while the app is focused—instead of on every mouse movement or keystroke. Stop pinging when the user logs out or the app becomes inactive.

</details>

<details>
<summary><strong>An integration (Redis, S3, …) isn't working — why?</strong></summary>

Integrations are optional and their clients remain `None` until the matching `config_*` values are present. Start by checking that the required URL, credentials, region, or provider setting is available to the running process—not only in your terminal.

Add the values to `.env`, restart Atom, and watch the startup output for connection or permission errors. Then verify the external service is reachable from the same machine or container. For example, Redis needs the relevant `config_redis_url*`, while S3 needs its region and AWS credentials.

Do not commit secrets to `config.py`. Use `.env` for environment-specific credentials and see the [configuration guide](../readme.md#configuration) for the available integrations.

</details>

<details>
<summary><strong>How do I add a new table?</strong></summary>

Define the table under `config_postgres["table"]`, preferably from `config_extend.py` so framework updates do not overwrite your customization. The first column must be Atom's standard primary key:

```python
config_postgres["table"]["project"] = [
    {"name": "id", "datatype": "bigserial", "is_primary": 1},
    {"name": "title", "datatype": "varchar(200)", "is_mandatory": 1},
    {"name": "created_at", "datatype": "timestamptz", "default": "CURRENT_TIMESTAMP"},
]
```

Restart Atom after the change. Startup schema initialization creates the table and missing columns, then refreshes the schema cache used by generic CRUD routes. Review data types, defaults, indexes, and uniqueness rules before applying changes to production. See [extend.md](extend.md#4-add-or-change-database-tables).

</details>

<details>
<summary><strong>How do I cache an endpoint's response?</strong></summary>

Add `api_cache_sec` to the route's `config_api` policy. The format is `[mode, ttl_seconds, user_flag]`:

```python
config_api["/public/catalog"] = {
    "id": 211,
    "is_token": 0,
    "api_cache_sec": ["inmemory", 60, 0],
}
```

This example caches matching responses for 60 seconds. Cache keys include the route and query string; set the final flag to `1` when responses must also be isolated by authenticated user. Use `"redis"` instead of `"inmemory"` when multiple Atom processes need to share the same cache, and configure Redis first.

Cache read-heavy endpoints whose responses may safely be slightly stale. Avoid caching rapidly changing or side-effecting responses.

</details>

<details>
<summary><strong>How do I rate-limit an endpoint?</strong></summary>

Add `api_ratelimiting_times_sec` to the route's `config_api` entry. Its format is `[mode, request_count, window_seconds]`:

```python
config_api["/public/otp-send-email"] = {
    "id": 212,
    "is_token": 0,
    "api_ratelimiting_times_sec": ["inmemory", 10, 60],
}
```

This permits at most 10 requests in 60 seconds. Authenticated traffic is keyed by user ID; anonymous traffic is keyed by client IP. Use `"redis"` for a shared limit across multiple workers or servers, because each process has its own in-memory counters.

Choose tighter limits for sensitive or costly routes such as login, OTP, uploads, and AI calls. See [security.md](security.md).

</details>

<details>
<summary><strong>How do I run a raw SQL query?</strong></summary>

Use the administrator query-runner endpoints, choosing the narrowest operation that fits:

- `POST /admin/postgres-query-runner-read` executes a read query and returns rows.
- `POST /admin/postgres-query-runner-write` executes a data-changing query.
- `POST /admin/postgres-query-runner-read-export` returns read results as CSV.

These routes use the configured Postgres connection and require the appropriate admin policy/token. Prefer parameterized application functions for normal product behavior; the query runner is best for trusted administration, diagnostics, and one-off maintenance. Test write statements as reads or inside a transaction before modifying production data. See [admin.md](admin.md).

</details>

<details>
<summary><strong>How do I refresh caches without restarting?</strong></summary>

Call `GET /admin/sync` with an authorized token. It reloads runtime caches for the database schema, configuration, user roles/status, and generated OpenAPI document without requiring a full process restart.

Use it after an out-of-band database or configuration-table change when Atom's cached view is stale. It does **not** reload edited Python source files or recreate external clients; restart the application for code changes, `.env` changes, or integration connection changes.

</details>

<details>
<summary><strong>Where do failed background jobs go?</strong></summary>

A worker appends an unrecoverable job to `tmp/consumer_failed_payload.jsonl`. Each JSON Lines record contains the original payload and traceback, so one failed job does not make the whole file unreadable.

Inspect the traceback, correct the underlying data or service problem, and replay only the jobs you have verified are safe. Be careful with non-idempotent operations: blindly replaying a partially completed create or external call can produce duplicates.

The `tmp` directory is runtime storage and is recreated when Atom starts, so forward or archive failures elsewhere if you need durable production retention. See [workers.md](workers.md).

</details>

<details>
<summary><strong>How do I increase the max upload size?</strong></summary>

Adjust both upload controls:

```python
config_blob_limit_size_kb = 2048  # 2 MB per file
config_blob_limit_upload = 20     # files per request
```

`config_blob_limit_size_kb` applies to each file, while `config_blob_limit_upload` caps the number of files in one request. Restart Atom after changing the configuration.

Also check limits imposed by your reverse proxy, hosting platform, and storage provider; a request rejected before it reaches Atom cannot be fixed by Atom's settings alone. Larger uploads increase memory, bandwidth, and storage exposure, so keep the limits no higher than the product requires. See [blob.md](blob.md).

</details>

<details>
<summary><strong>How do I inspect the database schema or size?</strong></summary>

Use the two authenticated inspection endpoints:

- `GET /admin/postgres-schema` returns Atom's view of tables and columns, which is useful when building CRUD requests or checking whether a migration was detected.
- `GET /admin/postgres-info` reports database-level information such as storage and connection details exposed by the framework.

Both responses are cached by default. If you changed the database directly and the result looks stale, call `GET /admin/sync` or wait for the cache TTL before checking again.

</details>

<details>
<summary><strong>How do I update Atom to the latest version?</strong></summary>

```bash
venv/bin/python sync.py
```

Run the command from the project root and review its output. The updater refreshes framework-managed files while preserving your `.env`, `config_extend.py`, `function_extend.py`, and custom routers.

Commit or back up your work first, then review the Git diff after syncing and run the application/tests before deploying. Keeping custom behavior in the extension files reduces conflicts with future framework updates. See [extend.md](extend.md#updating-the-framework).

</details>

<details>
<summary><strong>How do I disable a user without deleting them?</strong></summary>

Set `deactivated_at` on the user's row instead of deleting it. This preserves the account, ownership relationships, and audit history while marking the user as inactive.

Routes configured with `user_check_deactivated` will then reject the user. Check that sensitive routes actually include this policy—deactivation is enforced by route configuration, not automatically on every endpoint.

To restore access, clear `deactivated_at` and refresh the relevant caches with `GET /admin/sync` if necessary.

</details>

<details>
<summary><strong>How do I send a request's work to the background?</strong></summary>

Create endpoints support two ways to move work off the request path:

- Add `?is_background=1` for an in-process background task. This is simple and fast, but the task can be lost if the API process stops.
- Add `?queue=redis` (or another configured queue mode) to publish the payload for a separate worker. This is the better choice for durable, scalable, or slow workloads.

Make sure the selected queue client is configured and its consumer process is running before publishing jobs. Design handlers to be idempotent so retries cannot create duplicates, and monitor `tmp/consumer_failed_payload.jsonl` for terminal failures. See [workers.md](workers.md).

</details>

<details>
<summary><strong>I'm getting CORS errors in the browser — how do I fix them?</strong></summary>

CORS errors occur when the browser's frontend origin is not allowed by the API. Add the exact origin—including scheme and port—to `config_cors_allow_origins`:

```python
config_cors_allow_origins = [
    "https://app.example.com",
    "http://localhost:3000",
]
```

Alternatively, use a narrowly scoped `config_cors_allow_origin_regex` for controlled subdomains. The default `.*` is convenient in development but should be restricted in production, especially when credentials are allowed.

Restart Atom after changing these values. If the preflight still fails, inspect the browser network panel and verify that the requested method and headers are permitted and that a reverse proxy is not stripping CORS headers. See [security.md](security.md).

</details>

<details>
<summary><strong>Login returns "incorrect password" — what's wrong?</strong></summary>

Atom looks up password logins by both the supplied identity and **role**. A valid username or email with the wrong role behaves like a missing user and returns the same generic password error.

Check that:

- the request uses the same role selected when the user was created;
- the correct login endpoint and identity field are being used;
- the user exists and has a password hash;
- the submitted password has not been altered by whitespace or client-side encoding.

Passwords are Argon2 hashes and cannot be recovered from the database. Reset the password through an authorized workflow rather than editing the hash manually. See [auth.md](auth.md).

</details>

<details>
<summary><strong>How do I change the OTP length or expiry?</strong></summary>

Set the number of generated digits and the validity window in seconds:

```python
config_otp_length = 6
config_otp_expiry_sec = 600  # 10 minutes
```

The new length applies to codes generated after restart, while verification uses the configured expiry against the code's creation time. If you change the length, also update any frontend validation and message templates that assume six digits.

Shorter windows reduce the time available for abuse but can frustrate users when email or SMS delivery is delayed. Pair OTP endpoints with rate limits and avoid logging codes in production. See [config.md](config.md#otp).

</details>

<details>
<summary><strong>How do I read/write a second (external) database?</strong></summary>

`config_postgres_url` is Atom's primary Postgres connection and is used by CRUD, admin query runners, and schema endpoints. Pointing it at another database switches the application datastore; it does not create a separate named secondary connection.

If you need the main application and a second database at the same time, create an additional client in `function_extend.py` or your own lifespan integration, then expose narrowly scoped functions/routes for that database. Keep credentials in `.env`, use parameterized queries, and give the secondary database account only the permissions it needs.

For a one-database deployment, simply change `config_postgres_url` and restart Atom so the connection pool and schema cache are rebuilt.

</details>

<details>
<summary><strong>Why is a config value from `.env` being ignored?</strong></summary>

Atom only loads environment overrides whose names start with `config_` and exactly match a configuration variable. Environment values are parsed according to the original value's type.

Check the common causes:

- the variable name has a typo or incorrect capitalization;
- `.env` is not in the process working directory or is not available inside the container;
- lists and dictionaries are not valid JSON;
- the process was not restarted after the change;
- `config_extend.py` overrides the value later during startup.

For example:

```dotenv
config_is_enable_signup=false
config_cors_allow_origins=["https://app.example.com"]
```

Booleans accept values such as `true`, `1`, `yes`, and `on`; structured values must use JSON with double-quoted strings. Never print secret values while debugging—confirm only whether they were loaded. See [config.md](config.md#how-config-is-loaded--overridden).

</details>

---

📚 [Back to README](../readme.md)
