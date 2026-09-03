# 🆔 User Identities & Auth Column Configuration

Atom provides a flexible, schema-driven identity architecture for user management and authentication. This document explains how identity columns work, how to configure their uniqueness scope (globally unique vs. composite multi-tenant/per-role), and how to add new custom identity columns to the authentication system.

---

## 1. Built-in Identity Columns

Out of the box, Atom supports multiple identity fields on the `users` table:

| Column | Data Type | Auth Flow & Purpose | Endpoints |
| :--- | :--- | :--- | :--- |
| **`username`** | `text` | Username + password authentication. | `POST /auth/signup-username-password`<br>`POST /auth/login-username-password` |
| **`email`** | `text` | Primary email address for password and Email OTP login. | `POST /auth/login-email-password`<br>`POST /auth/login-email-otp` |
| **`mobile`** | `text` | Mobile phone number for SMS OTP and password login. | `POST /auth/login-mobile-password`<br>`POST /auth/login-mobile-otp` |
| **`google_login_id`** | `text` | Google OAuth subject (`sub`) ID for Google Social Login. | `POST /auth/login-google` |
| **`id_ext`** | `text` | External identifier (Employee ID, Student ID, ERP sync) for password login or SSO. | `POST /auth/login-id-ext-password`<br>Included in JWT token claims |

---

## 2. Configuring Uniqueness

Column uniqueness is declared directly in the `users` table schema within [`config.py`](../config.py). Atom automatically manages PostgreSQL `UNIQUE` constraints during startup migration (`func_postgres_schema_init`).

### Pattern A: Composite Uniqueness with Role (Default & Recommended)
By default, Atom configures identities to be unique **per role** using a comma `,`:
```python
# config.py -> config_postgres["table"]["users"]
{"name": "username", "datatype": "text", "unique": "username,role"},
{"name": "email", "datatype": "text", "unique": "email,role"},
{"name": "mobile", "datatype": "text", "unique": "mobile,role"},
{"name": "id_ext", "datatype": "text", "unique": "id_ext,role"},
{"name": "google_login_id", "datatype": "text", "unique": "google_login_id,role"},
```
This enables multi-persona applications (e.g. Rider vs. Driver or Buyer vs. Seller) where one person uses the same email/phone across different roles.

### Pattern B: Globally Unique Across System (Single Identity System)
If your app strictly requires that each identity exists only once across all roles:
```python
{"name": "username", "datatype": "text", "unique": "username"},
{"name": "email", "datatype": "text", "unique": "email"},
{"name": "mobile", "datatype": "text", "unique": "mobile"},
{"name": "google_login_id", "datatype": "text", "unique": "google_login_id"},
{"name": "id_ext", "datatype": "text", "unique": "id_ext"},
```

### Pattern C: Multi-Tenant Uniqueness
For multi-tenant SaaS where identities are scoped per organization or tenant:
```python
{"name": "username", "datatype": "text", "unique": "username,tenant_id"},
{"name": "email", "datatype": "text", "unique": "email,org_id"},
```

### Pattern C: Multiple Simultaneous Unique Rules
Use a **pipe `|`** to define multiple distinct unique constraints for the same column:

```python
# Unique globally AND composite with tenant
{"name": "username", "datatype": "text", "unique": "username|username,tenant_id"},
```
Atom will generate two separate PostgreSQL constraints: `unique_users_username` and `unique_users_username_tenant_id`.

### Pattern D: Soft-Delete Uniqueness (Partial Unique Indexes)
In PostgreSQL, `NULL != NULL`. A standard constraint on `(email, deleted_at)` will allow duplicate active users because `deleted_at` is `NULL`.

