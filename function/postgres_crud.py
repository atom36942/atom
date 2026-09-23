"""Atom postgres crud functions."""

async def func_postgres_table_column_groupby_read(*, app_state: any, client_postgres: any, cache_postgres_schema: dict, table: str, col: any, limit: int, page: int, agg: str = "count", agg_col: str = "*", order: str = "count desc", filter: list = None) -> dict:
    """Executes a PostgreSQL GROUP BY query dynamically across single or multiple columns and returns flat paginated results."""
    if not client_postgres: raise Exception("postgres client not initialized")
    import re
    if limit < 1: raise Exception("query limit must be greater than 0")
    if page < 1: raise Exception("page must be greater than 0")
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    if table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    cols = [col] if isinstance(col, str) else list(col or [])
    if not cols: raise Exception("at least one column must be specified")
    blocked_cols = set(getattr(app_state, "config_column_read_blocked", [])) | {"password"}
    for c in cols:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c)): raise Exception(f"invalid identifier: {c}")
        if c in blocked_cols: raise Exception(f"reading column '{c}' is blocked")
        if c not in cache_postgres_schema[table]: raise Exception(f"column '{c}' not found in table: {table}")
    agg = (agg or "count").lower()
    if agg not in ["count", "sum", "avg", "min", "max"]: raise Exception(f"unsupported agg: {agg}")
    if agg_col != "*":
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(agg_col)): raise Exception("invalid aggregate column")
        if agg_col in blocked_cols: raise Exception(f"reading column '{agg_col}' is blocked")
        if agg_col not in cache_postgres_schema[table]: raise Exception(f"column '{agg_col}' not found in table: {table}")
    where_clause, values = await app_state.func_postgres_where_build(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, filter=filter or [], prefix="x.", config_column_read_blocked=getattr(app_state, "config_column_read_blocked", None))
    select_exprs, group_exprs, unnest_clauses = [], [], []
    for c in cols:
        dt = cache_postgres_schema.get(table, {}).get(c, {}).get("datatype", "text").lower()
        is_array = "[]" in dt or "array" in dt
        if is_array:
            alias_c = f"{c}_item"
            unnest_clauses.append(f'CROSS JOIN LATERAL unnest(x."{c}") "{alias_c}"')
            select_exprs.append(f'"{alias_c}" AS "{c}"')
            group_exprs.append(f'"{alias_c}"')
        else:
            select_exprs.append(f'x."{c}" AS "{c}"')
            group_exprs.append(f'x."{c}"')
    agg_field = "count" if agg == "count" and agg_col == "*" else (f"{agg}_{agg_col}" if agg_col != "*" else agg)
    agg_col_sql = f'x."{agg_col}"' if agg_col != "*" else "*"
    select_exprs.append(f'{agg.upper()}({agg_col_sql}) AS "{agg_field}"')
    order = (order or "count desc").strip()
    order_lower = order.lower()
    if "count" in order_lower or agg in order_lower:
        order_dir = "DESC" if "desc" in order_lower else "ASC"
        order_sql = f'"{agg_field}" {order_dir}'
    elif "item desc" in order_lower or "item asc" in order_lower:
        order_dir = "DESC" if "desc" in order_lower else "ASC"
        order_sql = f'{group_exprs[0]} {order_dir}'
    else:
        parts = order.split()
        order_col_name = parts[0]
        order_dir = parts[1].upper() if len(parts) > 1 and parts[1].lower() in ("asc", "desc") else "ASC"
        if order_col_name in cols:
            dt = cache_postgres_schema.get(table, {}).get(order_col_name, {}).get("datatype", "text").lower()
            order_sql = f'"{order_col_name}_item" {order_dir}' if ("[]" in dt or "array" in dt) else f'x."{order_col_name}" {order_dir}'
        else:
            order_sql = f'"{agg_field}" DESC'
    order_sql = f'{order_sql}, {", ".join(group_exprs)}'
    select_sql = ", ".join(select_exprs)
    group_sql = ", ".join(group_exprs)
    source_sql = f' {" ".join(unnest_clauses)}' if unnest_clauses else ""
    bind_idx = len(values) + 1
    sql = f'SELECT {select_sql} FROM "{table}" x{source_sql} {where_clause} GROUP BY {group_sql} ORDER BY {order_sql} LIMIT ${bind_idx} OFFSET ${bind_idx + 1}'
    values.extend([limit + 1, (page - 1) * limit])
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    ol = [dict(row) for row in rows]
    return {"obj_list": ol[:limit], "has_next_page": len(ol) > limit}

