async def func_postgres_serialize(*, client_postgres_pool: any, client_password_hasher: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: int) -> list:
    """Format and validate a list of objects based on PostgreSQL schema, including password hashing, JSON encoding, and type casting."""
    import orjson, re
    from datetime import datetime
    schema = cache_postgres_schema.get(table, {})
    if not schema: return obj_list
    res_list = []
    for obj in obj_list:
        new_obj = {}
        for col, val in obj.items():
            if col not in schema: continue
            dtype = schema[col]["datatype"].lower()
            if val is None or str(val).lower() == "null":
                new_obj[col] = None
                continue
            if col == "password":
                new_obj[col] = client_password_hasher.hash(str(val))
            elif "json" in dtype:
                new_obj[col] = orjson.dumps(val).decode("utf-8") if not isinstance(val, str) else val
            elif "[]" in dtype or "array" in dtype:
                if isinstance(val, str):
                    new_obj[col] = [x.strip() for x in val.split(",")]
                else:
                    new_obj[col] = val
            elif "timestamp" in dtype:
                if isinstance(val, str):
                    try: new_obj[col] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    except: new_obj[col] = val
                else: new_obj[col] = val
            elif "int" in dtype or "serial" in dtype:
                new_obj[col] = int(val)
            elif "bool" in dtype:
                new_obj[col] = bool(val)
            elif "float" in dtype or "numeric" in dtype or "double" in dtype:
                new_obj[col] = float(val)
            else:
                new_obj[col] = str(val)
        if not is_base:
            if "created_at" in schema and "created_at" not in new_obj: new_obj["created_at"] = datetime.now()
            if "updated_at" in schema and "updated_at" not in new_obj: new_obj["updated_at"] = datetime.now()
        res_list.append(new_obj)
    return res_list

async def func_postgres_schema_read(*, client_postgres_pool: any) -> dict:
    """Read full PostgreSQL schema from public namespace, mapping internal data types to a standard dictionary format."""
    query = """
        SELECT table_name, column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        ORDER BY table_name, ordinal_position;
    """
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query)
    schema = {}
    for r in records:
        tbl = r["table_name"]
        if tbl not in schema: schema[tbl] = {}
        schema[tbl][r["column_name"]] = {"datatype": r["data_type"], "is_nullable": r["is_nullable"], "default": r["column_default"]}
    return schema

async def func_postgres_schema_init(*, client_postgres_pool: any, client_password_hasher: any, config_postgres: dict, config_postgres_root_user_password: str) -> str:
    """Initialize PostgreSQL schema from configuration, creating tables and the mandatory root user (id=1)."""
    async with client_postgres_pool.acquire() as conn:
        for table_name, cols in config_postgres.get("table", {}).items():
            col_defs = []
            for col in cols:
                d = f"{col['name']} {col['datatype']}"
                if col.get("is_primary"): d += " PRIMARY KEY"
                if not col.get("is_nullable"): d += " NOT NULL"
                if col.get("default") is not None: d += f" DEFAULT {col['default']}"
                if col.get("is_unique"): d += " UNIQUE"
                col_defs.append(d)
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)});")
        if config_postgres_root_user_password:
            res = await conn.fetchval("SELECT id FROM users WHERE id=1")
            if not res:
                hashed = client_password_hasher.hash(config_postgres_root_user_password)
                await conn.execute("INSERT INTO users (id, role, password, email, is_active) VALUES (1, 1, $1, 'root@atom.com', 1) ON CONFLICT DO NOTHING", hashed)
    return "schema initialized"

async def func_postgres_map_column(*, client_postgres_pool: any, config_sql: str) -> dict:
    """Execute a mapping SQL query and return a dictionary from the first two columns."""
    if not config_sql: return {}
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch(config_sql)
    return {r[0]: r[1] for r in rows}