If you want an identity to be unique **only among active users** (allowing deleted users' emails/usernames to be re-registered), use a partial index in `config_postgres["sql"]`:

```python
# 1. In config.py -> users table: keep column without unique attribute
{"name": "email", "datatype": "text"},

# 2. In config.py -> config_postgres["sql"]:
"sql": {
    "idx_users_email_active_unique": """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_active_unique
        ON users (email)
        WHERE deleted_at IS NULL;
    """
}
```

---

## 3. How to Add a New Custom Identity Column to Auth

Follow these steps to add a new authentication identity (for example, `github_login_id`, `apple_login_id`, or `employee_code`):

### Step 1: Add the Column to the Schema
In [`config.py`](../config.py) (or `config_extend.py`), add the column under `users`:

```python
# Example: Adding GitHub Login ID
{"name": "github_login_id", "datatype": "text", "unique": "github_login_id"},
{"name": "github_metadata", "datatype": "jsonb"},
```

### Step 2: Include in JWT Claims (Optional)
If your application needs this field available on `request.state.user` in protected routes without hitting the database, add it to `config_column_token_encode`:

```python
config_column_token_encode = ["id", "role", "username", "email", "github_login_id", "deactivated_at", "deleted_at"]
```

### Step 3: Add Validation Rules (Optional)
If the identity format needs regex validation (e.g. employee code or custom username syntax), add a rule to `config_regex`:

```python
config_regex = {
    "employee_code": ["^EMP-[0-9]{4,8}$", "Employee code must match EMP-XXXX format"],
}
```

### Step 4: Add the Login Route
In [`router/auth.py`](../router/auth.py) (or `router_extend.py`), register the endpoint and implement the verification flow:

```python
@router.post("/auth/login-github")
async def func_api_auth_login_github(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres:
        raise Exception("postgres client not initialized")
    
    # 1. Read request parameters
    ob = await app_state.func_request_param_read(
        request=request,
        mode="body",
        strict=False,
        param_specs=[
            {"name": "role", "type": "int", "required": True, "allowed": app_state.config_allowed_users_role, "default": None},
            {"name": "github_token", "type": "str", "required": True, "allowed": None, "default": None},
            {"name": "source", "type": "int", "required": False, "allowed": None, "default": None}
        ]
    )

    # 2. Verify external OAuth token (e.g. GitHub API call)
    github_user = await verify_github_token(ob["github_token"])
    github_id = str(github_user["id"])

    # 3. Find or create user
    async with app_state.client_postgres.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE github_login_id = $1;", github_id)
        if not records and not app_state.config_is_signup:
            raise Exception("signup disabled")
        if not records and ob["role"] == 1:
            raise Exception("role 1 not allowed for user creation")
        
        user = dict(records[0]) if records else dict((await conn.fetch(
            "INSERT INTO users (role, github_login_id, email, name, github_metadata, source) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;",
            ob["role"], github_id, github_user.get("email"), github_user.get("name"), orjson.dumps(github_user).decode("utf-8"), ob.get("source")
        ))[0])

    # 4. Mint and return JWT token pair
    token = await app_state.func_token_encode(
        user=user,
        config_token_secret_key=app_state.config_token_secret_key,
        config_access_token_expires_sec=app_state.config_access_token_expires_sec,
        config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec,
        config_column_token_encode=app_state.config_column_token_encode
    )
    return {"status": 1, "message": token}
```

### Step 5: Register the API Endpoint
In [`config.py`](../config.py), add the new route under `config_api`:

```python
"/auth/login-github": {"id": 105, "is_token": False},
```

---

## 4. Root User Initialization Caveat

When configuring uniqueness on the `username` column, ensure that [`func_postgres_schema_users_init`](../function.py) matches your unique constraint target:

* **When `username` is globally unique (`"unique": "username"`):**
  ```sql
  INSERT INTO users (username, password, role) VALUES ('admin', $1, 1)
  ON CONFLICT (username) DO UPDATE ...
  ```
* **When `username` is composite per role (`"unique": "username,role"`):**
  ```sql
  INSERT INTO users (username, password, role) VALUES ('admin', $1, 1)
  ON CONFLICT (username, role) DO UPDATE ...
  ```

---

## 5. Summary Checklist

When modifying or adding authentication identity columns:
1. Declare the column and `unique` rule in `config_postgres["table"]["users"]`.
2. Add regex formatting in `config_regex` if inputs require format checks.
3. Update `config_column_token_encode` if the identity should be packed inside JWTs.
4. Register the route in `config_api` with `is_token: False`.
5. Restart the server — Atom will automatically apply the database schema changes and constraints.

---

📚 [Back to Auth Guide](auth.md) | [Back to README](../readme.md)
