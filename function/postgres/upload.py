async def func_postgres_bulk_upload_csv(*, mode: str, csv_path: str, pg_dsn: str, table: str, const_column: list | None):
    """
    High-performance, schema-aware bulk CSV uploader for PostgreSQL.
    
    Modes:
    - 'strict': Halts ingestion immediately on any data mismatch (fails fast).
    - 'reject': Skips the row on error and logs it to a file in the tmp/ directory.
    - 'loose':  Coerces problematic values to NULL and continues the ingestion.
    
    Features:
    - Pre-flight Audit: Indexed column list with PASS/FAIL safety checks.
    - Plan Optimization: Pre-calculates 'Conversion Plan' for max-speed ingestion.
    - Automation: Fetches DB schema dynamically to map columns and types.
    - Performance: Uses Binary COPY protocol (asyncpg) for millions of rows.
    """
    import asyncio, asyncpg, csv, time, os
    from datetime import datetime
    
    if mode not in ("strict", "reject", "loose"):
        raise ValueError(f"Invalid mode '{mode}'. Must be 'strict', 'reject', or 'loose'.")
    
    t0, log_every = time.time(), 100000
    db_name = pg_dsn.split('/')[-1].split('?')[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    reject_path = f"tmp/rejected_{table}_{ts}.csv"
    
    print(f"\n{'-'*60}\n🚚 INGESTION DASHBOARD | MODE: {mode.upper()}\n{'-'*60}")
    print(f"📁 SOURCE:      {csv_path}\n🎯 DESTINATION: {db_name} -> {table}\n{'-'*60}")
    
    valid_consts = [c for c in const_column if isinstance(c, (tuple, list)) and len(c) == 2] if const_column else []
    c_names, c_vals = [c[0] for c in valid_consts], [c[1] for c in valid_consts]
    
    conn = await asyncpg.connect(pg_dsn)
    try:
        print(f"🔗 DB: Successfully connected to {db_name}\n{'-'*60}")
        q = "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position"
        columns_records = await conn.fetch(q, table)
        if not columns_records: raise Exception(f"Table '{table}' not found")
        table_cols = [r['column_name'] for r in columns_records if r['column_name'] != 'id']
        col_type_map = {r['column_name']: r['data_type'].lower() for r in columns_records}
        col_null_map = {r['column_name']: r['is_nullable'] == 'YES' for r in columns_records}
        
        def infer_type(val):
            if not val or str(val).lower() in ("null", "none", "n/a", ""): return "null"
            v = str(val).strip()
            if v.replace('.', '', 1).isdigit(): return "float" if "." in v else "integer"
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y%m%d"):
                try: 
                    datetime.strptime(v, fmt); return "date"
                except: continue
            return "text"

        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header = reader.fieldnames or []
            if not csv_header: raise Exception("Empty CSV or missing header")
            first_row = next(reader, {})
            f.seek(0); f.readline() 
            
            print(f"📋 CSV TO DB SCHEMA COMPARISON:\n{'-'*130}\n{'Idx':<4} | {'COLUMN NAME':<30} | {'CSV TYPE':<12} | {'DB TYPE':<15} | {'MATCH':^5} | {'NULL':^5} | {'CONV':^5} | {'PASS':^5}\n{'-'*130}")
            for idx, col in enumerate(csv_header, 1):
                match = "✅" if col in table_cols else "❌"
                csv_t = infer_type(first_row.get(col))
                db_t = col_type_map.get(col, "(missing)").replace("int ", "integer ").replace("integer4", "integer")
                if db_t == "int": db_t = "integer"
                is_nullable = "✅" if col_null_map.get(col, True) else "❌"
                needs_conv = "✅" if db_t != "text" and db_t != "(missing)" else "❌"
                status = "✅"
                if match == "✅":
                    if csv_t == "text" and db_t in ("integer", "bigint", "numeric", "real", "double precision"): status = "❌"
                    if csv_t == "float" and db_t in ("integer", "bigint"): status = "❌"
                    if csv_t == "text" and "date" in db_t: status = "❌"
                    if csv_t == "null" and not col_null_map.get(col, True): status = "❌"
                print(f"{idx:<4} | {col[:29]:<30} | {csv_t:<12} | {db_t:<15} | {match:^5} | {is_nullable:^5} | {needs_conv:^5} | {status:^5}")
            print(f"{'-'*130}")

            matched_cols = [c for c in csv_header if c in table_cols and c not in c_names]
            final_cols = matched_cols + c_names
            if not final_cols: raise Exception("No valid columns to upload")
            
            ans = input(f"👉 Proceed with upload to '{table}' using '{mode}' mode? (y/N): ")
            if ans.lower() != 'y':
                print(f"\n❌ [CANCELLED] Upload aborted by user.\n"); return

            print(f"\n⚡ INGESTION IN PROGRESS...")
            class RowReject(Exception): pass
            
            def get_converter(col_name):
                t = col_type_map.get(col_name, "text")
                def base_clean(val):
                    if val is None: return None
                    s = str(val).strip()
                    if s.lower() in ("", "none", "null", "n/a"): return None
                    return s
                if t == "text" or "char" in t: return lambda v: base_clean(v)
                def converter(v):
                    v_str = base_clean(v)
                    if v_str is None: return None
                    try:
                        if "int" in t: return int(float(v_str)) if '.' in v_str else int(v_str)
                        if "numeric" in t or "real" in t or "double" in t: return float(v_str)
                        if "bool" in t: return v_str.lower() in ("true", "1", "yes", "t", "y")
                        if "date" in t or "timestamp" in t:
                            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%d.%m.%Y", "%Y%m%d"):
                                try:
                                    dt = datetime.strptime(v_str, fmt); return dt.date() if t == "date" else dt
                                except: continue
                            raise ValueError(f"No matching date format")
                    except Exception as e:
                        if mode == "strict": raise ValueError(f"Column '{col_name}' ({t}) received '{v}': {e}")
                        if mode == "loose": return None
                        if mode == "reject": raise RowReject(f"Column '{col_name}' error: {e}")
                    return v_str
                return converter

            col_plan = [get_converter(c) for c in matched_cols]
            const_converters = [get_converter(c) for c in c_names]
            conv_c_vals = [conv(v) for conv, v in zip(const_converters, c_vals)]

            def row_generator():
                count, rejected = 0, 0
                f_rej = None
                if mode == "reject": 
                    os.makedirs("tmp", exist_ok=True)
                    f_rej = open(reject_path, "w", encoding='utf-8')
                    writer = csv.DictWriter(f_rej, fieldnames=csv_header)
                    writer.writeheader()
                
                try:
                    for row in reader:
                        try:
                            line = [plan(row.get(col)) for plan, col in zip(col_plan, matched_cols)]
                            line.extend(conv_c_vals)
                            yield tuple(line)
                            count += 1
                        except RowReject:
                            rejected += 1
                            if f_rej: csv.DictWriter(f_rej, fieldnames=csv_header).writerow(row)
                        if count % log_every == 0: 
                            r_info = f" | ⚠️ REJECTED: {rejected:,}" if rejected else ""
                            print(f"  🔹 PROGRESS: {count:,} rows {r_info} | ⏳ {int(time.time()-t0)}s")
                finally:
                    if f_rej: f_rej.close()
                
                if rejected: print(f"{'-'*60}\n📁 REJECT LOG: {reject_path}\n{'-'*60}")
            
            result = await conn.copy_records_to_table(table, records=row_generator(), columns=final_cols)
            print(f"{'-'*60}\n✅ COMPLETED: {result}\n⏱️  Total Time: {int(time.time()-t0)}s\n{'-'*60}\n")
            
    finally: await conn.close()
