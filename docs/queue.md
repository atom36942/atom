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
Atom's `script/` has one consumer per broker: `consumer_redis`, `consumer_rabbitmq`, `consumer_kafka`, `consumer_celery`. Each reads only its own broker's `.env` keys plus `config_postgres_url_master`, and takes the channel to listen on from the command.

### Channels:
`func_consumer_channels` (`function/queues.py`) is the only place a channel name maps to the function that handles it. Channel names start with `channel_` and say what the message does:

| Channel | Sent by | Handled by |
|---|---|---|
| `channel_object_create` | `POST /my/object-create?queue=...` | `func_consumer_object_create` (`func_postgres_create`) |
| `channel_object_update` | `PUT /my/object-update?queue=...` | `func_consumer_object_update` (`func_postgres_update`) |

A new channel is one `func_consumer_<name>(*, payload, context)` plus one line in `func_consumer_channels`; every broker script then supports it. A project's own consumer goes in `script_extend/` and calls `func_run_broker` with its own function.

### Consumer Runner (`func_consumer_run`):
Each broker script calls `func_consumer_run`, which checks the channel, opens the Postgres pool, schema cache and password hasher once per process, and runs `func_run_broker`:

```python
func_run_broker(
    queue="redis",                   # redis | rabbitmq | kafka | celery
    channel="channel_object_create", # topic, queue or list name
    broker_settings={...},           # connection credentials
    setup_callback=setup,            # runs once (opens db pools, loads schema)
    execute_callback=execute,        # runs per message
    concurrency=10,                  # jobs running at once (config_queue_concurrency)
    retry_max=3,                     # retries after the first failure (config_queue_retry_max)
)
```

### Delivery: at least once
A job counts as done only after its function returns. A job that raises is retried up to `retry_max` times (it goes to the back of the queue), then kept in `<channel>_failed` in the same broker with its error, to inspect and send again. A consumer that stops mid-job loses nothing: the job runs again after the restart.

| Broker | Taken | Done | Kept after the last retry |
|---|---|---|---|
| Redis | moved to `<channel>_processing` (`BLMOVE`), only when a worker is free, so waiting jobs stay in Redis | removed from `<channel>_processing`; on start, a consumer puts back what a stopped one left | list `<channel>_failed`: `{"payload", "attempt", "error", "failed_at"}` |
| RabbitMQ | delivered, at most `concurrency` unacknowledged | acknowledged (a failure is published again with header `x-attempt` first) | queue `<channel>_failed`, headers `x-attempt` and `x-error` |
| Kafka | batches of at most `concurrency` messages, auto-commit off | the batch's offsets are committed once every job in it is finished (a failure is produced again with header `x-attempt` first) | topic `<channel>_failed`, headers `x-attempt` and `x-error` |
| Celery | one job at a time per worker process (`solo` pool; run more workers to scale), acknowledged late | done; a failure is retried by Celery after 1, 2, 4, ... seconds | queue `<channel>_failed` (the task's `kwargs` are the payload), headers `x-attempt` and `x-error` |

- A job can run twice: if a consumer stops after the job's work but before it counts as done, the job runs again. Make a job safe to repeat; for creates, a unique column (an invoice number) turns the repeat into a failed job instead of a duplicate row.
- Redis: one consumer per channel (a `<channel>_consumer` key, kept alive every 20 s). A second one waits as a standby and takes over within 60 s of the first one stopping, which is also how long a restart after a crash waits. Scale with `config_queue_concurrency`; run several consumers with RabbitMQ.
- Stopping: SIGTERM (a deploy, a scale-down) or Ctrl+C makes a consumer take no new job, wait up to 60 s (`func_run_broker(stop_wait_sec=...)`) for the running ones, then exit; a Redis consumer releases its channel, so a restart takes over at once. A second Ctrl+C exits at once, and a job cut short that way runs again on the next start. Celery does the same on its own (warm shutdown).
- Queued creates are written at once, whatever `mode` the API call had: rows buffered in a consumer would be lost if it stopped after the job counted as done.
- Redis jobs are `{"payload": ..., "attempt": n}`, as `func_producer` sends them.

### Running a Consumer:
One process per broker and channel, for example `venv/bin/python -m script.consumer_redis channel_object_create`. The `# command` lines at the top of each consumer list its channels; the API call's `queue` must match the script's broker.

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
