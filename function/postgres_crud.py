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

async def func_postgres_serialize(*, client_postgres: any, client_password_hasher: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: bool) -> list:
    """Serialize Python objects (JSON, Arrays, Geog) to PostgreSQL compatible formats using schema-aware injection."""
    import orjson
    if table not in cache_postgres_schema: return obj_list
    output_list, schema = [], cache_postgres_schema[table]
    def normalize_dtype(t):
        t = str(t).lower().strip()
        array_alias_map = {
            "_int2": "smallint[]",
            "_int4": "integer[]",
            "_int8": "bigint[]",
            "_float4": "real[]",
            "_float8": "double precision[]",
            "_numeric": "numeric[]",
            "_bool": "boolean[]",
            "_text": "text[]",
            "_varchar": "character varying[]",
            "_bpchar": "character[]",
            "_date": "date[]",
            "_timestamp": "timestamp without time zone[]",
            "_timestamptz": "timestamp with time zone[]",
        }
        return array_alias_map.get(t, t)
    def cast_val(v, t):
        t = normalize_dtype(t)
        vs = str(v).strip()
        if not vs or vs.lower() == "null": return None
        if "geography" in t or "geometry" in t: return v
        if "bool" in t:
            bool_map = {
                "true": True, "1": True, "yes": True, "on": True, "ok": True, "t": True, "y": True,
                "false": False, "0": False, "no": False, "off": False, "f": False, "n": False,
            }
            key = vs.lower()
            if key not in bool_map: raise ValueError(f"invalid boolean value: {v}")
            return bool_map[key]
        if any(x in t for x in ("int", "serial", "bigint")): return int(vs)
        if any(x in t for x in ("numeric", "float", "double", "real")): return float(vs)
        if "timestamp" in t:
            from datetime import datetime
            return datetime.fromisoformat(vs.replace("Z", "+00:00")) if isinstance(v, str) else v
        if "date" in t:
            from datetime import date
            return date.fromisoformat(vs) if isinstance(v, str) else v
        return v
    def array_val(v, base_dtype):
        if isinstance(v, (list, tuple)): return [cast_val(x, base_dtype) for x in v]
        v_arr = str(v).strip().strip("{}")
        return [cast_val(x.strip(), base_dtype) for x in v_arr.split(",")] if v_arr else []
    def serialize_val(val, dtype):
        dtype = normalize_dtype(dtype)
        is_json, is_array = "json" in dtype, "[]" in dtype or "array" in dtype
        base_dtype = dtype.replace("[]", "").replace("array", "").strip()
        if is_json:
            if is_base:
                return orjson.dumps(val).decode("utf-8") if not isinstance(val, str) else val
            if isinstance(val, str):
                val_str = val.strip()
                return orjson.loads(val_str) if val_str.startswith(("{", "[")) else val_str
            return val
        if is_array:
            return array_val(val, base_dtype)
        if not is_base and "bytea" in dtype:
            return val.encode() if isinstance(val, str) else val
        return cast_val(val, dtype)
    for item in obj_list:
        new_item = {}
        for col, val in item.items():
            if table == "users" and col == "password" and val:
                val = client_password_hasher.hash(str(val))
            if col not in schema:
                if col == "id":
                    new_item[col] = val
                    continue
                raise Exception(f"column '{col}' does not exist in table '{table}'")
            if val is None:
                new_item[col] = val
                continue
            new_item[col] = serialize_val(val, schema[col]["datatype"])
        output_list.append(new_item)
    return output_list

