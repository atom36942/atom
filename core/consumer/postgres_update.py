#import
import sys
from argon2 import PasswordHasher
import asyncpg
from .base_broker import run_broker
from ..function import (
    func_postgres_schema_read,
    func_postgres_update,
    func_postgres_serialize,
    func_regex_check
)

#channel
channel = "func_postgres_update"

#config
from ..config import (
    config_postgres_url,
    config_postgres_min_connection,
    config_postgres_max_connection,
    config_regex,
    config_table,
    config_obj_list_limit
)

#func
async def setup():
    client_postgres_pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=config_postgres_min_connection, max_size=config_postgres_max_connection) if config_postgres_url else None
    cache_postgres_buffer_create = {}
    cache_postgres_schema = await func_postgres_schema_read(client_postgres_pool=client_postgres_pool)
    client_password_hasher = PasswordHasher()
    return client_postgres_pool, cache_postgres_buffer_create, cache_postgres_schema, client_password_hasher

async def execute(client_postgres_pool, payload, cache_postgres_buffer_create, cache_postgres_schema, client_password_hasher):
    table = payload.get("table")
    return await func_postgres_update(
        client_postgres_pool=client_postgres_pool,
        client_postgres_conn=None,
        client_password_hasher=client_password_hasher,
        func_postgres_serialize=func_postgres_serialize,
        func_regex_check=func_regex_check,
        cache_postgres_schema=cache_postgres_schema,
        config_regex=config_regex,
        config_table=config_table,
        config_obj_list_limit=config_obj_list_limit,
        table=table,
        obj_list=payload.get("obj_list"),
        created_by_id=payload.get("created_by_id")
    )

#init
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    queue = sys.argv[1]
    run_broker(queue, channel, setup, execute)
