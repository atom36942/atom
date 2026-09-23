"""Atom query ai functions."""

async def func_postgres_query_generator_ai(*, client_postgres: any, client_gemini: any, client_openai: any, func_postgres_schema_read_ai: callable, cache_postgres_schema_ai: dict, config_query_runner_read_limit: int, ai: str, question: str) -> dict:
    """Generates and validates safe PostgreSQL SELECT queries using LLM (Gemini/OpenAI) based on the database schema."""
    import re
    import json
    import asyncio
    from google.genai import types
    if ai == "gemini" and not client_gemini: raise Exception("Gemini client not initialized")
    if ai == "openai" and not client_openai: raise Exception("OpenAI client not initialized")
    if not client_postgres: raise Exception("postgres client not initialized")
    question = str(question or "").strip()
    default_limit = 10
    max_limit = config_query_runner_read_limit
    def func_postgres_query_ai_schema_prompt(cache_postgres_schema_ai: dict) -> list:
        output = []
        for table_key, table in sorted((cache_postgres_schema_ai or {}).items()):
            columns = []
            for column_name, column in sorted(table.get("columns", {}).items()):
                columns.append({
                    "name": column_name,
                    "data_type": column.get("data_type"),
                    "is_indexed": bool(column.get("is_indexed")),
                    "index_methods": column.get("index_methods") or [],
                    "is_primary": bool(column.get("is_primary")),
                    "is_unique": bool(column.get("is_unique")),
                })
            output.append({"table": table_key, "relation_type": table.get("relation_type"), "columns": columns})
        return output
    def func_postgres_query_ai_blocked_message(message: str) -> str:
        message = str(message or "").strip()
        if not message or re.search(r"\b(success|successfully|generated|done|created)\b", message, flags=re.IGNORECASE):
            return "Could not generate a safe SQL query. Please mention a valid object. Filters must use indexed columns."
        return message
    def func_postgres_query_ai_clean_identifier(identifier: str) -> str:
        return str(identifier or "").strip().strip('"')
    def func_postgres_query_ai_resolve_table_key(*, value: str, cache_postgres_schema_ai: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not value: return ""
        value = re.sub(r"\s*\.\s*", ".", value)
        lookup = {key.lower(): key for key in (cache_postgres_schema_ai or {}).keys()}
        lookup.update({str(table.get("table_name") or key.split(".")[-1]).lower(): key for key, table in (cache_postgres_schema_ai or {}).items()})
        return lookup.get(value.lower(), "")
    def func_postgres_query_ai_resolve_column_name(*, table_key: str, value: str, cache_postgres_schema_ai: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not table_key or not value: return ""
        columns = (cache_postgres_schema_ai.get(table_key, {}).get("columns") or {})
        lookup = {column.lower(): column for column in columns.keys()}
        return lookup.get(value.lower(), "")
    def func_postgres_query_ai_validate_sql(*, sql: str, default_limit: int, max_limit: int, cache_postgres_schema_ai: dict) -> str:
        sql = str(sql or "").strip().rstrip(";").strip()
        if not sql: raise Exception("AI did not generate SQL.")
        if ";" in sql: raise Exception("AI generated multiple SQL statements.")
        if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("AI generated non-read SQL.")
        known_tables = set((cache_postgres_schema_ai or {}).keys())
        table_matches = re.findall(r'\b(?:from|join)\s+((?:"[^"]+"|\w+)(?:\s*\.\s*(?:"[^"]+"|\w+))?)(?:\s+(?:as\s+)?("[^"]+"|\w+))?', sql, flags=re.IGNORECASE)
        alias_to_table = {}
        for raw_table, raw_alias in table_matches:
            parts = [part.strip().strip('"') for part in raw_table.split(".")]
            table_key = ".".join(parts) if len(parts) > 1 else f"public.{parts[0]}"
            table_key = func_postgres_query_ai_resolve_table_key(value=table_key, cache_postgres_schema_ai=cache_postgres_schema_ai) or table_key
            if table_key not in known_tables: raise Exception(f"AI generated SQL for unknown object: {table_key}")
            alias = raw_alias.strip().strip('"') if raw_alias else parts[-1]
            if alias.lower() in {"where", "join", "on", "group", "order", "limit"}: alias = parts[-1]
            alias_to_table[alias] = table_key
        where_match = re.search(r'\bwhere\b(.+?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)', sql, flags=re.IGNORECASE | re.DOTALL)
        if where_match:
            filters = re.findall(r'(?:(?:"([^"]+)"|(\w+))\s*\.\s*)?(?:"([^"]+)"|(\w+))\s*(=|<>|!=|>=|<=|>|<|\bILIKE\b|\bLIKE\b|\bIN\b|\bBETWEEN\b)', where_match.group(1), flags=re.IGNORECASE)
            for quoted_alias, plain_alias, quoted_col, plain_col, _operator in filters:
                alias = quoted_alias or plain_alias
                column = quoted_col or plain_col
                candidate_tables = [alias_to_table[alias]] if alias and alias in alias_to_table else list(alias_to_table.values())
                column_names = [(table_key, func_postgres_query_ai_resolve_column_name(table_key=table_key, value=column, cache_postgres_schema_ai=cache_postgres_schema_ai)) for table_key in candidate_tables]
                column_matches = [cache_postgres_schema_ai[table_key]["columns"][column_name] for table_key, column_name in column_names if column_name]
                if not column_matches: raise Exception(f"AI generated filter on unknown column: {column}")
                if column_matches and not any(col.get("is_indexed") for col in column_matches): raise Exception(f"AI generated filter on non-indexed column: {column}")
        limit_match = re.search(r'\blimit\s+(\d+)\s*$', sql, flags=re.IGNORECASE)
        if limit_match:
            limit = max(1, min(int(limit_match.group(1)), max_limit))
            sql = re.sub(r'\blimit\s+\d+\s*$', f"LIMIT {limit}", sql, flags=re.IGNORECASE)
        else:
            sql = f"{sql}\nLIMIT {default_limit}"
        return f"{sql.rstrip(';')};"
    cache_postgres_schema_ai = cache_postgres_schema_ai or {}
    if not cache_postgres_schema_ai:
        cache_postgres_schema_ai = await func_postgres_schema_read_ai(client_postgres=client_postgres)
    prompt_schema = func_postgres_query_ai_schema_prompt(cache_postgres_schema_ai)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "sql": {"type": "STRING", "nullable": True},
            "message": {"type": "STRING"},
            "warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
    }
    response_json_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sql": {"type": ["string", "null"]},
            "message": {"type": "string"},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["sql", "message", "warnings"],
    }
    prompt = "\n".join([
        "You generate safe PostgreSQL SELECT SQL for an internal read-only query runner.",
        "",
        "Rules:",
        "1. Return JSON only in the requested schema.",
        "2. If the request cannot be answered safely, return sql null and a short message.",
        "3. Generate only SELECT or WITH SQL.",
        "4. Use only objects and columns from the schema below.",
        f"5. If the user asks for a limit, use that LIMIT up to {max_limit}. If the user does not ask for a limit, use LIMIT {default_limit}.",
        "6. Prefer public schema objects without schema qualification when schema_name is public.",
        "7. Do not drop user intent. If the user asks for a specific value, place, customer, port, country, status, date, or other filter, include that filter.",
        "8. WHERE filters must use indexed columns. If the request requires filtering on a non-indexed column or no matching indexed column is clear, return sql null and ask admin to create an index or mention the indexed column.",
        "9. For text prefix search, use ILIKE 'value%'. Avoid broad contains search unless the column has a gin index.",
        "10. Limit-only SELECT from an explicitly named object is allowed and does not need an indexed filter.",
        "11. Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, or multiple statements.",
        "",
        "User question:",
        question,
        "",
        "Schema:",
        json.dumps(prompt_schema, separators=(",", ":")),
    ])
    if ai == "gemini":
        response = await asyncio.to_thread(
            client_gemini.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=response_schema, temperature=0.1),
        )
        data = json.loads(response.text or "{}")
    else:
        response = await asyncio.to_thread(
            client_openai.responses.create,
            model="gpt-4.1-mini",
            input=prompt,
            text={"format": {"type": "json_schema", "name": "postgres_query_generator", "schema": response_json_schema, "strict": True}},
            temperature=0.1,
        )
        data = json.loads(response.output_text or "{}")
    if not data.get("sql"):
        return {"sql": None, "message": func_postgres_query_ai_blocked_message(data.get("message")), "warnings": data.get("warnings") or []}
    sql = func_postgres_query_ai_validate_sql(sql=data.get("sql"), default_limit=default_limit, max_limit=max_limit, cache_postgres_schema_ai=cache_postgres_schema_ai)
    return {"sql": sql, "message": "SQL generated in the editor. Review before Run or Export.", "warnings": data.get("warnings") or []}

