# packages
import argparse
import asyncio
import textwrap
from datetime import datetime, timezone
import aioodbc
import asyncpg
from argon2 import PasswordHasher

# function
from function import func_postgres_create
from function import func_postgres_update
from function import func_postgres_serialize
from function import func_regex_check
from function import func_postgres_schema_read

# config
from config import config_mssql_url
from config import config_postgres_url
from config import config_regex
from config import config_table
from config import config_obj_list_limit
from config import config_buffer_limit_default
config_seed_buyer_password = "123456"
config_seed_buyer_user_type = 1
config_seed_buyer_role = 2

# logic
async def execute():
    batch_size = 1000
    def parse_args():
        parser = argparse.ArgumentParser(description="Seed CargoWise buyers into Postgres users.")
        parser.add_argument("--postgres-url", default=config_postgres_url, help="PostgreSQL DSN. Defaults to config_postgres_url.")
        parser.add_argument("--mssql-url", default=config_mssql_url, help="MSSQL ODBC DSN. Defaults to config_mssql_url.")
        parser.add_argument("--password", default=config_seed_buyer_password, help="Default password for newly-created buyer users.")
        parser.add_argument("--user-type", type=int, default=config_seed_buyer_user_type, help="users.type value for buyer users.")
        parser.add_argument("--role", type=int, default=config_seed_buyer_role, help="users.role value for buyer users.")
        parser.add_argument("--include-inactive", action="store_true", help="Include inactive CargoWise buyer orgs.")
        parser.add_argument("--dry-run", action="store_true", help="Print planned changes without writing to Postgres.")
        return parser.parse_args()
    def chunked(items, size):
        for i in range(0, len(items), size):
            yield items[i:i + size]
    def buyer_sql(include_inactive):
        active_filter = "" if include_inactive else "AND OH.OH_IsActive = 1"
        return textwrap.dedent(f"""\
            WITH BuyerIds AS (
                SELECT DISTINCT
                    BuyerPK
                FROM dbo.vw_Report_ConsignorBuyerDetails
                WHERE BuyerPK IS NOT NULL
                UNION
                SELECT DISTINCT
                    OL_OH_Buyer AS BuyerPK
                FROM dbo.OrgSupplierBuyerLink
                WHERE OL_IsValid = 1
            )
            SELECT DISTINCT
                CONVERT(varchar(36), OH.OH_PK) AS id_ext,
                OH.OH_Code AS buyer_code,
                OH.OH_FullName AS buyer_name
            FROM BuyerIds AS B
            JOIN dbo.OrgHeader AS OH
                ON OH.OH_PK = B.BuyerPK
            WHERE OH.OH_IsValid = 1
              {active_filter}
            ORDER BY OH.OH_Code;""")
    async def fetch_cargowise_buyers(mssql_url, include_inactive):
        pool = await aioodbc.create_pool(dsn=mssql_url, minsize=1, maxsize=3)
        try:
            async with pool.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(buyer_sql(include_inactive))
                columns = [column[0] for column in cursor.description]
                rows = await cursor.fetchall()
        finally:
            pool.close()
            await pool.wait_closed()
        buyers = []
        for row in rows:
            item = dict(zip(columns, row))
            id_ext = str(item.get("id_ext") or "").strip()
            buyer_code = str(item.get("buyer_code") or "").strip()
            buyer_name = str(item.get("buyer_name") or "").strip()
            if not id_ext or not buyer_code:
                continue
            buyers.append({"id_ext": id_ext, "username": buyer_code, "name": buyer_name})
        return buyers
    async def read_existing_users(client_postgres_pool, buyers, user_type):
        if not buyers:
            return []
        id_exts = [buyer["id_ext"] for buyer in buyers]
        usernames = [buyer["username"] for buyer in buyers]
        sql = textwrap.dedent("""\
            SELECT
                id,
                type,
                username,
                id_ext,
                name,
                role
            FROM users
            WHERE type = $1
              AND (
                    id_ext = ANY($2::text[])
                    OR username = ANY($3::text[])
              );""")
        async with client_postgres_pool.acquire() as conn:
            records = await conn.fetch(sql, user_type, id_exts, usernames)
        return [dict(record) for record in records]
    def plan_user_changes(buyers, existing_users, password, user_type, role):
        existing_by_id_ext = {}
        existing_by_username = {}
        duplicate_warnings = []
        for user in existing_users:
            if user.get("id_ext"):
                if user["id_ext"] in existing_by_id_ext:
                    duplicate_warnings.append(f"duplicate existing id_ext skipped: {user['id_ext']}")
                    continue
                existing_by_id_ext[user["id_ext"]] = user
            if user.get("username"):
                if user["username"] in existing_by_username:
                    duplicate_warnings.append(f"duplicate existing username skipped: {user['username']}")
                    continue
                existing_by_username[user["username"]] = user
        create_list = []
        update_list = []
        sync_time = datetime.now(timezone.utc)
        for buyer in buyers:
            existing = existing_by_id_ext.get(buyer["id_ext"])
            if not existing:
                existing_by_username_match = existing_by_username.get(buyer["username"])
                if existing_by_username_match and existing_by_username_match.get("id_ext") not in (None, "", buyer["id_ext"]):
                    duplicate_warnings.append(f"username conflict skipped: {buyer['username']} -> {buyer['id_ext']}")
                    continue
                existing = existing_by_username_match
            if not existing:
                create_list.append({"type": user_type, "username": buyer["username"], "password": password, "id_ext": buyer["id_ext"], "role": role, "name": buyer["name"]})
                continue
            desired = {"username": buyer["username"], "id_ext": buyer["id_ext"], "role": role, "name": buyer["name"]}
            if any(existing.get(key) != value for key, value in desired.items()):
                update_list.append({"id": existing["id"], **desired, "updated_at": sync_time})
        return create_list, update_list, duplicate_warnings
    async def create_users(client_postgres_pool, cache_postgres_schema, client_password_hasher, obj_list):
        total = 0
        cache_postgres_buffer_create = {}
        chunk_size = min(batch_size, config_obj_list_limit or batch_size)
        for batch in chunked(obj_list, chunk_size):
            await func_postgres_create(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer_create=cache_postgres_buffer_create, config_regex=config_regex, config_table=config_table, config_obj_list_limit=config_obj_list_limit, buffer_limit=config_table.get("users", {}).get("buffer_limit", config_buffer_limit_default), mode="now", table="users", obj_list=batch)
            total += len(batch)
        return total
    async def update_users(client_postgres_pool, cache_postgres_schema, client_password_hasher, obj_list):
        total = 0
        chunk_size = min(batch_size, config_obj_list_limit or batch_size)
        for batch in chunked(obj_list, chunk_size):
            await func_postgres_update(client_postgres_pool=client_postgres_pool, client_postgres_conn=None, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, func_regex_check=func_regex_check, cache_postgres_schema=cache_postgres_schema, config_regex=config_regex, config_table=config_table, config_obj_list_limit=config_obj_list_limit, table="users", obj_list=batch, created_by_id=None)
            total += len(batch)
        return total
    args = parse_args()
    if not args.postgres_url:
        print("Error: PostgreSQL URL is required. Set config_postgres_url or pass --postgres-url.")
        return
    if not args.mssql_url:
        print("Error: MSSQL URL is required. Set config_mssql_url or pass --mssql-url.")
        return
    print("Fetching CargoWise buyers...")
    buyers = await fetch_cargowise_buyers(args.mssql_url, args.include_inactive)
    print(f"Fetched {len(buyers)} buyer(s).")
    if not buyers:
        return
    client_postgres_pool = await asyncpg.create_pool(dsn=args.postgres_url, min_size=1, max_size=5)
    try:
        cache_postgres_schema = await func_postgres_schema_read(client_postgres_pool=client_postgres_pool)
        if "users" not in cache_postgres_schema:
            raise Exception("users table not found in Postgres schema")
        client_password_hasher = PasswordHasher()
        existing_users = await read_existing_users(client_postgres_pool, buyers, args.user_type)
        create_list, update_list, duplicate_warnings = plan_user_changes(buyers, existing_users, args.password, args.user_type, args.role)
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
        print(f"Created buyer user(s): {created_count}")
        print(f"Updated buyer user(s): {updated_count}")
        print("CargoWise buyer user seed completed.")
    finally:
        await client_postgres_pool.close()
        
# init
if __name__ == "__main__":
    asyncio.run(execute())
