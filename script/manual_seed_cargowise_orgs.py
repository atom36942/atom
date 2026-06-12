# packages
import argparse
import asyncio
import os
import textwrap
from datetime import datetime, timezone
import aioodbc
import asyncpg
from argon2 import PasswordHasher
from dotenv import load_dotenv

# function
from function import func_postgres_create
from function import func_postgres_update
from function import func_postgres_serialize
from function import func_regex_check
from function import func_postgres_schema_read

# config
load_dotenv(".env")
from config import config_postgres_url
from config import config_mssql_url_read
from config import config_regex
from config import config_table
from config import config_buffer_limit_default
seed_cargowise_user_password = os.getenv("seed_cargowise_user_password") or "123456"
seed_cargowise_user_type = int(os.getenv("seed_cargowise_user_type") or 1)
seed_cargowise_user_role = int(os.getenv("seed_cargowise_user_role") or 2)

# logic
async def execute():
    batch_size = 1000
    def parse_args():
        parser = argparse.ArgumentParser(description="Seed CargoWise orgs into Postgres users.")
        parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing to Postgres.")
        return parser.parse_args()
    def chunked(items, size):
        for i in range(0, len(items), size):
            yield items[i:i + size]
    def cargowise_org_sql():
        return textwrap.dedent(f"""\
            SELECT
                CONVERT(varchar(36), OH.OH_PK) AS username,
                OH.OH_FullName AS name,
                OH.OH_IsValid AS is_valid,
                OH.OH_IsActive AS is_active
            FROM dbo.OrgHeader AS OH
            ORDER BY OH.OH_FullName;""")
    async def fetch_cargowise_orgs(mssql_url):
        pool = await aioodbc.create_pool(dsn=mssql_url, minsize=1, maxsize=3)
        try:
            async with pool.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(cargowise_org_sql())
                columns = [column[0] for column in cursor.description]
                rows = await cursor.fetchall()
        finally:
            pool.close()
            await pool.wait_closed()
        orgs = []
        for row in rows:
            item = dict(zip(columns, row))
            username = str(item.get("username") or "").strip()
            name = str(item.get("name") or "").strip()
            is_valid = bool(item.get("is_valid"))
            is_active = bool(item.get("is_active"))
            if not username:
                continue
            orgs.append({"username": username, "name": name, "is_valid": is_valid, "is_active": is_active})
        return orgs
    async def read_existing_users(client_postgres_pool, orgs):
        if not orgs:
            return []
        usernames = [org["username"] for org in orgs]
        sql = textwrap.dedent("""\
            SELECT
                id,
                type,
                username,
                name,
                role,
                deactivated_at,
                deleted_at
            FROM users
            WHERE username = ANY($1::text[])
            ORDER BY username, deleted_at NULLS FIRST, deactivated_at NULLS FIRST, type;""")
        async with client_postgres_pool.acquire() as conn:
            records = await conn.fetch(sql, usernames)
        return [dict(record) for record in records]
    def plan_user_changes(orgs, existing_users, password, user_type, role):
        existing_by_username = {}
        duplicate_warnings = []
        for user in existing_users:
            if user.get("username"):
                if user["username"] in existing_by_username:
                    duplicate_warnings.append(f"duplicate existing username skipped: {user['username']}")
                    continue
                existing_by_username[user["username"]] = user
        create_list = []
        update_list = []
        sync_time = datetime.now(timezone.utc)
        for org in orgs:
            existing = existing_by_username.get(org["username"])
            
            deleted_at = None if org["is_valid"] else sync_time
            deactivated_at = None if org["is_active"] else sync_time
            
            if not existing:
                create_list.append({
                    "type": user_type, "username": org["username"], "password": password, 
                    "role": role, "name": org["name"], 
                    "deleted_at": deleted_at, "deactivated_at": deactivated_at
                })
                continue
            
            desired = {
                "type": user_type, "role": role, "name": org["name"], 
                "deleted_at": deleted_at, "deactivated_at": deactivated_at
            }
            if any(existing.get(key) != value for key, value in desired.items()):
                update_list.append({"id": existing["id"], **desired, "updated_at": sync_time})
        return create_list, update_list, duplicate_warnings
    async def create_users(client_postgres_pool, cache_postgres_schema, client_password_hasher, obj_list):
        total = 0
        cache_postgres_buffer_create = {}
        for batch in chunked(obj_list, batch_size):
            await func_postgres_create(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=config_regex, buffer_limit=config_table.get("users", {}).get("buffer_limit", config_buffer_limit_default), mode="now", table="users", obj_list=batch)
            total += len(batch)
        return total
    async def update_users(client_postgres_pool, cache_postgres_schema, client_password_hasher, obj_list):
        total = 0
        for batch in chunked(obj_list, batch_size):
            await func_postgres_update(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, config_regex=config_regex, table="users", obj_list=batch, created_by_id=None)
            total += len(batch)
        return total
    args = parse_args()
    if not config_postgres_url:
        print("Error: PostgreSQL URL is required. Set config_postgres_url in the config section.")
        return
    if not config_mssql_url_read:
        print("Error: MSSQL URL is required. Set config_mssql_url_read in the config section.")
        return
    print("Fetching CargoWise orgs...")
    orgs = await fetch_cargowise_orgs(config_mssql_url_read)
    print(f"Fetched {len(orgs)} org(s).")
    if not orgs:
        return
    client_postgres_pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=1, max_size=5)
    try:
        cache_postgres_schema = await func_postgres_schema_read(client_postgres_pool=client_postgres_pool)
        if "users" not in cache_postgres_schema:
            raise Exception("users table not found in Postgres schema")
        client_password_hasher = PasswordHasher()
        existing_users = await read_existing_users(client_postgres_pool, orgs)
        create_list, update_list, duplicate_warnings = plan_user_changes(orgs, existing_users, seed_cargowise_user_password, seed_cargowise_user_type, seed_cargowise_user_role)
        print(f"Existing matched user(s): {len(existing_users)}")
        print(f"Planned creates: {len(create_list)}")
        print(f"Planned updates: {len(update_list)}")
        if duplicate_warnings:
            print(f"Warnings: {len(duplicate_warnings)}")
            for warning in duplicate_warnings[:20]:
                print(f" - {warning}")
            if len(duplicate_warnings) > 20:
                print(f" - ... {len(duplicate_warnings) - 20} more")
        if args.dry_run:
            print("Dry run complete. No Postgres writes performed.")
            return
        created_count = await create_users(client_postgres_pool, cache_postgres_schema, client_password_hasher, create_list) if create_list else 0
        updated_count = await update_users(client_postgres_pool, cache_postgres_schema, client_password_hasher, update_list) if update_list else 0
        print(f"Created CargoWise user(s): {created_count}")
        print(f"Updated CargoWise user(s): {updated_count}")
        print("CargoWise user seed completed.")
    finally:
        await client_postgres_pool.close()
        
# init
if __name__ == "__main__":
    asyncio.run(execute())
