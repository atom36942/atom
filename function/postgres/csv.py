async def func_postgres_csv_crud(*, crud_mode: str, validation_mode: str, csv_path: str, pg_dsn: str, table: str, const_column: list | None):
    """
    Performs high-performance bulk operations from a CSV to Postgres. 
    Uses a 'Stage and Cast' architecture to support complex types (Geography, JSONB, Arrays) 
    by bypassing binary encoder limitations of the asyncpg COPY protocol.

    Parameters:
    - crud_mode (str): "create", "update", or "delete".
    - validation_mode (str): "strict" (abort on error), "reject" (log & skip), or "loose" (nullify bad cells).
    - csv_path (str): Path to source file.
    - pg_dsn (str): Postgres connection string.
    - table (str): Target table name.
    - const_column (list | None): Constant values to inject (ignored in "delete" mode).

    Examples:
    - CREATE: await func_postgres_csv_crud(crud_mode="create", validation_mode="strict", csv_path="in.csv", pg_dsn=dsn, table="users", const_column=[["status", "active"]])
    - UPDATE: await func_postgres_csv_crud(crud_mode="update", validation_mode="reject", csv_path="upd.csv", pg_dsn=dsn, table="users", const_column=[["sync_ts", "now()"]])
    - DELETE: await func_postgres_csv_crud(crud_mode="delete", validation_mode="strict", csv_path="del.csv", pg_dsn=dsn, table="users", const_column=None)
    """
    import asyncio, asyncpg, csv, time, os
    from datetime import datetime

    # 1. Validation & Initialization
    if crud_mode not in ("create", "update", "delete"):
        raise ValueError(f"Invalid crud_mode: {crud_mode}")
    if validation_mode not in ("strict", "reject", "loose"):
        raise ValueError(f"Invalid validation mode: {validation_mode}")

    t0, log_every = time.time(), 100000
    db_name = pg_dsn.split('/')[-1].split('?')[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rej_path = f"tmp/rejected_{crud_mode}_{table}_{ts}.csv"
    staging_table = f"staging_{crud_mode}_{table}_{ts}"
    
    # 1. Summary & Parameters Dashboard
    icons = {"create": "🚚", "update": "🚀", "delete": "🗑️"}
    valid_consts = [c for c in const_column if isinstance(c, (tuple, list)) and len(c) == 2] if const_column else []
    
    print(f"\n{'-'*60}\n{icons[crud_mode]} POSTGRES BULK {crud_mode.upper()} SUMMARY\n{'-'*60}")
    print(f"📁 SOURCE:      {csv_path}")
    print(f"🎯 TARGET:      {db_name} -> {table}")
    print(f"🛠️  CRUD MODE:   {crud_mode.upper()}")
    print(f"🛡️  VALIDATION: {validation_mode.upper()}")
    if valid_consts:
        print(f"➕ CONST COLS:  {', '.join([f'{k}={v}' for k, v in valid_consts])}")
    print(f"{'-'*60}")

    c_names, c_vals = [c[0] for c in valid_consts], [c[1] for c in valid_consts]
    conn = await asyncpg.connect(pg_dsn)
    try:
        print(f"🔗 DB: Connected to {db_name}\n{'-'*60}")
        
        # 2. Fetch Schema Info (including UDT Name for precise casting)
        q = """
        SELECT column_name, data_type, udt_name, is_nullable 
        FROM information_schema.columns 
        WHERE table_name=$1 
        ORDER BY ordinal_position
        """
        columns_records = await conn.fetch(q, table)
        if not columns_records:
            raise Exception(f"Table '{table}' not found")
        
        # Type and Nullability Maps
        # We prefer udt_name for casting custom types like geography/geometry
        col_type_map = {r['column_name']: r['udt_name'] for r in columns_records}
        col_null_map = {r['column_name']: r['is_nullable'] == 'YES' for r in columns_records}
        db_cols_all = [r['column_name'] for r in columns_records]
        
        # 3. CSV Header Analysis
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header = reader.fieldnames or []
            if not csv_header:
                raise Exception("Missing CSV header")
            
            if crud_mode in ("update", "delete") and "id" not in csv_header:
                raise Exception(f"CSV must contain 'id' column for {crud_mode} operations")
            if crud_mode in ("update", "delete") and "id" not in db_cols_all:
                raise Exception(f"Table '{table}' must have an 'id' column for {crud_mode} operations")

            first_row = next(reader, {})
            f.seek(0)
            f.readline() 

            # 4. Column Comparison Dashboard
            print(f"\n📋 CSV TO DB SCHEMA COMPARISON:")
            print(f"{'-'*130}\n{'Idx':<4} | {'COLUMN NAME':<30} | {'CSV TYPE':<12} | {'DB TYPE':<15} | {'MATCH':^5} | {'NULL':^5} | {'CONV':^5} | {'PASS':^5}")
            print(f"{'-'*130}")
            
            def infer_type(val):
                if not val or str(val).lower() in ("null","none","n/a",""): return "null"
                v = str(val).strip()
                if v.replace('.','',1).isdigit(): return "float" if "." in v else "integer"
                for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y%m%d"):
                    try: datetime.strptime(v, fmt); return "date"
                    except: continue
                return "text"

            for idx, col in enumerate(csv_header, 1):
                match = "✅" if col in db_cols_all else "❌"
                csv_t = infer_type(first_row.get(col))
                db_t = col_type_map.get(col, "(missing)")
                
                is_nullable = "✅" if col_null_map.get(col, True) else "❌"
                # In Stage-and-Cast, we always treat columns as needing conversion to target types from TEXT
                needs_conv = "✅"
                status = "✅"
                
                print(f"{idx:<4} | {col[:29]:<30} | {csv_t:<12} | {db_t:<15} | {match:^5} | {is_nullable:^5} | {needs_conv:^5} | {status:^5}")
            print(f"{'-'*130}")

            # 5. Planning the operation
            if crud_mode == "delete":
                final_cols = ["id"]
                matched_cols = ["id"]
            else:
                base_matched = [c for c in csv_header if c in db_cols_all]
                matched_cols = [c for c in base_matched if c not in c_names]
                final_cols = matched_cols + c_names

            if not final_cols:
                raise Exception("No valid columns to process")

            if input(f"👉 Proceed with bulk {crud_mode.upper()} on '{table}'? (y/N): ").lower() != 'y':
                print(f"\n❌ [CANCELLED] Aborted by user.\n"); return

            # 6. Execution Prep
            print(f"\n🏗️  PHASE 1: Preparing Staging Area...")
            # We create a TEMP table with ALL columns as TEXT to bypass binary encoder limits
            staging_cols_sql = ", ".join([f"{c} TEXT" for c in final_cols])
            await conn.execute(f"CREATE TEMP TABLE {staging_table} ({staging_cols_sql})")
            print(f"✅ Staging area '{staging_table}' created (using TEXT optimization).")

            print(f"\n⚡ PHASE 2: Ingesting Data to Staging...")
            class RowReject(Exception): pass

            # In this architecture, converters primarily handle base data cleaning
            # and format enforcement, returning strings for the TEXT staging table.
            def get_converter(col_name):
                t = col_type_map.get(col_name, "text")
                def base_clean(val):
                    if val is None: return None
                    s = str(val).strip()
                    if s.lower() in ("","none","null","n/a"): return None
                    return s
                
                def converter(v):
                    v_str = base_clean(v)
                    if v_str is None: return None
                    try:
                        # Basic validation based on target type (exclude arrays from scalar checks)
                        if ("int" in t or "numeric" in t or "real" in t or "double" in t) and not t.startswith('_'):
                            float(v_str) # Just validation
                        if "bool" in t:
                            v_str = "true" if v_str.lower() in ("true","1","yes","t","y") else "false"
                        if "date" in t or "timestamp" in t:
                            for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y-%m-%d %H:%M:%S","%Y/%m/%d","%d.%m.%Y","%Y%m%d"):
                                try:
                                    dt = datetime.strptime(v_str, fmt); 
                                    v_str = dt.isoformat(); break
                                except: continue
                            else: raise ValueError(f"No date format")
                    except Exception as e:
                        if validation_mode == "strict": raise ValueError(f"Column '{col_name}' ({t}) error: {e}")
                        if validation_mode == "loose": return None
                        if validation_mode == "reject": raise RowReject(e)
                    return v_str # Always return a string for the TEXT staging table
                return converter

            col_plan = [get_converter(c) for c in matched_cols]
            const_converters = [get_converter(c) for c in c_names]
            conv_c_vals = [conv(v) for conv, v in zip(const_converters, c_vals)]

            def row_generator():
                count, rejected, f_rej = 0, 0, None
                try:
                    for row in reader:
                        try:
                            if crud_mode == "delete":
                                # Apply the 'id' converter plan to ensure valid IDs and enable rejection
                                line = [col_plan[0](row.get("id"))]
                            else:
                                line = [plan(row.get(col)) for plan, col in zip(col_plan, matched_cols)]
                                line.extend(conv_c_vals)
                            
                            yield tuple(line)
                            count += 1
                        except RowReject:
                            rejected += 1
                            if validation_mode == "reject":
                                if f_rej is None:
                                    os.makedirs("tmp", exist_ok=True); f_rej = open(rej_path,"w",encoding='utf-8')
                                    csv.DictWriter(f_rej, fieldnames=csv_header).writeheader()
                                csv.DictWriter(f_rej, fieldnames=csv_header).writerow(row)
                        
                        if (count+rejected) % log_every == 0:
                            print(f"  🔹 PROGRESS: {count:,} rows {f'| ⚠️ REJECTED: {rejected:,}' if rejected else ''} | ⏳ {int(time.time()-t0)}s")
                finally:
                    if f_rej: f_rej.close()
                if rejected: print(f"{'-'*60}\n📁 REJECT LOG: {rej_path}\n{'-'*60}")

            # Stream strings into the staging table (binary copy handles TEXT efficiently)
            await conn.copy_records_to_table(staging_table, records=row_generator(), columns=final_cols)
            print(f"✅ Data streamed to staging. Now running atomic migration...")

            # 7. Final Step: Atomic Migration with Explicit Casting
            async with conn.transaction():
                print(f"⚡ PHASE 3: Running Atomic {crud_mode.upper()} with Casting...")
                if crud_mode == "delete":
                    res = await conn.execute(f"DELETE FROM {table} m USING {staging_table} s WHERE m.id = s.id::text")
                elif crud_mode == "create":
                    cols_sql = ", ".join(final_cols)
                    # We cast each staging TEXT column to the target UDT name
                    # Standard Types (int, bool) and Complex Types (geography, jsonb, _int4) all support ::casting
                    cast_sql = ", ".join([f"{c}::{col_type_map[c]}" for c in final_cols])
                    res = await conn.execute(f"INSERT INTO {table} ({cols_sql}) SELECT {cast_sql} FROM {staging_table}")
                else: # update
                    cols_to_update = [c for c in final_cols if c != "id"]
                    set_sql = ", ".join([f"{c} = s.{c}::{col_type_map[c]}" for c in cols_to_update])
                    res = await conn.execute(f"UPDATE {table} m SET {set_sql} FROM {staging_table} s WHERE m.id = s.id::{col_type_map['id']}")
                
                print(f"{'-'*60}\n✅ COMPLETED: {res} | ⏱️  {int(time.time()-t0)}s\n{'-'*60}\n")

    finally:
        await conn.close()