async def func_clickhouse_schema_read_ai(*, client_clickhouse: any) -> dict:
    """Read the current ClickHouse database schema in the compact form used by AI prompts."""
    if not client_clickhouse: raise Exception("clickhouse client not initialized")
    result = await client_clickhouse.query("""
        SELECT database, table, name, type, is_in_primary_key, is_in_sorting_key
        FROM system.columns
        WHERE database = currentDatabase()
        ORDER BY database, table, position
    """)
    schema = {}
    for database, table, name, data_type, is_primary, is_sorting in result.result_rows:
        schema.setdefault(f"{database}.{table}", []).append({"name": name, "data_type": data_type, "is_primary_key": bool(is_primary), "is_sorting_key": bool(is_sorting)})
    return schema

async def func_clickhouse_query_generator_ai(*, client_clickhouse: any, client_gemini: any, client_openai: any, func_clickhouse_schema_read_ai: callable, cache_clickhouse_schema_ai: dict, config_query_runner_read_limit: int, ai: str, question: str) -> dict:
    """Generate schema-aware, read-only ClickHouse SQL with Gemini or OpenAI."""
    import asyncio
    import json
    import re
    from google.genai import types
    if not client_clickhouse: raise Exception("clickhouse client not initialized")
    if ai == "gemini" and not client_gemini: raise Exception("Gemini client not initialized")
    if ai == "openai" and not client_openai: raise Exception("OpenAI client not initialized")
    question = str(question or "").strip()
    default_limit, max_limit = 10, int(config_query_runner_read_limit)
    schema = cache_clickhouse_schema_ai or await func_clickhouse_schema_read_ai(client_clickhouse=client_clickhouse)
    if not schema: raise Exception("clickhouse schema is empty")
    response_schema = {"type": "OBJECT", "properties": {"sql": {"type": "STRING", "nullable": True}, "message": {"type": "STRING"}, "warnings": {"type": "ARRAY", "items": {"type": "STRING"}}}}
    response_json_schema = {"type": "object", "additionalProperties": False, "properties": {"sql": {"type": ["string", "null"]}, "message": {"type": "string"}, "warnings": {"type": "array", "items": {"type": "string"}}}, "required": ["sql", "message", "warnings"]}
    prompt = "\n".join([
        "You generate safe ClickHouse SQL for an internal read-only query runner.",
        "Return JSON only in the requested schema.",
        "Generate exactly one SELECT or WITH statement. Never generate mutations, DDL, settings, or FORMAT clauses.",
        "Use only tables and columns in the supplied schema and use ClickHouse syntax and functions.",
        f"Use LIMIT {default_limit} unless requested; never exceed LIMIT {max_limit}.",
        "Prefer sorting-key or primary-key columns for filters when they satisfy the request.",
        "If the request cannot be answered from the schema, return sql null and explain briefly.",
        f"User question: {question}",
        f"Schema: {json.dumps(schema, separators=(',', ':'))}",
    ])
    if ai == "gemini":
        response = await asyncio.to_thread(client_gemini.models.generate_content, model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=response_schema, temperature=0.1))
        data = json.loads(response.text or "{}")
    else:
        response = await asyncio.to_thread(client_openai.responses.create, model="gpt-4.1-mini", input=prompt, text={"format": {"type": "json_schema", "name": "clickhouse_query_generator", "schema": response_json_schema, "strict": True}}, temperature=0.1)
        data = json.loads(response.output_text or "{}")
    if not data.get("sql"):
        message = str(data.get("message") or "").strip() or "Could not generate a safe ClickHouse query for the supplied schema."
        return {"sql": None, "message": message, "warnings": data.get("warnings") or []}
    sql = str(data["sql"]).strip().rstrip(";").strip()
    if not sql or ";" in sql: raise Exception("AI generated multiple SQL statements.")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("AI generated non-read SQL.")
    if re.search(r"\b(format|into\s+outfile|settings)\b", sql, flags=re.IGNORECASE): raise Exception("AI generated unsupported ClickHouse SQL.")
    known = {name.lower(): name for name in schema}
    known.update({name.split(".", 1)[-1].lower(): name for name in schema})
    for raw_table in re.findall(r"\b(?:from|join)\s+(`[^`]+`|[A-Za-z_]\w*(?:\s*\.\s*(?:`[^`]+`|[A-Za-z_]\w*))?)", sql, flags=re.IGNORECASE):
        table_name = re.sub(r"\s*\.\s*", ".", raw_table.replace("`", ""))
        if table_name.lower() not in known: raise Exception(f"AI generated SQL for unknown object: {table_name}")
    limit_match = re.search(r"\blimit\s+(\d+)\s*$", sql, flags=re.IGNORECASE)
    if limit_match:
        limit = max(1, min(int(limit_match.group(1)), max_limit))
        sql = re.sub(r"\blimit\s+\d+\s*$", f"LIMIT {limit}", sql, flags=re.IGNORECASE)
    else:
        sql = f"{sql}\nLIMIT {default_limit}"
    return {"sql": f"{sql};", "message": "SQL generated in the editor. Review before Run or Export.", "warnings": data.get("warnings") or []}
