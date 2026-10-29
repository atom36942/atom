# 💬 Messaging, Email & SMS Notifications

Atom provides a unified communications layer covering **in-app direct messaging**, **in-app notifications**, **transactional email**, and **SMS delivery**.

---

## 1. In-App Direct Messages

In-app conversations are backed by the `message` table. Each record connects a sender (`created_by_id`) to a recipient (`received_by_id`) with read timestamps (`read_at`).

### Sending a Message:
Messages are created using the standard create API:
```bash
POST /my/object-create?table=message
{"received_by_id": 42, "description": "Hello! Let's discuss the project."}
```
The sender ID is automatically stamped from the authenticated session token.

### Inbox View (`GET /my/message-inbox`):
Returns the **latest message per conversation** (one row per conversation partner), ordered by newest activity:
- Query parameters: `mode` (`"all"`, `"unread"`, `"read"`), `order`, `page`, `limit`.

### Conversation Thread (`GET /my/message-thread?user_id=42`):
Fetches the full back-and-forth conversation with another participant:
- Automatically marks incoming unread messages as read (`read_at = now()`).

### Live Messages (`/my/message-socket` WebSocket):
Off by default; turn it on with `"/my/message-socket": {"id": 38, "is_active": True}` in `config_extend.py`. WebSocket entries in `config_api` accept only `id` and `is_active` (startup fails on any other key, since the HTTP middleware never runs for WebSockets), so the socket authenticates itself:

1. Connect to `ws://<host>/my/message-socket`, then send the access token as the first message (never in the URL, where proxies log it): `{"token": "<access_token>"}`. A missing (after `auth_timeout_sec`), invalid, expired, or refresh token closes with code 1008. Reply: `{"type": "connected", "message": {"user_id": 1}}`.
2. Send `{"received_by_id": 42, "description": "Hello"}`. The row is inserted into `message` on master with `created_by_id` from the token, then `{"type": "message", "message": <row>}` is pushed to every open socket of both users. A recipient who is offline reads it later through the inbox and thread APIs, which stay the source of truth.
3. Bad input, an unknown recipient, or the rate limit returns `{"type": "error", "message": "..."}` and keeps the connection open.
4. When the access token expires, the socket closes with 1008 `token expired`; refresh with `/my/token-refresh` and reconnect.

Reference client: `/page/message`. Log in on its login card with username and password (`/auth/login-username-password`), enter the other user's id, and send messages; it loads history from `/my/message-thread` and shows new messages live. Like Atom's other pages it keeps the login alive (new tokens from `/my/token-refresh` before the access token runs out, and again before reconnecting) and shows an account avatar whose menu lists the username, user id, role and both token expiries, with Log out. It keeps `{access_token, refresh_token, username, peer_id, user, user_at}` in one localStorage key, `message` (never the password; `user` is `/my/profile`, read again after 3 hours), so a reload reconnects; Log out clears the login. localStorage is per browser, so use a second browser profile for the other user.

Limits are keyword defaults of `func_message_socket`: `auth_timeout_sec` (5), `description_length_max` (4000 characters), `rate_limit_per_minute` (60 messages per connection), `connection_per_user_max` (5 open sockets per user). Delivery reaches sockets in the same worker only, so startup fails if the socket is active with `config_uvicorn_workers` > 1. Account status (deactivated or deleted) is not rechecked during a connection.

---

## 2. In-App Notifications

Notifications live in the `notification` table, targeting `received_by_id` with metadata (`type`, `title`, `description`, `reference_table`, `reference_id`, `read_at`).

### Managing Notifications:
- **Create**: `POST /admin/object-create?table=notification`
- **Fetch Unread**: `GET /my/object-read?table=notification&ownership_column=received_by_id&filter=["read_at is null"]`.
- **Mark as Read**: The read request above automatically schedules `read_at` updates for fetched records on master, so reads can use a read replica (`?connection=replica`).
- **Delete Selected**: `POST /my/object-delete?ownership_column=received_by_id` with JSON body `{"table": "notification", "ids": [1, 2]}`.
- **Bulk Clear**: `DELETE /my/object-delete-all?table=notification&ownership_column=received_by_id`.

These operations require `received_by_id` in the corresponding operation list: `config_column_ownership_read` for fetching and `config_column_ownership_delete` for deletion. `received_by_id` is intentionally not update-approved by default.

---

## 3. Transactional Email Delivery

Atom supports pluggable email delivery via AWS SES, Resend, and Azure Communication Services.

| Provider | Service Key | Required Configurations |
| :--- | :--- | :--- |
| **AWS SES** | `ses` | `config_aws_access_key_id`, `config_aws_secret_access_key`, `config_aws_ses_region_name` |
| **Resend** | `resend` | `config_resend_url`, `config_resend_key` |
| **Azure ACS** | `azure` | `config_azure_email_connection_string` |

### Sending Transactional Emails (`POST /private/send-email`):
```bash
curl -X POST "http://localhost:8000/private/send-email"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{
    "service": "resend",
    "sender": "no-reply@example.com",
    "receiver": "user@example.com",
    "subject": "Order Confirmation",
    "body": "<h1>Thank you for your order!</h1>",
    "is_html": true
  }'
```

---

## 4. SMS & Mobile OTP Delivery

Atom provides SMS dispatch for login verification and text notifications across Azure, AWS SNS, and Fast2SMS.

| Provider | Service Key | Required Configurations |
| :--- | :--- | :--- |
| **Azure ACS** | `azure` | `config_azure_sms_connection_string`, `config_azure_sms_sender_number` |
| **AWS SNS** | `sns` | `config_aws_access_key_id`, `config_aws_secret_access_key` |
| **Fast2SMS** | `fast2sms` | `config_fast2sms_url`, `config_fast2sms_key` |

### Sending SMS (`POST /private/send-sms`):
```bash
curl -X POST "http://localhost:8000/private/send-sms"   -H "Authorization: Bearer <token>"   -H "Content-Type: application/json"   -d '{
    "service": "fast2sms",
    "mobile": "+1234567890",
    "message": "Your verification code is 482910"
  }'
```

### Mobile OTP Flow:
1. Client requests OTP: `POST /public/otp-send-mobile` with `mobile` and `role`.
2. Atom generates code of length `config_otp_length` (default 6) with expiration `config_otp_expiry_sec` (default 10m).
3. Client submits code: `POST /auth/login-mobile-otp` to authenticate.
