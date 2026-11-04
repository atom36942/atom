# command: venv/bin/python -m script.schema_plan

# info: Prints the SQL Atom's next start would run on the master database to match config_postgres (config.py and config_extend.py), without running it, and flags statements that lock or rewrite a table.
# - reads the database catalog on a read-only connection; changes nothing
# - run it with the new code before a deploy; a flagged statement on a big table is better run by hand when it is quiet

# import
import asyncio
import os
import sys
from types import SimpleNamespace
from dotenv import load_dotenv
import function
from function import func_client_postgres
from function import func_config_read
from function import func_postgres_schema_plan

# config
load_dotenv(".env")
config_postgres_url_master = os.getenv("config_postgres_url_master")

# setting
SQL_PREVIEW_CHARS = 300

# logic
async def plan_read(*, postgres_url):
    """The plan for the master database, with the project's merged config_postgres."""
    app_state = SimpleNamespace(**{name: getattr(function, name) for name in function.__all__})
    pool = await func_client_postgres(dsn=postgres_url, min_size=1, max_size=1, is_read_only=True)
    try: return await func_postgres_schema_plan(app_state=app_state, client_postgres=pool, config_postgres=func_config_read()["config_postgres"])
    finally: await pool.close()


def plan_print(*, plan):
    """One line per change, flagged ones first with their table's estimated rows; statements that run on every start are only counted."""
    changes = [step for step in plan if not step["is_routine"]]
    risky = [step for step in changes if step["risk"]]
    for step in [*risky, *[step for step in changes if not step["risk"]]]:
        sql = " ".join(step["sql"].split())
        flag = f"!! {step['risk']}" + (f" ({step['table']}: about {step['rows']:,} rows)" if step["table"] else "") + "\n   " if step["risk"] else "   "
        print(f"{flag}{sql[:SQL_PREVIEW_CHARS]}{'…' if len(sql) > SQL_PREVIEW_CHARS else ''}")
    routine = len(plan) - len(changes)
    print(("\n" if changes else "") + (f"{len(changes)} changes, {len(risky)} flagged" if changes else "No changes: the database already matches config_postgres") + f" (plus {routine} statements that run on every start)")


def main():
    if not config_postgres_url_master: sys.exit("Error: config_postgres_url_master is not set in .env")
    plan_print(plan=asyncio.run(plan_read(postgres_url=config_postgres_url_master)))

# main
if __name__ == "__main__":
    main()
