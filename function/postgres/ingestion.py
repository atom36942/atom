async def func_postgres_csv_crud(*, crud_mode: str, validation_mode: str, csv_path: str, pg_dsn: str, table: str, const_column: list | None, rename_column: list | None):
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
    - rename_column (list | None): Headers to rename before matching DB columns. (format: [["old", "new"]])

    Examples:
    - CREATE: await func_postgres_csv_crud(crud_mode="create", validation_mode="strict", csv_path="in.csv", pg_dsn=dsn, table="users", const_column=[["status", "active"]], rename_column=[["column_old", "column_new"]])
    - UPDATE: await func_postgres_csv_crud(crud_mode="update", validation_mode="reject", csv_path="upd.csv", pg_dsn=dsn, table="users", const_column=[["sync_ts", "now()"]], rename_column=None)
    - DELETE: await func_postgres_csv_crud(crud_mode="delete", validation_mode="strict", csv_path="del.csv", pg_dsn=dsn, table="users", const_column=None, rename_column=None)
    """
    import asyncio, asyncpg, csv, time, os, itertools, sys
    from datetime import datetime
    
    # Increase field size limit for extremely large CSV cells
    csv.field_size_limit(sys.maxsize)

    # 1. Validation & Initialization
    if crud_mode == "delete" and const_column:
        raise ValueError("const_column must be None for 'delete' mode as it is not utilized for row removal.")
    if crud_mode == "delete" and rename_column:
        raise ValueError("rename_column must be None for 'delete' mode.")
    if crud_mode not in ("create", "update", "delete"):
        raise ValueError(f"Invalid crud_mode: {crud_mode}")
    if validation_mode not in ("strict", "reject", "loose"):
        raise ValueError(f"Invalid validation mode: {validation_mode}")

    t0, log_every = time.time(), 100000
    db_name = pg_dsn.split('/')[-1].split('?')[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rej_path = f"tmp/rejected_{crud_mode}_{table}_{ts}.csv"
    staging_table = f"staging_sync_{table}"
    
    # 1. Summary & Parameters Dashboard
    icons = {"create": "🚚", "update": "🚀", "delete": "🗑️"}
    valid_consts = [c for c in const_column if isinstance(c, (tuple, list)) and len(c) == 2] if const_column else []
    valid_renames = [r for r in rename_column if isinstance(r, (tuple, list)) and len(r) == 2] if rename_column else []
    
    def get_ts(): return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"

    print(f"\n{'-'*60}\n{get_ts()} {icons[crud_mode]} POSTGRES BULK {crud_mode.upper()} SUMMARY\n{'-'*60}")
    print(f"📁 SOURCE:      {csv_path}")
    print(f"🎯 TARGET:      {db_name} -> {table}")
    print(f"🛠️  CRUD MODE:   {crud_mode.upper()}")
    print(f"🛡️  VALIDATION: {validation_mode.upper()}")
    if valid_consts:
        print(f"➕ CONST COLS:  {', '.join([f'{k}={v}' for k, v in valid_consts])}")
    if valid_renames:
        print(f"🔄 RENAMES:     {', '.join([f'{r[0]}->{r[1]}' for r in valid_renames])}")
    print(f"{'-'*60}")

    c_names, c_vals = [c[0] for c in valid_consts], [c[1] for c in valid_consts]
    # Set a 60s timeout for the initial connection handshake
    conn = await asyncpg.connect(pg_dsn, timeout=60)
    try:
        print(f"{get_ts()} 🔗 DB: Connected to {db_name}\n{'-'*60}")

        # 1.5 Strict Existence Check
        table_exists = await conn.fetchval('SELECT to_regclass($1)', f'"{table}"' if '.' not in table else table)
        if not table_exists:
            raise ValueError(f"Table '{table}' does not exist in database '{db_name}'. Please verify the table name and schema.")
        
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
            csv_header_original = reader.fieldnames or []
            if not csv_header_original:
                raise Exception("Missing CSV header")
            
            # Virtual Header Mapping
            rename_map = {old: new for old, new in valid_renames}
            reverse_rename_map = {new: old for old, new in valid_renames}
            csv_header = [rename_map.get(col, col) for col in csv_header_original]
            
            if crud_mode in ("update", "delete") and "id" not in csv_header:
                raise Exception(f"CSV must contain 'id' column (possibly renamed) for {crud_mode} operations")
            if crud_mode in ("update", "delete") and "id" not in db_cols_all:
                raise Exception(f"Table '{table}' must have an 'id' column for {crud_mode} operations")

            first_row = next(reader, {})
            f.seek(0)
            f.readline() 

            # Helper to extract values by their visual (potentially renamed) column name
            def get_csv_val(row_dict, mapped_col_name):
                original_name = reverse_rename_map.get(mapped_col_name, mapped_col_name)
                return row_dict.get(original_name)

            # 4. Column Comparison Dashboard
            print(f"\n{get_ts()} 📋 CSV TO DB SCHEMA COMPARISON:")
            
            # Dynamic width calculation for the 'COLUMN NAME' column
            max_col_len = max([len(c) for c in csv_header] + [len("COLUMN NAME")])
            separator_len = max_col_len + 75 
            
            print(f"{'-'*separator_len}\n{'Idx':<4} | {'COLUMN NAME':<{max_col_len}} | {'CSV TYPE':<12} | {'DB TYPE':<15} | {'MATCH':^5} | {'NULL':^5} | {'CONV':^5} | {'PASS':^5}")
            print(f"{'-'*separator_len}")
            
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
                csv_t = infer_type(get_csv_val(first_row, col))
                db_t = col_type_map.get(col, "(missing)")
                
                is_nullable = "✅" if col_null_map.get(col, True) else "❌"
                # Show conversion only if the target is NOT a plain text/char type
                needs_conv = "✅" if db_t not in ("text", "varchar", "character varying", "(missing)") else "❌"
                status = "✅"
                
                print(f"{idx:<4} | {col:<{max_col_len}} | {csv_t:<12} | {db_t:<15} | {match:^5} | {is_nullable:^5} | {needs_conv:^5} | {status:^5}")
            print(f"{'-'*separator_len}")

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

            # 6. Execution Prep & Resume Logic
            # Check if a persistent staging table already exists
            skip_count = 0
            existing_stage = await conn.fetchval('SELECT to_regclass($1)', f'"{staging_table}"')
            
            if existing_stage:
                existing_count = await conn.fetchval(f'SELECT count(*) FROM "{staging_table}"')
                print(f"⚠️  NOTICE: Persistent staging table '{staging_table}' already exists with {existing_count:,} rows.")
                choice = input(f"👉 [R]esume from row {existing_count+1:,}, [O]verwrite & start fresh, or [C]ancel? (r/o/C): ").lower()
                
                if choice == 'r':
                    skip_count = existing_count
                    print(f"✅ RESUMING: Skipping first {skip_count:,} rows in CSV...")
                elif choice == 'o':
                    await conn.execute(f'DROP TABLE "{staging_table}"')
                    print(f"🧹 OVERWRITING: Deleted old staging table.")
                else:
                    print(f"❌ Aborted by user."); return

            # We create a persistent table (not TEMP) to support resumes across connection drops
            if skip_count == 0:
                staging_cols_sql = ", ".join([f'"{c}" TEXT' for c in final_cols])
                try:
                    # UNLOGGED tables are much faster for staging because they don't generate WAL logs
                    await conn.execute(f'CREATE UNLOGGED TABLE "{staging_table}" ({staging_cols_sql})')
                    print(f"{get_ts()} ✅ Staging area '{staging_table}' created (using UNLOGGED optimization).")
                except Exception:
                    # Fallback to standard table if UNLOGGED is restricted (e.g. some managed DB tiers)
                    await conn.execute(f'CREATE TABLE "{staging_table}" ({staging_cols_sql})')
                    print(f"{get_ts()} ✅ Staging area '{staging_table}' created (standard mode).")

            print(f"\n{get_ts()} ⚡ PHASE 2: Ingesting Data to Staging...")
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

            def row_generator(offset=0):
                count, rejected, f_rej = offset, 0, None
                try:
                    # Use islice for high-performance row skipping when resuming
                    items = itertools.islice(reader, offset, None)
                    for row in items:
                        try:
                            if crud_mode == "delete":
                                # Apply the 'id' converter plan to ensure valid IDs and enable rejection
                                # Note: get_csv_val is used to respect potential renaming of the 'id' column
                                line = [col_plan[0](get_csv_val(row, "id"))]
                            else:
                                line = [plan(get_csv_val(row, col)) for plan, col in zip(col_plan, matched_cols)]
                                line.extend(conv_c_vals)
                            
                            yield tuple(line)
                            count += 1
                        except RowReject:
                            rejected += 1
                            if validation_mode == "reject":
                                if f_rej is None:
                                    os.makedirs("tmp", exist_ok=True); f_rej = open(rej_path,"w",encoding='utf-8')
                                    csv.DictWriter(f_rej, fieldnames=csv_header_original).writeheader()
                                csv.DictWriter(f_rej, fieldnames=csv_header_original).writerow(row)
                        
                        if (count+rejected) % log_every == 0:
                            print(f"{get_ts()}   🔹 PROGRESS: {count:,} rows {f'| ⚠️ REJECTED: {rejected:,}' if rejected else ''} | ⏳ {int(time.time()-t0)}s")
                    
                    print(f"{get_ts()} ✅ CSV reading complete ({count:,} rows total). Finalizing database stream...")
                finally:
                    if f_rej: f_rej.close()
                if rejected: print(f"{'-'*60}\n{get_ts()} 📁 REJECT LOG: {rej_path}\n{'-'*60}")

            # Stream strings into the staging table (binary copy handles TEXT efficiently)
            # Set a 1-hour timeout for the data stream to prevent indefinite hangs
            await conn.copy_records_to_table(staging_table, records=row_generator(skip_count), columns=final_cols, timeout=3600)
            print(f"{get_ts()} ✅ Data streamed to staging. Now running atomic migration...")

            # 7. Final Step: Atomic Migration with Explicit Casting
            async with conn.transaction():
                print(f"{get_ts()} ⚡ PHASE 3: Running Atomic {crud_mode.upper()} with Casting (Timeout: 1h)...")
                
                # Helper to generate robust cast expressions for integer types
                def get_cast(col):
                    t = col_type_map[col]
                    if t in ("int2", "int4", "int8"):
                        return f's."{col}"::numeric::{t}'
                    return f's."{col}"::{t}'

                # Migration operations use a 1-hour timeout
                if crud_mode == "delete":
                    cast_id = get_cast("id")
                    res = await conn.execute(f'DELETE FROM "{table}" m USING "{staging_table}" s WHERE m."id" = {cast_id}', timeout=3600)
                elif crud_mode == "create":
                    cols_sql = ", ".join([f'"{c}"' for c in final_cols])
                    cast_sql = ", ".join([get_cast(c) for c in final_cols])
                    res = await conn.execute(f'INSERT INTO "{table}" ({cols_sql}) SELECT {cast_sql} FROM "{staging_table}" s', timeout=3600)
                else: # update
                    cols_to_update = [c for c in final_cols if c != "id"]
                    set_sql = ", ".join([f'"{c}" = {get_cast(c)}' for c in cols_to_update])
                    cast_id = get_cast("id")
                    res = await conn.execute(f'UPDATE "{table}" m SET {set_sql} FROM "{staging_table}" s WHERE m."id" = {cast_id}', timeout=3600)
                
                print(f"{'-'*60}\n{get_ts()} ✅ COMPLETED: {res} | ⏱️  {int(time.time()-t0)}s\n{'-'*60}\n")
                
                # Cleanup: Only drop the staging table on absolute success
                await conn.execute(f'DROP TABLE "{staging_table}"')
                print(f"{get_ts()} 🧹 Staging table '{staging_table}' cleaned up.")

                # Final optimization: Update statistics for the new massive table
                print(f"{get_ts()} 📊 Optimizing database statistics (ANALYZE)...")
                await conn.execute(f'ANALYZE "{table}"')
                print(f"{get_ts()} ✅ Statistics updated. Ingestion complete.")

    finally:
        await conn.close()