async def func_postgres_create(*, client_postgres_pool: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, mode: str, table: str, obj_list: list, is_serialize: int, buffer_limit: int, cache_postgres_buffer: dict) -> any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization."""
    import re, orjson
    if mode == "flush":
        for key, buffer_list in list(cache_postgres_buffer.items()):
            if buffer_list:
                tbl = key.split("|")[0] if "|" in key else key
                await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="now", table=tbl, obj_list=buffer_list, is_serialize=0, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=client_postgres_conn)
                cache_postgres_buffer[key] = []
        return "flushed"
    if not obj_list: return None
    serialized_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=0 if len(obj_list) > 1 else 1) if is_serialize else obj_list
    if mode == "buffer":
        key = f"{table}|{','.join(sorted(serialized_list[0].keys()))}"
        cache_postgres_buffer.setdefault(key, []).extend(serialized_list)
        if len(cache_postgres_buffer[key]) >= buffer_limit:
            items = cache_postgres_buffer[key]
            await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="now", table=table, obj_list=items, is_serialize=0, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=client_postgres_conn)
            cache_postgres_buffer[key] = []
            return "buffered released"
        return "buffered"
    if mode == "now":
        columns = []
        for c in serialized_list[0]:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c)): raise Exception(f"invalid identifier {c}")
            columns.append(c)
        if len(serialized_list) == 1:
            placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
            query = f"""INSERT INTO {table} ({",".join(columns)}) VALUES ({placeholders}) RETURNING id"""
            if client_postgres_conn:
                ids = await client_postgres_conn.fetch(query, *serialized_list[0].values())
            else:
                async with client_postgres_pool.acquire() as conn:
                    ids = await conn.fetch(query, *serialized_list[0].values())
        else:
            schema = cache_postgres_schema.get(table, {})
            col_list = ",".join(columns)
            def_list = ",".join([f"{c} jsonb" for c in columns])
            cast_parts = []
            for c in columns:
                col_dtype = schema.get(c, {}).get("datatype", "text")
                if "[]" in col_dtype:
                    cast_parts.append(f"(SELECT ARRAY(SELECT jsonb_array_elements_text({c})))::{col_dtype}")
                elif "jsonb" in col_dtype:
                    cast_parts.append(f"{c}::{col_dtype}")
                else:
                    cast_parts.append(f"({c}->>0)::{col_dtype}")
            cast_list = ",".join(cast_parts)
            all_ids = []
            limit_chunk = 5000
            async def _execute_bulk(connection):
                for i in range(0, len(serialized_list), limit_chunk):
                    batch = serialized_list[i : i + limit_chunk]
                    query = f"INSERT INTO {table} ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id"
                    ids_batch = await connection.fetch(query, orjson.dumps(batch, default=str).decode('utf-8'))
                    all_ids.extend([dict(r) for r in ids_batch])
            if client_postgres_conn:
                await _execute_bulk(client_postgres_conn)
            else:
                async with client_postgres_pool.acquire() as conn:
                    await _execute_bulk(conn)
            ids = all_ids
        return [r["id"] for r in ids] if ids and "id" in ids[0] else "bulk created"
    return "unsupported mode"
    
async def func_postgres_read(*, client_postgres_pool: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table: str, filter_obj: dict, limit: int, page: int, order: str, column: str, creator_key: any, action_key: any) -> list:
    """Powerful generic PostgreSQL object reader with complex filtering, sorting, pagination, and relation fetching."""
    import re, orjson
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    order_list = []
    for part in order.split(","):
        p = part.strip().split()
        if p:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(p[0])): raise Exception(f"invalid identifier {p[0]}")
            col = p[0]
            direction = p[1].upper() if len(p) > 1 and p[1].lower() in ("asc", "desc") else "ASC"
            order_list.append(f"{col} {direction}")
    order_clause = ", ".join(order_list)
    column_list = "*"
    if column != "*":
        cols = []
        for c in column.split(","):
            c_strip = c.strip()
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c_strip)): raise Exception(f"invalid identifier {c_strip}")
            cols.append(c_strip)
        column_list = ",".join(cols)
    filters = {k: v for k, v in filter_obj.items() if k not in ("table", "order", "limit", "page", "column", "creator_key", "action_key")}
    async def serialize_filter(col, val, is_base_type=None):
        is_base_type = is_base_type if is_base_type is not None else 0
        if str(val).lower() == "null":
            return None
        serialized = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=[{col: val}], is_base=is_base_type)
        return serialized[0][col]
    conditions = []
    values = []
    bind_idx = 1
    v_ops = {"=":"=","==":"=","!=":"!=","<>":"<>",">":">","<":"<",">=":">=","<=":"<=","is":"IS","is not":"IS NOT","in":"IN","not in":"NOT IN","between":"BETWEEN","is distinct from":"IS DISTINCT FROM","is not distinct from":"IS NOT DISTINCT FROM"}
    s_ops = {"like":"LIKE","ilike":"ILIKE","~":"~","~*":"~*"}
    for filter_key, expression in filters.items():
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(filter_key)): raise Exception(f"invalid identifier {filter_key}")
        if expression.lower().startswith("point,"):
            _, coords = expression.split(",", 1)
            lon, lat, min_meter, max_meter = [float(x) for x in coords.split("|")]
            conditions.append(f"ST_Distance({filter_key}, ST_Point(${bind_idx}, ${bind_idx+1})::geography) BETWEEN ${bind_idx+2} AND ${bind_idx+3}")
            values.extend([lon, lat, min_meter, max_meter])
            bind_idx += 4
            continue
        datatype = cache_postgres_schema.get(table, {}).get(filter_key, {}).get("datatype", "text").lower()
        is_json = "json" in datatype
        is_array = "[]" in datatype or "array" in datatype
        if "," not in expression: raise Exception(f"invalid format for {filter_key}: {expression}")
        operator, raw_val = expression.split(",", 1)
        operator = operator.strip().lower()
        allowed_ops = list(v_ops.keys())
        if any(x in datatype for x in ("text", "char", "varchar")):
            allowed_ops += list(s_ops.keys())
        if is_array:
            allowed_ops += ["contains", "overlap", "any"]
        if is_json:
            allowed_ops += ["contains", "exists"]
        if operator not in allowed_ops: raise Exception(f"""invalid operator: {operator} for {filter_key}, allowed: {", ".join(allowed_ops)}""")
        serialized_val = None
        if operator == "contains":
            if is_json:
                if "|" in raw_val and not (raw_val.startswith("{") or raw_val.startswith("[")):
                    parts = raw_val.split("|")
                    k = parts[0]
                    vr = parts[1]
                    t = parts[2].lower() if len(parts) > 2 else "str"
                    v = int(vr) if t == "int" else (vr.lower() == "true" if t == "bool" else float(vr) if t == "float" else vr)
                    serialized_val = orjson.dumps({k: v}).decode('utf-8')
                else:
                    try:
                        serialized_val = orjson.dumps(orjson.loads(raw_val)).decode('utf-8')
                    except Exception:
                        serialized_val = raw_val
            elif is_array:
                parts = raw_val.split("|")
                dtype = cache_postgres_schema.get(table, {}).get(filter_key, {}).get("datatype", "text").lower()
                elem_type = dtype.replace("[]", "").replace("array", "").replace("int4", "int").replace("_", "").strip()
                fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": elem_type}}}
                async def serialize_element(v):
                    res = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=fake_schema, table=table, obj_list=[{filter_key: v}], is_base=1))[0][filter_key]
                    return res
                serialized_val = [(await serialize_element(x.strip())) for x in parts]
            else:
                serialized_val = await serialize_filter(filter_key, raw_val)
        elif operator == "overlap":
            parts = raw_val.split("|")
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": cache_postgres_schema.get(table, {}).get(filter_key, {}).get("datatype", "text").lower().replace("[]", "").replace("array", "").strip()}}}
            async def serialize_element(v):
                res = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=fake_schema, table=table, obj_list=[{filter_key: v}], is_base=1))[0][filter_key]
                return res
            serialized_val = [(await serialize_element(x.strip())) for x in parts]
        elif operator in ("in", "not in", "between"):
            serialized_val = [await serialize_filter(filter_key, x.strip(), 1 if is_array else 0) for x in raw_val.split("|")]
        elif operator == "any":
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": cache_postgres_schema.get(table, {}).get(filter_key, {}).get("datatype", "text").lower().replace("[]", "").replace("array", "").strip()}}}
            serialized_val = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=fake_schema, table=table, obj_list=[{filter_key: raw_val}], is_base=1))[0][filter_key]
        else:
            serialized_val = await serialize_filter(filter_key, raw_val, 1 if is_json and operator == "exists" else 0)
        if serialized_val is None:
            if operator not in ("is", "is not", "is distinct from", "is not distinct from"):
                raise Exception(f"null requires is/distinct for {filter_key}")
            conditions.append(f"{filter_key} {v_ops[operator]} NULL")
        elif operator == "contains":
            values.append(serialized_val)
            conditions.append(f"""{filter_key} @> ${bind_idx}{"::jsonb" if is_json else ""}""")
            bind_idx += 1
        elif operator == "exists":
            values.append(serialized_val)
            conditions.append(f"{filter_key} ? ${bind_idx}")
            bind_idx += 1
        elif operator == "overlap":
            values.append(serialized_val)
            conditions.append(f"{filter_key} && ${bind_idx}")
            bind_idx += 1
        elif operator == "any":
            values.append(serialized_val)
            conditions.append(f"${bind_idx} = ANY({filter_key})")
            bind_idx += 1
        elif operator in ("in", "not in"):
            place_holders = [f"${bind_idx + i}" for i in range(len(serialized_val))]
            values.extend(serialized_val)
            conditions.append(f"""{filter_key} {v_ops[operator]} ({",".join(place_holders)})""")
            bind_idx += len(serialized_val)
        elif operator == "between":
            values.extend(serialized_val)
            conditions.append(f"{filter_key} BETWEEN ${bind_idx} AND ${bind_idx+1}")
            bind_idx += 2
        else:
            conditions.append(f"{filter_key} {(v_ops.get(operator) or s_ops.get(operator))} ${bind_idx}")
            values.append(serialized_val)
            bind_idx += 1
    where_statement = ""
    if conditions:
        where_statement = "WHERE " + " AND ".join(conditions)
    final_query = f"SELECT {column_list} FROM {table} {where_statement} ORDER BY {order_clause} LIMIT ${bind_idx} OFFSET ${bind_idx+1}"
    values.extend([limit, (page - 1) * limit])
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(final_query, *values)
        result_list = [dict(r) for r in records]
        if creator_key and result_list:
            keys_to_fetch = creator_key.split(",") if isinstance(creator_key, str) else creator_key
            user_ids = {str(r["created_by_id"]) for r in result_list if r.get("created_by_id")}
            user_map = {}
            if user_ids:
                user_rows = await client_postgres_pool.fetch("SELECT * FROM users WHERE id = ANY($1);", list(map(int, user_ids)))
                user_map = {str(u["id"]): dict(u) for u in user_rows}
            for res_row in result_list:
                uid = str(res_row.get("created_by_id"))
                for k in keys_to_fetch:
                    res_row[f"creator_{k}"] = user_map[uid].get(k) if uid in user_map else None
        if action_key and result_list:
            action_parts = action_key.split(",") if isinstance(action_key, str) else action_key
            target_tbl, action_col, action_op, action_out_col = action_parts
            object_ids = {r.get("id") for r in result_list if r.get("id")}
            action_map = {}
            if object_ids:
                action_query = f"SELECT {action_col} AS id, {action_op}({action_out_col}) AS value FROM {target_tbl} WHERE {action_col} = ANY($1) GROUP BY {action_col};"
                action_rows = await client_postgres_pool.fetch(action_query, list(object_ids))
                action_map = {str(row["id"]): row["value"] for row in action_rows}
            for res_row in result_list:
                obj_id = str(res_row.get("id"))
                default_val = 0 if action_op == "count" else None
                res_row[f"{target_tbl}_{action_op}"] = action_map.get(obj_id, default_val)
        return result_list

async def func_postgres_update(*, client_postgres_pool: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, mode: str, table: str, obj_list: list, is_serialize: int, created_by_id: int, is_return_ids: int, buffer_limit: int, cache_postgres_buffer: dict) -> any:
    """Update PostgreSQL records with support for owner validation, batch processing, buffering, and dynamic serialization."""
    import re
    if mode == "flush":
        for key, buffer_list in list(cache_postgres_buffer.items()):
            if buffer_list:
                tbl = key.split("|")[0] if "|" in key else key
                await func_postgres_update(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="now", table=tbl, obj_list=buffer_list, is_serialize=0, created_by_id=None, is_return_ids=0, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=client_postgres_conn)
                cache_postgres_buffer[key] = []
        return "flushed"
    if not obj_list: return "0 rows updated"
    if is_serialize:
        obj_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=1)
    if mode == "buffer":
        key = f"{table}|{','.join(sorted(obj_list[0].keys()))}"
        cache_postgres_buffer.setdefault(key, []).extend(obj_list)
        if len(cache_postgres_buffer[key]) >= buffer_limit:
            items = cache_postgres_buffer[key]
            await func_postgres_update(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="now", table=table, obj_list=items, is_serialize=0, created_by_id=created_by_id, is_return_ids=is_return_ids, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=client_postgres_conn)
            cache_postgres_buffer[key] = []
            return "buffered released"
        return "buffered"
    if mode == "now":
        limit_batch = 5000
    if any("id" not in obj for obj in obj_list): raise Exception("missing required field: 'id' for update operation")
    update_cols = []
    for c in obj_list[0]:
        if c == "id":
            continue
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c)): raise Exception(f"invalid identifier {c}")
        update_cols.append(c)
    if not update_cols: return "0 rows updated"
    actual_batch_size = min(limit_batch, 65535 // (len(update_cols) + (2 if created_by_id else 1)))
    returned_ids = []
    if len(obj_list) == 1:
        async def _execute_one(conn):
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
            query = f"""UPDATE {table} SET {",".join(f"{c}=${i+1}" for i,c in enumerate(update_cols))} WHERE {where_clause};"""
            status = await conn.execute(query, *params)
            return f"{int(status.split()[-1])} rows updated"
        if client_postgres_conn:
            return await _execute_one(client_postgres_conn)
        async with client_postgres_pool.acquire() as conn:
            return await _execute_one(conn)
    total_updated = 0
    async def _execute_update(connection):
        nonlocal total_updated
        async with connection.transaction():
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
                            case_statements.append(f"WHEN id=${len(batch_vals)-2}::bigint AND created_by_id=${len(batch_vals)-1}::bigint THEN ${len(batch_vals)}")
                        else:
                            case_statements.append(f"WHEN id=${len(batch_vals)-1}::bigint THEN ${len(batch_vals)}")
                    set_clauses.append(f"""{col} = CASE {" ".join(case_statements)} ELSE {col} END""")
                id_list = [obj["id"] for obj in batch]
                where_clause = f"""id IN ({",".join(f"${len(batch_vals)+j+1}::bigint" for j in range(len(id_list)))})"""
                if created_by_id:
                    where_clause += f" AND created_by_id=${len(batch_vals)+len(id_list)+1}"
                batch_vals.extend(id_list)
                if created_by_id:
                    batch_vals.append(created_by_id)
                if is_return_ids == 1:
                    query = f"""UPDATE {table} SET {", ".join(set_clauses)} WHERE {where_clause} RETURNING id;"""
                    returned_ids.extend([r["id"] for r in (await connection.fetch(query, *batch_vals))])
                else:
                    query = f"""UPDATE {table} SET {", ".join(set_clauses)} WHERE {where_clause};"""
                    total_updated += int((await connection.execute(query, *batch_vals)).split()[-1])
    if client_postgres_conn:
        await _execute_update(client_postgres_conn)
    else:
        async with client_postgres_pool.acquire() as conn:
            await _execute_update(conn)
    return returned_ids if is_return_ids == 1 else f"{total_updated} rows updated"

async def func_postgres_delete(*, client_postgres_pool: any, client_postgres_conn: any, table: str, ids: any, created_by_id: int) -> str:
    """Delete records by ID with optional ownership and system table restrictions (identifier validated)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table == "users": raise Exception("users table not allowed")
    if isinstance(ids, str):
        ids_str = ",".join(str(int(x.strip())) for x in ids.split(",") if x.strip())
    elif isinstance(ids, (list, tuple)):
        ids_str = ",".join(str(int(x)) for x in ids)
    else:
        ids_str = ""
    delete_query = f"DELETE FROM {table} WHERE id IN ({ids_str}) AND ($1::bigint IS NULL OR created_by_id=$1);"
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if client_postgres_conn:
        await client_postgres_conn.execute(delete_query, created_by_id)
    else:
        async with client_postgres_pool.acquire() as conn:
            await conn.execute(delete_query, created_by_id)
    return "ids deleted"

