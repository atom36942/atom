# import
import re
from typing import Any
import asyncpg
import orjson
from argon2 import PasswordHasher
from .middleware import func_api_error
from .validation import func_regex_check
from .postgres_query import func_postgres_relation
from .postgres_query import func_postgres_serialize
from .postgres_query import func_postgres_where_build
from .postgres_page import func_page_after_next
from .postgres_page import func_page_after_where
from .postgres_page import func_page_keys
from .postgres_page import func_page_offset
from .postgres_page import func_page_order_sql

# function
async def func_postgres_create(*, client_postgres: asyncpg.Pool | None, client_postgres_conn: asyncpg.Connection | None, client_password_hasher: PasswordHasher | None, cache_postgres_schema: dict, buffer_postgres: dict, config_column_regex: dict, buffer_limit: int, mode: str, table: str, obj_list: list, buffer_rows_max: int = None, buffer_full_mode: str = "reject", runtime_error_count: dict = None, is_trusted: bool = False) -> Any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization.

    buffer_rows_max caps the rows pending in buffer_postgres (None: no cap), so a long outage cannot exhaust memory.
    When full, buffer_full_mode "reject" raises 503 (user data is never dropped silently) and "drop_oldest" drops the
    oldest rows of that buffer key, counted as runtime_error_count["buffer_dropped"] (for best-effort logs).
    Buffered rows are taken out of the buffer before inserting and put back at the front if the insert fails, so
    concurrent requests never insert the same rows twice or lose rows added during the insert.
    is_trusted skips column, regex and type checks for rows Atom builds itself (API logs). Never set it for
    request data: table and column names are still validated, but values reach Postgres unchecked.
    """
    if not client_postgres and not client_postgres_conn: raise func_api_error(message="postgres client not initialized", status_code=500)
    limit_chunk = 5000
    async def insert_serialized(tbl, serialized_list, connection=None):
        columns = [c for c in serialized_list[0] if re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c)) or (_ for _ in ()).throw(Exception(f"invalid identifier {c}"))]
        cols_sql = ",".join([f'"{c}"' for c in columns])
        if len(serialized_list) == 1:
            placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
            sql = f'INSERT INTO "{tbl}" ({cols_sql}) VALUES ({placeholders}) RETURNING id;'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
            args = [serialized_list[0][c] for c in columns]
            if connection: ids = await connection.fetch(sql, *args)
            elif client_postgres_conn: ids = await client_postgres_conn.fetch(sql, *args)
            else:
                async with client_postgres.acquire() as conn: ids = await conn.fetch(sql, *args)
        else:
            schema = cache_postgres_schema.get(tbl, {})
            col_list = ",".join([f'"{c}"' for c in columns])
            def_list = ",".join([f'"{c}" jsonb' for c in columns])
            cast_parts = []
            for c in columns:
                col_dtype = schema.get(c, {}).get("datatype", "text")
                if "[]" in col_dtype:
                    cast_parts.append(f'(SELECT ARRAY(SELECT jsonb_array_elements_text("{c}")))::{col_dtype}')
                elif "jsonb" in col_dtype:
                    cast_parts.append(f'"{c}"::{col_dtype}')
                else:
                    cast_parts.append(f'("{c}"->>0)::{col_dtype}')
            cast_list = ",".join(cast_parts)
            all_ids = []
            async def _execute_bulk(connection):
                async def insert_chunks():
                    for i in range(0, len(serialized_list), limit_chunk):
                        batch = serialized_list[i : i + limit_chunk]
                        sql = f'INSERT INTO "{tbl}" ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
                        ids_batch = await connection.fetch(sql, orjson.dumps(batch, default=str).decode('utf-8'))
                        all_ids.extend([dict(r) for r in ids_batch])
                # one INSERT is all-or-nothing by itself; a transaction only when several chunks must succeed together and none is open yet
                if len(serialized_list) > limit_chunk and not connection.is_in_transaction():
                    async with connection.transaction(): await insert_chunks()
                else: await insert_chunks()
            if connection:
                await _execute_bulk(connection)
            elif client_postgres_conn:
                await _execute_bulk(client_postgres_conn)
            else:
                async with client_postgres.acquire() as conn:
                    await _execute_bulk(conn)
            ids = all_ids
        return [r["id"] for r in ids] if ids and "id" in ids[0] else "created"
    def buffer_restore(key, items):
        buffer_postgres[key] = items + buffer_postgres.get(key, [])
    async def serialize_batches():
        for i in range(0, len(obj_list), limit_chunk):
            batch = obj_list[i:i+limit_chunk]
            if is_trusted:
                yield batch
                continue
            await func_regex_check(config_column_regex=config_column_regex, obj_list=batch)
            yield await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=batch, is_base=False if len(batch) > 1 else 1)
    if mode not in ("now", "buffer", "flush"): raise Exception(f"invalid mode: {mode}")
    if mode == "flush":
        for key in list(buffer_postgres.keys()):
            items = buffer_postgres.pop(key, None)
            if not items: continue
            try: await insert_serialized(key.split("|")[0], items)
            except Exception:
                buffer_restore(key, items)
                raise
        return "flushed"
    if not obj_list: raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]: raise Exception("object data required")
    obj_list = [dict(item) for item in obj_list]; [item.pop("id", None) for item in obj_list]
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    if cache_postgres_schema is not None and table in cache_postgres_schema and not is_trusted:
        schema = cache_postgres_schema[table]
        for item in obj_list:
            for c in item.keys():
                if c not in schema:
                    raise Exception(f"column '{c}' not found in table: {table}")
    if mode == "buffer":
        result = "buffered"
        async for serialized_list in serialize_batches():
            key = f"{table}|{','.join(sorted(serialized_list[0].keys()))}"
            if buffer_full_mode not in ("reject", "drop_oldest"): raise Exception(f"invalid buffer_full_mode: {buffer_full_mode}")
            excess = sum(len(rows) for rows in buffer_postgres.values()) + len(serialized_list) - buffer_rows_max if buffer_rows_max is not None else 0
            if excess > 0 and buffer_full_mode == "reject": raise func_api_error(message="buffer full, retry later", status_code=503)
            buffer_postgres.setdefault(key, []).extend(serialized_list)
            if excess > 0:
                dropped = min(excess, len(buffer_postgres[key]))
                del buffer_postgres[key][:dropped]
                if runtime_error_count is not None: runtime_error_count["buffer_dropped"] = runtime_error_count.get("buffer_dropped", 0) + dropped
            if len(buffer_postgres[key]) >= buffer_limit:
                items = buffer_postgres.pop(key)
                try: await insert_serialized(table, items)
                except Exception:
                    buffer_restore(key, items)
                    raise
                result = "buffered released"
        return result
    if mode == "now":
        all_ids = []
        async def _execute_now(connection):
            async def insert_batches():
                async for serialized_list in serialize_batches():
                    ids = await insert_serialized(table, serialized_list, connection=connection)
                    if isinstance(ids, list): all_ids.extend(ids)
            # up to limit_chunk rows is one INSERT, all-or-nothing by itself: no BEGIN/COMMIT round trips
            if len(obj_list) > limit_chunk and not connection.is_in_transaction():
                async with connection.transaction(): await insert_batches()
            else: await insert_batches()
            return all_ids if all_ids else "created"
        if client_postgres_conn:
            return await _execute_now(client_postgres_conn)
        async with client_postgres.acquire() as conn:
            return await _execute_now(conn)

async def func_postgres_read_sql(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, cache_postgres_schema: dict, table: str, filter: list, order: str, column: str, config_column_read_blocked: list = None, after: Any = None, is_key_selected: bool = False) -> tuple:
    """The SELECT behind func_postgres_read and func_postgres_read_export, without LIMIT: (sql, values, keys), the table, columns, filters and order checked; values bound as $1, $2.
    The order (default id desc, id added last) comes from func_page_keys; after limits it to the rows after that cursor; is_key_selected adds the order columns a column list leaves out (func_postgres_read removes them again)."""
    blocked_cols = set(config_column_read_blocked) if config_column_read_blocked is not None else {"password"}
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table not in (cache_postgres_schema or {}): raise Exception(f"table '{table}' not found")
    keys = func_page_keys(order=order, columns=cache_postgres_schema[table])
    for key in keys:
        if key["name"] in blocked_cols: raise Exception(f"column '{key['name']}' is restricted from reading")
    column_list = "*"
    if column != "*":
        cols = []
        for c in column.split(","):
            c_strip = c.strip()
            if c_strip in blocked_cols: raise Exception(f"column '{c_strip}' is restricted from reading")
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c_strip)): raise Exception(f"invalid identifier {c_strip}")
            if c_strip not in cache_postgres_schema[table]: raise Exception(f"column '{c_strip}' not found in table: {table}")
            cols.append(c_strip)
        if is_key_selected: cols += [key["name"] for key in keys if key["name"] not in cols]
        column_list = ",".join([f'"{c}"' for c in cols])
    where_statement, values = await func_postgres_where_build(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, filter=filter, prefix="", config_column_read_blocked=config_column_read_blocked)
    after_sql = func_page_after_where(keys=keys, after=after, values=values)
    if after_sql: where_statement = f"WHERE ({where_statement[len('WHERE '):]}) AND {after_sql}" if where_statement else f"WHERE {after_sql}"
    return f'SELECT {column_list} FROM "{table}" {where_statement} ORDER BY {func_page_order_sql(keys=keys)}', values, keys  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n

async def func_postgres_read(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, cache_postgres_schema: dict, config_sql_read_limit_max: int, config_sql_read_relation_fetch_limit_max: int, table: str, filter: list, limit: int, order: str, column: str, relation: list, config_column_read_blocked: list = None, blocked_tables: list = None, after: Any = None, page: int | None = None, config_page_offset_max: int = 10000) -> dict:
    """One page of a table with filters, order and relations: {"obj_list", "after"}. after (the previous page's after) reads the rows after that cursor, the default way;
    page jumps to page N with OFFSET, within config_page_offset_max rows (func_page_offset). The response's after is the cursor of the next page either way, None on the last one (one extra row is read to know)."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    blocked_cols = set(config_column_read_blocked) if config_column_read_blocked is not None else {"password"}
    if limit < 1: raise Exception("query limit must be greater than 0")
    if config_sql_read_limit_max and limit > config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {config_sql_read_limit_max}")
    offset = func_page_offset(page=page, after=after, limit=limit, offset_max=config_page_offset_max)
    sql, values, keys = await func_postgres_read_sql(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, filter=filter, order=order, column=column, config_column_read_blocked=config_column_read_blocked, after=after, is_key_selected=True)
    values.append(limit + 1)
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(f"{sql} LIMIT ${len(values)}{f' OFFSET {offset}' if offset else ''}", *values)    # offset: an int from func_page_offset
        next_after = func_page_after_next(keys=keys, rows=records, limit=limit)
        result_list = [dict(r) for r in records[:limit]]
        added = [key["name"] for key in keys if column != "*" and key["name"] not in [c.strip() for c in column.split(",")]]
        for r in result_list:
            for name in (*blocked_cols, *added): r.pop(name, None)
        if relation and result_list:
            result_list = await func_postgres_relation(client_postgres=client_postgres, client_postgres_conn=conn, obj_list=result_list, relation=relation, config_sql_read_relation_fetch_limit_max=config_sql_read_relation_fetch_limit_max, blocked_tables=blocked_tables, config_column_read_blocked=config_column_read_blocked)
        return {"obj_list": result_list, "after": next_after}

async def func_postgres_update(*, client_postgres: asyncpg.Pool | None, client_postgres_conn: asyncpg.Connection | None, client_password_hasher: PasswordHasher | None, cache_postgres_schema: dict, config_column_regex: dict, table: str, obj_list: list, created_by_id: int, ownership_column: str = "created_by_id") -> Any:
    """Update PostgreSQL records immediately with support for owner validation and dynamic serialization."""
    if not client_postgres and not client_postgres_conn: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not obj_list: raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]: raise Exception("object data required")
    if any(not isinstance(obj, dict) for obj in obj_list): raise Exception("object data invalid")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    if any("id" not in obj for obj in obj_list): raise Exception("missing required field: 'id' for update operation")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(ownership_column)): raise Exception(f"invalid identifier {ownership_column}")
    update_cols = [c for c in obj_list[0] if c != "id" and (re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c)) or (_ for _ in ()).throw(Exception(f"invalid identifier {c}")))]
    if not update_cols: raise Exception("update field required")
    if cache_postgres_schema is not None and table in cache_postgres_schema:
        schema = cache_postgres_schema[table]
        for c in update_cols:
            if c not in schema: raise Exception(f"column '{c}' not found in table: {table}")
    if any(set(obj.keys()) != set(obj_list[0].keys()) for obj in obj_list): raise Exception("object keys mismatch")
    returned_ids = []
    limit_batch = 5000
    # simple column types go through unnest: one array per column joined on id, a straight join with the same SQL for the same columns; other types (json, arrays, PostGIS) use CASE
    column_types = [str(((cache_postgres_schema or {}).get(table) or {}).get(c, {}).get("datatype", "")).lower() for c in ["id", *update_cols]]
    is_unnest = column_types[0] in ("smallint", "integer", "bigint") and all(re.match(r"^(smallint|integer|bigint|real|double precision|boolean|text|uuid|date|numeric(\(\d+(,\d+)?\))?|character( varying)?(\(\d+\))?|(timestamp|time)(\(\d\))? with(out)? time zone)$", t) for t in column_types[1:])
    actual_batch_size = limit_batch if is_unnest else max(1, (limit_batch - (1 if created_by_id is not None else 0)) // ((2 * len(update_cols)) + 1))
    async def _execute_update(connection):
        async def update_batches():
            for i in range(0, len(obj_list), actual_batch_size):
                batch_raw = obj_list[i:i+actual_batch_size]
                await func_regex_check(config_column_regex=config_column_regex, obj_list=batch_raw)
                batch = await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=batch_raw, is_base=True)
                if is_unnest:
                    first = {}
                    for obj in batch: first.setdefault(obj["id"], obj)    # a repeated id keeps its first values, as CASE did
                    arrays = [[obj[col] for obj in first.values()] for col in ["id", *update_cols]]
                    casts = ", ".join(f"${j + 1}::{t}[]" for j, t in enumerate(["bigint", *column_types[1:]]))
                    names = ", ".join(f'"{col}"' for col in ["id", *update_cols])
                    where_clause = 't."id" = v."id"' + (f' AND t."{ownership_column}" = ${len(arrays) + 1}' if created_by_id is not None else "")
                    sql = f'UPDATE "{table}" AS t SET {", ".join(f'"{col}" = v."{col}"' for col in update_cols)} FROM unnest({casts}) AS v({names}) WHERE {where_clause} RETURNING t."id";'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
                    returned_ids.extend([r["id"] for r in (await connection.fetch(sql, *arrays, *([created_by_id] if created_by_id is not None else [])))])
                    continue
                batch_vals, set_clauses = [], []
                for col in update_cols:
                    case_statements = []
                    for obj in batch:
                        batch_vals.extend([obj["id"], obj[col]])
                        case_statements.append(f'WHEN "id"=${len(batch_vals)-1}::bigint THEN ${len(batch_vals)}')
                    set_clauses.append(f'"{col}" = CASE {" ".join(case_statements)} ELSE "{col}" END')
                id_list = [obj["id"] for obj in batch]
                where_clause = f'"id" IN ({",".join(f"${len(batch_vals)+j+1}::bigint" for j in range(len(id_list)))})'
                if created_by_id is not None: where_clause += f' AND "{ownership_column}"=${len(batch_vals)+len(id_list)+1}'
                batch_vals.extend(id_list)
                if created_by_id is not None: batch_vals.append(created_by_id)
                sql = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE {where_clause} RETURNING id;'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
                returned_ids.extend([r["id"] for r in (await connection.fetch(sql, *batch_vals))])
        # one batch is one UPDATE, all-or-nothing by itself: no BEGIN/COMMIT round trips; several batches share one transaction
        if len(obj_list) > actual_batch_size and not connection.is_in_transaction():
            async with connection.transaction(): await update_batches()
        else: await update_batches()

    if client_postgres_conn: await _execute_update(client_postgres_conn)
    else:
        async with client_postgres.acquire() as conn: await _execute_update(conn)
    return returned_ids if returned_ids or len(obj_list) == 1 else "updated"

