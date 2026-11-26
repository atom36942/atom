# 🔐 Authentication & Users

Atom's users, logins and tokens: **stateless JWT tokens**, **Argon2 password hashing**, several **identity columns** and a protected **root user**. All `/auth/*` routes are **public** (`"auth": []`): they mint tokens rather than requiring one.

| Topic | Doc |
|---|---|
| Users, identities, signup and login, managing users, OTP, forgot password and invites, tokens, root | this page |
| Permissions: per-user ids on routes and tables | [auth-permission.md](auth-permission.md) |
| API keys for scripts and other systems | [auth-api-key.md](auth-api-key.md) |
| Two-factor login (TOTP) | [auth-totp.md](auth-totp.md) |
| Single sign-on with Google, Microsoft and any OIDC provider | [auth-oidc.md](auth-oidc.md) |
| Pages for user management | [user-management.md](user-management.md) |

---

## 1. Users & Roles

Users live in the `users` table:
- **`role`** (`smallint`): the user's tier; routes allow roles with `user_check_role`. Login validates a supplied role against `config_login_allowed_roles` (default roles `1` to `20`); public signup uses `config_signup_allowed_roles`. **Role `1` is the root/admin role** and cannot be registered through public signup.
- **`permissions`** (`smallint[]`): ids that open routes and table actions beyond the role ([auth-permission.md](auth-permission.md)).
- **Identity columns**: `username`, `email`, `mobile`, `id_ext`, and `oidc_<provider>` for each single sign-on provider.

---

## 2. Identity Columns & Uniqueness Rules

Atom supports multiple identity fields on the `users` table:

| Column | Data Type | Auth Flow & Purpose | Endpoints |
| :--- | :--- | :--- | :--- |
| **`username`** | `text` | Username + password authentication. | `POST /auth/signup-username-password` |
| **`email`** | `text` | Primary email for password and Email OTP login. | `POST /auth/login-email-password` / `POST /auth/login-email-otp` |
| **`mobile`** | `text` | Mobile number for SMS OTP and password login. | `POST /auth/login-mobile-password` / `POST /auth/login-mobile-otp` |
| **`oidc_<provider>`** | `text` | The provider's `sub` for single sign-on, one column per provider ([auth-oidc.md](auth-oidc.md)). | `POST /auth/login-oidc` |
| **`id_ext`** | `text` | External identifier (Employee ID, Student ID, ERP sync). | `POST /auth/login-id-ext-password` |

### Configuring Uniqueness in `config.py`:
Uniqueness constraints are declared under `config_postgres_schema_master["table"]["users"]`:

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
- **Soft-Delete Uniqueness (Partial Index)**: In PostgreSQL, `NULL != NULL`. To enforce uniqueness only among active users, define a partial index in `config_postgres_schema_master["sql"]`:
  ```sql
  CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_active_unique
  ON users (email) WHERE deleted_at IS NULL;
  ```

### Adding a Custom Identity Column:
For an OIDC provider, add it to `config_oidc_provider`: its column comes with it. For anything else (a provider without ID tokens, a company directory):
1. Add the column to `users` in `config_extend.py`, unique per role: `{"name": "github_login_id", "datatype": "text", "unique": "github_login_id,role"}`, and to `config_column_users_my_blocked`.
2. Add its login route in `router_extend/` (e.g. `POST /auth/login-github`) ending with `func_auth_login_finish`, so 2FA applies.

---

## 3. Signup & Login Methods

### Signup and login role settings

Configure these settings together in `config.py` or your configuration overrides:

```python
config_signup_allowed_roles = [5]
config_login_allowed_roles = [1, 2, 5]
```

In this example, new users can register only with role `5`. Login requests can supply roles `1`, `2`, or `5`.

- `config_signup_allowed_roles` defaults to `[]`, which disables public registration. It applies to username/password signup and to new users created through email OTP, mobile OTP, or OIDC login. Existing users can still log in when registration is disabled. Role `1` is always rejected for public registration, even if listed.
- `config_login_allowed_roles` defaults to roles `1` through `20`. It validates the supplied `role` in username, email, mobile, and external-ID password login, plus email OTP, mobile OTP, and OIDC login. OTP and OIDC login require `role`; password login allows it to be omitted. When omitted, password login does not apply this list and requires the identity to resolve to a single user.

For new users created through OTP or OIDC login, the requested role must pass both lists. These settings do not define role permissions or apply to the static `/auth/login-password` endpoint.

