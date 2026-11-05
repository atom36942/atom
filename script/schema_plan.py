# command: venv/bin/python -m script.schema_plan
# command: venv/bin/python -m script.schema_plan --apply

# info: Prints the SQL Atom's next start would run on the master database to match config_postgres (config.py and config_extend.py), and flags statements that lock or rewrite a table; --apply then runs it.
# - without --apply: reads the database catalog on a read-only connection; changes nothing
# - run it with the new code before a deploy; a flagged statement on a big table is better run by hand when it is quiet
# - --apply: runs exactly what startup runs with config_is_postgres_schema_init on (one transaction, the same lock and lock timeout); for projects that set it off, so startup only checks

# import
import argparse
import asyncio
import os
import sys
from types import SimpleNamespace
from dotenv import load_dotenv
import function
from function import func_client_password_hasher
from function import func_client_postgres
from function import func_config_read
from function import func_postgres_advisory_lock
from function import func_postgres_schema_init
from function import func_postgres_schema_plan

# config
load_dotenv(".env")
config_postgres_url_master = os.getenv("config_postgres_url_master")
config_root_user_password = os.getenv("config_root_user_password")

# setting
SQL_PREVIEW_CHARS = 300

# logic
def args_read():
    parser = argparse.ArgumentParser(description="Show the schema changes the next start would run on the master database; --apply runs them.")
    parser.add_argument("--apply", action="store_true", help="run the changes, as startup does with config_is_postgres_schema_init on")
    return parser.parse_args()


def app_state_build():
    return SimpleNamespace(**{name: getattr(function, name) for name in function.__all__})


async def plan_read(*, postgres_url, config):
    """The plan for the master database, with the project's merged config_postgres."""
    pool = await func_client_postgres(dsn=postgres_url, min_size=1, max_size=1, is_read_only=True)
    try: return await func_postgres_schema_plan(app_state=app_state_build(), client_postgres=pool, config_postgres=config["config_postgres"])
    finally: await pool.close()


def plan_print(*, plan):
    """One line per change, flagged ones first with their table's estimated rows; statements that run on every start are only counted. Returns the number of changes."""
    changes = [step for step in plan if not step["is_routine"]]
    risky = [step for step in changes if step["risk"]]
    for step in [*risky, *[step for step in changes if not step["risk"]]]:
        sql = " ".join(step["sql"].split())
        flag = f"!! {step['risk']}" + (f" ({step['table']}: about {step['rows']:,} rows)" if step["table"] else "") + "\n   " if step["risk"] else "   "
        print(f"{flag}{sql[:SQL_PREVIEW_CHARS]}{'…' if len(sql) > SQL_PREVIEW_CHARS else ''}")
    routine = len(plan) - len(changes)
    print(("\n" if changes else "") + (f"{len(changes)} changes, {len(risky)} flagged" if changes else "No changes: the database already matches config_postgres") + f" (plus {routine} statements that run on every start)")
    return len(changes)


async def plan_apply(*, postgres_url, config, root_user_password):
    """Run the schema steps as startup does: one app at a time (the same advisory lock), each table lock waited for at most config_postgres_schema_lock_timeout_sec."""
    pool = await func_client_postgres(dsn=postgres_url, min_size=1, max_size=2)    # one connection holds the lock, one runs the steps
    try:
        async with func_postgres_advisory_lock(client_postgres=pool, lock_id=3):
            password_hash = func_client_password_hasher().hash(str(root_user_password)) if root_user_password else None
            return await func_postgres_schema_init(app_state=app_state_build(), client_postgres=pool, config_postgres=config["config_postgres"], root_user_password_hash=password_hash, lock_timeout_sec=config["config_postgres_schema_lock_timeout_sec"])
    finally: await pool.close()


def main():
    args = args_read()
    if not config_postgres_url_master: sys.exit("Error: config_postgres_url_master is not set in .env")
    config = func_config_read()
    changes = plan_print(plan=asyncio.run(plan_read(postgres_url=config_postgres_url_master, config=config)))
    if args.apply and not changes: print("Nothing to apply.")
    elif args.apply:
        asyncio.run(plan_apply(postgres_url=config_postgres_url_master, config=config, root_user_password=config_root_user_password))
        print(f"Applied {changes} changes.")

# main
if __name__ == "__main__":
    main()
