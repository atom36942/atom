# 🔐 Authentication, Identities & User Architecture

Atom features a comprehensive, schema-driven authentication and user management system built on **stateless JWT tokens**, **Argon2 password hashing**, **flexible multi-column identities**, and **built-in superadmin protections**.

All auth endpoints live in [`router/auth.py`](../router/auth.py) and are **public** (`is_token=False`) — they mint tokens rather than requiring one.

---

## 1. Users, Roles & Multi-Tenancy

Users live in the `users` database table. Core authorization attributes include:
- **`role`** (`smallint`): The user's permission tier, validated against `config_allowed_users_role` (default `[1, 2, 3, 4, 5]`).
  - **Role `1` is the root/superadmin role** and cannot be registered via public signup routes.
- **Identity columns**: `username`, `email`, `mobile`, `google_login_id`, `id_ext`.

### Per-User Permissions

`users.permissions` is an optional `smallint[]` column with `default: None` (nullable). It stores permission IDs so users within the same role can have different capabilities. For example, two users with role `3` could have `[1, 2]` and `[2]`, respectively.

The IDs are defined in [`config_permissions_mapping`](config.md#config_permissions_mapping): `1` is `invoice.export`, `2` is `invoice.filter.apply`, and `3` is `invoice.delete`. Keep IDs stable and never reuse an existing ID for a different action. Treat `NULL` and an empty array as no per-user permissions granted.

The column and mapping provide storage and metadata only. Current role middleware does not enforce these permissions, and they are not included in the default JWT claims. Before using them for authorization, implement backend checks that load the user's permissions and require the relevant permission alongside the allowed role. Validate assigned IDs against the mapping and restrict permission updates to authorized administrators; `permissions` is not currently included in `config_column_admin`.

---

## 2. Identity Columns & Uniqueness Rules

Atom supports multiple identity fields on the `users` table:

| Column | Data Type | Auth Flow & Purpose | Endpoints |
| :--- | :--- | :--- | :--- |
| **`username`** | `text` | Username + password authentication. | `POST /auth/signup-username-password` |
| **`email`** | `text` | Primary email for password and Email OTP login. | `POST /auth/login-email-password` / `POST /auth/login-email-otp` |
| **`mobile`** | `text` | Mobile number for SMS OTP and password login. | `POST /auth/login-mobile-password` / `POST /auth/login-mobile-otp` |
| **`google_login_id`** | `text` | Google OAuth subject (`sub`) ID for Google Social Login. | `POST /auth/login-google` |
| **`id_ext`** | `text` | External identifier (Employee ID, Student ID, ERP sync). | `POST /auth/login-id-ext-password` |

### Configuring Uniqueness in `config.py`:
Uniqueness constraints are declared under `config_postgres["table"]["users"]`:

- **Composite with Role (Default & Recommended)**: Scopes identity per role, enabling multi-persona accounts (e.g. Driver vs. Rider):
  ```python
  {"name": "email", "datatype": "text", "unique": "email,role"},
  ```
- **Globally Unique Across System**:
  ```python
  {"name": "email", "datatype": "text", "unique": "email"},
  ```
- **Multi-Tenant Scoping**:
  ```python
  {"name": "email", "datatype": "text", "unique": "email,org_id"},
  ```
- **Multiple Simultaneous Rules**: Use a pipe `|`:
  ```python
  {"name": "username", "datatype": "text", "unique": "username|username,tenant_id"},
  ```
- **Soft-Delete Uniqueness (Partial Index)**: In PostgreSQL, `NULL != NULL`. To enforce uniqueness only among active users, define a partial index in `config_postgres["sql"]`:
  ```sql
  CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_active_unique
  ON users (email) WHERE deleted_at IS NULL;
  ```

### Adding a Custom Identity Column:
1. Add the column to `users` in `config.py` (or `config_extend.py`):
   ```python
   {"name": "github_login_id", "datatype": "text", "unique": "github_login_id"},
   ```
2. Include in token claims via `config_column_token_encode` if needed in `request.state.user`.
3. Add a dedicated login route in `router/auth.py` (e.g. `POST /auth/login-github`).

---

## 3. Signup & Login Methods

| Endpoint | Credentials | Notes |
| :--- | :--- | :--- |
| `/auth/signup-username-password` | role, username, password | Hashes with Argon2; validates regex; rejects `role: 1`. |
| `/auth/login-password` | password | Constant-time check against `config_login_password`. Returns `"ok"`. |
| `/auth/login-username-password` | username + password | Argon2 hash verification. |
| `/auth/login-email-password` | email + password | |
| `/auth/login-mobile-password` | mobile + password | |
| `/auth/login-id-ext-password` | id_ext + password | |
| `/auth/login-email-otp` | email + otp | Verifies OTP against `otp` table, auto-creates user on first login. |
| `/auth/login-mobile-otp` | mobile + otp | Same as email OTP, sent via SMS. |
| `/auth/login-google` | google_token (+ role) | Verifies Google ID token against `config_google_login_client_id`. |

### `POST /auth/login-password`
Compares the input against `config_login_password` configured in `.env`. If unconfigured, raises `"config_login_password not configured"`. Comparison uses `hmac.compare_digest` to prevent timing attacks.

---

## 4. OTP Flow

For OTP logins, the client requests a verification code and then submits it:
1. **Send**: `POST /public/otp-send-email` or `/public/otp-send-mobile` → `func_otp_generate` creates a random code of length `config_otp_length`, stores it in the `otp` table with `config_otp_expiry_sec`, and dispatches via configured provider.
2. **Verify / Login**: `POST /auth/login-email-otp` validates code via `func_otp_verify`.
3. **Stand-alone check**: `POST /public/otp-verify` validates a code without issuing a JWT session.

---

## 5. JWT Tokens (`func_token_encode` / `func_token_decode`)

Atom generates HS256 JWT pairs signed with `config_token_secret_key`:
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "access_token_expires_at": 1774000000,
  "refresh_token_expires_at": 1776500000
}
```

- **Payload Claims**: Minimal claims from `config_column_token_encode` (`id`, `role`, `username`, `id_ext`, `deactivated_at`, `deleted_at`).
- **Token Type**: Encodes `type: "access"` or `type: "refresh"`.
- **Refreshing**: `POST /my/token-refresh` reads the current refresh token, re-checks database status, and mints a fresh pair.

### Reading User in Route Handlers:
```python
@router.get("/my/profile")
async def func_api_my_profile(*, request: Request):
    current_user = request.state.user
    user_id = current_user["id"]
    role = current_user["role"]
    return {"status": 1, "message": current_user}
