# type: job

# command: venv/bin/python -m script.postgres_backup

# info: Backs up every table of the master database to CSV, with its columns and indexes, into tmp/postgres_backup/<date_time>/, from one consistent snapshot, and deletes backups older than BACKUP_KEEP_DAY; runs on config_schedule_script_postgres_backup (off by default).
# - step: disk, stops when free disk space is below the database's size
# - step: columns and indexes, written to columns.csv and indexes.csv
# - step: <table> (i/n), one CSV per table; tables.csv lists each table's row count
# - step: old backups, deletes folders older than BACKUP_KEEP_DAY

# import
import asyncio
import csv
import datetime
import os
import re
import shutil
import sys
import asyncpg
from dotenv import load_dotenv
from function import func_script_run

# config
load_dotenv(".env")
postgres_url_master = os.getenv("config_postgres_url_master")

# setting
BACKUP_ROOT = "tmp/postgres_backup"
BACKUP_KEEP_DAY = 7
TABLE_SKIP = ("spatial_ref_sys",)

# logic
def disk_check(*, database_bytes) -> None:
    free_bytes = shutil.disk_usage(BACKUP_ROOT).free
    if free_bytes < database_bytes: raise Exception(f"not enough disk space: the database is {database_bytes // 1048576} MB, {free_bytes // 1048576} MB free")

async def schema_export(*, conn, folder) -> None:
    await conn.copy_from_query("SELECT table_name, column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = 'public' ORDER BY table_name, ordinal_position", output=os.path.join(folder, "columns.csv"), format="csv", header=True)
    await conn.copy_from_query("SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname", output=os.path.join(folder, "indexes.csv"), format="csv", header=True)

async def tables_export(*, conn, folder) -> dict:
    tables = [row["tablename"] for row in await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename") if row["tablename"] not in TABLE_SKIP]
    counts = {}
    for number, table in enumerate(tables, 1):
        print(f"step: {table} ({number}/{len(tables)})", flush=True)
        result = await conn.copy_from_table(table, schema_name="public", output=os.path.join(folder, f"{table}.csv"), format="csv", header=True)
        counts[table] = int(result.split()[-1])
    counts_write(folder=folder, counts=counts)
    return counts

def counts_write(*, folder, counts) -> None:
    with open(os.path.join(folder, "tables.csv"), "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["table", "rows"])
        writer.writerows(counts.items())

def old_backup_delete(*, now) -> int:
    deleted = 0
    for name in sorted(os.listdir(BACKUP_ROOT)):
        if not re.fullmatch(r"\d{4}-\d\d-\d\d_\d{6}", name): continue
        if now - datetime.datetime.strptime(name, "%Y-%m-%d_%H%M%S").replace(tzinfo=datetime.UTC) > datetime.timedelta(days=BACKUP_KEEP_DAY):
            shutil.rmtree(os.path.join(BACKUP_ROOT, name))
            deleted += 1
    return deleted

def folder_size_mb(*, folder) -> int:
    return sum(os.path.getsize(os.path.join(folder, name)) for name in os.listdir(folder)) // 1048576

async def backup_run(*, postgres_url) -> None:
    async with func_script_run(postgres_url=postgres_url, script="postgres_backup"):
        now = datetime.datetime.now(datetime.UTC)
        folder = os.path.join(BACKUP_ROOT, now.strftime("%Y-%m-%d_%H%M%S"))
        os.makedirs(folder, exist_ok=True)
        conn = await asyncpg.connect(postgres_url)
        try:
            print("step: disk", flush=True)
            disk_check(database_bytes=await conn.fetchval("SELECT pg_database_size(current_database())"))
            async with conn.transaction(isolation="repeatable_read", readonly=True):    # every file comes from the same moment
                print("step: columns and indexes", flush=True)
                await schema_export(conn=conn, folder=folder)
                counts = await tables_export(conn=conn, folder=folder)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)    # never leave a half backup that looks complete
            raise
        finally:
            await conn.close()
        print("step: old backups", flush=True)
        deleted = old_backup_delete(now=now)
        print(f"backed up {len(counts)} tables, {sum(counts.values())} rows, {folder_size_mb(folder=folder)} MB to {folder}; deleted {deleted} old backup(s)", flush=True)

def main():
    if not postgres_url_master: sys.exit("config_postgres_url_master is not set")
    asyncio.run(backup_run(postgres_url=postgres_url_master))
    sys.exit(0)

# main
if __name__ == "__main__":
    main()
