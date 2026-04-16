async def func_postgres_bulk_upload_csv(*, csv_path: str, pg_dsn: str, table: str, const_column: list | None):
    """
    Resilient, schema-aware bulk CSV uploader for PostgreSQL.
    Features:
    - Performance: Uses Binary COPY protocol (asyncpg) for max-speed ingestion.
    - Automation: Fetches DB schema dynamically to map columns and types.
    - Security: Mandatory terminal-confirmation phase before ingestion starts.
    - Robustness: Handles dirty data (N/A, NULL strings) and multiple date formats.
    - Strictness: Aborts and reports specific column/row errors for data integrity.
    """
    import asyncio, asyncpg, csv, time
    from datetime import datetime
    t0, log_every = time.time(), 100000
    db_name = pg_dsn.split('/')[-1].split('?')[0]
    print(f"\n{'-'*60}\n🚚 INGESTION DASHBOARD\n{'-'*60}")
    print(f"📁 SOURCE:      {csv_path}\n🎯 DESTINATION: {db_name} -> {table}\n{'-'*60}")
    valid_consts = [c for c in const_column if isinstance(c, (list, tuple)) and len(c) == 2] if const_column else []
    c_names, c_vals = [c[0] for c in valid_consts], [c[1] for c in valid_consts]
    conn = await asyncpg.connect(pg_dsn)
    try:
        print(f"🔗 DB: Successfully connected to {db_name}\n{'-'*60}")
        columns_records = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position", table)
        if not columns_records: raise Exception(f"Table '{table}' not found")
        table_cols = [r['column_name'] for r in columns_records if r['column_name'] != 'id']
        col_type_map = {r['column_name']: r['data_type'] for r in columns_records}
        def infer_type(val):
            if not val or str(val).lower() in ("null", "none", "n/a", ""): return "null"
            v = str(val).strip()
            if v.replace('.', '', 1).isdigit(): return "float" if "." in v else "int"
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y%m%d"):
                try: 
                    datetime.strptime(v, fmt)
                    return "date"
                except: continue
            return "text"
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header = reader.fieldnames or []
            if not csv_header: raise Exception("Empty CSV or missing header")
            first_row = next(reader, {})
            f.seek(0); next(reader) # Reset reader
            print(f"📋 CSV TO DB SCHEMA COMPARISON:\n{'-'*85}\n{'COLUMN NAME':<30} | {'MATCH':^5} | {'CSV DATA TYPE':<15} | {'DB DATA TYPE':<15}\n{'-'*85}")
            for col in csv_header:
                match = "✅" if col in table_cols else "❌"
                csv_t = infer_type(first_row.get(col))
                db_t = col_type_map.get(col, "(missing)")
                print(f"{col[:29]:<30} | {match:^5} | {csv_t:<15} | {db_t:<15}")
            print(f"{'-'*85}")
            matched_cols = [c for c in csv_header if c in table_cols and c not in c_names]
            final_cols = matched_cols + c_names
            if not final_cols: raise Exception("No valid columns to upload")
            ans = input(f"👉 Proceed with upload to '{table}'? (y/N): ")
            if ans.lower() != 'y':
                print(f"\n❌ [CANCELLED] Upload aborted by user.\n")
                return
            print(f"\n⚡ INGESTION IN PROGRESS...")
            def convert_val(val, col_name):
                if val is None or str(val).lower().strip() in ("", "none", "null", "n/a"): return None
                t, v_str = col_type_map.get(col_name, "text"), str(val).strip()
                try:
                    if t in ("integer", "bigint", "smallint"): return int(float(v_str)) if '.' in v_str else int(v_str)
                    if t in ("numeric", "double precision", "real"): return float(v_str)
                    if t == "boolean": return v_str.lower() in ("true", "1", "yes", "t", "y")
                    if "date" in t or "timestamp" in t:
                        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d.%m.%Y", "%Y%m%d"):
                            try:
                                dt = datetime.strptime(v_str, fmt)
                                return dt.date() if t == "date" else dt
                            except: continue
                        raise ValueError(f"No matching format for date/time value '{v_str}'")
                except Exception as e:
                    raise ValueError(f"\n❌ CONVERSION ERROR: Column '{col_name}' expects {t}, received '{val}'.\nDetail: {e}")
                return val
            conv_c_vals = [convert_val(v, n) for n, v in zip(c_names, c_vals)]
            def row_generator():
                count = 0
                for row in reader:
                    line = [convert_val(row.get(c), c) for c in matched_cols]
                    line.extend(conv_c_vals)
                    yield tuple(line)
                    count += 1
                    if count % log_every == 0: print(f"  🔹 PROGRESS: {count:,} rows  |  ⏳ {int(time.time()-t0)}s")
            result = await conn.copy_records_to_table(table, records=row_generator(), columns=final_cols)
            print(f"{'-'*60}\n✅ COMPLETED: {result}\n⏱️  Total Time: {int(time.time()-t0)}s\n{'-'*60}\n")
    finally: await conn.close()
