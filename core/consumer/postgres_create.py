#import
import sys
from ..config import *
from ..function import *
from .base_broker import run_broker
from argon2 import PasswordHasher
import asyncpg

#taskname
task_name = "func_postgres_create"

#setup
async def setup():
    pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=config_postgres_min_connection, max_size=config_postgres_max_connection) if config_postgres_url else None
    buffer = {}
    schema = await func_postgres_schema_read(client_postgres_pool=pool)
    hasher = PasswordHasher()
    return pool, buffer, schema, hasher

#execute
async def execute(pool, payload, buffer, schema, hasher):
    tbl = payload.get("table")
    return await func_postgres_create(
        client_postgres_pool=pool,
        client_postgres_conn=None,
        client_password_hasher=hasher,
        func_postgres_serialize=func_postgres_serialize,
        func_regex_check=func_regex_check,
        cache_postgres_schema=schema,
        cache_postgres_buffer_create=buffer,
        config_regex=config_regex,
        config_table=config_table,
        config_obj_list_limit=config_obj_list_limit,
        config_buffer_limit=payload.get("config_buffer_limit", config_buffer_limit),
        mode=payload.get("mode", "now"),
        table=tbl,
        obj_list=payload.get("obj_list"),
        is_serialize=payload.get("is_serialize", 0)
    )

#init
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: venv/bin/python -m core.consumer.postgres_create [redis|rabbitmq|kafka|celery]")
        sys.exit(1)
    mode = sys.argv[1]
    channel = task_name
    run_broker(mode, channel, task_name, setup, execute)
