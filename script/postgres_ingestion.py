# command: venv/bin/python -m script.postgres_ingestion

# info: Performs high-performance bulk operations (create, update, delete) from a CSV file into PostgreSQL using staging tables and copy_records_to_table.

# import
import ast
import asyncio
import csv
import os
import re
import sys
from datetime import datetime
import asyncpg
from dotenv import load_dotenv

# config
load_dotenv(".env")
pg_dsn = os.getenv("PG_DSN")
csv_path = os.getenv("csv_path")
table = os.getenv("table")
crud_mode = os.getenv("crud_mode")
validation_mode = os.getenv("validation_mode") or "strict"
rename_column = ast.literal_eval(os.getenv("rename_column")) if os.getenv("rename_column") else None
ignore_column = ast.literal_eval(os.getenv("ignore_column")) if os.getenv("ignore_column") else None
const_column = ast.literal_eval(os.getenv("const_column")) if os.getenv("const_column") else None

# setting
STAGING_TABLE_PREFIX = "staging_sync_"
COPY_TIMEOUT_SEC = 28800    # 8 hours, for very large files
NULL_VALUES = ("", "none", "null", "n/a")
TRUE_VALUES = ("true", "1", "yes", "t", "y")
DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y%m%d")

# logic
class RowReject(Exception): pass

def option_check(*, pg_dsn: str, csv_path: str, table: str, crud_mode: str, validation_mode: str, ignore_column: list | None, const_column: list | None) -> None:
    if not pg_dsn: raise ValueError("PG_DSN is required")
    if not csv_path: raise ValueError("csv_path is required")
    if not os.path.isfile(csv_path): raise ValueError(f"csv_path not found: {csv_path}")
    if not table: raise ValueError("table is required")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table): raise ValueError(f"invalid table name: {table}")
    if crud_mode not in ("create", "update", "delete"): raise ValueError(f"Invalid crud_mode: '{crud_mode}'")
    if validation_mode not in ("strict", "reject", "loose"): raise ValueError(f"Invalid validation_mode: '{validation_mode}'")
    if crud_mode == "delete" and const_column: raise ValueError("'const_column' must be None for 'delete' mode.")
    if crud_mode == "delete" and ignore_column: raise ValueError("'ignore_column' must be None for 'delete' mode.")
    if crud_mode == "update" and ignore_column and "id" in ignore_column: raise ValueError("Cannot ignore 'id' column in 'update' mode.")

def pair_list(*, value: list | None) -> list:
    """The (name, value) pairs of a rename_column / const_column option."""
    return [pair for pair in value or [] if isinstance(pair, (tuple, list)) and len(pair) == 2]

async def column_type_read(*, conn: asyncpg.Connection, table: str) -> dict:
    """{column: udt name} of the target table."""
    records = await conn.fetch("SELECT column_name, udt_name FROM information_schema.columns WHERE table_name=$1", table)
    if not records: raise ValueError(f"Table '{table}' not found")
    return {r["column_name"]: r["udt_name"] for r in records}

def csv_header_read(*, csv_path: str, rename_map: dict, ignore_column: list | None, crud_mode: str) -> tuple:
    """(header as in the file, header after renames and ignores)."""
    with open(csv_path, newline="", encoding="utf-8") as f: header_original = csv.DictReader(f).fieldnames or []
    if not header_original: raise Exception("Missing CSV header")
    header = [col for col in (rename_map.get(c, c) for c in header_original) if not ignore_column or col not in ignore_column]
    if crud_mode in ("update", "delete") and "id" not in header: raise ValueError(f"id column is missing from CSV (required for {crud_mode})")
    return header_original, header

def final_column_list(*, crud_mode: str, header: list, column_type: dict, const_map: dict) -> list:
    """The columns sent to the staging table: CSV columns the table has, plus constants not in the CSV."""
    csv_cols = [c for c in header if c in column_type]
    const_cols = [c for c in const_map if c in column_type and c not in csv_cols]
    if crud_mode == "delete": return ["id"] if "id" in csv_cols else []
    if crud_mode == "update": return ["id"] + [c for c in csv_cols if c != "id"] + const_cols
    return csv_cols + const_cols

def value_convert(*, value, col_name: str, col_type: str, validation_mode: str) -> str | None:
    """Normalizes one value as text for its column type; on a bad value strict raises, reject skips the row, loose stores NULL."""
    value_str = str(value).strip() if value is not None else None
    if not value_str or value_str.lower() in NULL_VALUES: return None
    try:
        if ("int" in col_type or "numeric" in col_type or "real" in col_type or "double" in col_type) and not col_type.startswith("_"): float(value_str)
        if "bool" in col_type: value_str = "true" if value_str.lower() in TRUE_VALUES else "false"
        if "date" in col_type or "timestamp" in col_type:
            for fmt in DATE_FORMATS:
                try: value_str = datetime.strptime(value_str, fmt).isoformat(); break
                except ValueError: continue
            else: raise ValueError("Invalid date format")
    except Exception:
        if validation_mode == "strict": raise ValueError(f"Column '{col_name}' error") from None
        if validation_mode == "reject": raise RowReject(col_name) from None
        return None
    return value_str

