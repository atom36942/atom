"""Atom postgres sql functions."""

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
        if source_col in blocked_columns or target_col in blocked_columns: raise Exception("relation contains restricted column")
        if "*" in blocked_tables_set or target_table in blocked_tables_set: raise Exception(f"relation read disabled for table: {target_table}")
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
