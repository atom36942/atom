import sys
from ..config import *
from ..function import *
from .base_broker import run_broker
from argon2 import PasswordHasher

task_name = "func_postgres_create"

async def setup():
    pool = await func_client_read_postgres(config_postgres={"dsn": config_postgres_url, "min_size": config_postgres_min_connection, "max_size": config_postgres_max_connection})
    buffer = {}
    schema = await func_postgres_schema_read(client_postgres_pool=pool)
    hasher = PasswordHasher()
    return pool, buffer, schema, hasher

async def execute(pool, payload, buffer, schema, hasher):
    tbl = payload.get("table")
    return await func_postgres_create(
        client_postgres_pool=pool,
        client_password_hasher=hasher,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=schema,
        mode=payload.get("mode", "now"),
        table=tbl,
        obj_list=payload.get("obj_list"),
        is_serialize=payload.get("is_serialize", 0),
        buffer_limit=payload.get("buffer_limit", config_table.get(tbl, {}).get("buffer", 100) if tbl else 100),
        cache_postgres_buffer=buffer,
        client_postgres_conn=None
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"usage: venv/bin/python -m core.consumer.postgres_create [redis|rabbitmq|kafka|celery]")
        sys.exit(1)
    mode = sys.argv[1]
    channel = task_name
    run_broker(mode, channel, task_name, setup, execute)
