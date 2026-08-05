# command: venv/bin/python -m script.consumer_postgres_update

# info: Listens to message brokers (Redis, RabbitMQ, Kafka, Celery) and processes asynchronous bulk UPDATE operations for PostgreSQL.

# packages
import sys
import asyncpg
from argon2 import PasswordHasher

# function
from function import func_run_broker
from function import func_postgres_update
from function import func_postgres_serialize
from function import func_postgres_schema_read
from function import func_regex_check

# config
from config import config_postgres_url
from config import config_regex
from config import config_redis_url_queue
from config import config_rabbitmq_url
from config import config_celery_url
from config import config_kafka_url
from config import config_kafka_username
from config import config_kafka_password

# logic
async def setup():
    client_postgres = await asyncpg.create_pool(dsn=config_postgres_url, min_size=1, max_size=5)
    cache_postgres_buffer_create = {}
    cache_postgres_schema = await func_postgres_schema_read(client_postgres=client_postgres)
    client_password_hasher = PasswordHasher()
    return client_postgres, cache_postgres_buffer_create, cache_postgres_schema, client_password_hasher

async def execute(payload, client_postgres, cache_postgres_buffer_create, cache_postgres_schema, client_password_hasher):
    table = payload.get("table")
    return await func_postgres_update(client_postgres=client_postgres, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, config_regex=config_regex, table=table, obj_list=payload.get("obj_list"), created_by_id=payload.get("created_by_id"))

# init
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: queue is required. Usage: python script/consumer_postgres_update.py <redis|rabbitmq|kafka|celery>")
        sys.exit(1)
    queue = sys.argv[1]
    channel = "func_postgres_update"
    config_broker = {"config_redis_url_queue": config_redis_url_queue, "config_rabbitmq_url": config_rabbitmq_url, "config_kafka_url": config_kafka_url, "config_kafka_username": config_kafka_username, "config_kafka_password": config_kafka_password, "config_celery_url": config_celery_url}
    func_run_broker(queue=queue, channel=channel, config_broker=config_broker, setup_callback=setup, execute_callback=execute)