def func_postgres_sql_parallel(*, conn_str: str, sql_list: list[str]) -> dict:
    """Execute SQL list in parallel, automatically saturating the database's parallel worker pool."""
    import subprocess,time,sys
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor,as_completed
    t_start = time.time()
    def get_ts(): return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
    if not sql_list:
        print(f"{get_ts()} ⚠️  No SQL statements provided.")
        return "done"
    def print_progress(current, total, prefix=''):
        bar_len = 40
        filled_len = int(bar_len * current // total) if total > 0 else 0
        bar = '█' * filled_len + '-' * (bar_len - filled_len)
        percent = 100 * (current / total) if total > 0 else 0
        sys.stdout.write(f'\r{get_ts()} {prefix} |{bar}| {percent:>.1f}%')
        sys.stdout.flush()
        if current == total: sys.stdout.write('\n')
    def psql_scalar(sql:str)->int:
        p=subprocess.run(["psql",conn_str,"-tA","-v","ON_ERROR_STOP=1","-c",sql],capture_output=True,text=True)
        if p.returncode!=0:raise RuntimeError(p.stderr.strip())
        out=p.stdout.strip()
        return int(out) if out else 0
    try:
        mpw=psql_scalar("SHOW max_parallel_workers;")
        mpg=psql_scalar("SHOW max_parallel_workers_per_gather;")
    except Exception:
        mpw,mpg=0,0
    actual_parallel=min(mpw, 16) if mpw>0 else 8
    setup="SET work_mem='512MB'; SET maintenance_work_mem='1GB'; SET max_parallel_workers_per_gather=4; SET synchronous_commit=OFF;"
    meta = [
        ("🕒", "START TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ("⚙️", "FUNC", "func_postgres_sql_parallel"),
        ("🔗", "CONN_STR", conn_str.split('@')[-1] if '@' in conn_str else conn_str), 
        ("📊", "TOTAL SQL", f"{len(sql_list):,}"),
        ("⚡", "PARALLEL", f"{actual_parallel} workers (Auto-Saturated)"),
        ("🏗️", "WORKERS", f"max={mpw}, per_gather={mpg}"),
        ("📡", "STATUS", "AGGRESSIVE MODE")
    ]
    w_meta_lab = max(len(lab) for ico, lab, val in meta)
    separator_len = 80
    single_width_icons = {"⚙️", "🛠️", "🛡️", "➕", "✅", "⏳", "⚠️", "🏗️", "⚡", "📡"}
    print(f"{'-'*separator_len}")
    for ico, lab, val in meta:
        ico_norm = ico + "\uFE0F" if len(ico) == 1 else ico
        if ico_norm in single_width_icons: ico_norm += " "
        print(f"{ico_norm} {lab:<{w_meta_lab}} : {val}")
    print(f"{'-'*separator_len}")
    def run(sql:str):
        t0=time.time()
        p=subprocess.run(["psql",conn_str,"-v","ON_ERROR_STOP=1","-c",f"{setup} {sql}"],capture_output=True,text=True)
        dt=round(time.time()-t0,2)
        return {"sql":sql,"rc":p.returncode,"out":p.stdout,"err":p.stderr,"time_s":dt}
    results=[]; ok=0; fail=0
    print(f"{get_ts()} ⚡ PHASE 1: Executing SQL List in Parallel...")
    with ThreadPoolExecutor(max_workers=actual_parallel) as ex:
        futures=[ex.submit(run,s) for s in sql_list]
        for idx, f in enumerate(as_completed(futures), 1):
            r=f.result(); results.append(r)
            if r["rc"]==0:
                ok+=1
            else:
                fail+=1
                sys.stdout.write('\n')
                print(f"{get_ts()} ❌ FAIL :: {r['sql']}\n{r['err']}")
            print_progress(idx, len(sql_list), "EXECUTING")
    total_time=round(time.time()-t_start,2)
    h_duration = f"{int(total_time // 3600)}h {int((total_time % 3600) // 60)}m {int(total_time % 60)}s"
    status="success" if fail==0 else ("partial" if ok>0 else "failed")
    meta_final = [
        ("🕒", "START TIME", datetime.fromtimestamp(t_start).strftime('%Y-%m-%d %H:%M:%S')),
        ("⚙️", "FUNC", "func_postgres_sql_parallel"),
        ("📊", "TOTAL SQL", f"{len(sql_list):,}"),
        ("✅", "SUCCESS", f"{ok:,}"),
        ("❌", "FAILED", f"{fail:,}"),
        ("⏳", "DURATION", h_duration),
        ("🏆", "STATUS", status.upper()),
        ("🕒", "END TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ]
    w_meta_f_lab = max(len(lab) for ico, lab, val in meta_final)
    print(f"\n{'-'*separator_len}")
    for ico, lab, val in meta_final:
        ico_norm = ico + "\uFE0F" if len(ico) == 1 else ico
        if ico_norm in single_width_icons: ico_norm += " "
        print(f"{ico_norm} {lab:<{w_meta_f_lab}} : {val}")
    print(f"{'-'*separator_len}\n")
    return "done"

async def func_postgres_csv_ingestion(*, csv_path: str, pg_dsn: str, table: str, crud_mode: str, validation_mode: str, rename_column: list[list] | None, ignore_column: list[str] | None, const_column: list[list] | None):
    """Performs high-performance bulk operations from a CSV to Postgres."""
    import os
    import sys
    import csv
    import time
    import itertools
    import asyncpg
    from datetime import datetime
    csv.field_size_limit(sys.maxsize)
    if crud_mode not in ("create", "update", "delete"): raise ValueError(f"Invalid crud_mode: '{crud_mode}'")
    if validation_mode not in ("strict", "reject", "loose"): raise ValueError(f"Invalid validation_mode: '{validation_mode}'")
    if crud_mode == "delete" and const_column: raise ValueError("'const_column' must be None for 'delete' mode.")
    if crud_mode == "delete" and ignore_column: raise ValueError("'ignore_column' must be None for 'delete' mode.")
    if crud_mode == "update" and ignore_column and "id" in ignore_column: raise ValueError("Cannot ignore 'id' column in 'update' mode.")
    t_start = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_stem = os.path.splitext(os.path.basename(csv_path))[0]
    rej_path = f"tmp/{csv_stem}_rejected_{ts}.csv"
    staging_table = f"staging_sync_{table}"
    valid_consts = [c for c in const_column if isinstance(c, (tuple, list)) and len(c) == 2] if const_column else []
    valid_renames = [r for r in rename_column if isinstance(r, (tuple, list)) and len(r) == 2] if rename_column else []
    c_names, c_vals = [c[0] for c in valid_consts], [c[1] for c in valid_consts]
    rename_map = {old: new for old, new in valid_renames}
    reverse_rename_map = {new: old for old, new in valid_renames}
    conn = await asyncpg.connect(pg_dsn, timeout=60)
    try:
        q = "SELECT column_name, udt_name, is_nullable FROM information_schema.columns WHERE table_name=$1"
        columns_records = await conn.fetch(q, table)
        if not columns_records: raise ValueError(f"Table '{table}' not found")
        col_type_map = {r['column_name']: r['udt_name'] for r in columns_records}
        db_cols_all = [r['column_name'] for r in columns_records]
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header_original = reader.fieldnames or []
            if not csv_header_original: raise Exception("Missing CSV header")
            csv_header = [rename_map.get(col, col) for col in csv_header_original]
            if ignore_column:
                csv_header = [c for c in csv_header if c not in ignore_column]
            if crud_mode in ("update", "delete") and "id" not in csv_header: raise ValueError(f"id column is missing from CSV (required for {crud_mode})")
            itertools.islice(reader, 1)
        def get_csv_val(row_dict, mapped_col_name):
            original_name = reverse_rename_map.get(mapped_col_name, mapped_col_name)
            return row_dict.get(original_name)
        class RowReject(Exception): pass
        def get_converter(col_name):
            t = col_type_map.get(col_name, "text")
            def converter(v):
                v_str = str(v).strip() if v is not None else None
                if not v_str or v_str.lower() in ("","none","null","n/a"):
                    return None
                try:
                    if ("int" in t or "numeric" in t or "real" in t or "double" in t) and not t.startswith('_'):
                        float(v_str)
                    if "bool" in t:
                        v_str = "true" if v_str.lower() in ("true","1","yes","t","y") else "false"
                    if "date" in t or "timestamp" in t:
                        for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y-%m-%d %H:%M:%S","%Y%m%d"):
                            try:
                                dt = datetime.strptime(v_str, fmt)
                                v_str = dt.isoformat()
                                break
                            except:
                                continue
                        else:
                            raise ValueError("Invalid date format")
                except Exception:
                    if validation_mode == "strict": raise ValueError(f"Column '{col_name}' error")
                    if validation_mode == "reject": raise RowReject(col_name)
                    return None
                return v_str
            return converter
        csv_mapped_cols = [c for c in csv_header if c in db_cols_all]
        valid_c_names = [c for c in c_names if c in db_cols_all and c not in csv_mapped_cols]
        if crud_mode == "delete":
            final_cols = ["id"] if "id" in csv_mapped_cols else []
        elif crud_mode == "update":
            final_cols = ["id"] + [c for c in csv_mapped_cols if c != "id"] + valid_c_names
        else:
            final_cols = csv_mapped_cols + valid_c_names
        col_plan = [get_converter(c) for c in final_cols]
        tracker = {"rejected": 0}
        def row_generator(offset=0):
            with open(csv_path, newline='', encoding='utf-8') as f_ingest:
                ingest_reader = csv.DictReader(f_ingest)
                items = itertools.islice(ingest_reader, offset, None)
                f_rej = None
                try:
                    for row in items:
                        try:
                            line = []
                            for plan, col in zip(col_plan, final_cols):
                                if col in valid_c_names:
                                    line.append(plan(c_vals[c_names.index(col)]))
                                else:
                                    line.append(plan(get_csv_val(row, col)))
                            yield tuple(line)
                        except RowReject:
                            tracker["rejected"] += 1
                            if validation_mode == "reject":
                                if not f_rej:
                                    os.makedirs("tmp", exist_ok=True)
                                    f_rej = open(rej_path,"w",encoding='utf-8')
                                    csv.writer(f_rej).writerow(csv_header_original)
                                csv.writer(f_rej).writerow(row.values())
                finally:
                    if f_rej:
                        f_rej.close()
        staging_cols_sql = ", ".join([f'"{c}" TEXT' for c in final_cols])
        await conn.execute(f'DROP TABLE IF EXISTS "{staging_table}"')
        await conn.execute(f'CREATE TEMP TABLE "{staging_table}" ({staging_cols_sql})')
        await conn.copy_records_to_table(staging_table, records=row_generator(0), columns=final_cols, timeout=28800)
        async with conn.transaction():
            def get_cast(cl):
                ct = col_type_map[cl]
                if ct in ("int2", "int4", "int8"):
                    return f'ROUND(s."{cl}"::numeric)::{ct}'
                return f's."{cl}"::{ct}'
            if crud_mode == "delete":
                await conn.execute(f'DELETE FROM "{table}" m USING "{staging_table}" s WHERE m."id" = {get_cast("id")}')
            elif crud_mode == "create":
                c_sql = ", ".join([f'"{c}"' for c in final_cols])
                ct_sql = ", ".join([get_cast(c) for c in final_cols])
                await conn.execute(f'INSERT INTO "{table}" ({c_sql}) SELECT {ct_sql} FROM "{staging_table}" s')
            else:
                s_sql = ", ".join([f'"{c}" = {get_cast(c)}' for c in [x for x in final_cols if x != "id"]])
                await conn.execute(f'UPDATE "{table}" m SET {s_sql} FROM "{staging_table}" s WHERE m."id" = {get_cast("id")}')
            await conn.execute(f'DROP TABLE IF EXISTS "{staging_table}"')
        return "done"
    finally:
        await conn.close()
