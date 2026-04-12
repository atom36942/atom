async def func_postgres_runner(*, client_postgres_pool: any, execution_mode: str, sql_query: str) -> any:
    """Execute raw SQL queries in 'read' or 'write' mode with basic DDL and DELETE protection."""
    import re
    if execution_mode != "read" and execution_mode != "write":
        raise Exception(f"invalid execution mode: {execution_mode}")
    ql = sql_query.lower().strip()
    if re.search(r"\bdrop\b", ql):
        raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql):
        raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql):
        raise Exception("keyword delete forbidden")
    if execution_mode == "read" and not ql.startswith(("select", "with", "explain", "show", "describe")):
        raise Exception("read mode restricted to select/with/explain/show/describe")
    async with client_postgres_pool.acquire() as conn:
        if "returning" in ql:
            return await conn.fetch(sql_query, timeout=15)
        return await conn.execute(sql_query, timeout=15)

async def func_postgres_clean(*, client_postgres_pool: any, config_table: dict) -> None:
    """Perform database maintenance by cleaning up expired records based on retention configurations (identifier validated)."""
    import re
    if not config_table:
        return None
    for tbl, cfg in config_table.items():
        if (retention_days := cfg.get("retention_day")) is not None:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(tbl)):
                raise Exception(f"invalid identifier {tbl}")
            table = tbl
            query = f"DELETE FROM {table} WHERE created_at < NOW() - INTERVAL '{retention_days} days';"
            async with client_postgres_pool.acquire() as conn:
                await conn.execute(query)
    return None

async def func_postgres_object_read(*, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table_name: str, query_params: dict, limit: int = 100, page: int = 1, order: str = "id desc") -> list:
    """Powerful generic PostgreSQL object reader with complex filtering, sorting, pagination, and relation fetching."""
    import re, orjson
    from datetime import datetime
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table_name)):
        raise Exception(f"invalid identifier {table_name}")
    table = table_name
    limit = min(max(int(query_params.get("limit") or 100), 1), 500)
    page = max(int(query_params.get("page") or 1), 1)
    order_list = []
    for part in query_params.get("order", "id desc").split(","):
        p = part.strip().split()
        if p:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(p[0])):
                raise Exception(f"invalid identifier {p[0]}")
            col = p[0]
            dir = "ASC"
            if len(p) > 1 and p[1].lower() in ("asc", "desc"):
                dir = p[1].upper()
            order_list.append(f"{col} {dir}")
    order_clause = ", ".join(order_list)
    column_list = "*"
    if query_params.get("column", "*") != "*":
        cols = []
        for c in query_params.get("column").split(","):
            c_strip = c.strip()
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c_strip)):
                raise Exception(f"invalid identifier {c_strip}")
            cols.append(c_strip)
        column_list = ",".join(cols)
    creator_key = query_params.get("creator_key")
    action_key = query_params.get("action_key")
    filters = {k: v for k, v in query_params.items() if k not in ("table", "order", "limit", "page", "column", "creator_key", "action_key")}
    async def serialize_filter(col, val, is_base_type=None):
        is_base_type = is_base_type if is_base_type is not None else 0
        if str(val).lower() == "null":
            return None
        serialized = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table_name=table, obj_list=[{col: val}], is_base=is_base_type)
        return serialized[0][col]
    conditions = []
    values = []
    bind_idx = 1
    v_ops = {"=":"=","==":"=","!=":"!=","<>":"<>",">":">","<":"<",">=":">=","<=":"<=","is":"IS","is not":"IS NOT","in":"IN","not in":"NOT IN","between":"BETWEEN","is distinct from":"IS DISTINCT FROM","is not distinct from":"IS NOT DISTINCT FROM"}
    s_ops = {"like":"LIKE","ilike":"ILIKE","~":"~","~*":"~*"}
    for filter_key, expression in filters.items():
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(filter_key)):
            raise Exception(f"invalid identifier {filter_key}")
        # Spatial filter shortcut
        if expression.lower().startswith("point,"):
            _, coords = expression.split(",", 1)
            lon, lat, min_meter, max_meter = [float(x) for x in coords.split("|")]
            conditions.append(f"ST_Distance({filter_key}, ST_Point(${bind_idx}, ${bind_idx+1})::geography) BETWEEN ${bind_idx+2} AND ${bind_idx+3}")
            values.extend([lon, lat, min_meter, max_meter])
            bind_idx += 4
            continue
        datatype = cache_postgres_schema.get(table, {}).get(filter_key, "text").lower()
        is_json = "json" in datatype
        is_array = "[]" in datatype or "array" in datatype
        if "," not in expression:
            raise Exception(f"invalid format for {filter_key}: {expression}")
        operator, raw_val = expression.split(",", 1)
        operator = operator.strip().lower()
        # Determine allowed operators
        allowed_ops = list(v_ops.keys())
        if any(x in datatype for x in ("text", "char", "varchar")):
            allowed_ops += list(s_ops.keys())
        if is_array:
            allowed_ops += ["contains", "overlap", "any"]
        if is_json:
            allowed_ops += ["contains", "exists"]
        if operator not in allowed_ops:
            raise Exception(f"""invalid operator: {operator} for {filter_key}, allowed: {", ".join(allowed_ops)}""")
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
                dtype = cache_postgres_schema.get(table, {}).get(filter_key, "text").lower()
                elem_type = dtype.replace("[]", "").replace("array", "").replace("int4", "int").replace("_", "").strip()
                fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: elem_type}}
                async def serialize_element(v):
                    res = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=fake_schema, table_name=table, obj_list=[{filter_key: v}], is_base=1))[0][filter_key]
                    return res
                serialized_val = [(await serialize_element(x.strip())) for x in parts]
            else:
                serialized_val = await serialize_filter(filter_key, raw_val)
        elif operator == "overlap":
            parts = raw_val.split("|")
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: cache_postgres_schema.get(table, {}).get(filter_key, "text").lower().replace("[]", "").replace("array", "").strip()}}
            async def serialize_element(v):
                res = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=fake_schema, table_name=table, obj_list=[{filter_key: v}], is_base=1))[0][filter_key]
                return res
            serialized_val = [(await serialize_element(x.strip())) for x in parts]
        elif operator in ("in", "not in", "between"):
            serialized_val = [await serialize_filter(filter_key, x.strip(), 1 if is_array else 0) for x in raw_val.split("|")]
        elif operator == "any":
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: cache_postgres_schema.get(table, {}).get(filter_key, "text").lower().replace("[]", "").replace("array", "").strip()}}
            serialized_val = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=fake_schema, table_name=table, obj_list=[{filter_key: raw_val}], is_base=1))[0][filter_key]
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

