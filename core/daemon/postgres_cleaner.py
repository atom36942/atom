import asyncio
import os
import sys
import asyncpg

# Ensure the parent directory is in the path so we can import 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config import config_table, config_postgres_url

async def run_cleaner():
    if not config_postgres_url:
        print("Error: config_postgres_url is not set in environment or config.")
        return

    print("Starting Postgres Cleanup Daemon...")
    
    # Initialize connection pool
    pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=1, max_size=5)
    
    try:
        async with pool.acquire() as conn:
            for tbl, cfg in config_table.items():
                retention_days = cfg.get("retention_day")
                if retention_days is not None:
                    print(f"[{tbl}] Cleaning records older than {retention_days} days...")
                    
                    deleted_count = -1
                    total_deleted = 0
                    
                    # Delete in chunks to avoid table locks and heavy WAL usage
                    while deleted_count != 0:
                        query = f"""
                            DELETE FROM "{tbl}" 
                            WHERE ctid IN (
                                SELECT ctid FROM "{tbl}" 
                                WHERE "created_at" < NOW() - INTERVAL '{retention_days} days' 
                                LIMIT 5000
                            ) RETURNING id;
                        """
                        # Execute chunked delete
                        records = await conn.fetch(query)
                        deleted_count = len(records)
                        total_deleted += deleted_count
                        
                        # Brief sleep to yield execution to other transactions
                        await asyncio.sleep(0.1) 
                    
                    print(f"[{tbl}] Finished cleaning. Total deleted: {total_deleted}")
    finally:
        await pool.close()
        print("Postgres Cleanup Daemon finished.")

if __name__ == "__main__":
    asyncio.run(run_cleaner())
