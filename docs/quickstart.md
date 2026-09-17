# 🚀 Quickstart

Get up and running with Atom in less than 5 minutes.

---

## Prerequisites

1. Server running on `http://localhost:8000` (see [Installation](../readme.md#installation)).
2. PostgreSQL database connected via `config_postgres_url` in `.env`.
3. Required security keys set in `.env`:
   ```dotenv
   config_token_secret_key="your-long-secret-key-at-least-32-chars"
   config_root_user_password="your-strong-root-password"
   config_signup_allowed_roles=[2, 5]
   ```

---

## 1. Sign Up & Obtain Token

Register a new user account via `/auth/signup-username-password`:

```bash
curl -X POST http://localhost:8000/auth/signup-username-password \
  -H "Content-Type: application/json" \
  -d '{
    "role": 2,
    "username": "alice",
    "password": "secret123password"
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
    "refresh_token_expires_at": 1759229400
  }
}
```

Save the `access_token` from the response to use in subsequent requests:
```bash
export TOKEN="eyJhbGciOi..."
```

---

## 2. Create a Record

Insert a new record into any table (e.g. `test`) using `/my/object-create`:

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "hello atom", "type": 1}'
```

**Response:**
```json
{
  "status": 1,
  "message": [1]
}
```

The returned integer is the newly created row ID. Ownership (`created_by_id`) is automatically assigned from your token.

---

## 3. Read Your Records

Fetch records created by you using `/my/object-read`:

```bash
curl "http://localhost:8000/my/object-read?table=test" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "status": 1,
  "message": {
    "obj_list": [
      {
        "id": 1,
        "title": "hello atom",
        "type": 1,
        "created_by_id": 2,
        "created_at": "2026-09-17T15:00:00Z"
      }
    ],
    "has_next_page": false
  }
}
```

---

## 4. Filter and Paginate

Atom supports filtering and sorting directly in query parameters:

```bash
curl -G "http://localhost:8000/my/object-read" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "table=test" \
  --data-urlencode "limit=10" \
  --data-urlencode "order=id desc" \
  --data-urlencode 'filter=["title ilike %hello%", "type = 1"]'
```

---

## 5. Update a Record

Update records using `/my/object-update`:

```bash
curl -X PUT "http://localhost:8000/my/object-update?table=test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "title": "updated atom title"}'
```

---

## 6. Delete a Record

Soft-delete or delete records using `/my/object-delete`:

```bash
curl -X POST "http://localhost:8000/my/object-delete" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"table": "test", "ids": [1]}'
```

---

## Next Steps

- 🔐 **[Authentication Guide](auth.md)** — Google OAuth, OTP verification, and password management.
- 🗃️ **[Object Read Engine](crud.md)** — Relational joins, advanced filters, and aggregation.
- 🛠️ **[Admin Toolkit](admin.md)** — Live SQL execution, AI query generation, and schema management.
- ⚙️ **[Configuration Reference](config.md)** — Complete reference of all Atom settings.