async def func_postgres_object_update(*, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table_name: str, obj_list: list, is_serialize: int = 1, created_by_id: int = None, is_return_ids: int = 0) -> any:
    """Update PostgreSQL records with support for owner validation, batch processing, and dynamic serialization."""
    limit_batch = 5000
    import re, orjson
    if is_serialize:
        obj_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table_name=table_name, obj_list=obj_list)
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
                query = f"""UPDATE {table_name} SET {",".join(f"{c}=${i+1}" for i,c in enumerate(update_cols))} WHERE {where_clause} RETURNING id;"""
                records = await conn.fetch(query, *params)
                return [r["id"] for r in records]
            else:
                query = f"""UPDATE {table_name} SET {",".join(f"{c}=${i+1}" for i,c in enumerate(update_cols))} WHERE {where_clause};"""
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
                    query = f"""UPDATE {table_name} SET {", ".join(set_clauses)} WHERE {where_clause} RETURNING id;"""
                    returned_ids.extend([r["id"] for r in (await conn.fetch(query, *batch_vals))])
                else:
                    query = f"""UPDATE {table_name} SET {", ".join(set_clauses)} WHERE {where_clause};"""
                    total_updated += int((await conn.execute(query, *batch_vals)).split()[-1])
            return returned_ids if is_return_ids == 1 else f"{total_updated} rows updated"