Every login (password, OTP, OIDC):
- **Deleted or deactivated users are refused** with `account deleted` or `account deactivated` (403), checked only after valid credentials, so a stranger learns nothing about the account.
- **Emails match whatever their case**: `Ravi@Example.com` and `ravi@example.com` are the same user; new users are saved with the email in lowercase.

| Endpoint | Credentials | Notes |
| :--- | :--- | :--- |
| `/auth/signup-username-password` | role, username, password | Hashes with Argon2; validates regex; rejects `role: 1`. |
| `/auth/login-password` | password | Constant-time check against `config_login_password`. Returns `"ok"`. |
| `/auth/login-username-password` | role, username, password | Argon2 hash verification. |
| `/auth/login-email-password` | role, email, password | |
| `/auth/login-mobile-password` | role, mobile, password | |
| `/auth/login-id-ext-password` | role, id_ext, password | |
| `/auth/login-email-otp` | role, email, otp | Verifies OTP against `otp` table, auto-creates user on first login. |
| `/auth/login-mobile-otp` | role, mobile, otp | Same as email OTP, sent via SMS. |
| `/auth/login-oidc` | provider, id_token, role | Single sign-on with any configured provider ([auth-oidc.md](auth-oidc.md)). |
| `/auth/login-totp` | mfa_token, code | Second step for a user with 2FA on ([auth-totp.md](auth-totp.md)). |

### `POST /auth/login-password`
Compares the input against `config_login_password` configured in `.env`. If unconfigured, raises `"config_login_password not configured"`. Comparison uses `hmac.compare_digest` to prevent timing attacks.

---

## 4. Managing Users

Rows of `users` are written only through these APIs; the generic object APIs (`/my/object-update`, `/my/object-delete`, `/admin/object-create`, `/admin/object-update`, `/admin/object-delete`) refuse `table=users` (`write disabled for table: users`). The one exception is `/admin/postgres-import` (admins only, any table): a CSV can create or update `users` in bulk, and its `password` cells are hashed like everywhere else. Reading stays generic: `GET /my/profile` (own row plus `config_profile_metadata_sql`) and `/admin/object-read?table=users` (`password` is never readable).

