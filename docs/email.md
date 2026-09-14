# 📨 Email

Atom provides pluggable **Email** delivery for transactional messages and OTP authentication. The email provider is selected per-request using the `service` parameter and validated against `config_email_services`.

---

## 🚀 Supported Providers

| Provider | `service` | Key Configurations | Description |
| :--- | :--- | :--- | :--- |
| **AWS SES** | `ses` | `config_aws_access_key_id`<br>`config_aws_secret_access_key`<br>`config_aws_ses_region_name` | Amazon Simple Email Service. High-volume transactional email. |
| **Resend** | `resend` | `config_resend_url`<br>`config_resend_key` | Modern developer-first email platform via REST API. |
| **Azure Communication Services** | `azure` | `config_azure_email_connection_string` | Enterprise email delivery via Azure ACS EmailClient. |

Provider registry in [`config.py`](../config.py):
```python
config_email_services = ["ses", "resend", "azure"]
```

---

## ⚙️ Configuration Reference

Configure these parameters in [`config.py`](../config.py) or load them via `.env`:

### 1. AWS SES
```python
config_aws_access_key_id = "AKIA..."
config_aws_secret_access_key = "..."
config_aws_ses_region_name = "us-east-1"
```

### 2. Resend
```python
config_resend_url = "https://api.resend.com/emails"
config_resend_key = "re_..."
```

### 3. Azure Communication Services (Email)
```python
# ACS Connection String (Azure Portal > Communication Services Resource > Keys)
config_azure_email_connection_string = "endpoint=https://<resource>.communication.azure.com/;accesskey=<key>"
```

### 4. OTP System Settings
```python
config_otp_length = 6         # Number of digits in generated code (e.g. 6)
config_otp_expiry_sec = 600   # Code validity window in seconds (10 minutes)
config_otp_static = None      # Static code bypass for testing/staging (e.g. 123456)
```

---

## 📡 API Endpoints

### 1. Send Transactional Email — `POST /private/send-email`

Authenticated endpoint for application, notification, or alert emails with multi-recipient and carbon copy support.

#### Request Body:
```jsonc
{
  "service": "ses",                  // "ses", "resend", or "azure"
  "sender": "no-reply@yourapp.com",
  "to": ["user@example.com"],
  "subject": "Account Update",
  "text": "Your account details have been updated successfully.",
  "cc": [],                          // optional list of emails
  "bcc": [],                         // optional list of emails
  "reply_to": []                     // optional list of emails
}
```

#### Implementation:
Dispatches via `func_email_send` in [`function.py`](../function.py), mapping recipients and content to the chosen provider's SDK.

---

### 2. Send Email OTP — `POST /public/otp-send-email`

Generates a numeric OTP code according to `config_otp_length`, records it in the `otp` table, and sends it to the user's email address.

#### Query Parameters:
* **`service`** (`str`, required): One of `["ses", "resend", "azure"]`.
* **`sender`** (`str`, required): Verified sender email address (e.g. `auth@yourapp.com`).
* **`email`** (`str`, required): Target recipient email address.

#### Example:
```http
POST /public/otp-send-email?service=resend&sender=auth@yourapp.com&email=user@example.com
```

#### Response:
```json
{
  "status": 1,
  "message": "done"
}
```

---

### 3. Verify OTP & Authenticate — `POST /auth/login-email-otp`

Submits the received email code to authenticate and receive session tokens.

#### Request Body:
```json
{
  "email": "user@example.com",
  "otp": 492810
}
```

#### Response:
```json
{
  "status": 1,
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "user": {
    "id": 15,
    "email": "user@example.com",
    "role": 1
  }
}
```

---

## 🛠️ Architecture & Execution Flow

```
Client (User / Admin)
      │
      ├─► POST /public/otp-send-email  ──► func_otp_generate() ──► func_otp_send_email()
      │                                                                  │
      └─► POST /private/send-email    ──► func_email_send() ────────────┤
                                                                         │
                         ┌───────────────────────────────────────────────┤
                         ▼                       ▼                       ▼
                  service == "ses"       service == "resend"      service == "azure"
                         │                       │                       │
                     client_ses              HTTP API            client_azure_email
                  (aiobotocore/boto3)        (httpx)            (azure-comm-email)
                         │                       │                       │
                         └───────────────────────┼───────────────────────┘
                                                 ▼
                                        Recipient's Inbox
```

---

## 💡 Provider Comparison

| Feature | AWS SES | Resend | Azure Communication Services |
| :--- | :--- | :--- | :--- |
| **Best For** | High volume, AWS-native infra | Fast developer onboarding, HTML emails | Azure-native infra, Microsoft enterprise stacks |
| **Authentication** | IAM Access Keys / Roles | API Bearer Token | Connection string |
| **Client Type** | Boto3 / botocore | Async HTTP client (`httpx`) | Azure SDK `EmailClient` |

---

📚 **Related Documentation:**
* [sms.md](sms.md) — SMS and Mobile OTP delivery
* [messaging.md](messaging.md) — In-app direct messaging & notifications
* [auth.md](auth.md) — Authentication flows & token lifecycle
* [config.md](config.md) — Complete configuration reference
