# 📱 SMS & Mobile OTP

Atom provides pluggable **SMS** delivery for mobile verification and OTP authentication. The mobile provider is selected per-request using the `service` parameter and validated against `config_mobile_services`.

---

## 🚀 Supported Providers

| Provider | `service` | Key Configurations | Description |
| :--- | :--- | :--- | :--- |
| **Azure Communication Services** | `azure` | `config_azure_sms_connection_string`<br>`config_azure_sms_from_number` | Enterprise SMS via Azure ACS. Supports purchased E.164 phone numbers and alphanumeric sender IDs. |
| **AWS SNS** | `sns` | `config_aws_access_key_id`<br>`config_aws_secret_access_key`<br>`config_aws_sns_region_name` | Amazon Simple Notification Service. Supports direct SMS and DLT templates. |
| **Fast2SMS** | `fast2sms` | `config_fast2sms_url`<br>`config_fast2sms_key` | India-focused SMS gateway using automated transactional OTP routing. |

Provider registry in [`config.py`](../config.py):
```python
config_mobile_services = ["sns", "fast2sms", "azure"]
```

---

## ⚙️ Configuration Reference

Configure these parameters in [`config.py`](../config.py) or load them via `.env`:

### 1. Azure Communication Services (ACS)
```python
# ACS Connection String (Azure Portal > Communication Services Resource > Keys)
config_azure_sms_connection_string = "endpoint=https://<resource>.communication.azure.com/;accesskey=<key>"

# Purchased phone number (E.164, e.g. "+18005550100") or Alphanumeric Sender ID (e.g. "ATOM")
config_azure_sms_from_number = "+18005550100"
```

> [!NOTE]
> Azure strictly requires a sender (`from_`). You can define `config_azure_sms_from_number` as the default, or pass `sender` dynamically per API call.

### 2. AWS SNS
```python
config_aws_access_key_id = "AKIA..."
config_aws_secret_access_key = "..."
config_aws_sns_region_name = "us-east-1"
```

### 3. Fast2SMS
```python
config_fast2sms_url = "https://www.fast2sms.com/dev/bulkV2"
config_fast2sms_key = "YOUR_FAST2SMS_API_KEY"
```

### 4. OTP System Settings
```python
config_otp_length = 6         # Number of digits in generated code (e.g. 6)
config_otp_expiry_sec = 600   # Code validity window in seconds (10 minutes)
config_otp_static = None      # Static code bypass for testing/staging (e.g. 123456)
```

---

## 📡 API Endpoints

### 1. Send Mobile OTP — `POST /public/otp-send-mobile`

Generates a numeric OTP according to `config_otp_length`, stores it in the `otp` database table, and dispatches it via the selected mobile service.

#### Query Parameters:
* **`service`** (`str`, required): One of `["sns", "fast2sms", "azure"]`.
* **`mobile`** (`str`, required): Destination mobile number in E.164 format (e.g. `+1234567890`).
* **`sender`** (`str`, optional): Custom sender ID or phone number (useful for Azure per-tenant or per-brand origination). Falls back to `config_azure_sms_from_number` if omitted.

#### Examples:

**Using Azure:**
```http
POST /public/otp-send-mobile?service=azure&mobile=%2B1234567890
```

**Using Azure with custom Sender ID:**
```http
POST /public/otp-send-mobile?service=azure&mobile=%2B1234567890&sender=MYBRAND
```

**Using AWS SNS:**
```http
POST /public/otp-send-mobile?service=sns&mobile=%2B1234567890
```

**Using Fast2SMS:**
```http
POST /public/otp-send-mobile?service=fast2sms&mobile=9876543210
```

#### Response:
```json
{
  "status": 1,
  "message": "done"
}
```

---

### 2. Send Mobile OTP with DLT Template — `POST /public/otp-send-mobile-sns-template`

Sends via AWS SNS using a pre-registered **DLT Template** (mandated in India by telecom regulations). Atom replaces `{otp}` in the `message` with the generated code.

#### Request Body:
```json
{
  "mobile": "+919876543210",
  "message": "Your verification code is {otp}. Valid for 10 minutes.",
  "template_id": "1207161979...",
  "entity_id": "1201159876...",
  "sender_id": "MYAPPI"
}
```

#### Response:
```json
{
  "status": 1,
  "message": "done"
}
```

---

### 3. Verify OTP & Authenticate — `POST /auth/login-mobile-otp`

Once the user receives the OTP on their mobile phone, they submit it to the authentication endpoint.

#### Request Body:
```json
{
  "mobile": "+1234567890",
  "otp": 584920
}
```

#### Response:
```json
{
  "status": 1,
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "user": {
    "id": 42,
    "mobile": "+1234567890",
    "role": 1
  }
}
```

---

## 🛠️ Architecture & Execution Flow

```
Client (User)
      │
      │ 1. POST /public/otp-send-mobile?service=azure&mobile=+1234567890
      ▼
router/public.py  ──>  func_otp_generate()
                              │
                              ├─► Saves OTP + mobile in `otp` PostgreSQL table
                              │
                              ▼
                       func_otp_send_mobile()
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
     service == "azure"  service == "sns"  service == "fast2sms"
             │                │                │
      Azure SmsClient      AWS SNS         Fast2SMS HTTP API
   (client_azure_sms)  (client_sns)
             │                │                │
             └────────────────┴────────────────┘
                              │
                              ▼
                     Recipient's Phone
```

1. **Generation** ([`func_otp_generate`](../function.py)): Creates a secure random numeric code and writes it to the `otp` table.
2. **Dispatch** ([`func_otp_send_mobile`](../function.py)):
   - **Azure**: Uses `client_azure_sms.send(from_=..., to=[mobile], message=...)`.
   - **SNS**: Uses `client_sns.publish(PhoneNumber=mobile, Message=...)`.
   - **Fast2SMS**: Calls Fast2SMS GET API with `route="otp"`.
3. **Verification** ([`func_otp_verify`](../function.py)): Checks the latest OTP recorded for the mobile number against `config_otp_expiry_sec`.

---

## 💡 Provider Comparison

| Feature | Azure Communication Services | AWS SNS | Fast2SMS |
| :--- | :--- | :--- | :--- |
| **Global Reach** | High (Global Tier-1 networks) | High (Worldwide delivery) | Primarily India |
| **Sender Origination** | Strict: requires purchased number or alphanumeric ID | Shared pool default; dedicated optional | Managed automatically by Fast2SMS route |
| **Template Support** | Plain message format | Plain message & DLT template attributes | OTP variables (`variables_values`) |
| **Connection Setup** | Connection string | AWS IAM credentials & region | API Key & Gateway URL |

---

📚 **Related Documentation:**
* [auth.md](auth.md) — Authentication flows & JWT token lifecycle
* [email.md](email.md) — Email sending documentation
* [config.md](config.md) — Complete configuration variable reference
