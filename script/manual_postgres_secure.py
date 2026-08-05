# command: venv/bin/python -m script.manual_postgres_secure

# info: Discovers user databases on PostgreSQL server via superuser connection and installs event triggers to block DROP SCHEMA and DROP TABLE execution.

# packages
import asyncio
import os
import sys
from urllib.parse import urlparse, urlunparse
import asyncpg
from dotenv import load_dotenv

# env load
load_dotenv(".env")

# config
pg_root_url = os.getenv("PG_ROOT_URL")

# logic
async def execute():
    """Applies DROP SCHEMA and DROP TABLE Event Triggers across all user databases."""
    root_url = sys.argv[1] if len(sys.argv) > 1 else pg_root_url
    if not root_url: raise ValueError("PG_ROOT_URL is required")
    def get_db_url(base_url: str, db_name: str) -> str:
        parsed = urlparse(base_url)
        return urlunparse((parsed.scheme, parsed.netloc, f"/{db_name}", parsed.params, parsed.query, parsed.fragment))
    secure_event_trigger_sql = """CREATE OR REPLACE FUNCTION func_drop_disable() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'dropping objects (DROP SCHEMA, DROP TABLE) is disabled on this database'; END; $$; DROP EVENT TRIGGER IF EXISTS trigger_drop_disable; CREATE EVENT TRIGGER trigger_drop_disable ON ddl_command_start WHEN TAG IN ('DROP SCHEMA', 'DROP TABLE') EXECUTE FUNCTION func_drop_disable();"""
    async def secure_database(root_url_str: str, db_name: str) -> bool:
        db_url = get_db_url(root_url_str, db_name)
        try:
            conn = await asyncpg.connect(dsn=db_url)
            try:
                await conn.execute(secure_event_trigger_sql)
                print(f"  ✅ Secured database: {db_name}")
                return True
            finally:
                await conn.close()
        except Exception as e:
            print(f"  ❌ Failed to secure database '{db_name}': {e}")
            return False
    parsed = urlparse(root_url)
    discovery_url = get_db_url(root_url, "postgres")
    print(f"Connecting to PostgreSQL server at {parsed.hostname or 'localhost'}:{parsed.port or 5432} as superuser...")
    conn = await asyncpg.connect(dsn=discovery_url, timeout=60)
    try:
        rows = await conn.fetch("SELECT datname FROM pg_database WHERE datname NOT IN ('postgres', 'template0', 'template1') AND datistemplate = false;")
        user_dbs = [r['datname'] for r in rows]
    finally:
        await conn.close()
    if not user_dbs:
        print("No user databases found on this PostgreSQL server.")
        return
    print(f"Found {len(user_dbs)} user database(s): {', '.join(user_dbs)}")
    print("Applying DROP SCHEMA and DROP TABLE Event Triggers...\n")
    success_count = 0
    for db_name in user_dbs:
        if await secure_database(root_url, db_name):
            success_count += 1
    print(f"\nFinished: Successfully secured {success_count}/{len(user_dbs)} database(s).")

# init
if __name__ == "__main__":
    asyncio.run(execute())
