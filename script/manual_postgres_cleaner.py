# command: venv/bin/python -m script.manual_postgres_cleaner

# info: Periodically deletes expired database rows based on table retention day settings while guarding sensitive tables.

# packages
import asyncio
import time

# function
from function import func_client_postgres

# config
from config import config_postgres_url
from config import config_table
from config import config_table_protected

# logic
async def execute():
    blocked_tables = [table for table, cfg in config_table.items() if cfg.get("retention_day") is not None and table in config_table_protected]
    if blocked_tables:
        raise Exception(f"postgres cleaner blocked for protected table(s): {', '.join(blocked_tables)}")
    print("Starting Postgres Cleanup Script...")
    pool = await func_client_postgres(dsn=config_postgres_url, min_size=1, max_size=5)
    try:
        async with pool.acquire() as conn:
            await conn.execute("SET statement_timeout = '60s'")
            for tbl, cfg in config_table.items():
                retention_days = cfg.get("retention_day")
                if retention_days is not None:
                    try:
                        start_time = time.time()
                        deleted_count = -1
                        total_deleted = 0
                        while deleted_count != 0:
                            query = f'DELETE FROM "{tbl}" WHERE ctid IN (SELECT ctid FROM "{tbl}" WHERE "created_at" < NOW() - INTERVAL \'{retention_days} days\' LIMIT 5000) RETURNING id;'
                            records = await conn.fetch(query)
                            deleted_count = len(records)
                            total_deleted += deleted_count
                            await asyncio.sleep(0.1) 
                        exec_time = round(time.time() - start_time, 2)
                        print(f"[{tbl}] Deleted {total_deleted} records older than {retention_days} days (Took {exec_time}s)")
                    except Exception as e:
                        print(f"[{tbl}] Error during cleanup: {e}")
    finally:
        await pool.close()
        print("Postgres Cleanup Script finished.")

# init
if __name__ == "__main__":
    asyncio.run(execute())
