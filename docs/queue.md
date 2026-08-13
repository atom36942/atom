# 📬 Object Queues

The `queue` query parameter lets selected object APIs publish database work to an external broker instead of executing the write during the HTTP request. A separate consumer receives the payload and performs the PostgreSQL create or update.

## Supported object APIs

Only these endpoints currently accept `queue`:

| Endpoint | Channel | Consumer |
|----------|---------|----------|
| `POST /my/object-create` | `func_postgres_create` | `script/consumer_postgres_create.py` |
| `PUT /my/object-update` | `func_postgres_update` | `script/consumer_postgres_update.py` |

`/public/object-create`, `/admin/object-create`, all read APIs, and all delete APIs do **not** accept `queue`.

Allowed values come from `config_queue_services`:

```python
config_queue_services = ["redis", "rabbitmq", "kafka", "celery"]
```

## What happens when `queue` is present?

Without `queue`, the route calls the PostgreSQL function directly and returns after that function completes:

```text
HTTP request → validate request → write to PostgreSQL → return result
```

With `queue`, the route validates and enriches the request, publishes a payload, and returns after the broker accepts it:

```text
HTTP request
  → validate request and apply user ownership fields
  → publish payload to func_postgres_create or func_postgres_update
  → return broker acknowledgement

consumer process
  → receive payload
  → validate against its loaded PostgreSQL schema
  → execute create or update
  → log success or failure
```

A successful HTTP response confirms **publication**, not that the database row was committed. The client should not immediately assume that a queued row is readable.

## Queue a create

### Redis

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test&queue=redis" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Queued with Redis","type":1}'
```

### RabbitMQ

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test&queue=rabbitmq" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Queued with RabbitMQ","type":1}'
```

### Kafka

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test&queue=kafka" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Queued with Kafka","type":1}'
```

### Celery

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test&queue=celery" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Queued with Celery","type":1}'
```

Batch creates use the same `obj_list` shape as immediate creates:

```bash
curl -X POST "http://localhost:8000/my/object-create?table=test&queue=redis" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"obj_list":[
    {"title":"Queued A","type":1},
    {"title":"Queued B","type":2}
  ]}'
```

Before publication, Atom rejects disabled tables and restricted fields, enforces `config_batch_item_limit`, requires `created_by_id` on the table, and stamps `created_by_id` from the access token. The consumer validates datatypes, mandatory values, and regex rules when it performs the insert.

## Queue an update

```bash
curl -X PUT "http://localhost:8000/my/object-update?table=test&queue=redis" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"id":12,"title":"Queued update"}'
```

Batch update:

```bash
curl -X PUT "http://localhost:8000/my/object-update?table=test&queue=rabbitmq" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"obj_list":[
    {"id":12,"title":"Updated A"},
    {"id":13,"title":"Updated B"}
  ]}'
```

The route rejects restricted fields, requires the table to contain `updated_by_id`, and stamps the acting user's ID. For non-user tables, the queued payload also carries `created_by_id`, so the consumer updates only rows owned by that user.

User updates retain their additional route checks. A user can update only their own account; role changes are blocked; sensitive fields must be sent individually. Email/mobile updates may still need a live PostgreSQL connection for OTP verification before the payload is published.

## Configure a broker

Set the connection needed by the chosen backend in `.env` and restart the API:

### Redis

```dotenv
config_redis_url_queue=redis://localhost:6379/2
```

This URL is independent of `config_redis_url` and `config_redis_url_ratelimiter`, allowing queue traffic to use a separate Redis database or server.

### RabbitMQ

```dotenv
config_rabbitmq_url=amqp://guest:guest@localhost:5672/
```

The producer publishes a persistent message to the default exchange using the object function name as the routing key. The consumer declares that queue as durable.

### Kafka

```dotenv
config_kafka_url=localhost:9092
```

For the supported SASL/SSL setup:

```dotenv
config_kafka_url=broker.example.com:9093
config_kafka_username=atom
config_kafka_password=<secret>
```

The channel name becomes the Kafka topic. Create the topic ahead of time if the cluster does not allow automatic topic creation.

### Celery

```dotenv
config_celery_url=redis://localhost:6379/3
```

The configured URL is used as both Celery broker and result backend. The object function name is used as the task and queue name.

The API refuses a queued request when the matching producer client was not initialized. A producer connection alone is not enough—you must run the matching consumer.

## Start consumers

Create and update use separate channels, so start the consumer required by each operation.

### Redis consumers

```bash
venv/bin/python script/consumer_postgres_create.py redis
venv/bin/python script/consumer_postgres_update.py redis
```

### RabbitMQ consumers

```bash
venv/bin/python script/consumer_postgres_create.py rabbitmq
venv/bin/python script/consumer_postgres_update.py rabbitmq
```

### Kafka consumers

```bash
venv/bin/python script/consumer_postgres_create.py kafka
venv/bin/python script/consumer_postgres_update.py kafka
```

### Celery consumers

```bash
venv/bin/python script/consumer_postgres_create.py celery
venv/bin/python script/consumer_postgres_update.py celery
```

Each consumer needs access to the same `config_postgres_url`, schema configuration, regex rules, and broker configuration as the API. Run consumers as supervised services or separate containers rather than inside the API process.

