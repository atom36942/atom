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
    serialized_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=0 if len(obj_list) > 1 else 1) if is_serialize else obj_list
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

async def func_postgres_read(*, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table: str, filter_obj: dict, limit: int, page: int, order: str, column: str, creator_key: any, action_key: any) -> list:
    """Powerful generic PostgreSQL object reader with complex filtering, sorting, pagination, and relation fetching."""
    import re, orjson
    from datetime import datetime
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    order_list = []
    for part in order.split(","):
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
    if column != "*":
        cols = []
        for c in column.split(","):
            c_strip = c.strip()
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c_strip)):
                raise Exception(f"invalid identifier {c_strip}")
            cols.append(c_strip)
        column_list = ",".join(cols)
    filters = {k: v for k, v in filter_obj.items() if k not in ("table", "order", "limit", "page", "column", "creator_key", "action_key")}
    async def serialize_filter(col, val, is_base_type=None):
        is_base_type = is_base_type if is_base_type is not None else 0
        if str(val).lower() == "null":
            return None
        serialized = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=[{col: val}], is_base=is_base_type)
        return serialized[0][col]
    conditions = []
    values = []
    bind_idx = 1
    v_ops = {"=":"=","==":"=","!=":"!=","<>":"<>",">":">","<":"<",">=":">=","<=":"<=","is":"IS","is not":"IS NOT","in":"IN","not in":"NOT IN","between":"BETWEEN","is distinct from":"IS DISTINCT FROM","is not distinct from":"IS NOT DISTINCT FROM"}
    s_ops = {"like":"LIKE","ilike":"ILIKE","~":"~","~*":"~*"}
    for filter_key, expression in filters.items():
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(filter_key)):
            raise Exception(f"invalid identifier {filter_key}")
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
                    res = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=fake_schema, table=table, obj_list=[{filter_key: v}], is_base=1))[0][filter_key]
                    return res
                serialized_val = [(await serialize_element(x.strip())) for x in parts]
            else:
                serialized_val = await serialize_filter(filter_key, raw_val)
        elif operator == "overlap":
            parts = raw_val.split("|")
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: cache_postgres_schema.get(table, {}).get(filter_key, "text").lower().replace("[]", "").replace("array", "").strip()}}
            async def serialize_element(v):
                res = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=fake_schema, table=table, obj_list=[{filter_key: v}], is_base=1))[0][filter_key]
                return res
            serialized_val = [(await serialize_element(x.strip())) for x in parts]
        elif operator in ("in", "not in", "between"):
            serialized_val = [await serialize_filter(filter_key, x.strip(), 1 if is_array else 0) for x in raw_val.split("|")]
        elif operator == "any":
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: cache_postgres_schema.get(table, {}).get(filter_key, "text").lower().replace("[]", "").replace("array", "").strip()}}
            serialized_val = (await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=fake_schema, table=table, obj_list=[{filter_key: raw_val}], is_base=1))[0][filter_key]
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

async def func_postgres_update(*, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table: str, obj_list: list, is_serialize: int, created_by_id: int, is_return_ids: int) -> any:
    """Update PostgreSQL records with support for owner validation, batch processing, and dynamic serialization."""
    limit_batch = 5000
    import re, orjson
    if is_serialize:
        obj_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=1)
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

async def func_postgres_delete(*, client_postgres_pool: any, table: str, ids: any, created_by_id: int) -> str:
    """Delete records by ID with optional ownership and system table restrictions (identifier validated)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    if table == "users":
        raise Exception("users table not allowed")
    ids_str = ""
    if isinstance(ids, str):
        id_list = [str(int(x.strip())) for x in ids.split(",") if x.strip()]
        ids_str = ",".join(id_list)
    elif isinstance(ids, (list, tuple)):
        ids_str = ",".join([str(int(x)) for x in ids])
    delete_query = f"DELETE FROM {table} WHERE id IN ({ids_str}) AND ($1::bigint IS NULL OR created_by_id=$1);"
    if table == "spatial_ref_sys":
        raise Exception("system table protected")
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(delete_query, created_by_id)
    return "ids deleted"
import asyncio, asyncpg, csv, time, os, itertools, sys
from datetime import datetime
