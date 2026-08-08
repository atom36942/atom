# 🟥 Redis

Atom uses four separate asynchronous Redis clients. Each client has one responsibility and is enabled by its own connection URL. This separation lets API cache, user-state cache, rate-limiter, and queue workloads use different Redis databases or servers and prevents one workload from consuming another workload's capacity.

## Clients at a glance

| Configuration | Runtime client | Purpose |
|---------------|----------------|---------|
| `config_redis_url` | `app.state.client_redis` | API response cache and admin Redis import |
| `config_redis_url_user_state` | `app.state.client_redis_user_state` | User authorization and account status lookups |
| `config_redis_url_ratelimiter` | `app.state.client_redis_ratelimiter` | Distributed API rate-limit counters |
| `config_redis_url_queue` | `app.state.client_redis_producer` | Background-job queue producer |

All four settings default to `None`. `main.py` creates a `redis.asyncio.Redis` client only when the corresponding URL is configured, exposes it through `app.state`, and closes it during application shutdown.

## Configuration

Set the URLs in `.env`:

```bash
config_redis_url=redis://localhost:6379/0
config_redis_url_user_state=redis://localhost:6379/1
config_redis_url_ratelimiter=redis://localhost:6379/2
config_redis_url_queue=redis://localhost:6379/3
```

The database suffixes (`/0`, `/1`, `/2`, and `/3`) are optional. They provide logical separation on one Redis server. For stronger workload and failure isolation, use separate Redis instances:

```bash
config_redis_url=redis://cache.internal:6379/0
config_redis_url_user_state=redis://userstate.internal:6379/0
config_redis_url_ratelimiter=redis://ratelimiter.internal:6379/0
config_redis_url_queue=redis://queue.internal:6379/0
```

Authenticated and TLS connection strings can be supplied using standard Redis URL syntax:

```bash
config_redis_url=rediss://username:password@redis.example.com:6380/0
```

Only configure clients that the application uses. A missing URL leaves its client as `None`, and a feature that explicitly selects that Redis client will report that the required client is missing.

## User-state client

`config_redis_url_user_state` creates `client_redis_user_state`. Routes can choose Redis for role, deactivation, and deletion checks:

```python
"/private/example": {
    "id": 101,
    "is_token": 1,
    "user_check_role": {"mode": "redis", "roles": [1, 2]},
    "user_check_deactivated": {"mode": "redis"},
    "user_check_deleted": {"mode": "redis"},
},
```

On a cache miss, middleware reads the current value from Postgres and stores it in Redis for `config_redis_cache_ttl_sec` seconds. The keys are:

| Check | Redis key |
|-------|-----------|
| User role | `cache:user:role:{user_id}` |
| Deactivation status | `cache:user:active:{user_id}` |
| Deletion status | `cache:user:deleted_at:{user_id}` |

This mode reduces Postgres reads but permits values to remain stale until the TTL expires. Use `realtime` for operations that must see changes immediately, `token` to trust the JWT claim, or `inmemory` for process-local cached data.

### API response cache

Set a route's `cache` mode to `redis`:

```python
"/public/example": {
    "id": 102,
    "is_token": 0,
    "cache": {"mode": "redis", "ttl_sec": 300, "is_per_user": 0},
},
```

The dict keys are `{"mode": "...", "ttl_sec": ..., "is_per_user": ...}`. Set `is_per_user` to `1` to include the authenticated user id in the key, or `0` to share the cached response. Cache keys have this shape:

```text
cache:{path}?{sorted_query_parameters}:{user_id_or_0}
```

Responses are gzip-compressed and Base64-encoded before storage. Clients can bypass the lookup and write for a request with `?is_disable_cache=1`.

### Admin Redis import

`POST /admin/redis-import` uses `client_redis` to create or delete arbitrary keys from an uploaded CSV:

- `create` requires `key,value` columns. Values are JSON-encoded and use `config_redis_cache_ttl_sec` when it is non-zero.
- `delete` requires a single `key` column.
- Operations are pipelined in batches of up to 5,000 rows.

