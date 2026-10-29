# ⚡ Asynchronous Queues & Background Workers

Atom provides an asynchronous job processing system spanning multiple message brokers (**Redis Streams**, **RabbitMQ**, **Apache Kafka**, **Celery**) and standalone consumer workers in `script/`.

---

## 1. Supported Message Brokers

All queue brokers are optional and configured via `.env`:

| Broker | Configuration Key | Runtime Client | Use Case |
| :--- | :--- | :--- | :--- |
| **Redis Streams** | `config_redis_url_queue` | `client_redis_dict["queue"]` | High throughput, lightweight streaming. |
| **RabbitMQ** | `config_rabbitmq_url` | `client_rabbitmq_channel` | Traditional AMQP message queuing with ACKs. |
| **Apache Kafka** | `config_kafka_url` | `client_kafka_producer` | Partitioned distributed log streaming. |
| **Celery** | `config_celery_broker_url` | `client_celery` | Task queue with built-in retries and task states. |

---

## 2. Enqueuing Work from APIs

Any API request can offload heavy processing to a background queue using the `queue` query parameter on generic create/update endpoints:

```bash
POST /my/object-create?table=reports&queue=redis
{
  "title": "Quarterly Analytics",
  "parameters": {"year": 2026, "quarter": 1}
}
```

When `queue` is provided:
1. Atom validates the backend against `config_queue_services` (`["redis", "rabbitmq", "kafka", "celery"]`).
2. `func_producer` serializes the payload and pushes it to the designated broker channel.
3. The API immediately responds with `{"status": 1, "message": {"queued": true, "queue": "redis"}}`.

### App-Process Background Tasks (`?is_background=true`):
For lighter asynchronous tasks that don't need external queue broker infrastructure, append `?is_background=true` to any request. The middleware returns `202 added in background` at once and runs the route in an in-process task (tracked, and cancelled at shutdown). Errors are printed as `❌ background api error: ...`; nothing is retried, so use a queue for work that must not be lost.

---

## 3. Queue Consumer Workers

Standalone consumer scripts reside in [`script/`](../script). They run as independent OS processes outside of the web server.

### Built-in Consumers:
Atom's `script/` has consumers that run batch `func_postgres_create` and `func_postgres_update` on queued payloads.

### Unified Broker Runner (`func_run_broker`):
Consumers use `func_run_broker` to provide a single unified interface across all four message brokers:

```python
func_run_broker(
    queue="redis",                 # redis | rabbitmq | kafka | celery
    channel="postgres_create",     # topic or stream name
    broker_settings={...},         # connection credentials
    setup_callback=init_resources, # runs once (opens db pools, loads schema)
    execute_callback=process_msg,  # runs per message
)
```

### Dead-Letter & Failure Safety:
If a message processing callback raises an unhandled exception, `func_run_broker` appends the failed message, error, and stack trace to `tmp/consumer_failed_payload.jsonl` so no payload is silently lost.

### Running a Consumer:
Use the `# command` line at the top of the consumer's file (pick the broker: redis, rabbitmq, kafka, celery).

---

## 4. Table Pollers & Durable Job Pattern

For operations requiring database durability and automatic exponential retries (e.g. account deletion, video encoding), Atom uses the **Worker Status State Machine**.

Tables implementing this pattern include the standard `worker_*` columns:
- `worker_status` (int):
  - `1`: Processing
  - `2`: Completed
  - `3`: Failed (Retryable)
  - `4`: Dead (Exhausted retries)
- `worker_retry_count` (int): Current attempt count.
- `worker_next_retry_at` (timestamptz): Earliest eligible execution timestamp.
- `worker_processed_at` (timestamptz): Successful completion timestamp.
- `worker_last_error` (text): Stack trace or message from the last failure.

A poller process periodically executes:
```sql
SELECT * FROM tasks
WHERE worker_status IN (1, 3)
  AND (worker_next_retry_at IS NULL OR worker_next_retry_at <= now())
ORDER BY id ASC
LIMIT 50
FOR UPDATE SKIP LOCKED;
```

---

## 5. Buffer Flushes

Buffered writes (`mode="buffer"` creates and `log_api` rows) live in the web process's memory, so no separate worker can flush them. Each process flushes its own buffers every `config_postgres_buffer_flush_auto_sec` seconds, when a buffer reaches its limit, and once more on shutdown; `/admin/sync` also flushes the create buffer.