Non-Celery consumers process up to 10 messages concurrently in one process. You can run additional consumer processes for more throughput, subject to broker behavior and PostgreSQL connection capacity.

## Channels and payloads

The producer chooses the channel automatically; clients do not supply it.

Create payload:

```json
{
  "mode": "now",
  "table": "test",
  "obj_list": [
    {"title": "Queued object", "type": 1, "created_by_id": 7}
  ]
}
```

Update payload:

```json
{
  "table": "test",
  "obj_list": [
    {"id": 12, "title": "Queued update", "updated_by_id": 7}
  ],
  "created_by_id": 7
}
```

The queue payload contains application data. Protect broker credentials and network access, enable broker transport security in production, and avoid placing secrets in object fields unless the product requires them.

## `queue` versus `mode=buffer`

They solve different problems:

| Option | Work lives in | HTTP request waits for | Main risk |
|--------|---------------|------------------------|-----------|
| No option (`mode=now`) | API process and PostgreSQL | Database commit | Higher request latency |
| `mode=buffer` | API process memory | In-memory acceptance | Hard process loss before flush |
| `queue=<broker>` | External broker and consumer | Broker publication | Delayed or failed consumer execution |

For queued creates, keep the default `mode=now`:

```text
/my/object-create?table=test&queue=redis
```

Avoid combining `queue` with `mode=buffer` unless you fully manage consumer-buffer flushing. The create consumer has its own in-memory buffer; it does not run the API's periodic flush task. A `mode=buffer` message may remain only in consumer memory until that buffer reaches its configured limit, and a consumer shutdown does not currently perform the API's graceful buffer flush.

Use a queue when work should survive independently of the API request and can complete asynchronously. Use `mode=buffer` for high-volume, low-urgency writes inside the API process where its periodic and shutdown flush lifecycle is acceptable. See [Buffering](buffer.md).

## Delivery and failure behavior

Broker publication and database execution are separate events. Current consumers handle execution failures as follows:

- Every failed payload is appended to `tmp/consumer_failed_payload.jsonl` with its queue, channel, payload, error, and traceback.
- Redis removes a message with `BRPOP` before execution; a failed payload is logged but not automatically returned to the list.
- RabbitMQ uses durable messages and a durable queue, but the consumer records processing errors itself; failed application payloads are logged rather than automatically retried.
- Kafka consumers use group `atom` with automatic commits enabled; failed application payloads are logged and should be replayed deliberately if safe.
- Celery uses late acknowledgement and rejects tasks if a worker process is lost. An ordinary task exception is recorded by Celery and in the failure file, but no application retry policy is configured by these scripts.

Therefore, do not assume automatic retries or exactly-once execution. Design creates and updates to be idempotent where possible, add unique constraints for natural deduplication keys, and replay failures only after checking whether the original operation partially succeeded.

The failure file is local runtime storage under `tmp/` and the API recreates that directory at startup. In production, ship failures to durable storage or monitoring before they disappear with container/process replacement.

## Observability

The HTTP response contains a backend-specific publication result, not the created row ID or final update count. Consumer stdout prints `task started`, `task completed`, and `task failed` messages with an incrementing local task number.

For a user-visible job status, include a durable tracking ID in the object and update a PostgreSQL status column from the consumer, or use the table-poller pattern documented in [Background Workers](workers.md#table-pollers--the-worker-status-pattern). Broker acknowledgements alone are not an application job-status API.

Monitor at least:

- broker queue/topic depth and oldest-message age;
- consumer availability and restart count;
- task completion/failure logs;
- `tmp/consumer_failed_payload.jsonl` forwarding;
- PostgreSQL errors and pool utilization;
- end-to-end time from publication to committed row.

## Common errors

| Error or symptom | Cause | Fix |
|------------------|-------|-----|
| `required postgres/queue client not initialized` | The selected producer is not configured, or an OTP-sensitive update also needs Postgres | Set the matching URL/credentials and restart the API |
| `invalid queue` | Value is not in the supported services | Use `redis`, `rabbitmq`, `kafka`, or `celery` |
| HTTP succeeds but no row appears | Consumer is not running, is on the wrong backend/channel, or processing failed | Start the correct create/update consumer and inspect its output/failure file |
| Create consumer fails schema validation | API and consumer use different code, schema, or configuration | Deploy matching versions and restart the consumer to reload schema |
| Duplicate rows or repeated updates | A message was replayed or delivered more than once | Make operations idempotent and use appropriate unique constraints |
| Queued create remains invisible indefinitely | `mode=buffer` was combined with `queue` | Use the default `mode=now` for queued creates |

## Deployment checklist

- Configure only the broker backend you intend to use.
- Run separate create and update consumers when both operations are queued.
- Give the consumer access to Postgres and the same schema/config version as the API.
- Supervise consumers and shut them down deliberately.
- Secure broker networking and credentials.
- Monitor lag, failures, and database completion.
- Build an explicit retry/dead-letter policy for business-critical jobs.
- Make replay safe before automating it.

For the surrounding object API behavior, see [Object Read API](object_read.md). For general worker patterns, see [Background Workers](workers.md).

---

📚 [Back to README](../readme.md)