Because this endpoint can change arbitrary keys in the general Redis database, restrict it to trusted administrators and avoid key names used by unrelated applications.

## Rate-limiter client

`config_redis_url_ratelimiter` creates `client_redis_ratelimiter`. Only `func_middleware_check_ratelimiter` receives this client.

Enable distributed rate limiting for a route with:

```python
"/public/example": {
    "id": 103,
    "is_token": 0,
    "rate_limit": {"mode": "redis", "limit": 100, "window_sec": 60},
},
```

The dict keys are `{"mode": "...", "limit": ..., "window_sec": ...}`. Each counter is keyed by the authenticated user id or, for anonymous requests, the client IP:

```text
ratelimiter:{request_path}:{user_id_or_client_ip}
```

The first request creates the counter and applies the configured window as its expiry. Later requests increment it; requests above the limit raise `ratelimiter exceeded`.

Redis mode shares counters across application processes and hosts. `inmemory` mode needs no Redis URL but maintains independent counters in every process, so its effective global limit grows when the application is horizontally scaled.

At startup, configuration validation requires `config_redis_url_ratelimiter` when any route selects Redis rate limiting. The general `config_redis_url` is intentionally not used as a fallback.

## Queue client

`config_redis_url_queue` creates `client_redis_producer`. Routes whose object configuration selects the `redis` queue pass jobs to `func_producer`, which serializes each payload as JSON and runs:

```text
LPUSH {channel} {payload}
```

The worker scripts pass the same queue URL to `func_consumer`. A Redis consumer blocks on:

```text
BRPOP {channel} 0
```

Using `LPUSH` with `BRPOP` provides FIFO processing. Current job channels include `func_postgres_create` and `func_postgres_update`.

Run the corresponding consumer process when Redis queue mode is enabled; otherwise jobs remain in the list. Redis lists in this implementation do not provide acknowledgement or automatic redelivery after a worker removes a job, so use RabbitMQ, Kafka, or another durable workflow when stronger delivery guarantees are required.

## Key ownership summary

| Prefix or list | Owner | Expiry |
|----------------|-------|--------|
| `cache:user:*` | General client | `config_redis_cache_ttl_sec` |
| `cache:{path}?...` | General client | Route's `cache` TTL |
| Arbitrary imported keys | General client | `config_redis_cache_ttl_sec`, or none when set to `0` |
| `ratelimiter:*` | Rate-limiter client | Route's rate-limit window |
| `func_postgres_create` list | Queue client | No automatic expiry |
| `func_postgres_update` list | Queue client | No automatic expiry |

## Operational guidance

- Use a bounded-memory eviction policy suitable for cache and rate-limit instances. Do not use eviction on a queue instance if losing queued jobs is unacceptable.
- Keep the queue workload separate from cache workloads in production. Cache eviction is expected; queue eviction is data loss.
- Monitor memory, evictions, command latency, connection count, rate-limit key volume, and queue list lengths.
- Treat Redis URLs as secrets when they contain credentials and store them in `.env`, not source control.
- Use TLS (`rediss://`) when Redis traffic crosses an untrusted network.
- Do not flush a shared Redis database during deployment. The clients create and expire their own keys but do not require a startup flush.

## Failure behavior

Redis operations run in the request path for Redis-backed middleware:

- A general-client failure can reject Redis-backed user checks or API caching.
- A rate-limiter-client failure causes Redis-mode rate-limit checks to fail rather than silently allowing requests.
- A queue-client failure prevents the job from being enqueued.
- Features configured with `inmemory`, `token`, or `realtime` modes do not depend on the rate-limiter client.

There is currently no automatic fallback from a configured Redis mode to another mode. Choose the desired behavior explicitly in `config_api`.

---

📚 [Configuration](config.md) · [Middleware](middleware.md) · [Workers](workers.md) · [Back to README](../readme.md)
