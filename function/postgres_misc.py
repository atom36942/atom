async def func_postgres_runner(*, client_postgres_pool: any, mode: str, query: str) -> any:
    """Execute raw SQL queries in 'read' or 'write' mode with basic DDL and DELETE protection."""
    import re
    if mode != "read" and mode != "write":
        raise Exception(f"invalid mode: {mode}")
    ql = query.lower().strip()
    if re.search(r"\bdrop\b", ql):
        raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql):
        raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql):
        raise Exception("keyword delete forbidden")
    if mode == "read" and not ql.startswith(("select", "with", "explain", "show", "describe")):
        raise Exception("read mode restricted to select/with/explain/show/describe")
    async with client_postgres_pool.acquire() as conn:
        if "returning" in ql:
            return await conn.fetch(query, timeout=15)
        return await conn.execute(query, timeout=15)
        
async def func_postgres_stream(*, client_postgres_pool: any, query: str) -> any:
    """Stream PostgreSQL query results as a CSV Iterative Response with DDL and DELETE protection."""
    import re
    from fastapi.responses import StreamingResponse
    ql = query.lower().strip()
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
                async for record in conn.cursor(query):
                    if is_first == 1:
                        yield ",".join(record.keys()) + "\n"
                        is_first = 0
                    yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in record.values()]) + "\n"
    return StreamingResponse(generate(), media_type="text/csv")
    
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

async def func_postgres_map_column(*, client_postgres_pool: any, config_sql: str) -> dict:
    """Execute a SQL query and map results into a dictionary, supporting grouping for duplicate keys."""
    import re, orjson
    if not config_sql:
        return {}
    match = re.search(r"select\s+(.*?)\s+from\s", config_sql, flags=re.I | re.S)
    columns = [c.strip() for c in match.group(1).split(",")]
    key_col = columns[0]
    other_cols = columns[1:]
    result_map = {}
    async with client_postgres_pool.acquire() as conn:
        async with conn.transaction():
            async for record in conn.cursor(config_sql, prefetch=5000):
                key = record.get(key_col)
                if len(other_cols) == 1:
                    if other_cols[0] == "*":
                        val = dict(record)
                    else:
                        val = record.get(other_cols[0])
                else:
                    val = {c: record.get(c) for c in other_cols}
                if isinstance(val, str) and val.lstrip().startswith(("{", "[")):
                    try:
                        val = orjson.loads(val)
                    except Exception:
                        pass
                if key not in result_map:
                    result_map[key] = val
                else:
                    if not isinstance(result_map[key], list):
                        result_map[key] = [result_map[key]]
                    result_map[key].append(val)
    return result_map

async def func_postgres_serialize(*, client_postgres_pool: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: int) -> list:
    """Serialize Python objects (JSON, Arrays, Geog) to PostgreSQL compatible formats using schema-aware injection."""
    output_list = []
    import orjson, hashlib
    if table not in cache_postgres_schema:
        return obj_list
    schema = cache_postgres_schema[table]
    for item in obj_list:
        new_item = {}
        for col, val in item.items():
            if table == "users" and col == "password" and val:
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