async def func_postgres_table_column_distinct_read(*, app_state: any, client_postgres: any, cache_postgres_schema: dict, table: str, col: str, limit: int, page: int, order: str = "item asc", filter: list = None) -> dict:
    """Read paginated distinct values for a single column."""
    if not client_postgres: raise Exception("postgres client not initialized")
    import re
    if limit < 1: raise Exception("query limit must be greater than 0")
    if page < 1: raise Exception("page must be greater than 0")
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    if table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    blocked_cols = set(getattr(app_state, "config_column_read_blocked", [])) | {"password"}
    if col in blocked_cols: raise Exception(f"reading column '{col}' is blocked")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(col)): raise Exception(f"invalid identifier: {col}")
    if col not in cache_postgres_schema[table]: raise Exception(f"column '{col}' not found in table: {table}")
    where_clause, values = await app_state.func_postgres_where_build(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, filter=filter or [], prefix="x.", config_column_read_blocked=getattr(app_state, "config_column_read_blocked", None))
    datatype = cache_postgres_schema[table][col].get("datatype", "text").lower()
    is_array = "[]" in datatype or "array" in datatype
    q_col = f'"{col}"'
    order_direction = "DESC" if "desc" in (order or "").lower() else "ASC"
    bind_idx = len(values) + 1
    source_sql = f'CROSS JOIN LATERAL unnest(x.{q_col}) item_col' if is_array else ""
    item_sql = "item_col" if is_array else f'x.{q_col}'
    sql = f'SELECT DISTINCT {item_sql} AS item FROM "{table}" x {source_sql} {where_clause} ORDER BY item {order_direction} LIMIT ${bind_idx} OFFSET ${bind_idx + 1}'
    values.extend([limit + 1, (page - 1) * limit])
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    items = [row["item"] for row in rows]
    return {"item_list": items[:limit], "has_next_page": len(items) > limit}

