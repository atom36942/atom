#import
import sys
from ..config import *
from ..function import *
from .base_broker import run_broker
from argon2 import PasswordHasher

#taskname
task_name = "func_postgres_update"

#setup
async def setup():
    pool = await func_client_read_postgres(config_postgres={"dsn": config_postgres_url, "min_size": config_postgres_min_connection, "max_size": config_postgres_max_connection})
    buffer = {}
    schema = await func_postgres_schema_read(client_postgres_pool=pool)
    hasher = PasswordHasher()
    return pool, buffer, schema, hasher

#execute
async def execute(pool, payload, buffer, schema, hasher):
    return await func_postgres_update(
        client_postgres_pool=pool,
        client_password_hasher=hasher,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        table=payload.get("table"),
        obj_list=payload.get("obj_list"),
        is_serialize=payload.get("is_serialize", 1),
        created_by_id=payload.get("created_by_id"),
        is_return_ids=payload.get("is_return_ids", 0),
        client_postgres_conn=None
    )

#init
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: venv/bin/python -m core.consumer.postgres_update [redis|rabbitmq|kafka|celery]")
        sys.exit(1)
    mode = sys.argv[1]
    channel = task_name
    run_broker(mode, channel, task_name, setup, execute)

