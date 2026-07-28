# Background Workers

Work that shouldn't run inside a request — heavy processing, retries, scheduled cleanup, bulk ingestion — lives in [`script/`](../script) as standalone processes. They import the same `function.py` / `config.py` and run as separate OS processes (not part of the API server).

There are two shapes: **queue consumers** (react to messages) and **table pollers / manual jobs** (scan a table or run once).

---

## Producing work from the API

Any request can hand work off instead of doing it inline. The generic create endpoint accepts a `queue` param:

```jsonc
POST /my/object-create?table=jobseeker&queue=redis
{ ... }
```

`func_producer` publishes the payload to the chosen backend (`redis` / `rabbitmq` / `kafka` / `celery`, validated against `config_queue_services`), and a consumer picks it up. The middleware also supports `?is_background=1` for fire-and-forget within the app process (see [middleware.md](middleware.md)).

---

## Queue consumers

`script/consumer_postgres_create.py` and `consumer_postgres_update.py` consume queued payloads and apply them via `func_postgres_create` / `func_postgres_update`. They're built on **`func_run_broker`**, which abstracts the four brokers behind one runner:

```python
func_run_broker(
    queue="redis",                 # redis | rabbitmq | kafka | celery
    channel="postgres_create",     # queue/topic name
    config_broker={...},           # broker URLs from config
    setup_callback=...,            # opens DB pool, loads schema (once)
    execute_callback=...,          # processes one payload
)
```

- `setup_callback` runs once to establish shared resources (pool, schema); `execute_callback` runs per message.
- Failed payloads are appended to `tmp/consumer_failed_payload.jsonl` with the error and traceback, so nothing is silently lost.
- Celery is configured with `task_acks_late` + `worker_prefetch_multiplier=1` for at-least-once, one-at-a-time processing.

Run one:

```bash
venv/bin/python script/consumer_postgres_create.py <queue> <channel>
```

---

## Table pollers & the worker-status pattern

Some tables carry a set of `worker_*` columns that turn a plain row into a **durable job with retries** (see the `jobseeker` and `log_users_delete` tables in [config.md](config.md#config_postgres)):

| Column | Role |
|--------|------|
| `worker_status` | `1` Processing · `2` Completed · `3` Failed (retryable) · `4` Dead (`config_column_int_mapping`). |
| `worker_retry_count` | Attempts so far. |
| `worker_next_retry_at` | Earliest time to retry. |
| `worker_processed_at` | When it finished. |
| `worker_last_error` | Last failure message. |

`script/worker_resume_parser.py` is the reference implementation. Its loop:

1. **Claim** a batch atomically with `... FOR UPDATE ... SKIP LOCKED`, flipping `worker_status → 1` — so multiple worker instances never grab the same row.
2. **Process** each row (here: fetch a résumé, parse it with AI).
3. **On success** → `worker_status = 2`, set `worker_processed_at`.
4. **On failure** → increment `worker_retry_count`, set `worker_next_retry_at` using a **backoff schedule** (`[60, 300, 3600, 86400]` seconds), and mark `worker_status = 3`; once retries are exhausted, mark `worker_status = 4` (Dead).

This gives safe, concurrent, self-retrying background processing using only Postgres — no extra queue required.

---

## Scheduled / manual jobs

| Script | Purpose |
|--------|---------|
| `worker_users_delete.py` | Purges soft-deleted users and their blobs past `config_users_delete_data_retention_day`; skips `config_table_sensitive`. |
| `manual_postgres_cleaner.py` | Deletes old rows per each table's `retention_day`; **refuses** to touch sensitive tables. |
| `manual_postgres_ingestion.py` | Bulk-loads data into Postgres (reads `PG_DSN` from `.env`). |

Run these on a schedule (cron/systemd timer) or on demand.

---

## Running workers

Workers are separate processes — start them alongside the API (e.g. in their own containers or supervised services):

```bash
venv/bin/python script/consumer_postgres_create.py redis postgres_create
venv/bin/python script/worker_resume_parser.py
venv/bin/python script/worker_users_delete.py
```

They read the same `.env` / `config.py`, so a configured queue backend (`config_redis_url_queue`, `config_rabbitmq_url`, `config_kafka_url`, or `config_celery_url`) must be present for the consumers. Add your own workers in `script/` — see [extend.md](extend.md).

---

📚 [Back to README](../readme.md)
