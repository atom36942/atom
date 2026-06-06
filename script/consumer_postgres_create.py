# packages
import sys
import asyncpg
from argon2 import PasswordHasher

# function
from function import func_run_broker
from function import func_postgres_create
from function import func_postgres_serialize
from function import func_regex_check
from function import func_postgres_schema_read

# config
from config import config_postgres_url
from config import config_regex
from config import config_table
from config import config_buffer_limit_default
from config import config_redis_url_queue
from config import config_rabbitmq_url
from config import config_celery_url
from config import config_kafka_url
from config import config_kafka_username
from config import config_kafka_password

# logic
async def setup():
    client_postgres_pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=1, max_size=5)
    cache_postgres_buffer_create = {}
    cache_postgres_schema = await func_postgres_schema_read(client_postgres_pool=client_postgres_pool)
    client_password_hasher = PasswordHasher()
    return client_postgres_pool, cache_postgres_buffer_create, cache_postgres_schema, client_password_hasher

async def execute(payload, client_postgres_pool, cache_postgres_buffer_create, cache_postgres_schema, client_password_hasher):
    table = payload.get("table")
    return await func_postgres_create(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=config_regex, buffer_limit=config_table.get(table, {}).get("buffer_limit", config_buffer_limit_default), mode=payload.get("mode", "now"), table=table, obj_list=payload.get("obj_list"))

# init
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: queue is required. Usage: python script/consumer_postgres_create.py <redis|rabbitmq|kafka|celery>")
        sys.exit(1)
    queue = sys.argv[1]
    channel = "func_postgres_create"
    config_broker = {"config_redis_url_queue": config_redis_url_queue, "config_rabbitmq_url": config_rabbitmq_url, "config_kafka_url": config_kafka_url, "config_kafka_username": config_kafka_username, "config_kafka_password": config_kafka_password, "config_celery_url": config_celery_url}
    func_run_broker(queue=queue, channel=channel, config_broker=config_broker, setup_callback=setup, execute_callback=execute)