async def func_postgres_where_build(*, client_postgres: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table: str, filter: list, prefix: str = "", config_column_read_blocked: list = None) -> tuple:
    """Build a SQL WHERE clause with support for recursion, logical operators (_or, _and), flat SQL strings, and explicit operator syntax."""
    import re, orjson
    if not table: raise Exception("table required")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    values = []
    blocked_cols = set(config_column_read_blocked) if config_column_read_blocked is not None else {"password"}
    filter_pattern = r'^((?:"[^"]+")|[a-zA-Z_][a-zA-Z0-9_]*)\s+(is\s+not\s+distinct\s+from|is\s+distinct\s+from|is\s+not|not\s+in|>=|<=|==|!=|<>|~\*|=|>|<|eq|neq|gt|lt|gte|lte|is|in|between|like|ilike|~|contains|exists|overlap|any|point)\s+(.*)$'
    value_ops = {"=":"=","==":"=","eq":"=","!=":"!=","<>":"!=","neq":"!=","!=": "!=", ">":">","gt":">","<":"<","lt":"<",">=":">=","gte":">=","<=":"<=","lte":"<=","is":"IS","is not":"IS NOT","in":"IN","not in":"NOT IN","between":"BETWEEN","is distinct from":"IS DISTINCT FROM","is not distinct from":"IS NOT DISTINCT FROM"}
    string_ops = {"like":"LIKE","ilike":"ILIKE","~":"~","~*":"~*"}
    table_schema = cache_postgres_schema.get(table, {})
    def normalize_filter_value(operator, raw_val):
        raw_val = raw_val.strip().strip("'").strip('"').strip("(").strip(")")
        return raw_val.replace(" AND ", "|").replace(",", "|") if operator in ("between", "in", "not in", "overlap", "contains") else raw_val
    def parse_filter_item(item):
        match = re.match(filter_pattern, item.strip(), re.IGNORECASE)
        if not match: return None
        col, operator, raw_val = match.groups()
        operator = operator.lower()
        return {col.strip('"'): f"{operator},{normalize_filter_value(operator, raw_val)}"}
    def parse_filter_list(filter_list):
        converted_filters = {}
        def add_parsed_filter(parsed):
            if not parsed: return
            key = next(iter(parsed))
            if key in converted_filters:
                converted_filters.setdefault("_and", []).append({key: converted_filters.pop(key)})
                converted_filters["_and"].append(parsed)
            elif "_and" in converted_filters:
                converted_filters["_and"].append(parsed)
            else:
                converted_filters.update(parsed)
        for item in filter_list:
            if isinstance(item, dict):
                converted_filters.update(item)
                continue
            if not isinstance(item, str): continue
            or_parts = re.split(r"\s+OR\s+", item, flags=re.IGNORECASE)
            if len(or_parts) > 1:
                sub_or = [parsed for part in or_parts if (parsed := parse_filter_item(part))]
                if sub_or: converted_filters.setdefault("_and", []).append({"_or": sub_or})
                continue
            parsed = parse_filter_item(item)
            add_parsed_filter(parsed)
        return converted_filters
    def bind_next(val):
        bind_idx = len(values) + 1
        values.append(val)
        return bind_idx
    def validate_filter_column(filter_key):
        norm_key = str(filter_key).strip().strip('"')
        if norm_key in blocked_cols: raise Exception(f"filtering on column '{norm_key}' is blocked")
        if filter_key not in table_schema: raise Exception(f"invalid filter column: {filter_key} for table: {table}")
        if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(filter_key)): raise Exception(f"invalid identifier {filter_key}")
    def allowed_operators(datatype, is_json, is_array):
        allowed_ops = list(value_ops.keys())
        if any(x in datatype for x in ("text", "char", "varchar")): allowed_ops += list(string_ops.keys())
        if is_array: allowed_ops += ["contains", "overlap", "any"]
        if is_json: allowed_ops += ["contains", "exists"]
        return allowed_ops
    async def serialize_filter_many(col, val_list, is_base_type=False, schema_override=None):
        obj_list = [{col: None if str(val).lower() == "null" else val} for val in val_list]
        serialized = await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=schema_override or cache_postgres_schema, table=table, obj_list=obj_list, is_base=is_base_type)
        return [item[col] for item in serialized]
    async def serialize_filter(col, val, is_base_type=False):
        return (await serialize_filter_many(col, [val], is_base_type))[0]
    async def serialize_filter_value(filter_key, operator, raw_val, datatype, is_json, is_array):
        if operator == "contains":
            if is_json:
                if "|" in raw_val and not (raw_val.startswith("{") or raw_val.startswith("[")):
                    parts = raw_val.split("|"); k, vr, t = parts[0], parts[1], parts[2].lower() if len(parts) > 2 else "str"
                    v = int(vr) if t == "int" else (vr.lower() == "true" if t == "bool" else float(vr) if t == "float" else vr)
                    return orjson.dumps({k: v}).decode('utf-8')
                try: return orjson.dumps(orjson.loads(raw_val)).decode('utf-8')
                except: return raw_val
            if is_array:
                parts = raw_val.split("|"); elem_type = datatype.replace("[]", "").replace("array", "").replace("int4", "int").replace("_", "").strip()
                fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": elem_type}}}
                return await serialize_filter_many(filter_key, [x.strip() for x in parts], 1, fake_schema)
            return await serialize_filter(filter_key, raw_val)
        if operator == "overlap":
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": datatype.replace("[]", "").replace("array", "").strip()}}}
            return await serialize_filter_many(filter_key, [x.strip() for x in raw_val.split("|")], 1, fake_schema)
        if operator in ("in", "not in", "between"):
            return await serialize_filter_many(filter_key, [x.strip() for x in raw_val.split("|")], 1 if is_array else 0)
        if operator == "any":
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": datatype.replace("[]", "").replace("array", "").strip()}}}
            return (await serialize_filter_many(filter_key, [raw_val], 1, fake_schema))[0]
        return await serialize_filter(filter_key, raw_val, 1 if is_json and operator == "exists" else 0)
    def build_condition_sql(filter_key, operator, serialized_val, is_json):
        if serialized_val is None:
            return f'{prefix}"{filter_key}" {value_ops[operator]} NULL' if operator in ("is", "is not", "is distinct from", "is not distinct from") else None
        if operator == "contains":
            bind_idx = bind_next(serialized_val)
            return f'{prefix}"{filter_key}" @> ${bind_idx}{"::jsonb" if is_json else ""}'
        if operator == "exists":
            bind_idx = bind_next(serialized_val)
            return f'{prefix}"{filter_key}" ? ${bind_idx}'
        if operator == "overlap":
            bind_idx = bind_next(serialized_val)
            return f'{prefix}"{filter_key}" && ${bind_idx}'
        if operator == "any":
            bind_idx = bind_next(serialized_val)
            return f'${bind_idx} = ANY({prefix}"{filter_key}")'
        if operator in ("in", "not in"):
            bind_idx = len(values) + 1
            placeholders = [f"${bind_idx + i}" for i in range(len(serialized_val))]
            values.extend(serialized_val)
            return f'{prefix}"{filter_key}" {value_ops[operator]} ({",".join(placeholders)})'
        if operator == "between":
            bind_idx = len(values) + 1
            values.extend(serialized_val)
            return f'{prefix}"{filter_key}" BETWEEN ${bind_idx} AND ${bind_idx+1}'
        bind_idx = bind_next(serialized_val)
        return f'{prefix}"{filter_key}" {(value_ops.get(operator) or string_ops.get(operator))} ${bind_idx}'
    async def build_filter(filter_obj, is_root=True):
        if not filter_obj: return ""
        if isinstance(filter_obj, list) and is_root:
            filter_obj = parse_filter_list(filter_obj)
        conditions = []
        for filter_key, expression in filter_obj.items():
            if filter_key in ("_or", "_and"):
                if not isinstance(expression, list): raise Exception(f"{filter_key} must be a list of objects")
                inner_conditions = []
                for sub_filter in expression:
                    sub_where = await build_filter(sub_filter, is_root=False)
                    if sub_where: inner_conditions.append(sub_where)
                if inner_conditions:
                    logic_op = " OR " if filter_key == "_or" else " AND "
                    joined_conditions = (f' {logic_op} ').join(inner_conditions)
                    conditions.append(joined_conditions if filter_key == "_and" and len(inner_conditions) == 1 else f"({joined_conditions})")
                continue
            validate_filter_column(filter_key)
            clean_expr = str(expression)
            if clean_expr.lower().startswith("=,"): clean_expr = clean_expr[2:]
            if clean_expr.lower().startswith("point,"):
                _, coords = clean_expr.split(",", 1)
                lon, lat, min_meter, max_meter = [float(x) for x in coords.split("|")]
                bind_idx = len(values) + 1
                conditions.append(f'ST_Distance({prefix}"{filter_key}", ST_Point(${bind_idx}, ${bind_idx+1})::geography) BETWEEN ${bind_idx+2} AND ${bind_idx+3}')
                values.extend([lon, lat, min_meter, max_meter]); continue
            if "," not in str(expression): raise Exception(f"invalid expression for {filter_key}: {expression}. Expected 'operator,value'")
            datatype = table_schema.get(filter_key, {}).get("datatype", "text").lower()
            is_json, is_array = "json" in datatype, "[]" in datatype or "array" in datatype
            operator, raw_val = [x.strip() for x in expression.split(",", 1)]
            operator = operator.lower()
            if operator not in allowed_operators(datatype, is_json, is_array): raise Exception(f"invalid operator: {operator} for {filter_key}")
            serialized_val = await serialize_filter_value(filter_key, operator, raw_val, datatype, is_json, is_array)
            condition_sql = build_condition_sql(filter_key, operator, serialized_val, is_json)
            if condition_sql: conditions.append(condition_sql)
        prefix_sql = "WHERE " if is_root else ""
        return (prefix_sql + " AND ".join(conditions)) if conditions else ""
    where_sql = await build_filter(filter)
    return where_sql, values

