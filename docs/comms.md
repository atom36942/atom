# 📨 Email

Atom sends transactional **email** through pluggable providers, chosen per-request with a `service` param.

> [!TIP]
> For SMS and Mobile OTP delivery (Azure Communication Services, AWS SNS, Fast2SMS), see **[sms.md](sms.md)**.

| Channel | `service` options | Config registry |
|---------|-------------------|-----------------|
| Email | `ses` (AWS), `resend`, `azure` | `config_email_services` |

The chosen provider's client/keys must be configured (see [config.md](config.md)) or the call errors. Logic lives in `func_email_send` and `func_otp_send_email` in [`function.py`](../function.py).

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

## Sending Email OTP — `POST /public/otp-send-email`

Generates a `config_otp_length`-digit code, stores it in the `otp` table, and emails it via `func_otp_send_email`.

* **Query parameters**: `service` (`ses`/`resend`/`azure`), `sender`, `email`.

After sending, the client submits the code to an OTP login endpoint — see [auth.md](auth.md#otp-flow).

---

## Choosing an Email Provider

Providers are interchangeable — the same endpoint works with any configured `service`, so you can switch (e.g. SES → Resend) by changing one param and supplying the new provider's config.

| Provider | Channel | Notes |
|----------|---------|-------|
| `ses` | Email | AWS SES; needs `config_aws_ses_region_name` + credentials. |
| `resend` | Email | Needs `config_resend_url` / `config_resend_key`. |
| `azure` | Email | Needs `config_azure_email_connection_string`. |

---

📚 **Related Documentation:**
* [sms.md](sms.md) — SMS and Mobile OTP delivery
* [auth.md](auth.md) — OTP verification and login flows
* [config.md](config.md) — Configuration reference
* [Back to README](../readme.md)
