# import
import asyncio
import base64
import hashlib
import hmac
import ipaddress
import re
import secrets
import time
from typing import Any
from urllib.parse import urlsplit
import asyncpg
import httpx
import orjson
from .background import func_runtime_error_record
from .middleware import func_api_error
from .queues import QUEUE_POSTGRES_NOTIFY
from .queues import func_queue_postgres_job_take
WEBHOOK_CHANNEL = "channel_webhook"
WEBHOOK_EVENT_REGEX = re.compile(r"^[a-z0-9_.-]{1,100}\Z")
WEBHOOK_SEND = f"WITH job AS (INSERT INTO queue_job (channel, payload) SELECT $1, jsonb_build_object('webhook_id', id, 'message_id', 'msg_' || replace(gen_random_uuid()::text, '-', ''), 'event', $2::text, 'data', $3::jsonb) FROM webhook WHERE is_active AND $2 = ANY(events) RETURNING id) SELECT (SELECT count(*) FROM job), pg_notify('{QUEUE_POSTGRES_NOTIFY}', $1)"  # noqa: S608 - a constant, values bound as $n

# function
def func_webhook_secret_create() -> str:
    """A new signing secret in the Standard Webhooks format: whsec_ + base64 of 32 random bytes."""
    return "whsec_" + base64.b64encode(secrets.token_bytes(32)).decode()

