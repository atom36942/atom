async def func_postgres_bulk_upload_csv(*, mode: str, csv_path: str, pg_dsn: str, table: str, const_column: list | None):
    """Inserts records from CSV to PG using binary protocol with strict/loose/reject modes."""
    import asyncio, asyncpg, csv, time, os
    from datetime import datetime
    if mode not in ("strict", "reject", "loose"): raise ValueError(f"Invalid mode: {mode}")
    t0, log_every = time.time(), 100000
    db_name = pg_dsn.split('/')[-1].split('?')[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rej_path = f"tmp/rejected_{table}_{ts}.csv"
    print(f"\n{'-'*60}\n🚚 INGESTION DASHBOARD | MODE: {mode.upper()}\n{'-'*60}")
    print(f"📁 SOURCE: {csv_path}\n🎯 DESTINATION: {db_name} -> {table}\n{'-'*60}")
    valid_consts = [c for c in const_column if isinstance(c,(tuple,list)) and len(c)==2] if const_column else []
    c_names, c_vals = [c[0] for c in valid_consts], [c[1] for c in valid_consts]
    conn = await asyncpg.connect(pg_dsn)
    try:
        print(f"🔗 DB: Connected to {db_name}\n{'-'*60}")
        q = "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position"
        columns_records = await conn.fetch(q, table)
        if not columns_records: raise Exception(f"Table '{table}' not found")
        table_cols = [r['column_name'] for r in columns_records if r['column_name'] != 'id']
        col_type_map = {r['column_name']: r['data_type'].lower() for r in columns_records}
        col_null_map = {r['column_name']: r['is_nullable'] == 'YES' for r in columns_records}
        def infer_type(val):
            if not val or str(val).lower() in ("null","none","n/a",""): return "null"
            v = str(val).strip()
            if v.replace('.','',1).isdigit(): return "float" if "." in v else "integer"
            for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y%m%d"):
                try: 
                    datetime.strptime(v, fmt); return "date"
                except: continue
            return "text"
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header = reader.fieldnames or []
            if not csv_header: raise Exception("Missing CSV header")
            first_row = next(reader, {})
            f.seek(0); f.readline() 
            print(f"📋 CSV TO DB SCHEMA COMPARISON:\n{'-'*130}\n{'Idx':<4} | {'COLUMN NAME':<30} | {'CSV TYPE':<12} | {'DB TYPE':<15} | {'MATCH':^5} | {'NULL':^5} | {'CONV':^5} | {'PASS':^5}\n{'-'*130}")
            for idx, col in enumerate(csv_header, 1):
                match = "✅" if col in table_cols else "❌"
                csv_t, db_t = infer_type(first_row.get(col)), col_type_map.get(col, "(missing)").replace("int ","integer ").replace("integer4","integer")
                if db_t == "int": db_t = "integer"
                is_nullable, needs_conv, status = "✅" if col_null_map.get(col,True) else "❌", "✅" if db_t != "text" and db_t != "(missing)" else "❌", "✅"
                if match == "✅":
                    if csv_t == "text" and db_t in ("integer","bigint","numeric","real","double precision"): status = "❌"
                    if csv_t == "float" and db_t in ("integer","bigint"): status = "❌"
                    if csv_t == "text" and "date" in db_t: status = "❌"
                    if csv_t == "null" and not col_null_map.get(col, True): status = "❌"
                print(f"{idx:<4} | {col[:29]:<30} | {csv_t:<12} | {db_t:<15} | {match:^5} | {is_nullable:^5} | {needs_conv:^5} | {status:^5}")
            print(f"{'-'*130}")
            matched_cols = [c for c in csv_header if c in table_cols and c not in c_names]
            final_cols = matched_cols + c_names
            if not final_cols: raise Exception("No valid columns to upload")
            if input(f"👉 Proceed with upload to '{table}'? (y/N): ").lower() != 'y':
                print(f"\n❌ [CANCELLED] Aborted by user.\n"); return
            print(f"\n⚡ INGESTION IN PROGRESS...")
            class RowReject(Exception): pass
            def get_converter(col_name):
                t = col_type_map.get(col_name, "text")
                def base_clean(val):
                    if val is None: return None
                    s = str(val).strip()
                    if s.lower() in ("","none","null","n/a"): return None
                    return s
                if t == "text" or "char" in t: return lambda v: base_clean(v)
                def converter(v):
                    v_str = base_clean(v)
                    if v_str is None: return None
                    try:
                        if "int" in t: return int(float(v_str)) if '.' in v_str else int(v_str)
                        if "numeric" in t or "real" in t or "double" in t: return float(v_str)
                        if "bool" in t: return v_str.lower() in ("true","1","yes","t","y")
                        if "date" in t or "timestamp" in t:
                            for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y-%m-%d %H:%M:%S","%Y/%m/%d","%d.%m.%Y","%Y%m%d"):
                                try:
                                    dt = datetime.strptime(v_str, fmt); return dt.date() if t == "date" else dt
                                except: continue
                            raise ValueError(f"No date format")
                    except Exception as e:
                        if mode == "strict": raise ValueError(f"Column '{col_name}' ({t}) error: {e}")
                        if mode == "loose": return None
                        if mode == "reject": raise RowReject(e)
                    return v_str
                return converter
            col_plan, const_converters = [get_converter(c) for c in matched_cols], [get_converter(c) for c in c_names]
            conv_c_vals = [conv(v) for conv, v in zip(const_converters, c_vals)]
            def row_generator():
                count, rejected, f_rej = 0, 0, None
                try:
                    for row in reader:
                        try:
                            line = [plan(row.get(col)) for plan, col in zip(col_plan, matched_cols)]
                            line.extend(conv_c_vals); yield tuple(line); count += 1
                        except RowReject:
                            rejected += 1
                            if mode == "reject":
                                if f_rej is None:
                                    os.makedirs("tmp", exist_ok=True); f_rej = open(rej_path,"w",encoding='utf-8')
                                    csv.DictWriter(f_rej, fieldnames=csv_header).writeheader()
                                csv.DictWriter(f_rej, fieldnames=csv_header).writerow(row)
                        if (count+rejected)%log_every==0: print(f"  🔹 PROGRESS: {count:,} rows {f'| ⚠️ REJECTED: {rejected:,}' if rejected else ''} | ⏳ {int(time.time()-t0)}s")
                finally:
                    if f_rej: f_rej.close()
                if rejected: print(f"{'-'*60}\n📁 REJECT LOG: {rej_path}\n{'-'*60}")
            res = await conn.copy_records_to_table(table, records=row_generator(), columns=final_cols)
            print(f"{'-'*60}\n✅ COMPLETED: {res} | ⏱️  {int(time.time()-t0)}s\n{'-'*60}\n")
    finally: await conn.close()

async def func_postgres_bulk_update_csv(*, mode: str, csv_path: str, pg_dsn: str, table: str):
    """Updates records from CSV to PG using a dynamic staging table and binary protocol."""
    import asyncio, asyncpg, csv, time, os
    from datetime import datetime
    if mode not in ("strict", "reject", "loose"): raise ValueError(f"Invalid mode: {mode}")
    t0, log_every = time.time(), 100000
    db_name = pg_dsn.split('/')[-1].split('?')[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rej_path = f"tmp/rejected_update_{table}_{ts}.csv"
    staging_table = f"staging_{table}_{ts}"
    print(f"\n{'-'*60}\n🚀 BULK UPDATE DASHBOARD | MODE: {mode.upper()}\n{'-'*60}")
    print(f"📁 SOURCE: {csv_path}\n🎯 TARGET:   {db_name} -> {table}\n{'-'*60}")
    conn = await asyncpg.connect(pg_dsn)
    try:
        print(f"🔗 DB: Connected to {db_name}\n{'-'*60}")
        q = "SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=$1"
        columns_records = await conn.fetch(q, table)
        if not columns_records: raise Exception(f"Table '{table}' not found")
        col_type_map = {r['column_name']: r['data_type'].lower() for r in columns_records}
        col_null_map = {r['column_name']: r['is_nullable'] == 'YES' for r in columns_records}
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header = reader.fieldnames or []
            if "id" not in csv_header: raise Exception("CSV must contain 'id' column for updates")
            first_row = next(reader, {})
            f.seek(0); f.readline()
            matched_cols = [c for c in csv_header if c in col_type_map]
            cols_to_update = [c for c in matched_cols if c != "id"]
            if not cols_to_update: raise Exception("No columns to update")
            print(f"📋 DYNAMIC STAGING PLAN:\n{'-'*80}\n{'Idx':<4} | {'COLUMN NAME':<30} | {'DB TYPE':<15} | {'MATCH':^5}\n{'-'*80}")
            for idx, col in enumerate(matched_cols, 1):
                db_t = col_type_map.get(col)
                print(f"{idx:<4} | {col[:29]:<30} | {db_t:<15} | {'✅':^5}")
            print(f"{'-'*80}")
            if input(f"👉 Proceed with bulk UPDATE on '{table}'? (y/N): ").lower() != 'y':
                print(f"\n❌ [CANCELLED] Aborted.\n"); return
            print(f"\n🏗️  PHASE 1: Creating Staging Area...")
            staging_cols_sql = ", ".join([f"{c} {col_type_map[c].replace('serial','bigint')}" for c in matched_cols])
            await conn.execute(f"CREATE UNLOGGED TABLE {staging_table} ({staging_cols_sql})")
            print(f"✅ Staging table '{staging_table}' created.")
            class RowReject(Exception): pass
            def get_converter(col_name):
                t = col_type_map.get(col_name, "text")
                def base_clean(val):
                    if val is None: return None
                    s = str(val).strip()
                    if s.lower() in ("","none","null","n/a"): return None
                    return s
                if t == "text" or "char" in t: return lambda v: base_clean(v)
                def converter(v):
                    v_str = base_clean(v)
                    if v_str is None: return None
                    try:
                        if "int" in t: return int(float(v_str)) if '.' in v_str else int(v_str)
                        if "numeric" in t or "real" in t or "double" in t: return float(v_str)
                        if "bool" in t: return v_str.lower() in ("true","1","yes","t","y")
                        if "date" in t or "timestamp" in t:
                            for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y-..","%Y%m%d"):
                                try:
                                    dt = datetime.strptime(v_str, fmt); return dt.date() if t == "date" else dt
                                except: continue
                            return str(v_str) # Fallback
                    except:
                        if mode == "strict": raise ValueError(f"Column '{col_name}' error")
                        if mode == "loose": return None
                        if mode == "reject": raise RowReject()
                    return v_str
                return converter
            col_plan = [get_converter(c) for c in matched_cols]
            def row_generator():
                count, rejected, f_rej = 0, 0, None
                try:
                    for row in reader:
                        try:
                            line = [plan(row.get(col)) for plan, col in zip(col_plan, matched_cols)]
                            yield tuple(line); count += 1
                        except RowReject:
                            rejected += 1
                            if mode == "reject":
                                if f_rej is None:
                                    os.makedirs("tmp", exist_ok=True); f_rej = open(rej_path,"w",encoding='utf-8')
                                    csv.DictWriter(f_rej, fieldnames=csv_header).writeheader()
                                csv.DictWriter(f_rej, fieldnames=csv_header).writerow(row)
                        if (count+rejected)%log_every==0: print(f"  🔹 STREAMING: {count:,} rows | ⏳ {int(time.time()-t0)}s")
                finally:
                    if f_rej: f_rej.close()
            print(f"\n⚡ PHASE 2: Streaming Data to Staging...")
            await conn.copy_records_to_table(staging_table, records=row_generator(), columns=matched_cols)
            print(f"✅ Streaming completed. Now running atomic update...")
            set_sql = ", ".join([f"{c} = s.{c}" for c in cols_to_update])
            update_res = await conn.execute(f"UPDATE {table} m SET {set_sql} FROM {staging_table} s WHERE m.id = s.id")
            print(f"\n⚡ PHASE 3: Cleaning up...")
            await conn.execute(f"DROP TABLE {staging_table}")
            print(f"{'-'*60}\n✅ COMPLETED: {update_res} | ⏱️  {int(time.time()-t0)}s\n{'-'*60}\n")
    finally: await conn.close()
