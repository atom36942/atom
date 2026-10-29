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
- **Minimal Token Claims**: Encodes only non-sensitive routing fields (`id`, `role`, `username`, `id_ext`, `deactivated_at`, `deleted_at`) declared in `config_column_token_encode`.
- **Argon2 Password Hashing**: Passwords are never stored or logged in plaintext; hashed via Argon2id (`m=65536, t=3, p=4`).
- **Constant-Time Verification**: Endpoint checks (such as `/auth/login-password`) use `hmac.compare_digest` to thwart timing attacks.

---

## 3. Data Access & Column Protections

- **Parameterized SQL Queries**: All queries pass through `func_postgres_where_build` and `asyncpg` positional parameters (`, `). Raw user strings are never concatenated into SQL.
- **Sensitive Column Exfiltration Shield**: Projections, filters, distinct queries, and group-by aggregations strictly block sensitive fields declared in `config_column_read_blocked` and `"password"`.
- **Server-Managed Column Protections**: Clients cannot mutate fields in `config_column_admin` (`created_at`, `role`, `verified_at`).
- **User Writes Have Their Own APIs**: generic object APIs refuse `table=users`; `/my/user-*` and `/admin/user-*` update one user at a time, with `config_column_single_update` columns (`password`, `email`, `mobile`, `username`) sent alone and email or mobile verified by OTP.
- **Trusted Writes Are Internal Only**: `func_postgres_create(..., is_trusted=True)` skips column, regex and type checks for rows Atom builds itself (the API log). Never pass it for request data; a test fails if any `router/` or `router_extend/` file uses it.
- **Database Trigger Protections**: Superadmin user (`id: 1`) is guarded by PostgreSQL triggers (`trigger_protect_root_users`) preventing deletion.

---

## 4. Abuse Mitigation & Rate Limiting

- **Distributed Rate Limiting**: Per-route `rate_limit` policies enforced via Redis or memory counters. `inmemory` limits are per process: if you run more than one instance or worker, switch `rate_limit` to `"mode": "redis"` and set `config_redis_url_ratelimiter`, so all instances share one counter.
- **Key Partitioning**: Rate limit windows are keyed by `user_id` for authenticated sessions and by client IP for anonymous callers.
- **Client IP Behind a Proxy**: `func_middleware_client_ip` resolves the caller's IP for rate limits and `log_api.ip_address`. When the connection comes from a private address (a proxy such as Azure App Service's front end), it uses the last `X-Forwarded-For` entry with any port removed; the last entry is the one the proxy added, so client-supplied entries are ignored. Direct connections from public addresses always use the connection IP, so a forged header cannot bypass limits. `/pgweb` checks the raw connection address and also refuses any request carrying proxy headers; it is off unless `config_is_pgweb_enabled` is true (see [admin.md](admin.md#b-pgweb-staticpgwebhtml)).
- **WebSocket Guard**: WebSocket entries in `config_api` accept only `id` and `is_active`; startup fails on any other key, because HTTP policies (`is_token`, `user_check_*`, `rate_limit`, `cache`) never run for WebSockets. `/my/message-socket` is off by default (it closes on connect with 1008 `endpoint disabled`); when turned on it requires an access token as the first message (never in the URL), takes the sender from the token, and enforces size, rate, and per-user connection limits (defaults of `func_message_socket`).

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
