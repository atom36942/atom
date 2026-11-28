# type: job

# command: venv/bin/python -m script.postgres_cleanup

# info: Deletes rows older than their table's days in control.retention_day of config_postgres_schema_<name> (otp 1, log_api 7 and script_run 90 days by default; a table without it is kept), in every database; runs on config_schedule_script_postgres_cleanup (every hour by default).
# - step: <database>.<table>, deletes that table's old rows (script_run keeps a run still going)

# import
import asyncio
import sys
from function import func_client_postgres
from function import func_config_read
from function import func_postgres_schema_dict
from function import func_script_run
from function import func_table_retention_cleanup

# config

# setting
BATCH_PAUSE_SEC = 0.1
QUERY_TIMEOUT_SEC = 30

# logic
async def rows_delete(*, postgres_url, table, retention_day) -> int:
    pool = await func_client_postgres(dsn=postgres_url, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            cutoff = await conn.fetchval("SELECT CURRENT_TIMESTAMP - ($1::integer * INTERVAL '1 day')", retention_day)
            total = 0
            while True:
                deleted = await func_table_retention_cleanup(conn=conn, table=table, cutoff=cutoff, timeout_sec=QUERY_TIMEOUT_SEC)
                total += deleted
                if deleted < 5000: return total
                await asyncio.sleep(BATCH_PAUSE_SEC)
    finally:
        await pool.close()

async def cleanup_run(*, config) -> None:
    url_dict = config.get("config_postgres_url_dict") or {}
    if not url_dict.get("master"): raise Exception("config_postgres_url_master is not set")
    async with func_script_run(postgres_url=url_dict["master"], script="postgres_cleanup"):
        result = []
        for database, schema in func_postgres_schema_dict(values=config).items():
            if not url_dict.get(database): continue
            for table, retention_day in (((schema or {}).get("control") or {}).get("retention_day") or {}).items():
                print(f"step: {database}.{table}", flush=True)
                result.append(f"{database}.{table} {await rows_delete(postgres_url=url_dict[database], table=table, retention_day=retention_day)}")
        print(f"deleted rows: {', '.join(result) or 'none (no table in control.retention_day)'}", flush=True)

def main():
    config = func_config_read()
    asyncio.run(cleanup_run(config=config))
    sys.exit(0)

# main
if __name__ == "__main__":
    main()