```

---

## 6. Root Superadmin User Architecture

Atom features an automatic superadministrator (**root user**) with `role: 1` that is seeded on startup and defended by database triggers:

| Attribute | Value | Configuration / Source |
| :--- | :--- | :--- |
| **Username** | `admin` | Hardcoded default superadmin identity |
| **Role** | `1` | Full access to `/admin/*` routes |
| **Password** | String from `.env` | `config_root_user_password` (Argon2 hashed) |
| **Database ID** | `1` | Guaranteed primary slot `users.id = 1` |

### Seeding Logic (`func_postgres_schema_users_init`):
At startup, Atom ensures the `admin` user exists with `role: 1`, updates the password hash if `config_root_user_password` changed, restores active status if deleted/deactivated, and guarantees `id = 1`.

### Built-in Defenses:
1. **PostgreSQL Trigger Protection (`is_root_user_delete_disabled` = True)**:
   Installs `trigger_protect_root_users` on the `users` table. Any direct SQL `DELETE` or API delete targeting `id = 1` raises an exception:
   ```sql
   RAISE EXCEPTION 'DELETE not allowed for root user (id=1)';
   ```
2. **Public Signup Immunity**:
   All public registration endpoints explicitly reject `role: 1`:
   ```python
   if ob["role"] == 1:
       raise Exception("role 1 not allowed for user creation")
   ```