async def func_postgres_relation(*, client_postgres: any, client_postgres_conn: any = None, obj_list: list, relation: list, config_sql_read_relation_fetch_limit_max: int, blocked_tables: list = None, config_column_read_blocked: list = None) -> list:
    """Standardized relationship logic: handles both aggregates (count, sum, etc) and associations (fetching rows) from source to target."""
    if not relation or not obj_list: return obj_list
    import re
    from collections import defaultdict
    blocked_tables_set = set(blocked_tables) if blocked_tables is not None else set()
    blocked_columns = set(config_column_read_blocked) if config_column_read_blocked is not None else {"password"}
    relations = relation if isinstance(relation, (list, tuple)) else [relation]
    for rel_str in relations:
        if not rel_str: continue
        parts = [p.strip() for p in rel_str.split(",", 4)]
        if len(parts) < 5: raise Exception("relation must have 5 parts: source_col,target_table,target_col,op,val")
        source_col, target_table, target_col, op, val = parts
        if target_table in blocked_tables_set: raise Exception(f"relation read disabled for table: {target_table}")
        op_parts = op.split("|")
        op_main = op_parts[0].lower()
        for p in (target_table, op_main):
             if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", p): raise Exception(f"invalid identifier in relation: {p}")
        for p in (source_col, target_col):
             if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", p): raise Exception(f"invalid identifier in relation: {p}")
        if val != "*" and not all(re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", v.strip()) for v in val.split(",")): raise Exception(f"invalid value in relation: {val}")
        if val != "*" and any(v.strip() in blocked_columns for v in val.split(",")): raise Exception("relation contains restricted column")
        if val in blocked_columns: raise Exception("relation contains restricted column")
        if any(source_col not in r for r in obj_list): raise Exception(f"relation source column missing from selected columns: {source_col}")
        source_ids = {r.get(source_col) for r in obj_list if r.get(source_col) is not None}
        if not source_ids: continue
        client = client_postgres_conn or client_postgres
        if op_main in ("count", "sum", "avg", "min", "max"):
            val_sql = "*" if val == "*" else f'"{val}"'
            sql = f'SELECT "{target_col}" AS id, {op_main}({val_sql}) AS value FROM "{target_table}" WHERE "{target_col}" = ANY($1) GROUP BY "{target_col}";'
            rows = await client.fetch(sql, list(source_ids))
            mapping = {str(r["id"]): r["value"] for r in rows}
            for obj in obj_list:
                sid = str(obj.get(source_col))
                obj[f"{target_table}_{op_main}"] = mapping.get(sid, 0 if op_main == "count" else None)
        elif op_main == "fetch":
            if len(op_parts) < 2 or not op_parts[1].isdigit(): raise Exception("explicit limit required in relation fetch (e.g. fetch|10)")
            custom_limit = int(op_parts[1])
            if custom_limit > config_sql_read_relation_fetch_limit_max: raise Exception(f"relation fetch limit {custom_limit} exceeds maximum allowed: {config_sql_read_relation_fetch_limit_max}")
            cols_sql = "*" if val == "*" else ",".join([f'"{v.strip()}"' for v in val.split(",")])
            if val != "*" and "id" not in val.split(",") and target_col != "id": cols_sql += f',"{target_col}"'
            sql = f'SELECT * FROM (SELECT {cols_sql}, "{target_col}" AS relation_id, ROW_NUMBER() OVER(PARTITION BY "{target_col}" ORDER BY id DESC) as rn FROM "{target_table}" WHERE "{target_col}" = ANY($1)) t WHERE rn <= $2'
            rows = await client.fetch(sql, list(source_ids), custom_limit)
            mapping = defaultdict(list)
            for r in rows:
                d = dict(r)
                d.pop("rn", None); rid = str(d.pop("relation_id", None))
                for b_col in blocked_columns:
                    d.pop(b_col, None)
                mapping[rid].append(d)
            for obj in obj_list:
                sid = str(obj.get(source_col))
                if target_col == "id": obj[target_table] = mapping[sid][0] if mapping[sid] else None
                else: obj[target_table] = mapping[sid]
        else: raise Exception(f"invalid operator: {op}")
    return obj_list

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

def func_postgres_mark_read(*, client_postgres: any, table: str, ownership_column: str, user_id: int, ids: list) -> None:
    """Schedule a non-blocking read_at update for fetched objects owned by a user."""
    import asyncio, re
    if not ids: return
    for identifier in (table, ownership_column):
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(identifier)): raise Exception(f"invalid identifier {identifier}")
    read_ids = list(dict.fromkeys(int(obj_id) for obj_id in ids if obj_id is not None))
    if not read_ids: return
    async def update_read_at():
        async with client_postgres.acquire() as conn:
            await conn.execute(f'UPDATE "{table}" SET read_at=now() WHERE "{ownership_column}"=$1 AND "id"=ANY($2::bigint[]) AND read_at IS NULL', user_id, read_ids)
    task = asyncio.create_task(update_read_at())
    task.add_done_callback(lambda t: (t.exception() if not t.cancelled() else None))
    return None
