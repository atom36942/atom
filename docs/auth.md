# 🔐 Authentication

Atom uses **stateless JWT** authentication. Clients log in once, receive an access + refresh token, and send the access token as a `Bearer` header on every protected request. The middleware decodes it into `request.state.user`; nothing is stored server-side.

All auth endpoints live in [`router/auth.py`](../router/auth.py) and are **public** (`is_token=False`) — they mint tokens, they don't require one.

---

## Users, roles & multi-tenancy

Users live in the `users` table. Two fields shape auth:

- **`role`** (smallint) — the user's role. Validated on signup/login against `config_allowed_users_role` (default `[1,2,3,4,5]`). **Role `1` is the root/admin role** and cannot be created through the public auth endpoints.
- **Identity fields** — `username`, `email`, `mobile`, `google_login_id`, `id_ext`. By default, each identity is globally unique across the system (e.g. `unique:"email"`). You can also configure them to be composite (e.g. `unique:"email,role"` or `unique:"email,tenant_id"`). See **[identity.md](identity.md)** for detailed identity configuration and customization.

---

## Signup

### `POST /auth/signup-username-password`
Body: `role`, `username`, `password`, optional `source`.

Flow: validate role → regex-check username/password (`config_regex`) → reject if `config_is_signup=false` → reject `role=1` → hash password with Argon2 → insert user → return tokens.

```jsonc
// request body
{"role": 2, "username": "alice", "password": "secret123"}
// response
{"status": 1, "message": {"access_token": "…", "refresh_token": "…",
                          "access_token_expires_at": 0, "refresh_token_expires_at": 0}}
```

> OTP and Google logins **auto-create** the user on first login (unless signup is disabled), so they double as signup.

---

## Login methods

| Endpoint | Credentials | Notes |
|----------|-------------|-------|
| `/auth/login-password` | password | Compares against `config_login_password` and returns `"ok"` when correct. |
| `/auth/login-username-password` | username + password | Password verified with Argon2. |
| `/auth/login-email-password` | email + password | |
| `/auth/login-mobile-password` | mobile + password | |
| `/auth/login-email-otp` | email + otp | Verifies OTP, then finds-or-creates the user. |
| `/auth/login-mobile-otp` | mobile + otp | Same, via SMS OTP. |
| `/auth/login-google` | `google_token` (+ role) | Verifies the Google ID token, finds-or-creates by `google_login_id`. |

**Password logins** fetch the user (`func_auth_user_login_fetch`) and verify the hash; a wrong password raises `"incorrect password"`.

**OTP logins** call `func_otp_verify` first (checks the code against the `otp` table within `config_otp_expiry_sec`), then look the user up by identity+role and create them if absent.

**Google login** verifies the token against `config_google_login_client_id` (off-thread), then matches on the Google `sub` id, storing profile info in `google_login_metadata`.

Every user login method ends the same way — `func_token_encode` returns the token pair.

### `POST /auth/login-password`

Body: `password`.

This route compares the supplied password with `config_login_password`. It does not query a user or generate tokens.

```jsonc
// request body
{"password": "123456"}
// response
{"status": 1, "message": "ok"}
```

An incorrect password raises `"incorrect password"`.

---

## OTP flow

For OTP logins the client first requests a code, then submits it:

1. **Send** — `POST /public/otp-send-email` or `/public/otp-send-mobile` → `func_otp_generate` creates a `config_otp_length`-digit code, stores it in the `otp` table, and sends it via the chosen email/SMS service.
2. **Login** — `POST /auth/login-email-otp` (or mobile) with the code → `func_otp_verify` validates it's correct and unexpired.

`/public/otp-verify` exists to check a code without logging in.

---

## Tokens (`func_token_encode` / `func_token_decode`)

`func_token_encode` produces two HS256 JWTs signed with `config_token_secret_key`:

```jsonc
{"access_token", "refresh_token", "access_token_expires_at", "refresh_token_expires_at"}
```

- The payload embeds only the fields listed in **`config_column_token_encode`** (`id`, `role`, `username`, `id_ext`, `deactivated_at`, `deleted_at`) — not the whole user row. Keep this minimal; it's what `token`-mode middleware checks trust without a DB hit.
- Lifetimes come from `config_access_token_expires_sec` / `config_refresh_token_expires_sec`.
- Each token carries a `type` (`access` / `refresh`), surfaced on decode as `user["_token_type"]`.

`func_token_decode` (run by the middleware) reads the `Authorization: Bearer <token>` header, verifies the signature, and returns the claims dict (or `{}` if absent). It never rejects — enforcement is the middleware's job. See [middleware.md](middleware.md).

### Refreshing — `POST /my/token-refresh`
Requires a valid token, re-reads the user from the DB, and issues a fresh token pair — use it to rotate an expiring access token.

---

## Using a token

```bash
curl http://localhost:8000/my/profile \
  -H "Authorization: Bearer <access_token>"
```

In a handler, the authenticated user is on `request.state.user`:

```python
user_id = request.state.user["id"]      # protected route (is_token=True)
role    = request.state.user["role"]
```

---

## How enforcement happens

Minting a token doesn't protect anything by itself — a route is protected by its `config_api` entry (`is_token`, `user_check_role`, …), checked in the middleware. See [config.md](config.md#config_api) and [security.md](security.md).

---

📚 [Back to README](../readme.md)
