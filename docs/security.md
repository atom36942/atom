# 🛡️ Security Model & Production Hardening

Atom enforces a layered, defense-in-depth security model across network boundaries, identity verification, authorization policies, database access, and data sanitization.

See the [SQL, storage, and credential audit](audit.md) for verified
findings, fixes, test coverage, and remaining deployment checks.

---

## 1. Baseline Security Headers

Atom attaches standard baseline security headers to every HTTP response before returning:
- `X-Content-Type-Options: nosniff`: Prevents MIME-sniffing attacks.
- `X-Frame-Options: DENY`: Mitigates clickjacking attacks.
- `Referrer-Policy: strict-origin-when-cross-origin`: Protects referrer leakage.
- `X-XSS-Protection: 0`: Disables legacy flawed browser XSS filters in favor of modern CSP.

---

## 2. Identity & Token Security

- **Stateless HS256 JWTs**: Signed using `config_token_secret_key`. No session state is held server-side. In production startup refuses a key shorter than 32 bytes, since a short key can be brute-forced from any issued token and then used to forge admin tokens.
- **Auth in `master` Only**: users, logins, tokens, API keys and permissions live in the `master` database; another database's `users` table is a plain table that logs nobody in ([database.md](database.md#master-holds-auth-other-databases-hold-data)).
- **Minimal Token Claims**: Encodes only non-sensitive routing fields (`id`, `role`, `username`, `id_ext`, `deactivated_at`, `deleted_at`, `permissions`): `id` and the `users` columns in `config_users_token_column`.
- **Argon2 Password Hashing**: Passwords are never stored or logged in plaintext; hashed via Argon2id (`m=65536, t=3, p=4`).
- **Constant-Time Verification**: Endpoint checks (such as `/auth/login-password`) use `hmac.compare_digest` to thwart timing attacks.

---

## 3. Data Access & Column Protections