async def func_postgres_create(*, client_postgres: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, func_regex_check: callable, cache_postgres_schema: dict, cache_postgres_buffer: dict, config_column_regex: dict, buffer_limit: int, mode: str, table: str, obj_list: list) -> any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization."""
    if not client_postgres and not client_postgres_conn: raise Exception("postgres client not initialized")
    import re, orjson
    limit_chunk = 5000
    async def insert_serialized(tbl, serialized_list, connection=None):
        columns = [c for c in serialized_list[0] if re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c)) or (_ for _ in ()).throw(Exception(f"invalid identifier {c}"))]
        cols_sql = ",".join([f'"{c}"' for c in columns])
        if len(serialized_list) == 1:
            placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
            sql = f'INSERT INTO "{tbl}" ({cols_sql}) VALUES ({placeholders}) RETURNING id;'
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
                async with connection.transaction():
                    for i in range(0, len(serialized_list), limit_chunk):
                        batch = serialized_list[i : i + limit_chunk]
                        sql = f'INSERT INTO "{tbl}" ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id'
                        ids_batch = await connection.fetch(sql, orjson.dumps(batch, default=str).decode('utf-8'))
                        all_ids.extend([dict(r) for r in ids_batch])
            if connection:
                await _execute_bulk(connection)
            elif client_postgres_conn:
                await _execute_bulk(client_postgres_conn)
            else:
                async with client_postgres.acquire() as conn:
                    await _execute_bulk(conn)
            ids = all_ids
        return [r["id"] for r in ids] if ids and "id" in ids[0] else "created"
    async def serialize_batches():
        for i in range(0, len(obj_list), limit_chunk):
            batch = obj_list[i:i+limit_chunk]
            await func_regex_check(config_column_regex=config_column_regex, obj_list=batch)
            yield await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=batch, is_base=False if len(batch) > 1 else 1)
    if mode not in ("now", "buffer", "flush"): raise Exception(f"invalid mode: {mode}")
    if mode == "flush":
        for key, buffer_list in list(cache_postgres_buffer.items()):
            if buffer_list:
                parts = key.split("|")
                tbl = parts[0]
                await insert_serialized(tbl, buffer_list)
                cache_postgres_buffer[key] = []
        return "flushed"
    if not obj_list: raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]: raise Exception("object data required")
    obj_list = [dict(item) for item in obj_list]; [item.pop("id", None) for item in obj_list]
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    if cache_postgres_schema is not None and table in cache_postgres_schema:
        schema = cache_postgres_schema[table]
        for item in obj_list:
            for c in item.keys():
                if c not in schema:
                    raise Exception(f"column '{c}' not found in table: {table}")
    if mode == "buffer":
        result = "buffered"
        async for serialized_list in serialize_batches():
            key = f"{table}|{','.join(sorted(serialized_list[0].keys()))}"
            cache_postgres_buffer.setdefault(key, []).extend(serialized_list)
            if len(cache_postgres_buffer[key]) >= buffer_limit:
                items = cache_postgres_buffer[key]
                await insert_serialized(table, items)
                cache_postgres_buffer[key] = []
                result = "buffered released"
        return result
    if mode == "now":
        all_ids = []
        async def _execute_now(connection):
            async with connection.transaction():
                async for serialized_list in serialize_batches():
                    ids = await insert_serialized(table, serialized_list, connection=connection)
                    if isinstance(ids, list): all_ids.extend(ids)
            return all_ids if all_ids else "created"
        if client_postgres_conn:
            return await _execute_now(client_postgres_conn)
        async with client_postgres.acquire() as conn:
            return await _execute_now(conn)

async def func_postgres_read(*, client_postgres: any, client_password_hasher: any, func_postgres_serialize: callable, func_postgres_where_build: callable, func_postgres_relation: callable, cache_postgres_schema: dict, config_sql_read_limit_max: int, config_sql_read_relation_fetch_limit_max: int, table: str, filter: list, limit: int, page: int, order: str, column: str, relation: list, config_column_read_blocked: list = None, blocked_tables: list = None) -> list:
    """Powerful generic PostgreSQL object reader with complex filtering, sorting, pagination, and relation fetching."""
    if not client_postgres: raise Exception("postgres client not initialized")
    import re
    blocked_cols = set(config_column_read_blocked) if config_column_read_blocked is not None else {"password"}
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    if limit < 1: raise Exception("query limit must be greater than 0")
    if page < 1: raise Exception("query page must be greater than 0")
    if config_sql_read_limit_max and limit > config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {config_sql_read_limit_max}")
    order = str(order or "").strip() or "id desc"
    order_list = []
    for part in order.split(","):
        p = part.strip().split()
        if p:
            # Allow alphanumeric, underscores, and spaces (for quoted identifiers)
            if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(p[0])): raise Exception(f"invalid identifier {p[0]}")
            col = p[0]
            direction = p[1].upper() if len(p) > 1 and p[1].lower() in ("asc", "desc") else "ASC"
            order_list.append(f'"{col}" {direction}')
    order_clause = ", ".join(order_list)
    if "id" in cache_postgres_schema.get(table, {}) and not any(part.split()[0].strip('"') == "id" for part in order_list):
        order_clause = f'{order_clause}, "id" DESC'
    column_list = "*"
    if column != "*":
        cols = []
        for c in column.split(","):
            c_strip = c.strip()
            if c_strip in blocked_cols: raise Exception(f"column '{c_strip}' is restricted from reading")
            if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c_strip)): raise Exception(f"invalid identifier {c_strip}")
            if cache_postgres_schema is not None and table in cache_postgres_schema and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c_strip)):
                if c_strip not in cache_postgres_schema[table]: raise Exception(f"column '{c_strip}' not found in table: {table}")
            cols.append(c_strip)
        column_list = ",".join([f'"{c}"' for c in cols])
    filters = filter
    where_statement, values = await func_postgres_where_build(client_postgres=client_postgres, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, filter=filters, prefix="", config_column_read_blocked=config_column_read_blocked)
    fetch_limit = limit + 1
    bind_idx = len(values) + 1
    sql_select = f'SELECT {column_list} FROM "{table}" {where_statement} ORDER BY {order_clause} LIMIT ${bind_idx} OFFSET ${bind_idx+1}'
    values.extend([fetch_limit, (page - 1) * limit])
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql_select, *values)
        result_list = [dict(r) for r in records]
        if blocked_cols and result_list:
            for r in result_list:
                for b_col in blocked_cols:
                    r.pop(b_col, None)
        if relation and result_list:
            result_list = await func_postgres_relation(client_postgres=client_postgres, client_postgres_conn=conn, obj_list=result_list, relation=relation, config_sql_read_relation_fetch_limit_max=config_sql_read_relation_fetch_limit_max, blocked_tables=blocked_tables, config_column_read_blocked=config_column_read_blocked)
        return result_list

async def func_postgres_update(*, client_postgres: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, func_regex_check: callable, cache_postgres_schema: dict, config_column_regex: dict, table: str, obj_list: list, created_by_id: int, ownership_column: str = "created_by_id") -> any:
    """Update PostgreSQL records immediately with support for owner validation and dynamic serialization."""
    if not client_postgres and not client_postgres_conn: raise Exception("postgres client not initialized")
    import re
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
    actual_batch_size = max(1, (limit_batch - (1 if created_by_id is not None else 0)) // ((2 * len(update_cols)) + 1))
    async def _execute_update(connection):
        async with connection.transaction():
            for i in range(0, len(obj_list), actual_batch_size):
                batch_raw = obj_list[i:i+actual_batch_size]
                await func_regex_check(config_column_regex=config_column_regex, obj_list=batch_raw)
                batch = await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=batch_raw, is_base=True)
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
                sql = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE {where_clause} RETURNING id;'
                returned_ids.extend([r["id"] for r in (await connection.fetch(sql, *batch_vals))])
    if client_postgres_conn: await _execute_update(client_postgres_conn)
    else:
        async with client_postgres.acquire() as conn: await _execute_update(conn)
    return returned_ids if returned_ids or len(obj_list) == 1 else "updated"

async def func_postgres_delete(*, client_postgres: any, client_postgres_conn: any, cache_postgres_schema: dict = None, table: str, ids: list, created_by_id: int, ownership_column: str = "created_by_id") -> int:
    """Delete records by ID with schema-aware optional ownership restrictions."""
    if not client_postgres and not client_postgres_conn: raise Exception("postgres client not initialized")
    import re
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
        async with connection.transaction():
            for i in range(0, len(id_list), limit_chunk):
                batch_ids = id_list[i:i+limit_chunk]
                where_clause = '"id" = ANY($1::bigint[])'
                values = [batch_ids]
                if created_by_id is not None:
                    where_clause += f' AND "{ownership_column}"=$2::bigint'
                    values.append(created_by_id)
                sql_delete = f'WITH deleted AS (DELETE FROM "{table}" WHERE {where_clause} RETURNING 1) SELECT COUNT(*) FROM deleted;'
                deleted_count += await connection.fetchval(sql_delete, *values)
        return deleted_count
    if client_postgres_conn:
        return await _execute_delete(client_postgres_conn)
    else:
        async with client_postgres.acquire() as conn:
            return await _execute_delete(conn)

async def func_postgres_delete_all(*, client_postgres: any, client_postgres_conn: any = None, cache_postgres_schema: dict = None, table: str, ownership_column: str, user_id: int, limit: int = 5000) -> dict:
    """Delete records in a table matching an ownership column for a user in safe batches."""
    if not client_postgres and not client_postgres_conn: raise Exception("postgres client not initialized")
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(ownership_column)): raise Exception(f"invalid identifier {ownership_column}")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    schema = (cache_postgres_schema or {}).get(table, {})
    if schema and ownership_column not in schema: raise Exception(f"table '{table}' lacks required '{ownership_column}' column")
    id_col = '"id"' if (not schema or "id" in schema) else "ctid"
    batch_limit = limit if limit and limit > 0 else 5000
    async def _execute_delete_all(connection):
        sql = f'WITH to_delete AS (SELECT {id_col} FROM "{table}" WHERE "{ownership_column}"=$1 LIMIT $2) DELETE FROM "{table}" WHERE {id_col} IN (SELECT {id_col} FROM to_delete)'
        result = await connection.execute(sql, user_id, batch_limit)
        deleted_count = int(result.rsplit(" ", 1)[-1])
        if deleted_count < batch_limit:
            has_more = False
        else:
            has_more = bool(await connection.fetchval(f'SELECT EXISTS(SELECT 1 FROM "{table}" WHERE "{ownership_column}"=$1 LIMIT 1)', user_id))
        return {"deleted_count": deleted_count, "has_more": has_more, "has_next_page": has_more}
    if client_postgres_conn:
        return await _execute_delete_all(client_postgres_conn)
    else:
        async with client_postgres.acquire() as conn:
            return await _execute_delete_all(conn)
