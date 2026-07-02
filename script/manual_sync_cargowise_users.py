# packages
import argparse
import ast
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
from config import config_mssql_url_read
from config import config_postgres_url
from config import config_regex
from config import config_table
from config import config_buffer_limit_default
seed_cargowise_user_type = ast.literal_eval(os.getenv("seed_cargowise_user_type")) if os.getenv("seed_cargowise_user_type") else 1
seed_cargowise_user_role = ast.literal_eval(os.getenv("seed_cargowise_user_role")) if os.getenv("seed_cargowise_user_role") else 2
seed_cargowise_user_password = os.getenv("seed_cargowise_user_password") if os.getenv("seed_cargowise_user_password") else "123456"

# logic
async def execute():
    batch_size = 1000
    def parse_args():
        parser = argparse.ArgumentParser(description="Seed CargoWise orgs into Postgres users.")
        parser.add_argument("--postgres-url", default=config_postgres_url, help="PostgreSQL DSN. Defaults to config_postgres_url.")
        parser.add_argument("--mssql-url", default=config_mssql_url_read, help="MSSQL ODBC DSN. Defaults to config_mssql_url_read.")
        parser.add_argument("--password", default=seed_cargowise_user_password, help="Default password for newly-created CargoWise users.")
        parser.add_argument("--user-type", type=int, default=seed_cargowise_user_type, help="users.type value for CargoWise users.")
        parser.add_argument("--role", type=int, default=seed_cargowise_user_role, help="users.role value for CargoWise users.")
        parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing to Postgres.")
        return parser.parse_args()
    def chunked(items, size):
        for i in range(0, len(items), size):
            yield items[i:i + size]
    def clean_optional_text(value):
        value = str(value or "").strip()
        return value or None
    def cargowise_org_sql():
        return textwrap.dedent(f"""\
            SELECT
                CONVERT(varchar(36), OH.OH_PK) AS username,
                OH.OH_FullName AS name,
                OH.OH_Code AS code
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
            if not username:
                continue
            orgs.append({
                "username": username,
                "name": str(item.get("name") or "").strip(),
                "code": clean_optional_text(item.get("code"))
            })
        return orgs
    async def read_existing_users(client_postgres, orgs):
        if not orgs:
            return []
        usernames = [org["username"] for org in orgs]
        sql = textwrap.dedent("""\
            SELECT
                id, type, username, code, name, role, deactivated_at, deleted_at
            FROM users
            WHERE username = ANY($1::text[])
            ORDER BY username, deleted_at NULLS FIRST, deactivated_at NULLS FIRST, type;""")
        async with client_postgres.acquire() as conn:
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
            
            desired = {
                "type": user_type,
                "role": role,
                "name": org["name"],
                "code": org["code"]
            }
            
            if not existing:
                create_list.append({
                    "username": org["username"],
                    "password": password,
                    **desired
                })
                continue
            if any(existing.get(key) != value for key, value in desired.items()):
                update_list.append({"id": existing["id"], **desired, "updated_at": sync_time})
        return create_list, update_list, duplicate_warnings
    async def create_users(client_postgres, cache_postgres_schema, client_password_hasher, obj_list):
        total = 0
        cache_postgres_buffer_create = {}
        for batch in chunked(obj_list, batch_size):
            await func_postgres_create(client_postgres=client_postgres, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=config_regex, buffer_limit=config_table.get("users", {}).get("buffer_limit", config_buffer_limit_default), mode="now", table="users", obj_list=batch)
            total += len(batch)
        return total
    async def update_users(client_postgres, cache_postgres_schema, client_password_hasher, obj_list):
        total = 0
        for batch in chunked(obj_list, batch_size):
            await func_postgres_update(client_postgres=client_postgres, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, config_regex=config_regex, table="users", obj_list=batch, created_by_id=None)
            total += len(batch)
        return total
    args = parse_args()
    if not args.postgres_url:
        print("Error: PostgreSQL URL is required. Set config_postgres_url or pass --postgres-url.")
        return
    if not args.mssql_url:
        print("Error: MSSQL URL is required. Set config_mssql_url_read or pass --mssql-url.")
        return
    print("Fetching CargoWise orgs...")
    orgs = await fetch_cargowise_orgs(args.mssql_url)
    print(f"Fetched {len(orgs)} org(s).")
    if not orgs:
        return
    client_postgres = await asyncpg.create_pool(dsn=args.postgres_url, min_size=1, max_size=5)
    try:
        cache_postgres_schema = await func_postgres_schema_read(client_postgres=client_postgres)
        if "users" not in cache_postgres_schema:
            raise Exception("users table not found in Postgres schema")
        client_password_hasher = PasswordHasher()
        existing_users = await read_existing_users(client_postgres, orgs)
        create_list, update_list, duplicate_warnings = plan_user_changes(orgs, existing_users, args.password, args.user_type, args.role)
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
        created_count = await create_users(client_postgres, cache_postgres_schema, client_password_hasher, create_list) if create_list else 0
        updated_count = await update_users(client_postgres, cache_postgres_schema, client_password_hasher, update_list) if update_list else 0
        print(f"Created CargoWise user(s): {created_count}")
        print(f"Updated CargoWise user(s): {updated_count}")
        print("CargoWise user seed completed.")
    finally:
        await client_postgres.close()
        
# init
if __name__ == "__main__":
    asyncio.run(execute())