async def func_postgres_delete(*, client_postgres: asyncpg.Pool | None, client_postgres_conn: asyncpg.Connection | None, cache_postgres_schema: dict = None, table: str, ids: list, created_by_id: int, ownership_column: str = "created_by_id") -> int:
    """Delete records by ID with schema-aware optional ownership restrictions."""
    if not client_postgres and not client_postgres_conn: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    schema = (cache_postgres_schema or {}).get(table, {})
    if schema and "id" not in schema: raise Exception(f"table '{table}' missing id column")
    if not ids or not isinstance(ids, (list, tuple)): raise Exception("ids required")
    id_list = [int(x) for x in ids]
    limit_chunk = 5000
    if created_by_id is not None:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(ownership_column)): raise Exception(f"invalid identifier {ownership_column}")
        if schema and ownership_column not in schema: raise Exception(f"table '{table}' lacks required '{ownership_column}' column")
    async def _execute_delete(connection):
        deleted_count = 0
        async def delete_batches():
            nonlocal deleted_count
            for i in range(0, len(id_list), limit_chunk):
                batch_ids = id_list[i:i+limit_chunk]
                where_clause = '"id" = ANY($1::bigint[])'
                values = [batch_ids]
                if created_by_id is not None:
                    where_clause += f' AND "{ownership_column}"=$2::bigint'
                    values.append(created_by_id)
                sql_delete = f'WITH deleted AS (DELETE FROM "{table}" WHERE {where_clause} RETURNING 1) SELECT COUNT(*) FROM deleted;'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
                deleted_count += await connection.fetchval(sql_delete, *values)
        # up to limit_chunk ids is one DELETE, all-or-nothing by itself; several share one transaction
        if len(id_list) > limit_chunk and not connection.is_in_transaction():
            async with connection.transaction(): await delete_batches()
        else: await delete_batches()
        return deleted_count
    if client_postgres_conn:
        return await _execute_delete(client_postgres_conn)
    async with client_postgres.acquire() as conn:
        return await _execute_delete(conn)
