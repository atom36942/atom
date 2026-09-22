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
Returns the **latest message per conversation** (one row per chat participant), ordered by newest activity:
- Query parameters: `mode` (`"all"`, `"unread"`, `"read"`), `order`, `page`, `limit`.

### Conversation Thread (`GET /my/message-thread?user_id=42`):
Fetches the full back-and-forth conversation with another participant:
- Automatically marks incoming unread messages as read (`read_at = now()`).

---

## 2. In-App Notifications

Notifications live in the `notification` table, targeting `received_by_id` with metadata (`type`, `title`, `description`, `reference_table`, `reference_id`, `read_at`).

### Managing Notifications:
- **Create**: `POST /admin/object-create?table=notification`
- **Fetch Unread**: `GET /my/object-read?table=notification&ownership_column=received_by_id&filter=["read_at is null"]`.
- **Mark as Read**: The read request above automatically schedules `read_at` updates for fetched records on the primary database.
- **Delete Selected**: `POST /my/object-delete?ownership_column=received_by_id` with JSON body `{"table": "notification", "ids": [1, 2]}`.
- **Bulk Clear**: `DELETE /my/object-delete-all?table=notification&ownership_column=received_by_id`.

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