def row_generate(*, csv_path: str, final_cols: list, column_type: dict, const_map: dict, reverse_rename_map: dict, validation_mode: str, header_original: list, reject_path: str, counter: dict):
    """Yields one converted tuple per CSV row; in reject mode, bad rows go to reject_path instead."""
    file_reject = None
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    yield tuple(value_convert(value=const_map[col] if col in const_map else row.get(reverse_rename_map.get(col, col)), col_name=col, col_type=column_type.get(col, "text"), validation_mode=validation_mode) for col in final_cols)
                except RowReject:
                    counter["rejected"] += 1
                    if not file_reject:
                        os.makedirs("tmp", exist_ok=True)
                        file_reject = open(reject_path, "w", encoding="utf-8")    # noqa: SIM115 - opened on the first rejected row, closed in the finally below
                        csv.writer(file_reject).writerow(header_original)
                    csv.writer(file_reject).writerow(row.values())
    finally:
        if file_reject: file_reject.close()

def column_cast(*, col: str, col_type: str) -> str:
    if col_type in ("int2", "int4", "int8"): return f'ROUND(s."{col}"::numeric)::{col_type}'
    return f's."{col}"::{col_type}'

async def staging_apply(*, conn: asyncpg.Connection, table: str, staging_table: str, crud_mode: str, final_cols: list, column_type: dict) -> None:
    """Applies the staged rows to the table in one transaction, then drops the staging table."""
    cast = {col: column_cast(col=col, col_type=column_type[col]) for col in final_cols}
    async with conn.transaction():
        if crud_mode == "delete":
            await conn.execute(f'DELETE FROM "{table}" m USING "{staging_table}" s WHERE m."id" = {cast["id"]}')  # noqa: S608 - table pattern-checked, columns limited to existing database columns
        elif crud_mode == "create":
            col_sql = ", ".join(f'"{c}"' for c in final_cols)
            await conn.execute(f'INSERT INTO "{table}" ({col_sql}) SELECT {", ".join(cast.values())} FROM "{staging_table}" s')  # noqa: S608 - table pattern-checked, columns limited to existing database columns
        else:
            set_sql = ", ".join(f'"{c}" = {cast[c]}' for c in final_cols if c != "id")
            await conn.execute(f'UPDATE "{table}" m SET {set_sql} FROM "{staging_table}" s WHERE m."id" = {cast["id"]}')  # noqa: S608 - table pattern-checked, columns limited to existing database columns
        await conn.execute(f'DROP TABLE IF EXISTS "{staging_table}"')

async def main():
    csv.field_size_limit(sys.maxsize)
    option_check(pg_dsn=pg_dsn, csv_path=csv_path, table=table, crud_mode=crud_mode, validation_mode=validation_mode, ignore_column=ignore_column, const_column=const_column)
    renames, const_map = pair_list(value=rename_column), dict(pair_list(value=const_column))
    reject_path = f"tmp/{os.path.splitext(os.path.basename(csv_path))[0]}_rejected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    staging_table, counter = f"{STAGING_TABLE_PREFIX}{table}", {"rejected": 0}
    conn = await asyncpg.connect(pg_dsn, timeout=60)
    try:
        column_type = await column_type_read(conn=conn, table=table)
        header_original, header = csv_header_read(csv_path=csv_path, rename_map=dict(renames), ignore_column=ignore_column, crud_mode=crud_mode)
        final_cols = final_column_list(crud_mode=crud_mode, header=header, column_type=column_type, const_map=const_map)
        rows = row_generate(csv_path=csv_path, final_cols=final_cols, column_type=column_type, const_map=const_map, reverse_rename_map={new: old for old, new in renames}, validation_mode=validation_mode, header_original=header_original, reject_path=reject_path, counter=counter)
        await conn.execute(f'DROP TABLE IF EXISTS "{staging_table}"')
        staging_cols_sql = ", ".join(f'"{c}" TEXT' for c in final_cols)
        await conn.execute(f'CREATE TEMP TABLE "{staging_table}" ({staging_cols_sql})')
        await conn.copy_records_to_table(staging_table, records=rows, columns=final_cols, timeout=COPY_TIMEOUT_SEC)
        await staging_apply(conn=conn, table=table, staging_table=staging_table, crud_mode=crud_mode, final_cols=final_cols, column_type=column_type)
    finally:
        await conn.close()
    print(f"{crud_mode} done | {table} | rejected {counter['rejected']}" + (f" -> {reject_path}" if counter["rejected"] and validation_mode == "reject" else ""))

# main
if __name__ == "__main__":
    asyncio.run(main())
