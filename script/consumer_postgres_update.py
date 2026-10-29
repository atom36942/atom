# command: venv/bin/python -m script.consumer_postgres_update redis    (or rabbitmq, kafka, celery)

# info: Listens to message brokers (Redis, RabbitMQ, Kafka, Celery) and processes asynchronous bulk UPDATE operations for PostgreSQL.

# import
import sys
from function import func_client_postgres
from function import func_client_password_hasher
from function import func_run_broker
from function import func_postgres_update
from function import func_postgres_schema_read

# config
from config import config_postgres_url_dict
from config import config_column_regex
from config import config_redis_url_dict
from config import config_rabbitmq_url
from config import config_celery_url
from config import config_kafka_url
from config import config_kafka_username
from config import config_kafka_password
postgres_url_master = config_postgres_url_dict.get("master")
redis_url_queue = config_redis_url_dict.get("queue")

# setting
CHANNEL = "func_postgres_update"
QUEUES = ("redis", "rabbitmq", "kafka", "celery")

# logic
async def client_setup():
    """Runs once per consumer process; func_run_broker passes its result to payload_execute after the payload, in this order."""
    client_postgres = await func_client_postgres(dsn=postgres_url_master, min_size=1, max_size=5)
    buffer_postgres_create = {}
    cache_postgres_schema = await func_postgres_schema_read(client_postgres=client_postgres)
    client_password_hasher = func_client_password_hasher()
    return client_postgres, buffer_postgres_create, cache_postgres_schema, client_password_hasher

async def payload_execute(payload, client_postgres, buffer_postgres_create, cache_postgres_schema, client_password_hasher):
    table = payload.get("table")
    return await func_postgres_update(client_postgres=client_postgres, client_postgres_conn=None, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, config_column_regex=config_column_regex, table=table, obj_list=payload.get("obj_list"), created_by_id=payload.get("created_by_id"), ownership_column=payload.get("ownership_column", "created_by_id"))

def main():
    queue = sys.argv[1] if len(sys.argv) > 1 else None    # the broker to listen on
    if queue not in QUEUES: raise SystemExit(f"Error: queue is required. Usage: venv/bin/python -m script.consumer_postgres_update <{'|'.join(QUEUES)}>")
    broker_settings = {"config_redis_url_queue": redis_url_queue, "config_rabbitmq_url": config_rabbitmq_url, "config_kafka_url": config_kafka_url, "config_kafka_username": config_kafka_username, "config_kafka_password": config_kafka_password, "config_celery_url": config_celery_url}
    func_run_broker(queue=queue, channel=CHANNEL, broker_settings=broker_settings, setup_callback=client_setup, execute_callback=payload_execute)

# main
if __name__ == "__main__":
    main()