def func_webhook_sign(*, secret: str, message_id: str, timestamp: int, body: bytes) -> str:
    """The webhook-signature header (Standard Webhooks): v1,base64(HMAC-SHA256(key, "<message_id>.<timestamp>.<body>")), key = the base64 after whsec_."""
    key = base64.b64decode(secret.removeprefix("whsec_"))
    digest = hmac.new(key, f"{message_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()

def func_webhook_event_check(*, event: str) -> str:
    """An event name: 1-100 of a-z, 0-9, dot, dash, underscore (shipment.delivered)."""
    if not isinstance(event, str) or not WEBHOOK_EVENT_REGEX.match(event): raise func_api_error(message=f"invalid webhook event: {event!r}; use 1-100 of a-z, 0-9, dot, dash, underscore, as in shipment.delivered", status_code=400)
    return event

async def func_webhook_url_check(*, url: str) -> str:
    """Refuse a webhook URL that is not https or whose host resolves to a private, loopback, link-local or reserved address (SSRF); checked at creation and again before every delivery."""
    parts = urlsplit(url or "")
    if parts.scheme != "https" or not parts.hostname: raise func_api_error(message="webhook url must be https://<host>/...", status_code=400)
    try: infos = await asyncio.get_running_loop().getaddrinfo(parts.hostname, parts.port or 443)
    except OSError: raise func_api_error(message=f"webhook url host does not resolve: {parts.hostname}", status_code=400) from None
    for info in infos:
        address = ipaddress.ip_address(info[4][0].split("%")[0])
        if not address.is_global: raise func_api_error(message=f"webhook url host is not public: {parts.hostname}", status_code=400)
    return url

async def func_webhook_create(*, client_postgres: asyncpg.Pool | None, user_id: int, url: str, events: list) -> dict:
    """Subscribe url to events: checks both, creates the secret and returns the row with the secret, the only time it is shown."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not events: raise func_api_error(message="events must name at least one event", status_code=400)
    events = list(dict.fromkeys(func_webhook_event_check(event=e) for e in events))
    await func_webhook_url_check(url=url)
    secret = func_webhook_secret_create()
    row = await client_postgres.fetchrow("INSERT INTO webhook (created_by_id, url, events, secret) VALUES ($1, $2, $3, $4) RETURNING id, created_at, url, events, is_active", user_id, url, events, secret)
    return {**dict(row), "secret": secret}

async def func_webhook_send(*, client_postgres: Any, event: str, data: dict) -> int:
    """Queue event with data for every active webhook subscribed to it: one queue_job row each on channel_webhook, delivered by the app (config_webhook_is_active).
    client_postgres is a pool or a connection: pass the connection of an open transaction and the deliveries are queued only if it commits. Returns the number queued."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    func_webhook_event_check(event=event)
    return await client_postgres.fetchval(WEBHOOK_SEND, WEBHOOK_CHANNEL, event, orjson.dumps(data).decode())

async def func_webhook_deliver(*, client_postgres: Any, client_http: httpx.AsyncClient, payload: Any, timeout_sec: float) -> None:
    """POST one queued delivery to its webhook, signed; raises on anything but a 2xx so the queue retries it. A webhook deleted or turned off since is skipped."""
    payload = orjson.loads(payload) if isinstance(payload, (str, bytes)) else payload
    webhook = await client_postgres.fetchrow("SELECT url, secret, is_active FROM webhook WHERE id = $1", payload["webhook_id"])
    if not webhook or not webhook["is_active"]: return
    await func_webhook_url_check(url=webhook["url"])
    timestamp = int(time.time())
    body = orjson.dumps({"type": payload["event"], "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp)), "data": payload["data"]})
    headers = {"content-type": "application/json", "webhook-id": payload["message_id"], "webhook-timestamp": str(timestamp), "webhook-signature": func_webhook_sign(secret=webhook["secret"], message_id=payload["message_id"], timestamp=timestamp, body=body)}
    response = await client_http.post(webhook["url"], content=body, headers=headers, timeout=timeout_sec, follow_redirects=False)
    if not 200 <= response.status_code < 300: raise Exception(f"webhook answered {response.status_code}")

async def func_webhook_deliver_periodic_task(*, client_postgres: asyncpg.Pool, client_http: httpx.AsyncClient, runtime_error_count: dict, timeout_sec: float, retry_max: int, retry_wait_sec: float, poll_sec: float) -> None:
    """Deliver queued webhooks, one at a time per app worker (FOR UPDATE SKIP LOCKED: workers never send the same one twice); a failed one waits retry_wait_sec, doubled each retry, and stays failed (queue_job status 2) after retry_max retries."""
    async def run(payload):
        try: await func_webhook_deliver(client_postgres=client_postgres, client_http=client_http, payload=payload, timeout_sec=timeout_sec)
        except Exception as e: return e
        return None
    while True:
        try:
            if await func_queue_postgres_job_take(client_postgres=client_postgres, channel=WEBHOOK_CHANNEL, run=run, retry_max=retry_max, retry_wait_sec=retry_wait_sec) is None: await asyncio.sleep(poll_sec)
        except asyncio.CancelledError: raise
        except Exception as e:
            func_runtime_error_record(runtime_error_count=runtime_error_count, key="webhook_deliver", error=e)
            await asyncio.sleep(poll_sec)

def func_webhook_verify_scheme_check(*, name: str, scheme: Any) -> None:
    """Refuse a config_webhook_verify_scheme entry Atom can't verify with: unknown fields, encodings or placeholders, or a {id}/{timestamp} with no field saying where it is."""
    allowed = {"header", "prefix", "key", "encoding", "signed", "id", "timestamp", "secret_encoding"}
    where = f"config_webhook_verify_scheme[{name!r}]"
    if not isinstance(scheme, dict): raise Exception(f"{where} must be a dict")
    if unknown := set(scheme) - allowed: raise Exception(f"{where}: unknown field {', '.join(sorted(unknown))}; allowed: {', '.join(sorted(allowed))}")
    if not isinstance(scheme.get("header"), str) or not scheme["header"]: raise Exception(f"{where}: header must name the signature header")
    if scheme.get("encoding") not in ("hex", "base64"): raise Exception(f"{where}: encoding must be hex or base64")
    if scheme.get("secret_encoding", "raw") not in ("raw", "base64"): raise Exception(f"{where}: secret_encoding must be raw or base64")
    for field in ("prefix", "key"):
        if field in scheme and not isinstance(scheme[field], str): raise Exception(f"{where}: {field} must be a string")
    signed = scheme.get("signed")
    if not isinstance(signed, str) or not signed.endswith("{body}") or signed.count("{body}") != 1: raise Exception(f"{where}: signed must end with {{body}}, as in \"{{timestamp}}.{{body}}\"")
    for part in ("id", "timestamp"):
        value = scheme.get(part)
        if value is not None and (not isinstance(value, dict) or len(value) != 1 or not isinstance(next(iter(value.values())), str) or next(iter(value)) not in ("header", "key")): raise Exception(f"{where}: {part} must be {{\"header\": <name>}} or {{\"key\": <name in the signature header>}}")
        if value and "key" in value and "key" not in scheme: raise Exception(f"{where}: {part} has a key, so the scheme needs key (the signature's own key in that header)")
        if ("{" + part + "}") in signed and not value: raise Exception(f"{where}: signed uses {{{part}}}, so the scheme needs {part}")
    if set(re.findall(r"\{(\w+)\}", signed)) - {"id", "timestamp", "body"}: raise Exception(f"{where}: signed may use only {{id}}, {{timestamp}} and {{body}}")

def func_webhook_verify(*, scheme: dict, secret: str, headers: Any, body: bytes, tolerance_sec: int, now: float | None = None) -> dict:
    """Check an incoming webhook's HMAC-SHA256 signature as scheme describes (header, prefix or key, encoding, signed bytes); a timestamp more than tolerance_sec off is refused. Returns {"id", "timestamp"} or raises 401."""
    def refuse(message): return func_api_error(message=f"webhook signature invalid: {message}", status_code=401)
    raw = headers.get(scheme["header"])
    if not raw: raise refuse(f"{scheme['header']} header missing")
    pairs = [p.split("=", 1) for p in raw.split(",") if "=" in p] if "key" in scheme else []
    def part(name):
        where = scheme.get(name)
        if not where: return ""
        value = headers.get(where["header"]) if "header" in where else next((v.strip() for k, v in pairs if k.strip() == where["key"]), None)
        if not value: raise refuse(f"{name} missing")
        return value
    message_id, timestamp = part("id"), part("timestamp")
    if timestamp:
        try: age = abs((now if now is not None else time.time()) - int(timestamp))
        except ValueError: raise refuse("timestamp is not a number") from None
        if age > tolerance_sec: raise refuse("timestamp too old or in the future")
    if "key" in scheme: candidates = [v.strip() for k, v in pairs if k.strip() == scheme["key"]]
    else:
        prefix = scheme.get("prefix", "")
        candidates = [c.removeprefix(prefix) for c in raw.split() if c.startswith(prefix)] if prefix else [raw.strip()]
    key = base64.b64decode(secret.removeprefix("whsec_")) if scheme.get("secret_encoding") == "base64" else secret.encode()
    signed = scheme["signed"].removesuffix("{body}").format(id=message_id, timestamp=timestamp).encode() + body
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    expected = digest.hex() if scheme["encoding"] == "hex" else base64.b64encode(digest).decode()
    if not any(hmac.compare_digest(expected.encode(), c.encode()) for c in candidates): raise refuse("signature does not match")
    return {"id": message_id or None, "timestamp": int(timestamp) if timestamp else None}

async def func_webhook_verify_request(*, request: Any, receive: Any, webhook_verify: dict, config_webhook_verify_scheme: dict, config_webhook_verify_tolerance_sec: int, secret: str | None) -> Any:
    """Middleware step for a route with webhook_verify: verify the raw body's signature (401 if bad), put {"scheme", "id", "timestamp"} on request.state.webhook, and return a receive that replays the body to the route."""
    if not secret: raise func_api_error(message=f"webhook secret not set: {webhook_verify['secret']}", status_code=500)
    body = await request.body()
    result = func_webhook_verify(scheme=config_webhook_verify_scheme[webhook_verify["scheme"]], secret=secret, headers=request.headers, body=body, tolerance_sec=config_webhook_verify_tolerance_sec)
    request.state.webhook = {"scheme": webhook_verify["scheme"], **result}
    sent = False
    async def receive_replay():
        nonlocal sent
        if sent: return await receive()
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}
    return receive_replay
