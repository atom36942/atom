# 📨 Email & SMS

Atom sends **email** and **SMS** through pluggable providers, chosen per-request with a `service` param. This page covers the sending side; for the OTP login *flow* that builds on it, see [auth.md](auth.md).

| Channel | `service` options | Config registry |
|---------|-------------------|-----------------|
| Email | `ses` (AWS), `resend`, `azure` | `config_email_services` |
| SMS | `sns` (AWS), `fast2sms` | `config_mobile_services` |

The chosen provider's client/keys must be configured (see the [README](../readme.md#configuration)) or the call errors. Logic lives in `func_email_send`, `func_otp_send_email`, and `func_otp_send_mobile` in [`function.py`](../function.py).

---

## Sending email — `POST /private/send-email`

Authenticated. Body:

```jsonc
{
  "service": "ses",
  "sender": "no-reply@yourapp.com",
  "to": ["user@example.com"],
  "subject": "Hello",
  "text": "Body text",
  "cc": [], "bcc": [], "reply_to": []
}
```

`to`, `cc`, `bcc`, `reply_to` are lists; `cc`/`bcc`/`reply_to` are optional. `func_email_send` dispatches to the provider named in `service`.

---

## Sending SMS (via OTP endpoints)

SMS sending is exposed through the OTP endpoints (the framework's built-in SMS use case):

### `POST /public/otp-send-email`
Query: `service` (email provider), `sender`, `email`. Generates a `config_otp_length`-digit code, stores it in the `otp` table, and emails it via `func_otp_send_email`.

### `POST /public/otp-send-mobile`
Query: `service` (`sns`/`fast2sms`), `mobile`. Generates + stores a code and sends it by SMS via `func_otp_send_mobile`.

### `POST /public/otp-send-mobile-sns-template`
Body: `mobile`, `message`, `template_id`, `entity_id`, `sender_id`. Sends via AWS SNS using a **DLT template** (required for transactional SMS in some regions, e.g. India). The template fields are passed through to SNS as `sns_template`.

After sending, the client submits the code to an OTP login endpoint — see [auth.md](auth.md#otp-flow).

---

## Choosing a provider

Providers are interchangeable — the same endpoint works with any configured `service`, so you can switch (e.g. SES → Resend) by changing one param and supplying the new provider's config. Because each is optional, enable only what you use.

| Provider | Channel | Notes |
|----------|---------|-------|
| `ses` | Email | AWS SES; needs `config_aws_ses_region_name` + credentials. |
| `resend` | Email | Needs `config_resend_url` / `config_resend_key`. |
| `azure` | Email | Needs `config_azure_email_connection_string`. |
| `sns` | SMS | AWS SNS; supports DLT templates. |
| `fast2sms` | SMS | Needs `config_fast2sms_url` / `config_fast2sms_key`. |

---

📚 [Back to README](../readme.md)
