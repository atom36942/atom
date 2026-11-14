# type: job

# command: venv/bin/python -m script.postgres_cleanup

# info: Deletes OTP, API-log and script-run rows older than their retention (config_retention_day_otp, config_retention_day_log_api, config_retention_day_script_run; None skips one); runs on config_schedule_script_postgres_cleanup (every hour by default).
# - step: otp, deletes old codes from the master database
# - step: log_api, deletes old request logs from the database config_postgres_db_log_api names
# - step: script_run, deletes old finished runs of scheduled and hand-run scripts from the master database

# import
import asyncio
import sys
from function import func_client_postgres
from function import func_config_read
from function import func_log_api_cleanup
from function import func_otp_cleanup
from function import func_script_run
from function import func_script_run_cleanup

# config

# setting
BATCH_PAUSE_SEC = 0.1
QUERY_TIMEOUT_SEC = 30

# logic
async def rows_delete(*, postgres_url, cleanup, retention_day) -> int:
    pool = await func_client_postgres(dsn=postgres_url, min_size=1, max_size=1)
    try:
        async with pool.acquire() as conn:
            cutoff = await conn.fetchval("SELECT CURRENT_TIMESTAMP - ($1::integer * INTERVAL '1 day')", retention_day)
            total = 0
            while True:
                deleted = await cleanup(conn=conn, cutoff=cutoff, timeout_sec=QUERY_TIMEOUT_SEC)
                total += deleted
                if deleted < 5000: return total
                await asyncio.sleep(BATCH_PAUSE_SEC)
    finally:
        await pool.close()

async def cleanup_run(*, config) -> None:
    url_dict = config.get("config_postgres_url_dict") or {}
    if not url_dict.get("master"): raise Exception("config_postgres_url_master is not set")
    log_db = config.get("config_postgres_db_log_api") if config.get("config_is_log_api") else None
    async with func_script_run(postgres_url=url_dict["master"], script="postgres_cleanup"):
        result = []
        print("step: otp", flush=True)
        if config.get("config_retention_day_otp") is not None:
            result.append(f"otp {await rows_delete(postgres_url=url_dict['master'], cleanup=func_otp_cleanup, retention_day=config['config_retention_day_otp'])}")
        print("step: log_api", flush=True)
        if log_db and url_dict.get(log_db) and config.get("config_retention_day_log_api") is not None:
            result.append(f"log_api {await rows_delete(postgres_url=url_dict[log_db], cleanup=func_log_api_cleanup, retention_day=config['config_retention_day_log_api'])}")
        print("step: script_run", flush=True)
        if config.get("config_retention_day_script_run") is not None:
            result.append(f"script_run {await rows_delete(postgres_url=url_dict['master'], cleanup=func_script_run_cleanup, retention_day=config['config_retention_day_script_run'])}")
        print(f"deleted rows: {', '.join(result) or 'none (every cleanup is off)'}", flush=True)

def main():
    config = func_config_read()
    asyncio.run(cleanup_run(config=config))
    sys.exit(0)

# main
if __name__ == "__main__":
    main()