- **Parameterized SQL Queries**: All queries pass through `func_postgres_where_build` and `asyncpg` positional parameters (`$1`, `$2`). Raw user strings are never concatenated into SQL.
- **Tables Closed Unless Listed**: `func_object_access`, the one gate of Atom's table routes, refuses a table (and every table a read joins) not in the group's `control` access list of the request's database (`public_create`, `public_read`, `private_read`, `my_*`, `admin_*`; 403 naming what to add); `/admin/*` needs both the route's id and the table in `admin_<action>` (`["*"]`, allowed only there, opens every table; Atom's master default). No fallback to master: a database without its own schema is closed to every table route ([config.md](config.md#control)).
- **Sensitive Column Exfiltration Shield**: Projections, filters, distinct queries, and group-by aggregations strictly block the columns whose `read_blocked` lists the route's group (`users.password`, `totp_secret`, `totp_recovery`, `api_key.key_hash` and `webhook.secret` for every group).
- **Per-User Permissions**: a route with `user_check_permission` admits only users whose `users.permissions` holds its `id`, admins included; only `/admin/user-update` grants them, and only labelled ids ([auth-permission.md](auth-permission.md)).
- **Server-Managed Column Protections**: create and update refuse a column whose `write_blocked` lists the route's group (`users.role`, `verified_at` for `/my`; `is_protected`, `last_active_at` for every group) and every audit column (400).
- **User Writes Have Their Own APIs**: generic object APIs refuse `table=users`; `/my/user-*` and `/admin/user-*` update one user at a time, with `config_users_update_alone_column` columns (`password`, `email`, `mobile`, `username`) sent alone and email or mobile verified by OTP.
- **Trusted Writes Are Internal Only**: `func_postgres_create(..., is_trusted=True)` skips column, regex and type checks for rows Atom builds itself (the API log). Never pass it for request data; a test fails if any `router/` or `router_extend/` file uses it.
- **Database Trigger Protections**: with `config_is_root_user` on, the superadmin user (`id: 1`) is guarded by a PostgreSQL trigger (`trigger_protect_root_users`) preventing deletion.
- **Logs Nobody Edits**: tables only Atom writes (`log_api`, `log_users_password`, `log_users_delete`, `script_run`, `otp`) are in no `/public` or `/my` write list, so those routes refuse them (403); `log_api` and `log_users_password` are append-only in the database (`control.row_update_disabled`: a trigger refuses every `UPDATE`), and `log_users_password` and `log_users_delete` refuse every `DELETE` (`row_delete_disabled`), raw SQL and `/admin` routes included. `TRUNCATE` is refused in every database unless its `control` sets `"is_truncate_disabled": False`. The app's database login owns the tables and can drop a trigger, so the SQL runner can still undo this; for logs that even a database owner can't change, give the app a login that doesn't own them.

- **Two-Factor Login (optional per user)**: a user with TOTP on needs a 6-digit code from their authenticator app after the password; the password step returns only a 5-minute `mfa_token` that opens no route. Secrets are AES-GCM encrypted with `config_totp_encryption_key` (a database copy alone reveals none), each code works once, `/auth/login-totp` allows 5 tries a minute ([auth-totp.md](auth-totp.md)).
- **Single Sign-On Tokens Are Checked in Full**: `/auth/login-oidc` accepts only an ID token signed with the provider's published key (asymmetric algorithms only), for this app's `client_id`, from the configured issuer (and tenant), not expired, and with the page's `nonce` when sent; an untrusted email never links to an existing user ([auth-oidc.md](auth-oidc.md)).
- **Webhooks Reach Only Public HTTPS**: a webhook URL must be `https` and resolve to a public address, checked when it is created and again before every delivery, so no one can point Atom at `localhost`, a private network or a cloud metadata address (SSRF); redirects are not followed. Its signing `secret` is `read_blocked` for every group, shown once at creation ([webhook.md](webhook.md)).
- **Incoming Webhooks Are Signed**: a public route another service calls takes `webhook_verify`, so the middleware checks the HMAC of the raw body (constant-time) and the timestamp (at most 300 s off) before the route runs; a forged or replayed call is 401 ([webhook.md](webhook.md#incoming)).

- **Limits Even Admins Have**:
  - Every `/admin/*` route that writes or grants access (object create, update, delete; user create, update, delete; imports; the SQL write runners; blob operations; slow-query reset) checks the role, deactivation and any permission against the database on each call (`realtime`), so a demoted, deactivated or revoked admin stops at once, whatever the token says; and it is rate limited.
  - Audit columns (`created_*`, `updated_*`, `deleted_*`) are set only by Atom or the database: every create and update refuses them (admin, `/my`, `/public`, CSV import, the user APIs; 400), and imported rows get the importing admin as `created_by_id` (created) or `updated_by_id` (updated). A column `write_blocked` for `admin` is refused on the admin routes too, so only Atom, a project function or raw SQL sets it.
  - `/admin/postgres-query-runner-write` takes one `INSERT`, `UPDATE` or `DELETE`; `UPDATE` and `DELETE` need a `WHERE`; no `DROP`, `TRUNCATE`, `ALTER`, `CREATE`, `GRANT`, `DO` or other commands (the schema comes from `config_postgres_schema_master`; PgWeb, with its own database login, stays the full SQL tool).
  - No user changes their own `role`, `permissions` or `deactivated_at` through the user routes: another admin must.

---

## 4. Abuse Mitigation & Rate Limiting

- **Distributed Rate Limiting**: Per-route `rate_limit` policies enforced via Redis or memory counters. `inmemory` limits are per process: if you run more than one instance or worker, switch `rate_limit` to `"mode": "redis"` and set `config_redis_url_ratelimiter`, so all instances share one counter.
- **Key Partitioning**: Rate limit windows are keyed by `user_id` for authenticated sessions and by client IP for anonymous callers.
- **Client IP Behind a Proxy**: `func_middleware_client_ip` resolves the caller's IP for rate limits and `log_api.ip_address`. When the connection comes from a private address (a proxy such as Azure App Service's front end), it uses the last `X-Forwarded-For` entry with any port removed; the last entry is the one the proxy added, so client-supplied entries are ignored. Direct connections from public addresses always use the connection IP, so a forged header cannot bypass limits. `/pgweb` checks the raw connection address and also refuses any request carrying proxy headers; it is off unless `config_is_pgweb_enabled` is true (see [admin.md](admin.md#b-pgweb-pagepgweb)).
- **WebSocket Guard**: WebSocket entries in `config_api` accept only `id` and `is_active`; startup fails on any other key, because HTTP policies (`auth`, `user_check_*`, `rate_limit`, `cache`) never run for WebSockets. `/my/message-socket` is off by default (it closes on connect with 1008 `endpoint disabled`); when turned on it requires an access token as the first message (never in the URL), takes the sender from the token, and enforces size, rate, and per-user connection limits (defaults of `func_message_socket`).

---

## 5. Production Hardening Checklist

When deploying Atom to production:

### 1. Mandatory Production Environment Keys (`.env`):
```dotenv
config_is_prod=true
config_token_secret_key=generate-a-secure-random-64-char-string
config_root_user_password=strong-complex-root-password
config_login_password=strong-login-password
# restrict open registration if applicable
config_signup_allowed_roles=[]
```

### 2. Disable High-Risk Admin APIs:
In production, set `"is_active": False` in `config_api` for sensitive write and runner endpoints:
- `/admin/sync`
- `/admin/postgres-import`
- `/admin/mongodb-import`
- `/admin/postgres-query-runner-write`
- `/admin/mssql-query-runner-write`
- `/admin/clickhouse-query-runner-write`
- `/admin/blob-container-ops`
- `/admin/blob-delete-url`
