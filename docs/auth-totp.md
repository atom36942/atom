# Two-factor authentication (TOTP)

A second step after the password: a 6-digit code from an authenticator app on the user's phone, changing every 30 seconds, so a leaked password alone no longer logs in. **Optional for each user and off by default:** a user who never turns it on logs in exactly as before. Backend only: Atom's pages do not show the code step yet, so a user who turns 2FA on finishes login through the API until a page adds it.

| Term | Meaning in Atom |
| :--- | :--- |
| TOTP | Time-based one-time password (RFC 6238): `HMAC-SHA1(secret, now ÷ 30)` cut to 6 digits. The phone and the server compute it separately from the same secret and clock |
| Authenticator app | Any: Microsoft or Google Authenticator, Apple Passwords, 1Password, Bitwarden, Authy. Atom uses the defaults every app supports (SHA-1, 6 digits, 30 s) |
| TOTP secret | 20 random bytes per user, shown once (QR code) and kept in `users.totp_secret`, encrypted with AES-GCM by `config_totp_encryption_key` and bound to the user's id |
| `mfa_token` | A 5-minute JWT of type `mfa` holding only the user id: proof that the password step passed. It opens no route; only `/auth/login-totp` reads it |
| Recovery codes | 10 one-time codes (`XXXXX-XXXXX`) shown once when 2FA is turned on, for a lost phone; kept as HMAC hashes and removed when used |

## Turn it on for the app
Set `config_totp_encryption_key` in `.env` (32 characters or more, e.g. `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`). Until then the 2FA routes answer "2FA not configured" and nothing else changes. Keep the key: changing it makes every stored secret unreadable, and those users need an admin reset. `config_totp_issuer` names the app in the authenticator (default: the master database name).

## What a page reads
| Need | Where |
|---|---|
| Is 2FA available in this app? (show the Two-factor row or not) | `GET /info` → `is_totp_enabled` (`true` when `config_totp_encryption_key` is set) |
| Is it on for this user, since when? | `GET /my/profile` → `totp_enabled_at` (`null` = off) |
| Is it on for each user? (User management) | `/admin/object-read?table=users` → `totp_enabled_at` |

## Columns in `users`
| Column | Holds |
| :--- | :--- |
| `totp_enabled_at` | `null` = off (everyone at first), else when it was turned on |
| `totp_secret` | The encrypted secret (set at setup, before 2FA is on) |
| `totp_last_step` | The last 30-second step used, so a code works once |
| `totp_recovery` | The recovery codes' hashes |

`totp_secret` and `totp_recovery` are in `config_column_read_blocked` (never returned); `totp_secret`, `totp_last_step` and `totp_recovery` are in `config_column_users_blocked`; `totp_enabled_at` only an admin may change, and only to `null`. Clearing `totp_enabled_at`, by any path, clears the other three (trigger `users_totp_clear`).

## Flow
| Step | Request → response |
| :--- | :--- |
| Setup | `POST /my/totp-setup` → `{"secret", "uri"}`; the page shows `uri` (`otpauth://totp/pulse:ravi@x.com?secret=...`) as a QR code. 2FA is not on yet |
| Enable | `POST /my/totp-enable {"code": "492039"}` → `{"recovery_codes": [10 codes]}`, shown only here. 2FA is on |
| Login, step 1 | Any `/auth/login-*` with the right password → `{"mfa_required": true, "mfa_token": "eyJ..."}` instead of tokens |
| Login, step 2 | `POST /auth/login-totp {"mfa_token": "eyJ...", "code": "310554"}` (or a recovery code) → `{"access_token", "refresh_token", ...}`, the same as any login |
| Disable | `POST /my/totp-disable {"code": "..."}` (a current or recovery code) → `"2FA off"` |
| Lost phone | A recovery code at step 2, or an admin: `PUT /admin/user-update {"id": 42, "totp_enabled_at": null}`; the user sets it up again |

A client handles the one new response:
```js
const r = (await post("/auth/login-username-password", {username, password, role})).message;
const tokens = r.mfa_required ? (await post("/auth/login-totp", {mfa_token: r.mfa_token, code: await askCode()})).message : r;
```

## Checks
- A code is accepted for the current step and one either side (clock drift) and only for a step after the last one used, saved in one `UPDATE`, so the same code never works twice, even on two workers at once.
- `/auth/login-totp` is limited to 5 tries a minute; an `mfa_token` expires in 5 minutes. Signup, `/my/token-refresh` and API keys are unchanged (they come after a full login).
- The password is checked first and fails as before; the code is asked only after it.
