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