async def func_postgres_object_create(*, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, execution_mode: str = "now", table_name: str = "", obj_list: list[dict[str, any]] = [], is_serialize: int = 1, table_buffer_limit: int = 100, cache_postgres_buffer: dict = {}) -> any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization."""
    if execution_mode == "flush":
        for table, buffer_list in list(cache_postgres_buffer.items()):
            if buffer_list:
                await func_postgres_object_create(client_postgres_pool=client_postgres_pool, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, execution_mode="now", table_name=table, obj_list=buffer_list, is_serialize=0, table_buffer_limit=None, cache_postgres_buffer=cache_postgres_buffer)
                cache_postgres_buffer[table] = []
        return "flushed"
    if not obj_list:
        return None
    serialized_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table_name=table_name, obj_list=obj_list) if is_serialize else obj_list
    if execution_mode == "buffer":
        if table_name not in cache_postgres_buffer:
            cache_postgres_buffer[table_name] = []
        cache_postgres_buffer[table_name].extend(serialized_list)
        if len(cache_postgres_buffer[table_name]) >= table_buffer_limit:
            items = cache_postgres_buffer[table_name]
            columns = items[0].keys()
            placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
            query = f"""INSERT INTO {table_name} ({",".join(columns)}) VALUES ({placeholders})"""
            async with client_postgres_pool.acquire() as conn:
                await conn.executemany(query, [tuple(i.values()) for i in items])
            cache_postgres_buffer[table_name] = []
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
        query = f"""INSERT INTO {table_name} ({",".join(columns)}) VALUES ({placeholders}) RETURNING id"""
        async with client_postgres_pool.acquire() as conn:
            ids = await conn.fetch(query, *serialized_list[0].values())
    else:
        import orjson
        schema = cache_postgres_schema.get(table_name, {})
        if not schema:
            schema = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table_name=table_name, obj_list=[]))
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
                query = f"INSERT INTO {table_name} ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id"
                ids_batch = await conn.fetch(query, orjson.dumps(batch, default=str).decode('utf-8'))
                all_ids.extend([dict(r) for r in ids_batch])
        ids = all_ids
    return [r["id"] for r in ids] if ids and "id" in ids[0] else "bulk created"

async def func_postgres_serialize(*, client_postgres_pool: any, cache_postgres_schema: dict, table_name: str, obj_list: list, is_base: int) -> list:
    """Serialize Python objects (JSON, Arrays, Geog) to PostgreSQL compatible formats using schema-aware injection."""
    output_list = []
    import orjson, hashlib
    if table_name not in cache_postgres_schema:
        return obj_list
    schema = cache_postgres_schema[table_name]
    for item in obj_list:
        new_item = {}
        for col, val in item.items():
            if table_name == "users" and col == "password" and val:
                val = hashlib.sha256(str(val).encode()).hexdigest()
            if col not in schema:
                if col == "id":
                    new_item[col] = val
                continue
            if val is None:
                new_item[col] = val
                continue
            dtype = schema[col].lower()
            val_str = str(val).strip()
            base_dtype = schema[col].lower().replace("[]", "").replace("array", "").strip()
            def cast_val(v, t):
                vs = str(v).strip()
                if not vs or vs.lower() == "null":
                    return None
                if any(x in t for x in ("int", "serial", "bigint")):
                    return int(vs)
                if "bool" in t:
                    return 1 if vs.lower() in ("true", "1", "yes", "on", "ok") else 0
                if any(x in t for x in ("numeric", "float", "double")):
                    return float(vs)
                if "timestamp" in t:
                    from datetime import datetime
                    if isinstance(v, str):
                        return datetime.fromisoformat(vs.replace("Z", "+00:00"))
                    return v
                if "date" in t:
                    from datetime import date
                    if isinstance(v, str):
                        return date.fromisoformat(vs)
                    return v
                return v
            if is_base == 1:
                if "json" in dtype:
                    new_item[col] = orjson.dumps(val).decode('utf-8') if not isinstance(val, str) else val
                elif "[]" in dtype or "array" in dtype:
                    v_arr = val_str.strip("{}")
                    arr = val if isinstance(val, (list, tuple)) else ([x.strip() for x in v_arr.split(",")] if v_arr else [])
                    new_item[col] = [cast_val(x, base_dtype) for x in arr]
                else:
                    new_item[col] = cast_val(val, dtype)
            else:
                if "json" in dtype:
                    if isinstance(val, str):
                        new_item[col] = orjson.loads(val_str) if val_str.startswith(("{", "[")) else val_str
                    else:
                        new_item[col] = orjson.dumps(val).decode('utf-8')
                elif "[]" in dtype or "array" in dtype:
                    v_arr = val_str.strip("{}")
                    arr = val if isinstance(val, (list, tuple)) else ([x.strip() for x in v_arr.split(",")] if v_arr else [])
                    new_item[col] = [cast_val(x, base_dtype) for x in arr]
                elif "bytea" in dtype:
                    new_item[col] = val.encode() if isinstance(val, str) else val
                else:
                    new_item[col] = cast_val(val, dtype)
        output_list.append(new_item)
    return output_list

async def func_postgres_stream(*, client_postgres_pool: any, sql_query: str) -> any:
    """Stream PostgreSQL query results as a CSV Iterative Response with DDL and DELETE protection."""
    import re
    from fastapi.responses import StreamingResponse
    ql = sql_query.lower().strip()
    if re.search(r"\bdrop\b", ql):
        raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql):
        raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql):
        raise Exception("keyword delete forbidden")
    if not ql.startswith(("select", "with", "explain", "show", "describe")):
        raise Exception("export restricted to select/with/explain/show/describe")
    async def generate():
        async with client_postgres_pool.acquire() as conn:
            async with conn.transaction():
                is_first = 1
                async for record in conn.cursor(sql_query):
                    if is_first == 1:
                        yield ",".join(record.keys()) + "\n"
                        is_first = 0
                    yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in record.values()]) + "\n"
    return StreamingResponse(generate(), media_type="text/csv")

async def func_postgres_init(*, client_postgres_pool: any, config_postgres: dict) -> str:
    """Initialize PostgreSQL database schema, tables, indexes, constraints, and triggers based on configuration."""
    if not config_postgres:
        raise Exception("config_postgres missing")
    if "table" not in config_postgres:
        raise Exception("config_postgres.table missing")
    control = config_postgres.get("control", {})
    is_ext = control.get("is_extension", 0)
    is_match = control.get("is_column_match", 0)
    bulk_blocked = control.get("table_row_delete_disable_bulk", [])
    table_blocked = control.get("table_row_delete_disable", [])
    is_autovacuum = control.get("is_autovacuum_optimize", 0)
    is_analyze = control.get("is_analyze_init", 0)
    catalog = {"idx": set(), "uni": set(), "chk": set(), "tg": set()}
    for table_name, column_configs in config_postgres["table"].items():
        column_names = [col["name"] for col in column_configs]
        if len(set(column_names)) != len(column_configs):
            raise Exception(f"Duplicate column in {table_name}")
    async with client_postgres_pool.acquire() as conn:
        if is_ext:
            for extension in ("postgis", "pg_trgm", "btree_gin"):
                await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {extension};")
        for table_name, column_configs in config_postgres["table"].items():
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id BIGSERIAL PRIMARY KEY);")
            if is_autovacuum:
                await conn.execute(f"ALTER TABLE {table_name} SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);")
            current_cols = {row[0]: row[1] for row in await conn.fetch("SELECT a.attname, format_type(a.atttypid, a.atttypmod) FROM pg_attribute a JOIN pg_class t ON a.attrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid WHERE t.relname = $1 AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped", table_name)}
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_name not in current_cols:
                    old_name = col_cfg.get("old")
                    if old_name and old_name in current_cols:
                        await conn.execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {col_name}")
                        current_cols[col_name] = current_cols.pop(old_name)
                    else:
                        default_val = f"""DEFAULT {col_cfg["default"]}""" if "default" in col_cfg else ""
                        await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {default_val}")
                        current_cols[col_name] = col_type.split("(")[0].lower()
                else:
                    type_mapping = {"timestamp with time zone": "timestamptz", "character varying": "varchar", "integer": "int", "boolean": "bool"}
                    current_type = type_mapping.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0])
                    target_type = type_mapping.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0])
                    if current_type != target_type:
                        if is_match:
                            await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {col_type} USING {col_name}::{col_type}")
                        else:
                            raise Exception(f"Type mismatch {table_name}.{col_name}: {current_cols[col_name]} vs {col_type}")
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_cfg.get("index"):
                    for index_type in (x.strip() for x in col_cfg["index"].split(",")):
                        idx_name = f"idx_{table_name}_{col_name}_{index_type}"
                        catalog["idx"].add(idx_name)
                        if idx_name not in [r[0] for r in await conn.fetch("SELECT indexname FROM pg_indexes WHERE tablename=$1", table_name)]:
                            ops = "gin_trgm_ops" if index_type == "gin" and "text" in col_type.lower() and "[]" not in col_type.lower() else ""
                            await conn.execute(f"CREATE INDEX {idx_name} ON {table_name} USING {index_type}({col_name} {ops});")
                if "in" in col_cfg:
                    chk_name = f"check_{table_name}_{col_name}_in"
                    catalog["chk"].add(chk_name)
                    await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {chk_name}")
                    await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {chk_name} CHECK ({col_name} IN {col_cfg["in"]});""")
                if col_cfg.get("unique"):
                    for group in col_cfg["unique"].split("|"):
                        unique_cols = [x.strip() for x in group.split(",")]
                        uni_name = f"""unique_{table_name}_{"_".join(unique_cols)}"""
                        catalog["uni"].add(uni_name)
                        await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {uni_name}")
                        await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {uni_name} UNIQUE ({",".join(unique_cols)});""")
            if is_match:
                configured_cols = {cfg["name"] for cfg in column_configs} | {"id"}
                for col_to_drop in set(current_cols.keys()) - configured_cols:
                    await conn.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_to_drop} CASCADE;")
        db_schema_rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
        db_tables = {}
        for row in db_schema_rows:
            db_tables.setdefault(row[0], []).append(row[1])
        users_cols = db_tables.get("users", [])
        if users_cols:
            catalog["tg"].add("trigger_users_root_no_delete")
            await conn.execute("CREATE OR REPLACE FUNCTION func_users_root_no_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; END; $$; DROP TRIGGER IF EXISTS trigger_users_root_no_delete ON users; CREATE TRIGGER trigger_users_root_no_delete BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_users_root_no_delete();")
            if all(c in users_cols for c in ("type", "username", "password", "role", "is_active")):
                root_user_password = control.get("root_user_password", "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3")
                await conn.execute("INSERT INTO users (type, username, password, role, is_active) VALUES (1, 'atom', $1, 1, 1) ON CONFLICT (username, type) DO UPDATE SET password = EXCLUDED.password, role = EXCLUDED.role, is_active = EXCLUDED.is_active;", root_user_password)
            if "password" in users_cols and "log_users_password" in db_tables:
                catalog["tg"].add("trigger_users_password_log")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_password_log() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.password IS DISTINCT FROM NEW.password THEN INSERT INTO log_users_password (user_id, password) VALUES (NEW.id, NEW.password); END IF; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_users_password_log ON users; CREATE TRIGGER trigger_users_password_log AFTER UPDATE ON users FOR EACH ROW EXECUTE FUNCTION func_users_password_log();")
            if control.get("is_users_child_delete_soft", 0) and "is_deleted" in users_cols:
                catalog["tg"].add("trigger_users_soft_delete")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_soft_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; v INTEGER; BEGIN v := (CASE WHEN NEW.is_deleted=1 THEN 1 ELSE NULL END); FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'is_deleted') THEN EXECUTE format('UPDATE %I.%I SET is_deleted = $1 WHERE %I = $2', r.table_schema, r.table_name, r.column_name) USING v, NEW.id; END IF; END LOOP; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_users_soft_delete ON users; CREATE TRIGGER trigger_users_soft_delete AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.is_deleted IS DISTINCT FROM NEW.is_deleted) EXECUTE FUNCTION func_users_soft_delete();")
            if control.get("is_users_child_delete_hard", 0):
                catalog["tg"].add("trigger_users_hard_delete")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_hard_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; BEGIN FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP EXECUTE format('DELETE FROM %I.%I WHERE %I = $1', r.table_schema, r.table_name, r.column_name) USING OLD.id; END LOOP; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_users_hard_delete ON users; CREATE TRIGGER trigger_users_hard_delete AFTER DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_users_hard_delete();")
            if control.get("is_users_delete_disable_role", 0) and "role" in users_cols:
                catalog["tg"].add("trigger_delete_disable_users_role")
                await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_users_role() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL THEN RAISE EXCEPTION 'DELETE not allowed for user with role'; END IF; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_delete_disable_users_role ON users; CREATE TRIGGER trigger_delete_disable_users_role BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_users_role();")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected=1 THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %', TG_TABLE_NAME; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'delete not allowed on %', TG_TABLE_NAME; END; $$;")
        for table, cols in db_tables.items():
            if table == "spatial_ref_sys":
                continue
            if "is_protected" in cols:
                prot_tg_name = f"trigger_delete_disable_is_protected_{table}"
                catalog["tg"].add(prot_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {prot_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {prot_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected();")
            if "updated_at" in cols:
                upd_tg_name = f"trigger_set_updated_at_{table}"
                catalog["tg"].add(upd_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {upd_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {upd_tg_name} BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION func_set_updated_at();")
        # Expand Wildcards
        if table_blocked == ["*"]:
            table_blocked = [t for t in db_tables if t != "spatial_ref_sys"]
        if bulk_blocked and bulk_blocked[0][0] == "*":
            limit = bulk_blocked[0][1]
            bulk_blocked = [[t, limit] for t in db_tables if t != "spatial_ref_sys"]
        for table, limit in bulk_blocked:
            if table in db_tables:
                bulk_tg_name = f"trigger_delete_disable_bulk_{table}"
                catalog["tg"].add(bulk_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {bulk_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {bulk_tg_name} AFTER DELETE ON {table} REFERENCING OLD TABLE AS deleted_rows FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_bulk({limit});")
        for table in table_blocked:
            if table in db_tables:
                tab_tg_name = f"trigger_delete_disable_{table}"
                catalog["tg"].add(tab_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {tab_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {tab_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table();")
        for prefix in ("tg", "uni_chk", "idx"):
            wants = catalog["tg"] if prefix == "tg" else catalog["uni"] | catalog["chk"] if prefix == "uni_chk" else catalog["idx"] | catalog["uni"] | catalog["chk"]
            wants_str = ",".join(f"'{i}'" for i in wants) if wants else "NULL"
            if prefix == "idx":
                selection = "indexname"
                info_tbl = "pg_indexes"
                join_clause = ""
                drop_fmt = "DROP INDEX IF EXISTS %I"
                drop_vars = "record.indexname"
                like_filter = "(indexname LIKE 'idx_%%' OR indexname LIKE 'unique_%%' OR indexname LIKE 'check_%%')"
            elif prefix == "tg":
                selection = "tgname, relname"
                info_tbl = "pg_trigger"
                join_clause = "JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid"
                drop_fmt = "DROP TRIGGER IF EXISTS %I ON %I"
                drop_vars = "record.tgname, record.relname"
                like_filter = "tgname LIKE 'trigger_%%'"
            else:
                selection = "conname, relname"
                info_tbl = "pg_constraint"
                join_clause = "JOIN pg_class ON pg_constraint.conrelid = pg_class.oid"
                drop_fmt = "ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I"
                drop_vars = "record.relname, record.conname"
                like_filter = "(conname LIKE 'unique_%%' OR conname LIKE 'check_%%')"
            await conn.execute(f"""DO $$ DECLARE record RECORD; BEGIN FOR record IN SELECT {selection} FROM {info_tbl} {join_clause} WHERE {like_filter} LOOP IF NOT record.{selection.split(",")[0]} IN ({wants_str}) THEN EXECUTE format('{drop_fmt}', {drop_vars}); END IF; END LOOP; END $$;""")
    await conn.execute("ANALYZE;")
    return "database init done"

async def func_postgres_schema_read(*, client_postgres_pool: any) -> dict:
    """Read full database schema as a simplified dictionary."""
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch("SELECT table_name, column_name, CASE WHEN data_type = 'ARRAY' THEN ltrim(udt_name, '_') || '[]' WHEN data_type = 'USER-DEFINED' THEN udt_name ELSE data_type END AS data_type FROM information_schema.columns WHERE table_schema = 'public'")
        schema = {}
        for r in rows:
            table = r["table_name"]
            col = r["column_name"]
            if table not in schema:
                schema[table] = {}
            schema[table][col] = r["data_type"]
    return schema

# identifier validation now inlined for simplicity
