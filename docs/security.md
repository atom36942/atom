# 🛡️ Security Model & Production Hardening

Atom enforces a layered, defense-in-depth security model across network boundaries, identity verification, authorization policies, database access, and data sanitization.

---

## 1. Baseline Security Headers

Atom attaches standard baseline security headers to every HTTP response before returning:
- `X-Content-Type-Options: nosniff`: Prevents MIME-sniffing attacks.
- `X-Frame-Options: DENY`: Mitigates clickjacking attacks.
- `Referrer-Policy: strict-origin-when-cross-origin`: Protects referrer leakage.
- `X-XSS-Protection: 0`: Disables legacy flawed browser XSS filters in favor of modern CSP.

---

## 2. Identity & Token Security

- **Stateless HS256 JWTs**: Signed using `config_token_secret_key`. No session state is held server-side.
- **Minimal Token Claims**: Encodes only non-sensitive routing fields (`id`, `role`, `username`, `id_ext`, `deactivated_at`, `deleted_at`) declared in `config_column_token_encode`.
- **Argon2 Password Hashing**: Passwords are never stored or logged in plaintext; hashed via Argon2id (`m=65536, t=3, p=4`).
- **Constant-Time Verification**: Endpoint checks (such as `/auth/login-password`) use `hmac.compare_digest` to thwart timing attacks.

---

## 3. Data Access & Column Protections

- **Parameterized SQL Queries**: All queries pass through `func_postgres_where_build` and `asyncpg` positional parameters (`, `). Raw user strings are never concatenated into SQL.
- **Sensitive Column Exfiltration Shield**: Projections, filters, distinct queries, and group-by aggregations strictly block sensitive fields declared in `config_column_read_blocked` and `"password"`.
- **Server-Managed Column Protections**: Clients cannot mutate fields in `config_column_admin` (`created_at`, `role`, `verified_at`).
- **Single-Field Update Guards**: High-risk identity fields (`password`, `email`, `mobile`) cannot be updated in bulk; `config_column_single_update` forces isolated, single-field mutations.
- **Database Trigger Protections**: Superadmin user (`id: 1`) is guarded by PostgreSQL triggers (`trigger_protect_root_users`) preventing deletion.

---

## 4. Abuse Mitigation & Rate Limiting

- **Distributed Rate Limiting**: Per-route `rate_limit` policies enforced via Redis or memory counters.
- **Key Partitioning**: Rate limit windows are keyed by `user_id` for authenticated sessions and by client IP for anonymous callers.
- **WebSocket Flooding Guard**: Unauthenticated WebSocket endpoints (such as `/websocket`) default to `is_active: False` and close immediately on connect.

---

## 5. Production Hardening Checklist

When deploying Atom to production:

### 1. Mandatory Production Environment Keys (`.env`):
```dotenv
config_is_prod=true
config_token_secret_key="generate-a-secure-random-64-char-string"
config_root_user_password="strong-complex-root-password"
config_login_password="strong-login-password"
config_signup_allowed_roles=[] # Restrict open registration if applicable
```

### 2. Disable High-Risk Admin APIs:
In production, set `"is_active": False` in `config_api` for sensitive write and runner endpoints:
- `/admin/sync`
- `/admin/postgres-import`
- `/admin/redis-import`
- `/admin/mongodb-import`
- `/admin/postgres-query-runner-write`
- `/admin/mssql-query-runner-write`
- `/admin/clickhouse-query-runner-write`
- `/admin/blob-container-ops`
- `/admin/blob-delete-url`
