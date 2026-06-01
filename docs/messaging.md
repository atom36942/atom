# Message Queues and Event Publishing

Atom is designed to seamlessly integrate with various background job and event streaming services (e.g., Celery, Kafka, RabbitMQ, Redis). While background workers (Consumers) are configured in `core/script/`, the API needs a standardized way to *Publish* events to these queues.

## 1. The Unified Producer (`func_producer`)

To abstract away the complexities of different message brokers, `core/function.py` provides a unified `func_producer`.

Instead of writing broker-specific publishing code (e.g., `kafka_producer.send()` or `celery.send_task()`), you pass the payload to `func_producer` alongside the desired queue engine name. Atom will handle routing the payload to the correct pre-initialized client.

### Basic Usage

```python
# Inside a FastAPI router or internal business logic
await app_state.func_producer(
    queue="rabbitmq", # Choose between "celery", "kafka", "rabbitmq", "redis"
    client_celery_producer=app_state.client_celery_producer,
    client_kafka_producer=app_state.client_kafka_producer,
    client_rabbitmq_producer=app_state.client_rabbitmq_producer,
    client_redis_producer=app_state.client_redis_producer,
    channel="email_notifications", # The name of the topic, queue, or channel
    payload={"email": "user@example.com", "type": "welcome"}, # The message body (dict)
    config_allowed_queue_services=["celery", "kafka", "rabbitmq", "redis"]
)
```

---

## 2. Broker Implementations

Depending on the `queue` argument you specify, `func_producer` behaves differently internally:

### RabbitMQ
Packs the JSON payload and pushes it to a durable queue using `aio_pika`. The queue is declared automatically if it doesn't exist to prevent drops.

### Kafka
Serializes the JSON payload into bytes and produces it to the Kafka topic. The Kafka client handles underlying partitioning and SASL authentication.

### Redis
Uses Redis `PUBLISH` to broadcast the payload to a specific Pub/Sub channel. Alternatively, it can be configured to use `LPUSH` for list-based queueing.

### Celery
Pushes the task to a designated Celery broker by task name (the `channel` parameter acts as the Celery task name).

---

## 3. Best Practices

- **Fire and Forget**: Pushing to a queue is asynchronous and extremely fast. Always use event publishing for heavy processing (e.g., parsing PDFs, generating reports, sending bulk emails) to keep the HTTP response times under 50ms.
- **Client Fallbacks**: Ensure the integration variables in `core/config.py` are set for the queue you intend to use. If you request `queue="kafka"` but `client_kafka_producer` is `None`, the event will not be published.
- **Idempotency**: Consumers processing these payloads might occasionally receive duplicate events depending on the broker's delivery guarantees. Always design downstream tasks to be idempotent.
