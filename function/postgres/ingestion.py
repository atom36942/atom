import asyncio, asyncpg, csv, time, os, itertools, sys
from datetime import datetime
def get_ts(): return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
async def func_postgres_csv_ingestion(
    *,
    csv_path: str,
    pg_dsn: str,
    table: str,
    crud_mode: str,
    validation_mode: str,
    rename_column: list[list] | None,
    ignore_column: list[str] | None,
    const_column: list[list] | None
):
    """
    Performs high-performance bulk operations from a CSV to Postgres. 
    Uses a 'Stage and Cast' architecture to support complex types (Geography, JSONB, Arrays) 
    by bypassing binary encoder limitations of the asyncpg COPY protocol.
    Rules & Constraints:
    - DELETE mode: `const_column`, `rename_column`, and `ignore_column` MUST be None. `validation_mode` cannot be "loose".
    - UPDATE mode: If `ignore_column` is used, it MUST NOT contain "id" (required for matching). `loose` validation IS allowed.
    - UPDATE & DELETE modes: The CSV MUST contain an 'id' column (after applying any renames) to identify records.
    
    Parameters:
    - csv_path (str): Path to source file.
    - pg_dsn (str): Postgres connection string.
    - table (str): Target table name.
    - crud_mode (str): "create", "update", or "delete".
    - validation_mode (str): "strict" (abort on error), "reject" (log & skip), or "loose" (nullify bad cells).
    - rename_column (list | None): Headers to rename before matching DB columns. (format: [["old", "new"]])
    - ignore_column (list | None): List of CSV columns to skip during processing.
    - const_column (list | None): Constant values to inject.
    Example:
        await func_postgres_csv_ingestion(csv_path="data.csv", pg_dsn=DSN, table="users", crud_mode="create", validation_mode="reject", rename_column=[["x","y"],["a","b"]], ignore_column=["tmp"], const_column=[["src","api"]])
        await func_postgres_csv_ingestion(csv_path="data.csv", pg_dsn=DSN, table="users", crud_mode="update", validation_mode="reject", rename_column=[["uid","id"]], ignore_column=["tmp"], const_column=None)
        await func_postgres_csv_ingestion(csv_path="data.csv", pg_dsn=DSN, table="users", crud_mode="delete", validation_mode="strict", rename_column=None, ignore_column=None, const_column=None)
    """
    
    # Increase field size limit for extremely large CSV cells
    csv.field_size_limit(sys.maxsize)
    # 1. Validation & Initialization
    if crud_mode not in ("create", "update", "delete"):
        raise ValueError(f"❌ ERROR: Invalid crud_mode: '{crud_mode}'. Allowed: 'create', 'update', 'delete'.")
    if validation_mode not in ("strict", "reject", "loose"):
        raise ValueError(f"❌ ERROR: Invalid validation_mode: '{validation_mode}'. Allowed: 'strict', 'reject', 'loose'.")

    if crud_mode == "delete":
        if const_column: raise ValueError("❌ ERROR: 'const_column' must be None for 'delete' mode.")
        if rename_column: raise ValueError("❌ ERROR: 'rename_column' must be None for 'delete' mode.")
        if ignore_column: raise ValueError("❌ ERROR: 'ignore_column' must be None for 'delete' mode.")
        if validation_mode == "loose": raise ValueError("❌ ERROR: 'validation_mode' cannot be 'loose' for 'delete' mode. Use 'strict' or 'reject'.")

    if crud_mode == "update":
        if ignore_column and "id" in ignore_column:
            raise ValueError("❌ ERROR: Cannot ignore 'id' column in 'update' mode as it is required for row identification.")
    t_start = time.time()
    db_name = pg_dsn.split('/')[-1].split('?')[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_stem = os.path.splitext(os.path.basename(csv_path))[0]
    rej_path = f"tmp/{csv_stem}_rejected_{ts}.csv"
    staging_table = f"staging_sync_{table}"
    
    def print_progress(current, total, prefix=''):
        bar_len = 40
        filled_len = int(bar_len * current // total)
        bar = '█' * filled_len + '-' * (bar_len - filled_len)
        percent = 100 * (current / total)
        sys.stdout.write(f'\r{get_ts()} {prefix} |{bar}| {percent:>.1f}%')
        sys.stdout.flush()
        if current == total: sys.stdout.write('\n')
    
    valid_consts = [c for c in const_column if isinstance(c, (tuple, list)) and len(c) == 2] if const_column else []
    valid_renames = [r for r in rename_column if isinstance(r, (tuple, list)) and len(r) == 2] if rename_column else []
    
    c_names, c_vals = [c[0] for c in valid_consts], [c[1] for c in valid_consts]
    conn = await asyncpg.connect(pg_dsn, timeout=60)
    try:
        # 1.5 Strict Existence Check
        table_exists = await conn.fetchval('SELECT to_regclass($1)', f'"{table}"' if '.' not in table else table)
        if not table_exists:
            raise ValueError(f"Table '{table}' does not exist in database '{db_name}'.")
        
        # 2. Fetch Schema Info
        q = """
        SELECT column_name, data_type, udt_name, is_nullable 
        FROM information_schema.columns 
        WHERE table_name=$1 
        ORDER BY ordinal_position
        """
        columns_records = await conn.fetch(q, table)
        if not columns_records:
            raise Exception(f"Table '{table}' not found")
        
        col_type_map = {r['column_name']: r['udt_name'] for r in columns_records}
        col_null_map = {r['column_name']: r['is_nullable'] == 'YES' for r in columns_records}
        db_cols_all = [r['column_name'] for r in columns_records]
        
        # 3. CSV Header Analysis & Sampling
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header_original = reader.fieldnames or []
            if not csv_header_original:
                raise Exception("Missing CSV header")
            
            rename_map = {old: new for old, new in valid_renames}
            reverse_rename_map = {new: old for old, new in valid_renames}
            csv_header = [rename_map.get(col, col) for col in csv_header_original]
            # Apply ignore filter
            if ignore_column:
                csv_header = [c for c in csv_header if c not in ignore_column]
                valid_renames = [r for r in valid_renames if r[0] not in ignore_column and r[1] not in ignore_column]
                
            if crud_mode in ("update", "delete") and "id" not in csv_header:
                raise ValueError(f"❌ ERROR: 'id' column is missing from CSV (required for '{crud_mode}' mode). Use rename_column if it's named differently.")
                rename_map = {old: new for old, new in valid_renames}
                reverse_rename_map = {new: old for old, new in valid_renames}
            
            if crud_mode in ("update", "delete") and "id" not in csv_header:
                raise Exception(f"CSV must contain 'id' column for {crud_mode} operations")
            if crud_mode in ("update", "delete") and "id" not in db_cols_all:
                raise Exception(f"Table '{table}' must have an 'id' column for {crud_mode} operations")
            # Sample first 100 rows for smarter type inference
            samples = list(itertools.islice(reader, 100))
            f.seek(0); f.readline() 
            def get_csv_val(row_dict, mapped_col_name):
                original_name = reverse_rename_map.get(mapped_col_name, mapped_col_name)
                return row_dict.get(original_name)
            # 4. Column Comparison Dashboard
            from wcwidth import wcswidth
            def align(text, width):
                text = str(text)
                for char in "✅❌🚫🔄➕":
                    text = text.replace(char, char + "\uFE0F")
                if text == "-": text = "- "
                res = text.center(width)
                if "⚠️" in text: res += " "
                return res
            def infer_type_for_column(mapped_col):
                vals = [get_csv_val(s, mapped_col) for s in samples if get_csv_val(s, mapped_col)]
                if not vals: return "null"
                types = set()
                for v in vals:
                    v_clean = str(v).strip()
                    if v_clean.replace('.','',1).isdigit(): 
                        types.add("float" if "." in v_clean else "integer")
                    else:
                        for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y%m%d"):
                            try: datetime.strptime(v_clean, fmt); types.add("date"); break
                            except: continue
                        else: types.add("text")
                if "text" in types: return "text"
                if "date" in types: return "date"
                if "float" in types: return "float"
                return "integer"
            rows = []
            has_error = False
            # Get original CSV headers for the dashboard (including ignored ones)
            f.seek(0); full_header = next(csv.reader(f))
            f.seek(0); f.readline()
            
            for const_name, _ in valid_consts:
                if const_name not in full_header:
                    full_header.append(f"__CONST__{const_name}")
            
            for idx, raw_col in enumerate(full_header, 1):
                is_const = raw_col.startswith("__CONST__")
                col = raw_col.replace("__CONST__", "") if is_const else raw_col
                
                if ignore_column and col in ignore_column:
                    rows.append({
                        "idx": str(idx),
                        "col": col,
                        "csv_t": "-",
                        "db_t": "-",
                        "c": "-",
                        "n": "-",
                        "p": f"🚫 {'IGNORED':<7}",
                        "rem": "Explicitly ignored by user."
                    })
                    continue
                
                if is_const:
                    csv_t = "const"
                    mapped_col = col
                else:
                    csv_t = infer_type_for_column(col)
                    mapped_col = rename_map.get(col, col)
                    
                db_t = col_type_map.get(mapped_col, "(missing)")
                m_icon = "✅" if mapped_col in db_cols_all else "🚫"
                n_icon = "✅" if col_null_map.get(mapped_col, True) else "❌"
                c_icon = "✅" if db_t not in ("text", "varchar", "character varying", "(missing)") else "❌"
                
                # Compatibility Logic
                if m_icon == "🚫":
                    p_text, rem = f"🚫 {'MISSING':<7}", "Column skipped (missing in database table)."
                elif is_const:
                    p_text, rem = f"➕ {'CONST':<7}", "Constant value injected dynamically."
                elif csv_t == "text" and any(x in db_t for x in ("int", "numeric", "real", "double")):
                    p_text, rem = f"❌ {'ERROR':<7}", f"Type Mismatch. CSV is alphanumeric 'text', but DB is '{db_t}'."
                elif csv_t == "float" and "int" in db_t and not db_t.startswith('_'):
                    p_text, rem = f"⚠️ {'WARNING':<7}", f"Truncation Risk. CSV has decimals ('float'), but DB is '{db_t}'."
                elif csv_t == "text" and ("date" in db_t or "timestamp" in db_t):
                    p_text, rem = f"⚠️ {'WARNING':<7}", "Date Format Risk. Ensure CSV strings match a standard ISO or YYYY-MM-DD format."
                elif col in rename_map:
                    p_text, rem = f"🔄 {'RENAMED':<7}", f"Mapped to DB column '{mapped_col}'."
                else:
                    p_text, rem = f"✅ {'FOUND':<7}", ""
                    
                if "❌" in p_text: has_error = True
                rows.append({
                    "idx": str(idx),
                    "col": col,
                    "csv_t": csv_t,
                    "db_t": db_t,
                    "c": c_icon,
                    "n": n_icon,
                    "p": p_text,
                    "rem": rem
                })
            # Calculate dynamic widths
            w_idx = max(len(r["idx"]) for r in rows) if rows else 3
            w_col = max(len(r["col"]) for r in rows + [{"col": "COLUMN NAME"}])
            w_csv = max(len(r["csv_t"]) for r in rows + [{"csv_t": "CSV TYPE"}])
            w_db = max(len(r["db_t"]) for r in rows + [{"db_t": "DB TYPE"}])
            w_sta = max(len(r["p"]) for r in rows + [{"p": "STATUS"}]) + 6
            w_ico = 10 # Standard width for smaller columns
            h = f"{'Idx':<{w_idx}} | {'COLUMN NAME':<{w_col}} | {'CSV TYPE':<{w_csv}} | {'DB TYPE':<{w_db}} | {align('DB CONV', w_ico)} | {align('DB NULL', w_ico)} | {align('STATUS', w_sta)} |  REMARK"
            separator_len = len(h) + 10
            # 1. Unified Summary & Schema Dashboard
            const_str = ', '.join([f'{k}={v}' for k, v in valid_consts]) if valid_consts else "None"
            rename_str = ', '.join([f'{r[0]}->{r[1]}' for r in valid_renames]) if valid_renames else "None"
            ignore_str = ', '.join(ignore_column) if ignore_column else "None"
            
            meta = [
                ("🕒", "TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                ("⚙️", "FUNC", sys._getframe().f_code.co_name),
                ("📁", "csv_path", csv_path),
                ("🔗", "pg_dsn", pg_dsn),
                ("🎯", "table", table),
                ("🛠️", "crud_mode", crud_mode.upper()),
                ("🛡️", "validation_mode", validation_mode.upper()),
                ("🔄", "rename_column", rename_str),
                ("🚫", "ignore_column", ignore_str),
                ("➕", "const_column", const_str),
                ("📡", "DB STATUS", "CONNECTED"),
                ("📊", "STATUS ICONS", "✅ FOUND, 🔄 RENAMED, ➕ CONST, ⚠️ WARNING, 🚫 MISSING, 🚫 IGNORED, ❌ ERROR")
            ]
            
            w_meta_lab = max(len(lab) for ico, lab, val in meta)
            # Icons that terminals often treat as 1-column wide, causing overlap
            single_width_icons = {"⚙️", "🛠️", "🛡️", "➕", "✅", "⏳", "⚠️", "🏗️"}
            print(f"{'-'*separator_len}")
            for ico, lab, val in meta:
                ico_norm = ico + "\uFE0F" if len(ico) == 1 else ico
                if ico_norm in single_width_icons: ico_norm += " " # visual terminal compensation
                print(f"{ico_norm} {lab:<{w_meta_lab}} : {val}")
            print(f"{'-'*separator_len}")
            print(h)
            print(f"{'-'*separator_len}")
            for r in rows:
                print(f"{r['idx']:<{w_idx}} | {r['col']:<{w_col}} | {r['csv_t']:<{w_csv}} | {r['db_t']:<{w_db}} | {align(r['c'], w_ico)} | {align(r['n'], w_ico)} | {align(r['p'], w_sta)} |  {r['rem']}")
            print(f"{'-'*separator_len}")
            
            if has_error:
                print(f"🚨 WARNING: Logical errors detected. Proceeding with 'STRICT' validation will cause a crash.")
                print(f"💡 TIP: Use validation_mode='reject' to skip bad rows, or fix your DB schema.")
                print(f"{'-'*separator_len}")
            # 5. Confirmation
            confirm = input(f"👉 Proceed with bulk {crud_mode.upper()} on '{table}'? (y/N): ").strip().lower()
            if confirm != 'y':
                print(f"\n❌ [CANCELLED] Aborted by user.")
                # Final Summary (Cancelled)
                meta_cancel = [
                    ("🕒", "START TIME", datetime.fromtimestamp(t_start).strftime('%Y-%m-%d %H:%M:%S')),
                    ("⚙️", "FUNC", sys._getframe().f_code.co_name),
                    ("📁", "csv_path", csv_path),
                    ("🔗", "pg_dsn", pg_dsn),
                    ("🎯", "table", table),
                    ("🛠️", "crud_mode", crud_mode.upper()),
                    ("🛡️", "validation_mode", validation_mode.upper()),
                    ("👤", "USER ENTERED", "NO (Aborted)"),
                    ("🕒", "END TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                ]
                w_meta_c_lab = max(len(lab) for ico, lab, val in meta_cancel)
                single_width_icons = {"⚙️", "🛠️", "🛡️", "➕", "✅", "⏳", "⚠️", "🏗️"}
                print(f"\n{'-'*separator_len}")
                for ico, lab, val in meta_cancel:
                    ico_norm = ico + "\uFE0F" if len(ico) == 1 else ico
                    if ico_norm in single_width_icons: ico_norm += " "
                    print(f"{ico_norm} {lab:<{w_meta_c_lab}} : {val}")
                print(f"{'-'*separator_len}")
                await conn.close(); return
            # 6. Row Count & Ingestion
            print(f"{get_ts()} 📊 ANALYZING: Calculating total rows in CSV...")
            import subprocess
            try:
                row_count_out = subprocess.check_output(['wc', '-l', csv_path]).split()[0]
                total_rows = int(row_count_out) - 1 # Subtract header
            except:
                total_rows = 0 # Fallback
            print(f"{get_ts()} 📊 TOTAL ROWS: {total_rows:,}")
            csv_mapped_cols = [c for c in csv_header if c in db_cols_all]
            valid_c_names = [c for c in c_names if c in db_cols_all and c not in csv_mapped_cols]
            
            if crud_mode == "delete":
                final_cols = ["id"] if "id" in csv_mapped_cols else []
            elif crud_mode == "update":
                final_cols = ["id"] + [c for c in csv_mapped_cols if c != "id"] + valid_c_names if "id" in csv_mapped_cols else []
            else:
                final_cols = [c for c in csv_mapped_cols if c != "id"] + valid_c_names
                
            if not final_cols: raise Exception("No valid columns to process")
            # 6. Execution Prep & Resume Logic
            skip_count = 0
            existing_stage = await conn.fetchval('SELECT to_regclass($1)', f'"{staging_table}"')
            if existing_stage:
                existing_count = await conn.fetchval(f'SELECT count(*) FROM "{staging_table}"')
                print(f"⚠️  NOTICE: Persistent staging table '{staging_table}' already exists with {existing_count:,} rows.")
                choice = input(f"👉 [R]esume from row {existing_count+1:,}, [O]verwrite & start fresh, or [C]ancel? (r/o/C): ").lower()
                if choice == 'r': skip_count = existing_count
                elif choice == 'o': 
                    await conn.execute(f'DROP TABLE "{staging_table}"')
                    print(f"🧹 OVERWRITING: Deleted old staging table.")
                else: print(f"❌ Aborted by user."); return
            if skip_count == 0:
                staging_cols_sql = ", ".join([f'"{c}" TEXT' for c in final_cols])
                try: await conn.execute(f'CREATE UNLOGGED TABLE "{staging_table}" ({staging_cols_sql})')
                except Exception: await conn.execute(f'CREATE TABLE "{staging_table}" ({staging_cols_sql})')
                print(f"{get_ts()} ✅ Staging area '{staging_table}' created.")
            print(f"\n{get_ts()} ⚡ PHASE 2: Ingesting Data to Staging...")
            class RowReject(Exception): pass
            def get_converter(col_name):
                t = col_type_map.get(col_name, "text")
                def converter(v):
                    v_str = str(v).strip() if v is not None else None
                    if not v_str or v_str.lower() in ("","none","null","n/a"): return None
                    try:
                        if ("int" in t or "numeric" in t or "real" in t or "double" in t) and not t.startswith('_'):
                            num = float(v_str)
                            if t == "int2" and not (-32768 <= num <= 32767): raise ValueError(f"Value {num} out of range for int2")
                            if t == "int4" and not (-2147483648 <= num <= 2147483647): raise ValueError(f"Value {num} out of range for int4")
                            if t == "int8" and not (-9223372036854775808 <= num <= 9223372036854775807): raise ValueError(f"Value {num} out of range for int8")
                        if "bool" in t: v_str = "true" if v_str.lower() in ("true","1","yes","t","y") else "false"
                        if "date" in t or "timestamp" in t:
                            for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y-%m-%d %H:%M:%S","%Y%m%d"):
                                try: dt = datetime.strptime(v_str, fmt); v_str = dt.isoformat(); break
                                except: continue
                            else: raise ValueError("No date format")
                    except Exception as e:
                        if validation_mode == "strict": raise ValueError(f"Column '{col_name}' error: {e}")
                        if validation_mode == "loose": return None
                        if validation_mode == "reject": raise RowReject(col_name)
                    return v_str
                return converter
            col_plan = [get_converter(c) for c in final_cols]
            tracker = {"rejected": 0, "rejected_cols": set()}
            def row_generator(offset=0):
                count, f_rej = offset, None
                try:
                    items = itertools.islice(reader, offset, None)
                    for row in items:
                        try:
                            line = []
                            for plan, col in zip(col_plan, final_cols):
                                if col in valid_c_names:
                                    idx = c_names.index(col)
                                    line.append(plan(c_vals[idx]))
                                else:
                                    line.append(plan(get_csv_val(row, col)))
                            yield tuple(line)
                            count += 1
                            if count % 10000 == 0 and total_rows > 0:
                                print_progress(count, total_rows, "INGESTING")
                        except RowReject as err:
                            tracker["rejected"] += 1
                            if err.args: tracker["rejected_cols"].add(str(err.args[0]))
                            if validation_mode == "reject":
                                vals = []
                                for k, v in row.items():
                                    if k is None: vals.extend(v)
                                    else: vals.append(v)
                                if f_rej is None:
                                    os.makedirs("tmp", exist_ok=True); f_rej = open(rej_path,"w",encoding='utf-8')
                                    header_out = list(csv_header_original)
                                    for i in range(len(vals) - len(header_out)): header_out.append(f"EXTRA_COL_{i+1}")
                                    csv.writer(f_rej).writerow(header_out)
                                csv.writer(f_rej).writerow(vals)
                        if (count+tracker["rejected"]) % 10000 == 0 and total_rows > 0:
                            print_progress(count + tracker["rejected"], total_rows, "INGESTING")
                finally:
                    if f_rej: f_rej.close()
                    if total_rows > 0: print_progress(total_rows, total_rows, "INGESTING")
            # Set an 8-hour timeout for the data stream
            await conn.copy_records_to_table(staging_table, records=row_generator(skip_count), columns=final_cols, timeout=28800)
            print(f"{get_ts()} ✅ Data streamed to staging.")
            async with conn.transaction():
                print(f"{get_ts()} ⚡ PHASE 3: Running Atomic {crud_mode.upper()} (Timeout: 8h)...")
                def get_cast(col):
                    t = col_type_map[col]
                    if t in ("int2", "int4", "int8"): return f'ROUND(s."{col}"::numeric)::{t}'
                    return f's."{col}"::{t}'
                if crud_mode == "delete":
                    res = await conn.execute(f'DELETE FROM "{table}" m USING "{staging_table}" s WHERE m."id" = {get_cast("id")}', timeout=28800)
                elif crud_mode == "create":
                    cols_sql = ", ".join([f'"{c}"' for c in final_cols])
                    cast_sql = ", ".join([get_cast(c) for c in final_cols])
                    res = await conn.execute(f'INSERT INTO "{table}" ({cols_sql}) SELECT {cast_sql} FROM "{staging_table}" s', timeout=28800)
                else:
                    set_sql = ", ".join([f'"{c}" = {get_cast(c)}' for c in [x for x in final_cols if x != "id"]])
                    res = await conn.execute(f'UPDATE "{table}" m SET {set_sql} FROM "{staging_table}" s WHERE m."id" = {get_cast("id")}', timeout=28800)
                
                if total_rows > 0: print_progress(total_rows, total_rows, "COMPLETED")
                print(f"{'-'*separator_len}\n{get_ts()} ✅ COMPLETED: {res} | ⏱️  {int(time.time()-t_start)}s\n{'-'*separator_len}\n")
                
                await conn.execute(f'DROP TABLE "{staging_table}"')
                print(f"{get_ts()} 🧹 Cleanup: Staging table dropped.")
                print(f"{get_ts()} ✅ Ingestion finished successfully.")
    finally:
        await conn.close()
    # 10. FINAL SUMMARY
    t_end = time.time()
    duration = t_end - t_start
    h_duration = f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m {int(duration % 60)}s"
    
    meta_final = [
        ("🕒", "START TIME", datetime.fromtimestamp(t_start).strftime('%Y-%m-%d %H:%M:%S')),
        ("⚙️", "FUNC", sys._getframe().f_code.co_name),
        ("📁", "csv_path", csv_path),
        ("🔗", "pg_dsn", pg_dsn),
        ("🎯", "table", table),
        ("🛠️", "crud_mode", crud_mode.upper()),
        ("🛡️", "validation_mode", validation_mode.upper()),
        ("👤", "USER ENTERED", "YES (Proceed)"),
        ("🏗️", "STAGING TABLE", "CREATED -> DELETED"),
        ("📊", "TOTAL ROWS", f"{total_rows:,}"),
        ("✅", "STATUS", "SUCCESS"),
        ("⏳", "DURATION", h_duration),
        ("🕒", "END TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ]
    
    if validation_mode == "reject" and tracker.get("rejected", 0) > 0:
        meta_final.insert(-2, ("⚠️", "REJECTED ROWS", f"{tracker['rejected']:,} (Saved to {rej_path})"))
        if tracker.get("rejected_cols"):
            cols_str = ", ".join(sorted(tracker["rejected_cols"]))
            meta_final.insert(-2, ("🚫", "REJECTED COLS", cols_str))
    
    # Final Receipt with Manual Alignment
    w_meta_f_lab = max(len(lab) for ico, lab, val in meta_final)
    single_width_icons = {"⚙️", "🛠️", "🛡️", "➕", "✅", "⏳", "⚠️", "🏗️"}
    print(f"\n{'-'*separator_len}")
    for ico, lab, val in meta_final:
        ico_norm = ico + "\uFE0F" if len(ico) == 1 else ico
        if ico_norm in single_width_icons: ico_norm += " "
        print(f"{ico_norm} {lab:<{w_meta_f_lab}} : {val}")
    print(f"{'-'*separator_len}\n")
