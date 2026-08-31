# 👑 Root User Architecture & Administration

Atom features a built-in superadministrator (**root user**) with `role: 1` that is automatically seeded, managed, and guarded by database triggers.

---

## 1. Overview & Identity

| Attribute | Value | Source / Config |
| :--- | :--- | :--- |
| **Username** | `admin` | Hardcoded in [`function.py`](../function.py) startup initializer |
| **Role** | `1` | Superadministrator role (has full access to `/admin/*` routes) |
| **Default Password** | `123456` | `config_root_user_password` (Override via `.env` in production) |
| **Database ID** | `1` | Maintained at `users.id = 1` |

---

## 2. Configuration Switches

Root user behavior is governed by the following settings in [`config.py`](../config.py):

| Setting | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `config_root_user_password` | `str` | `"123456"` | Root password string, hashed with Argon2 at startup. |
| `is_root_user_create` | `bool` | `True` | Automatically seeds or updates the root user in the database on startup. |
| `is_root_user_delete_disabled` | `bool` | `True` | Installs a database trigger preventing `id=1` from being deleted. |

```python
# config.py
config_root_user_password = "123456"

# In config_postgres["control"]:
"control": {
    "is_root_user_create": True,
    "is_root_user_delete_disabled": True,
}
```

---

## 3. Startup Seeding Logic

When Atom starts (`main.py` -> [`func_postgres_schema_users_init`](../function.py)):

1. **Password Hashing**: `config_root_user_password` is hashed using **Argon2** (`m=65536, t=3, p=4`).
2. **Upsert Operation**: Atom ensures the `admin` user exists with `role: 1`:
   ```sql
   INSERT INTO users (username, password, role) 
   VALUES ('admin', $1, 1) 
   ON CONFLICT (username) DO UPDATE 
   SET username = 'admin', 
       password = EXCLUDED.password, 
       role = 1, 
       deleted_at = NULL, 
       deactivated_at = NULL;
   ```
3. **Primary Slot Guarantee**: Atom assigns `id = 1` to the root user:
   ```sql
   UPDATE users 
   SET username = 'admin', 
       password = $1, 
       role = 1, 
       deleted_at = NULL, 
       deactivated_at = NULL 
   WHERE id = 1;
   ```
   > **Note:** If the root user was previously deactivated or soft-deleted, restarting the application restores it to active status.

---

## 4. Built-in Security Protections

### A. Database Trigger Protection (`is_root_user_delete_disabled`)
Atom installs a PostgreSQL trigger `trigger_protect_root_users` on the `users` table:

```sql
CREATE OR REPLACE FUNCTION func_protect_root_users() 
RETURNS trigger LANGUAGE plpgsql AS $$ 
BEGIN 
    IF TG_OP = 'DELETE' THEN 
        IF OLD.id = 1 THEN 
            RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; 
        END IF; 
        RETURN OLD; 
    END IF; 
    RETURN NULL; 
END; $$;
```
Any `DELETE` query targeting `id = 1` will fail with an exception, even if issued through direct SQL runner or admin delete routes.

### B. Public Signup Immunity
All public signup routes in [`router/auth.py`](../router/auth.py) enforce role validation:
```python
if ob["role"] == 1: 
    raise Exception("role 1 not allowed for user creation")
```
No external user can register or escalate privileges to `role: 1` through standard authentication APIs.

---

## 5. Logging In as Root

Authenticate using the `/auth/login-username-password` endpoint:

```bash
curl -X POST http://localhost:8000/auth/login-username-password \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "123456",
    "role": 1
  }'
```

**Response:**
```json
{
  "status": 1,
  "message": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "access_token_expires_at": 1756637400,
    "refresh_token_expires_at": 1756637400000
  }
}
```

Use the returned `access_token` in the `Authorization: Bearer <token>` header to access protected `/admin/*` routes.

---

## 6. Production Hardening Checklist

1. **Set a Strong Root Password in `.env`**:
   Never deploy with the default password. Add to `.env`:
   ```bash
   config_root_user_password=YourSuperSecurePassword!2026
   ```
2. **Restrict Admin Endpoints**:
   Ensure `/admin/*` routes in `config_api` use `"mode": "realtime"` or `"token"` role checks for `role: [1]`.
3. **Change Root Username (Optional)**:
   If you wish to change the root username from `admin` to something else (e.g. `superadmin` or `system`), update the query in [`function.py`](../function.py#L447) under `func_postgres_schema_users_init`.

---

📚 [Back to Auth Guide](auth.md) | [Back to Admin Toolkit](admin.md) | [Back to README](../readme.md)
