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