| API | Query | Body | Rules |
|---|---|---|---|
| `POST /admin/user-create` | | `{role, username, password, ...columns}` | The three required; any other `users` column (profile fields, a project's own columns) is set in the same insert, except those in `config_permission_user_column_blocked` and `config_column_users_blocked` (sign-up, login, verification, permissions, system) and `id`, `deactivated_at`; returns `{"id": ...}` |
| `PUT /admin/user-update` | | `{id, ...users columns}`, or several as `{"obj_list": [{id, ...}, ...]}` | Up to `config_batch_item_limit` users, ids unique, each with its own columns and checked by the same rules; one transaction, so a missing id (404) or any refused user updates none. `email`/`mobile` need `otp` only when `config_is_otp_require_users_update` is on. The root user's `role` and `deactivated_at` cannot change. `permissions` must be route ids labelled in `config_column_int_mapping["users"]["permissions"]` |
| `POST /permission/user-create` | | `{username, password, role, ...columns}` | A user of a role in `config_permission_user_roles`, for users granted 61 (an app's own user management); other `users` columns as in `/admin/user-create`; `created_by_id` is the caller |
| `PUT /permission/user-update` | | `{id, ...users columns}` | For users granted 62, on a user whose role is in `config_permission_user_roles` (never 1, so never root or an admin). Any columns except those in `config_permission_user_column_blocked` (`role`, `permissions`, the login ones `username`, `email`, `mobile`, ...) and `config_column_users_blocked`: the profile, `password` (alone, as everywhere) and `deactivated_at` (a timestamp blocks the user, `deactivated_by_id` is the caller; `null` restores them). `updated_by_id` is the caller |
| `DELETE /admin/user-delete` | `id` | | One user; never the root user |
| `PUT /my/user-update` | | `{...own users columns}` | Own row from the token (an `id`, if sent, must be the user's own). `email`/`mobile` always need `otp` (sent to the new value with `/public/otp-send-email` or `-mobile`). Columns in `config_column_users_my_blocked` (`role`, `permissions`, `deactivated_at`, ...) are refused |
| `DELETE /my/user-delete` | | | Own account; token only |

Both updates accept any `users` column (Atom's and a project's own), checked against the table; only the fields sent are updated.

Rules for both updates:
- A column in `config_column_single_update` (`username`, `password`, `email`, `mobile`) is updated alone: `{password}`, `{email, otp}`, never `{password, name}`.
- Columns in `config_column_users_blocked` (`created_*`, `updated_*`, `deleted_*`, `is_protected`, `last_active_at`) are refused by both; columns in `config_column_users_my_blocked` only by `/my/user-update`; every other column, a project's own included, is allowed. A project adds its own columns to either list in `config_extend.py`.
- `password` is hashed (Argon2) and logged in `log_users_password`; `email` is saved in lowercase; formats follow `config_column_regex`.

### Deactivated or deleted accounts

Set `deactivated_at` to block a user and keep the account (clear it to restore); `deleted_at` (soft delete) or `/admin/user-delete` removes them. Atom refuses them with 403 and one of two messages, the same everywhere:

| Where | When the user is blocked |
|---|---|
| Login, `/my/token-refresh` | At once: `account deactivated` / `account deleted` |
| Every route with a credential | By `config_api_global_user_check_deleted` / `_deactivated` (default `token`: when the access token was issued after the block, so in practice at the next renewal; `realtime`: at once, one `users` lookup per request) or the route's own `user_check_*` |
| `GET /my/profile` | Always answers with the current row, so `deactivated_at` / `deleted_at` show at once |

A page handles it the same way in every case:
- On a 403 with either message, or a profile with `deactivated_at` or `deleted_at`: log out, clear its storage, and say which, e.g. "Your account is deactivated. Please contact your admin." or "Your account was deleted. Please contact your admin." (never "Session expired").
- No extra request for it: the page's regular sync (token renewal, then `/my/profile`, e.g. every 3 hours) catches a block on an open page. The server keeps accepting an access token issued before the block until it expires (`config_access_token_expires_sec`, 7 days); use `realtime` on routes that must stop at once.

Deleting needs two switches, because the database guards `users` too: `config_is_user_delete=true` and `users` removed from `config_postgres_schema_master["control"]["table_row_delete_disable"]` (default on: the API then answers "users delete blocked in the database"). The root user (`id` 1) is never deleted.

## 5. OTP Flow

For OTP logins, the client requests a verification code and then submits it:
1. **Send**: `POST /public/otp-send-email` or `/public/otp-send-mobile` → `func_otp_generate` creates a random code of length `config_otp_length`, the configured provider sends it, and only then `func_otp_save` stores it in the `otp` table (valid for `config_otp_expiry_sec`). A failed send stores nothing.
2. **Verify / Login**: `POST /auth/login-email-otp` validates code via `func_otp_verify`. Each code accepts at most `config_otp_max_attempt` guesses (default `5`), counted in `otp.attempt`; after that even the correct code returns HTTP 429 and the user must request a new one. Expired codes do not use up attempts.
3. **Stand-alone check**: `GET /public/otp-verify` validates a code without issuing a JWT session.

### Forgot password and invites
One route, `POST /public/password-set {role, email or mobile, otp, password}` (5 a minute), after the code from `/public/otp-send-email` or `-mobile`. It sets the password of the user with that `email` (or `mobile`) and role: password rules, hashed, logged in `log_users_password`; the code works once.

| Need | Steps |
|---|---|
| Forgot password | The page sends a code to the user's email, then calls `/public/password-set` with it and the new password |
| Invite | An admin creates the user as usual with a random password nobody is told (`/admin/user-create`), sets their `email` or `mobile` (`/admin/user-update`), and tells them to use Forgot password; the admin never knows the password |

- The code is checked before the account, so without it the answer is the same whether an account exists or not; only the owner of the email, holding its code, learns there is none (404).
- Refused: role 1 (the root user's password is `config_root_user_password`), a deleted or deactivated user (403, as at login), unknown fields.
- The user is found by `email` or `mobile` only: a user whose `username` is an email but whose `email` is empty gets it set first.
- Tokens issued before the change stay valid until they expire (`config_access_token_expires_sec`).

---

## 6. JWT Tokens (`func_token_encode` / `func_token_decode`)

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
- **Refreshing**: `POST /my/token-refresh` reads the current refresh token, re-reads the user and mints a fresh pair; a deleted or deactivated account gets `403` instead, as at login.

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
---

## 7. Root Superadmin User Architecture

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
