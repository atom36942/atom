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

Atom applies authentication and authorization from `config_api`, not from the router filename. Current versions require **every registered route** to have a matching entry; startup fails if a route is missing so an accidentally unprotected endpoint cannot silently go live.

Add the exact route path and enable the checks you need:

```python
config_api["/my/report"] = {
    "id": 210,
    "is_token_check": 1,
    "user_check_role": {"mode": "token", "roles": [1, 2]},
    "user_check_deactivated": {"mode": "realtime"},
}
```

For an intentionally public route, still register it with `"is_token_check": 0`. Make sure the path exactly matches the registered route, every entry has a unique positive `id`, and protected routes set `"is_token_check": 1`. Then restart the app so startup validation can check the policy. See [config.md](config.md#config_api) and [middleware.md](middleware.md).

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

Add `cache` to the route's `config_api` policy. The format is `{"mode": "inmemory", "ttl_sec": 60, "is_per_user": 0}`:

```python
config_api["/public/catalog"] = {
    "id": 211,
    "is_token_check": 0,
    "cache": {"mode": "inmemory", "ttl_sec": 60, "is_per_user": 0},
}
```

This example caches matching responses for 60 seconds. Cache keys include the route and query string; set `is_per_user` to `1` when responses must also be isolated by authenticated user. Use `"redis"` instead of `"inmemory"` when multiple Atom processes need to share the same cache, and configure Redis first.

Cache read-heavy endpoints whose responses may safely be slightly stale. Avoid caching rapidly changing or side-effecting responses.

</details>

<details>
<summary><strong>How do I rate-limit an endpoint?</strong></summary>

Add `rate_limit` to the route's `config_api` entry. Its format is `{"mode": "inmemory", "limit": 10, "window_sec": 60}`:

```python
config_api["/public/otp-send-email"] = {
    "id": 212,
    "is_token_check": 0,
    "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60},
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

Make sure the selected queue client is configured and its consumer process is running before publishing jobs. Design handlers to be idempotent so retries cannot create duplicates, and monitor `tmp/consumer_failed_payload.jsonl` for terminal failures. See [Object Queues](queue.md) for object API details and [Background Workers](workers.md) for broader worker patterns.

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

Atom only loads environment overrides whose names start with `config_` and match a configuration variable. Matching is case-insensitive for Windows compatibility, although lowercase `config_*` is the canonical style. Environment values are parsed according to the original value's type.

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

<details>
<summary><strong>Does Atom require Postgres, Redis, or every listed integration to start?</strong></summary>

No. Integrations are opt-in: if a connection URL or credential is unset, Atom leaves that client as `None` and continues starting. A bare installation can serve `/`, `/health`, `/info`, and other routes that do not depend on a missing service.

Features still require their backing service. Generic CRUD, authentication records, request logs, and the example WebSocket need Postgres. Shared caching and rate limits need Redis, while queues, blob storage, email, SMS, and AI features need their selected provider.

Custom routes should check the client they depend on and return a clear error when it is unavailable. See [about.md](about.md) for the component overview.

</details>

<details>
<summary><strong>What is the difference between `/public`, `/my`, and `/admin` CRUD?</strong></summary>

The prefixes represent data-access scope, not just route organization:

- `/public/object-*` is anonymous and limited by `config_table_public_create_enable` and `config_table_public_read_enable`.
- `/my/object-*` requires a user and automatically scopes rows through ownership columns such as `created_by_id` or `user_id`.
- `/admin/object-*` can operate on any row and table, subject to its administrator route policy.

Use `/my` for normal user-owned product data and `/admin` only for trusted operations. Do not expose a table publicly merely to avoid ownership configuration; add an ownership column and use the authenticated tier instead.

For endpoint-by-endpoint curl examples covering create, read, update, and delete in all three tiers, see [Object APIs](object.md). For filter and relation internals, see [Generic CRUD](crud.md).

</details>

<details>
<summary><strong>How do filtering, sorting, and pagination work on object reads?</strong></summary>

Pass `table`, `filter`, `order`, `limit`, and `page` to an object-read endpoint. Filters are a list of conditions; separate list items are combined with `AND`, while `OR` can appear inside a condition:

```text
GET /my/object-read?table=test&filter=["type = 1","title ilike %atom%"]&order=id desc&limit=20&page=1
```

The response contains `obj_list` and `has_next_page`. Atom fetches one extra row to calculate that flag, and caps the requested limit with `config_sql_read_limit_max`.

Table and column names are validated against the live schema, and filter values are parameter-bound. Supported operators include comparisons, ranges, text matching, arrays, and JSON operations. See [Reading Objects](read.md#filters) for encoding and examples.

</details>

<details>
<summary><strong>How do I include related rows without creating an N+1 query problem?</strong></summary>

Use the `relation` parameter on object reads. A relation describes the local key, related table, and foreign key; Atom collects the relevant IDs and fetches related rows in a batched query instead of issuing one query per result.

Relation result size is capped by `config_sql_read_relation_fetch_limit_max`. On public reads, the related table must also be present in the public read allow-list, so a relation cannot bypass table access rules.

Keep relation payloads focused and select only the columns the client needs. For deeply nested or domain-specific projections, a custom endpoint and purpose-built query may be clearer and more efficient. See [Reading Objects](read.md#relations) for the five-part syntax and examples.

</details>

<details>
<summary><strong>What does `mode=buffer` do, and when should I use it?</strong></summary>

The `/public/object-create`, `/my/object-create`, and `/admin/object-create` APIs accept `mode=now` or `mode=buffer`. The default, `mode=now`, inserts into PostgreSQL during the request and normally returns the created IDs. `mode=buffer` validates and serializes the objects, then keeps them temporarily in the API process's memory so multiple rows can be inserted as a batch:

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test&mode=buffer" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Buffered object","type":1}'
```

A successful response with `"message": "buffered"` means the row is accepted in memory but is **not yet committed or readable from PostgreSQL**. `"buffered released"` means that buffer group reached its limit and was inserted immediately.

Pending groups are flushed when they reach the table's `buffer_limit`, approximately every 60 seconds, by `GET /admin/sync`, and during graceful shutdown. `config_table[<table>]["buffer_limit"]` overrides `config_buffer_limit_default`. Rows are grouped by table and column shape, so differently shaped objects can reach their limits independently.

Use buffering for high-volume, low-urgency records where delayed visibility and possible loss during a crash or forced shutdown are acceptable. Use `mode=now` when the caller needs the inserted ID, must read the row immediately, or requires database persistence before success is returned.

`mode=buffer` is process-local batching, not a durable queue. For broker-backed asynchronous work, use the supported `queue` parameter and keep queued creates on their default `mode=now`; combining `queue` with `mode=buffer` can leave records only in consumer memory. See [PostgreSQL Buffers](buffer.md) and [Object Queues](queue.md#queue-versus-modebuffer).

</details>

<details>
<summary><strong>How should I add custom code without making future updates painful?</strong></summary>

Keep project-specific changes outside framework-managed files:

- Put configuration overrides in `config_extend.py`.
- Put new or overridden `func_*` logic in `function_extend.py`.
- Add endpoints in a new `router/<name>.py` containing an `APIRouter`.
- Add standalone consumers and jobs under `script/`.

Register every custom route in `config_api`; use `"is_token_check": 0` for an intentionally public route, then add role checks, caching, or rate limiting as needed. `sync.py` overwrites core files and the shipped documentation, but preserves extension files, custom routers, and `.env`.

If you are fixing Atom itself for everyone, edit the core source and submit a pull request instead. See [extend.md](extend.md).

</details>

<details>
<summary><strong>How do I start Atom with a read-only PostgreSQL URL?</strong></summary>

Enable Atom's global read-only mode and use read-only database credentials as the primary connection:

```dotenv
config_postgres_url=postgresql://readonly_user:password@host:5432/database
config_is_read_only=1
```

When read-only mode is enabled, Atom:

- configures the primary and named asyncpg pools with `default_transaction_read_only=on`;
- skips PostgreSQL schema initialization, regardless of `config_is_enable_postgres_schema_init`;
- does not start the periodic PostgreSQL buffer-flush task;
- does not buffer request records into `log_api`; and
- skips final primary and API-log buffer flushes during shutdown.

Read routes continue to work normally. Write-capable routes remain registered, including generic CRUD, OTP generation, first-login user creation, message read-marking, blob metadata operations, the WebSocket example, and the admin write-query runner. If one is called, PostgreSQL rejects its write because every transaction on Atom's pools is read-only.

Use an actual read-only PostgreSQL role as well. `config_is_read_only` prevents Atom's expected lifecycle writes and makes its pools read-only, while database permissions provide an independent enforcement boundary for custom code, separately configured clients, workers, and scripts.

The setting only controls PostgreSQL activity created through the pools initialized by `main.py`. It does not disable writes to Redis, MongoDB, object storage, queues, local files, or independent PostgreSQL connections opened by standalone workers and scripts. Do not run write consumers, ingestion scripts, or deletion workers as part of a read-only deployment.

Use the read-only URL as `config_postgres_url`, rather than configuring only a named URL such as `config_postgres_url_read`, when Atom needs its normal primary schema and authorization caches. Named pools are intended for explicitly selected read endpoints and do not replace the primary connection during startup.

</details>

<details>
<summary><strong>Will automatic schema initialization delete or alter existing database objects?</strong></summary>

It can. When `config_is_enable_postgres_schema_init = 1`, startup compares `config_postgres` with the live schema and applies configured tables, columns, constraints, indexes, extensions, and triggers. The `config_postgres["control"]` flags determine whether missing tables or columns may be dropped and whether mismatched column types may be recreated.

Review those controls carefully before pointing Atom at an existing or production database. Back up the database, test schema changes on a copy, and use a database account with appropriately limited privileges. For a safe column rename, set the column's `old` key instead of removing one name and adding another. See [config.md](config.md#control).

</details>

<details>
<summary><strong>Can I run multiple API workers or multiple Atom instances?</strong></summary>

Yes, but in-memory state is local to each process. Response caches, rate-limit counters, and buffered writes are not automatically shared between workers.

Use Redis modes for response caching and rate limiting when behavior must be consistent across instances. Use a configured external queue and separate consumers for durable background work. Graceful shutdown is especially important because each process performs a final flush of its own write buffer.

Run schema initialization in a controlled deployment phase when possible rather than letting many new instances race to change the schema simultaneously. Postgres remains the shared source of truth, while Redis or another external system coordinates the features that must be shared.

</details>

<details>
<summary><strong>Is the built-in `/websocket` endpoint ready for production use?</strong></summary>

Treat it as a minimal example, not a complete chat or event system. The shipped endpoint accepts a text message, buffers it into the `test` table, and echoes the operation result. It does not authenticate the connection, enforce a role, manage rooms, or provide delivery guarantees.

HTTP middleware and `config_api` policies do not automatically secure WebSocket connections. For production, add a custom WebSocket route that validates a token during connection setup, checks authorization for every subscribed resource, applies message-size and rate limits, and handles disconnects and backpressure. Use an external broker when messages must reach clients connected to different API instances.

</details>

<details>
<summary><strong>Why does Atom fail during startup after I change configuration or a table definition?</strong></summary>

Startup intentionally validates configuration before serving traffic. It rejects duplicate API IDs, unknown `config_api` keys or modes, invalid table definitions, duplicate/reserved column names, incompatible index types, unsafe schema-control combinations, and other inconsistent settings.

Read the first startup exception rather than the later shutdown noise. Check recent edits in `config_extend.py`, `config_api`, and `config_postgres`, then compare them with [config.md](config.md). Common mistakes include forgetting the exact first `id` column definition, referencing a nonexistent index column, using malformed JSON in `.env`, or registering a policy path that does not match a route.

</details>

<details>
<summary><strong>What should I change before deploying Atom publicly?</strong></summary>

At minimum:

- Replace `config_token_secret_key` and `config_root_user_password`.
- Set `config_is_debug = 0`.
- Restrict CORS origins and review every public table allow-list.
- Use short, intentional token lifetimes and realtime checks for destructive admin operations.
- Rate-limit authentication, OTP, upload, write, and costly integration routes.
- Use TLS at the proxy/load balancer and keep secrets in the deployment environment.
- Configure monitoring, database backups, graceful shutdown, and durable handling for failed jobs.

Also review automatic schema controls and remove or protect example data/routes you do not need. Work through the full [production hardening checklist](security.md#production-hardening-checklist) before exposing the service.

</details>

<details>
<summary><strong>How can a user see their API usage?</strong></summary>

Call `GET /my/api-usage?days=30` with the user's bearer token. The required `days` parameter defines the reporting window, and the response groups the authenticated user's `log_api` records by API path with a request count for each. This can support an account dashboard or basic usage troubleshooting.

Because request logs are buffered, the newest calls may not appear until the buffer is flushed. Treat this as operational usage information rather than a billing-grade meter: define explicit retention, aggregation, timezone, and idempotency rules before using it for quotas or invoices. For platform-wide reporting, query `log_api` through an authorized admin workflow or export it to your observability system.

</details>

<details>
<summary><strong>Can I use Atom in a commercial project, and how can I contribute?</strong></summary>

Atom is released under the [MIT License](../LICENSE), which permits commercial use, modification, distribution, and private use subject to the license's notice requirements. Review the license itself for the authoritative terms.

For project-specific behavior, prefer extension files and custom routers so your work remains easy to maintain. For changes that improve Atom generally, open an issue describing the problem or submit a focused pull request. Keep route handlers thin, place reusable logic in functions, preserve the standard `{"status": 1, "message": ...}` response shape, update relevant documentation, and include a reproducible verification path. See [Development Guidelines](guideline.md).

</details>

---

📚 [Back to README](../readme.md)
