async def func_postgres_create(*, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, mode: str, table: str, obj_list: list, is_serialize: int, buffer_limit: int, cache_postgres_buffer: dict) -> any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization."""
    if mode == "flush":
        for tbl, buffer_list in list(cache_postgres_buffer.items()):
            if buffer_list:
                await func_postgres_create(client_postgres_pool=client_postgres_pool, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="now", table=tbl, obj_list=buffer_list, is_serialize=0, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer)
                cache_postgres_buffer[tbl] = []
        return "flushed"
    if not obj_list:
        return None
    serialized_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=0) if is_serialize else obj_list
    if mode == "buffer":
        if table not in cache_postgres_buffer:
            cache_postgres_buffer[table] = []
        cache_postgres_buffer[table].extend(serialized_list)
        if len(cache_postgres_buffer[table]) >= buffer_limit:
            items = cache_postgres_buffer[table]
            columns = items[0].keys()
            placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
            query = f"""INSERT INTO {table} ({",".join(columns)}) VALUES ({placeholders})"""
            async with client_postgres_pool.acquire() as conn:
                await conn.executemany(query, [tuple(i.values()) for i in items])
            cache_postgres_buffer[table] = []
            return "buffered released"
        return "buffered"
    import re
    cols = []
    for c in serialized_list[0].keys():
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c)):
            raise Exception(f"invalid identifier {c}")
        cols.append(c)
    columns = cols
    if len(serialized_list) == 1:
        placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
        query = f"""INSERT INTO {table} ({",".join(columns)}) VALUES ({placeholders}) RETURNING id"""
        async with client_postgres_pool.acquire() as conn:
            ids = await conn.fetch(query, *serialized_list[0].values())
    else:
        import orjson
        schema = cache_postgres_schema.get(table, {})
        if not schema:
            schema = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=[], is_base=0))
        col_list = ",".join(columns)
        def_list = ",".join([f"{c} jsonb" for c in columns])
        cast_parts = []
        for c in columns:
            col_dtype = schema.get(c, "text")
            if "[]" in col_dtype:
                cast_parts.append(f"(SELECT ARRAY(SELECT jsonb_array_elements_text({c})))::{col_dtype}")
            elif "jsonb" in col_dtype:
                cast_parts.append(f"{c}::{col_dtype}")
            else:
                cast_parts.append(f"({c}->>0)::{col_dtype}")
        cast_list = ",".join(cast_parts)
        all_ids = []
        limit_chunk = 5000
        async with client_postgres_pool.acquire() as conn:
            for i in range(0, len(serialized_list), limit_chunk):
                batch = serialized_list[i : i + limit_chunk]
                query = f"INSERT INTO {table} ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id"
                ids_batch = await conn.fetch(query, orjson.dumps(batch, default=str).decode('utf-8'))
                all_ids.extend([dict(r) for r in ids_batch])
        ids = all_ids
    return [r["id"] for r in ids] if ids and "id" in ids[0] else "bulk created"

async def func_postgres_update(*, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table: str, obj_list: list, is_serialize: int, created_by_id: int, is_return_ids: int) -> any:
    """Update PostgreSQL records with support for owner validation, batch processing, and dynamic serialization."""
    limit_batch = 5000
    import re, orjson
    if is_serialize:
        obj_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=0)
    if not obj_list:
        return "0 rows updated"
    if any("id" not in obj for obj in obj_list):
        raise Exception("missing required field: 'id' for update operation")
    update_cols = []
    for c in obj_list[0]:
        if c != "id":
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c)):
                raise Exception(f"invalid identifier {c}")
            update_cols.append(c)
    if not update_cols:
        return "0 rows updated"
    actual_batch_size = min(limit_batch, 65535 // (len(update_cols) + (2 if created_by_id else 1)))
    async with client_postgres_pool.acquire() as conn:
        if len(obj_list) == 1:
            obj = obj_list[0]
            params = [obj[c] for c in update_cols] + [obj["id"]]
            where_clause = f"id=${len(params)}"
            if created_by_id:
                where_clause += f" AND created_by_id=${len(params)+1}"
                params.append(created_by_id)
            if is_return_ids == 1:
                query = f"""UPDATE {table} SET {",".join(f"{c}=${i+1}" for i,c in enumerate(update_cols))} WHERE {where_clause} RETURNING id;"""
                records = await conn.fetch(query, *params)
                return [r["id"] for r in records]
            else:
                query = f"""UPDATE {table} SET {",".join(f"{c}=${i+1}" for i,c in enumerate(update_cols))} WHERE {where_clause};"""
                status = await conn.execute(query, *params)
                return f"{int(status.split()[-1])} rows updated"
        async with conn.transaction():
            returned_ids = []
            total_updated = 0
            for i in range(0, len(obj_list), actual_batch_size):
                batch = obj_list[i:i+actual_batch_size]
                batch_vals = []
                set_clauses = []
                for col in update_cols:
                    case_statements = []
                    for obj in batch:
                        batch_vals.extend([obj["id"], obj[col]])
                        if created_by_id:
                            batch_vals.append(created_by_id)
                            case_statements.append(f"WHEN id=${len(batch_vals)-2} AND created_by_id=${len(batch_vals)-1} THEN ${len(batch_vals)}")
                        else:
                            case_statements.append(f"WHEN id=${len(batch_vals)-1} THEN ${len(batch_vals)}")
                    set_clauses.append(f"""{col} = CASE {" ".join(case_statements)} ELSE {col} END""")
                id_list = [obj["id"] for obj in batch]
                where_clause = f"""id IN ({",".join(f"${len(batch_vals)+j+1}" for j in range(len(id_list)))})"""
                if created_by_id:
                    where_clause += f" AND created_by_id=${len(batch_vals)+len(id_list)+1}"
                batch_vals.extend(id_list)
                if created_by_id:
                    batch_vals.append(created_by_id)
                if is_return_ids == 1:
                    query = f"""UPDATE {table} SET {", ".join(set_clauses)} WHERE {where_clause} RETURNING id;"""
                    returned_ids.extend([r["id"] for r in (await conn.fetch(query, *batch_vals))])
                else:
                    query = f"""UPDATE {table} SET {", ".join(set_clauses)} WHERE {where_clause};"""
                    total_updated += int((await conn.execute(query, *batch_vals)).split()[-1])
            return returned_ids if is_return_ids == 1 else f"{total_updated} rows updated"

async def func_postgres_delete(*, client_postgres_pool: any, table: str, ids: any, created_by_id: int, config_postgres_ids_delete_limit: int) -> str:
    """Delete records by ID with optional ownership and system table restrictions (identifier validated)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    if table == "users":
        raise Exception("users table not allowed")
    ids_str = ""
    if isinstance(ids, str):
        id_list = [str(int(x.strip())) for x in ids.split(",") if x.strip()]
        if len(id_list) > config_postgres_ids_delete_limit:
            raise Exception("ids length exceeded")
        ids_str = ",".join(id_list)
    elif isinstance(ids, (list, tuple)):
        if len(ids) > config_postgres_ids_delete_limit:
            raise Exception("ids length exceeded")
        ids_str = ",".join([str(int(x)) for x in ids])
    delete_query = f"DELETE FROM {table} WHERE id IN ({ids_str}) AND ($1::bigint IS NULL OR created_by_id=$1);"
    if table == "spatial_ref_sys":
        raise Exception("system table protected")
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(delete_query, created_by_id)
    return "ids deleted"
