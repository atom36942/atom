# Webhooks

Two directions, both signed with HMAC-SHA256:

| | Who calls whom | Atom's part |
|---|---|---|
| [Outgoing](#outgoing) | Your app calls another system when something happens | Queue, sign, send, retry |
| [Incoming](#incoming) | Another service (Stripe, GitHub, Razorpay, another Atom app) calls your route | Verify the signature before the route runs |

# Outgoing

When something happens in your app, Atom calls another system's URL with a signed POST, so that system never has to poll your API. The format follows the [Standard Webhooks](https://www.standardwebhooks.com) spec, the one Stripe-style receivers and the `standardwebhooks` libraries already verify.

## Terms

| Term | Meaning in Atom |
|---|---|
| **Webhook** (subscription) | A row in `webhook`: the receiver's `url`, the `events` it wants, its signing `secret`, `is_active` |
| **Event** | A name for what happened, such as `shipment.delivered`: 1-100 of `a-z 0-9 . - _` |
| **Delivery** | One event for one webhook: a `queue_job` row on channel `channel_webhook` until it is sent |
| **Signing secret** | `whsec_` + base64 of 32 random bytes, created by Atom and shown once |
| **Signature** | `webhook-signature: v1,<base64 HMAC-SHA256(key, "<id>.<timestamp>.<body>")>`, so the receiver knows the call is yours and unchanged |
| **Outbox** | Deliveries are rows written in the same transaction as the change: if the change rolls back, nothing is sent |

## Flow

```
1. admin   POST /admin/webhook-create {"url": "https://erp.acme.com/hook", "events": ["shipment.delivered"]}
           → {"id": 3, "secret": "whsec_…"}                          (the secret is shown only here; give it to the receiver)
2. code    await app_state.func_webhook_send(client_postgres=conn, event="shipment.delivered", data={"shipment_id": 881})
           → one queue_job row per active webhook listening to that event
3. Atom    the app's delivery loop (config_webhook_is_active) takes the row (FOR UPDATE SKIP LOCKED) and POSTs:
             webhook-id: msg_…   webhook-timestamp: 1763712000   webhook-signature: v1,…
             {"type": "shipment.delivered", "timestamp": "2026-11-21T10:42:00Z", "data": {"shipment_id": 881}}
4. result  2xx → row deleted (delivered)
           else → retried after 60 s, doubled each time (60 s, 2 min, 4 min … about 4 h over 8 retries)
           after 8 retries → kept with status 2 (failed) and its error
```

## Setup

1. `.env` or `config_extend.py`: `config_webhook_is_active=True`. The delivery loop runs inside the app, one per worker; there is no other process to deploy.
2. Create the webhook with `/admin/webhook-create` (id 101: root, or a user granted it). The URL must be `https` and resolve to a public address (checked at creation and before every delivery, so a webhook can never reach `localhost`, `10.x`, `169.254.169.254` and the like).
3. Call `func_webhook_send` where the event happens: a route in `router_extend/`, a function or a script. Pass the connection of the open transaction (`client_postgres=conn`) to queue the deliveries only if the change commits; a pool sends them on its own.

## Manage

| Need | How |
|---|---|
| List webhooks | `GET /admin/object-read?table=webhook` (the `secret` is `read_blocked` for every group, so never returned) |
| Pause or change events | `PUT /admin/object-update?table=webhook` with `{"id": 3, "is_active": false}` or `events`; a paused webhook's queued deliveries are skipped |
| Remove | `POST /admin/object-delete` with `{"table": "webhook", "ids": [3]}` |
| Rotate the secret | Create a new webhook for the same URL, give the receiver the new secret, delete the old one |
| See failed deliveries | `/admin/postgres-query-runner-read`: `SELECT * FROM queue_job WHERE channel = 'channel_webhook' AND status = 2` |
| Resend failed ones | `/admin/postgres-query-runner-write`: `UPDATE queue_job SET status = 1, attempt = 0, run_at = now() WHERE channel = 'channel_webhook' AND status = 2` |

## The receiver

A delivery may come more than once (a timeout after the receiver already saved it): keep `webhook-id` and ignore one already seen. Refuse a timestamp more than 5 minutes off, so an old call can't be replayed.

```python
import base64, hashlib, hmac, time
def verify(secret, headers, body: bytes):
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f'{headers["webhook-id"]}.{headers["webhook-timestamp"]}.'.encode() + body
    expected = "v1," + base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    if abs(time.time() - int(headers["webhook-timestamp"])) > 300: raise ValueError("too old")
    if not any(hmac.compare_digest(expected, s) for s in headers["webhook-signature"].split()): raise ValueError("bad signature")
```

## Example: a customer's ERP learns about deliveries

```python
# router_extend/shipment.py
@router.put("/shipment/deliver")
async def func_api_shipment_deliver(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "id", "type": "int", "required": True}])
    async with app_state.client_postgres_dict["master"].acquire() as conn, conn.transaction():
        await conn.execute("UPDATE shipment SET status = 4, delivered_at = now() WHERE id = $1", ob["id"])
        await app_state.func_webhook_send(client_postgres=conn, event="shipment.delivered", data={"shipment_id": ob["id"]})
    return {"status": 1, "message": "done"}
```

ACME's ERP gets the signed POST within seconds and closes its purchase order; if its server is down, Atom keeps retrying for about 4 hours.

## Limits

- One delivery at a time per app worker; a slow receiver (up to 10 s) delays the next. Fine for thousands a day, not for a firehose.
- Order is not guaranteed across retries; send the state in `data`, not only "it changed".
- Incoming webhooks (another service calling you) are below.

# Incoming

A route another service calls must be public (the service can't log in), so anyone who finds its URL could post a fake "payment captured". The signature is the proof: the service signs the exact body with a secret only you and it know, and Atom checks it before your route runs. This is **webhook signature verification**.

## Flow

```
Razorpay  POST /payment/webhook   X-Razorpay-Signature: 9f2c…   {"event":"payment.captured",…}
   │
Atom middleware (route has webhook_verify)
   │  reads the raw body once → HMAC-SHA256(secret, signed bytes) → constant-time compare with the header
   ├─ missing, wrong, or timestamp over 300 s off → 401, the route never runs
   └─ match → request.state.webhook = {"scheme", "id", "timestamp"} → your route reads the body as usual
```

## Setup

```python
# .env
config_webhook_secret_razorpay=<from the Razorpay dashboard>

# config_extend.py
"/payment/webhook": {"id": 220, "auth": [], "webhook_verify": {"scheme": "razorpay", "secret": "config_webhook_secret_razorpay"}},
```

```python
# router_extend/payment.py: business logic only, no signature code
@router.post("/payment/webhook")
async def func_api_payment_webhook(*, request: Request):
    app_state = request.app.state
    event = orjson.loads(await request.body())
    if event["event"] == "payment.captured":
        await app_state.client_postgres_dict["master"].execute("UPDATE invoice SET paid_at = now() WHERE razorpay_id = $1 AND paid_at IS NULL", event["payload"]["payment"]["entity"]["id"])
    return {"status": 1, "message": "ok"}
```

`auth` must be `[]` (the signature is the credential); `secret` names the `config_` setting, never the secret itself. Startup refuses an unknown scheme or a bad entry; a request is 500 while the secret setting is empty.

## Schemes are data

Every provider signs the same way and differs only in which header, which bytes and how the HMAC is written, so a scheme is a dict in `config_webhook_verify_scheme`, not code. Atom ships:

| Scheme | For | Header and signed bytes |
|---|---|---|
| `standard` | [Standard Webhooks](https://www.standardwebhooks.com): Svix, Clerk, Resend, and **Atom's own outgoing webhooks**, so one Atom app can receive another's | `webhook-signature: v1,<base64>` of `{id}.{timestamp}.{body}`; secret `whsec_…` |
| `stripe` | Stripe | `Stripe-Signature: t=…,v1=<hex>` of `{timestamp}.{body}` |
| `github` | GitHub | `X-Hub-Signature-256: sha256=<hex>` of `{body}` |
| `shopify` | Shopify | `X-Shopify-Hmac-Sha256: <base64>` of `{body}` |
| `razorpay` | Razorpay | `X-Razorpay-Signature: <hex>` of `{body}` |

A provider Atom doesn't know is one line in `config_extend.py`:

```python
from config import config_webhook_verify_scheme as base_config_webhook_verify_scheme
config_webhook_verify_scheme = {**base_config_webhook_verify_scheme, "acme_wms": {"header": "X-Acme-Sig", "encoding": "hex", "signed": "{timestamp}.{body}", "timestamp": {"header": "X-Acme-Time"}}}
```

| Field | Meaning |
|---|---|
| `header` | The header holding the signature (required) |
| `encoding` | `hex` or `base64` (required) |
| `signed` | The signed bytes, ending with `{body}`: `{body}`, `{timestamp}.{body}`, `{id}.{timestamp}.{body}` (required) |
| `prefix` | Text before each signature (`sha256=`, `v1,`); several space-separated signatures are each tried |
| `key` | The signature is this key's value in a `k=v,k=v` header (Stripe's `v1`) |
| `timestamp`, `id` | Where they are: `{"header": <name>}` or `{"key": <name in the signature header>}`; a timestamp is checked against the tolerance |
| `secret_encoding` | `raw` (default, the secret's bytes) or `base64` (the part after `whsec_`) |

Every scheme is checked at startup, so a typo fails at boot, not on the first payment. A provider that signs with public-key cryptography rather than a shared secret (PayPal, Amazon SNS) is verified in its route with the provider's SDK.

## Duplicates

Providers retry, so one event can arrive twice: store the event's id (`request.state.webhook["id"]` for `standard`, the id in the body otherwise) with a unique index, and skip one already handled, as the `paid_at IS NULL` above does.

## Senders that can't sign

Some services push without any signature: many device and IoT clouds post each location or alarm to a URL you give them. Their route is public too, so it needs another proof. Two `config_api` keys, on any route, checked before the body is read:

| Key | Passes when | Else |
| :--- | :--- | :--- |
| `"ip_allow": ["203.0.113.0/24", "198.51.100.7"]` | The caller's real IP (the last `X-Forwarded-For` entry behind a private proxy, as for rate limits) is in one of the addresses or CIDR ranges | 403 |
| `"token_verify": {"secret": "config_webhook_token_<name>", "in": "header", "name": "x-webhook-token"}` | The header (or query value, `"in": "query"`) equals the secret in `.env`, compared in constant time | 403; 500 when the secret is not set |

```python
# .env
config_webhook_token_devices=<long random value>

# config_extend.py
"/device/location-push": {"id": 300, "auth": [], "ip_allow": ["203.0.113.0/24"], "token_verify": {"secret": "config_webhook_token_devices"}},
```

- Prefer both: the sender's published IP ranges, and a token in a header. `in` defaults to `header`, `name` to `x-webhook-token` (`token` for a query).
- A query token is for a sender that only takes a URL: its name must contain `token`, so the request log hides its value. It is weaker than a header (a URL is copied into proxy and browser logs), so add `ip_allow` with it.
- Neither proves the body wasn't changed, as a signature does: use `webhook_verify` whenever the sender can sign.
- Such senders often don't retry: reply fast (write with `mode="buffer"`, [database.md](database.md#4-in-memory-write-buffering)) and fill gaps from the sender's history API.
