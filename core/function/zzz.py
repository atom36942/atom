def func_postgres_sql_parallel(*, conn_str: str, sql_list: list[str]) -> dict:
    """Execute SQL list in parallel, automatically saturating the database's parallel worker pool."""
    import subprocess,time,sys
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor,as_completed
    t_start = time.time()
    def get_ts(): return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
    if not sql_list:
        print(f"{get_ts()} ⚠️  No SQL statements provided.")
        return "done"
    def print_progress(current, total, prefix=''):
        bar_len = 40
        filled_len = int(bar_len * current // total) if total > 0 else 0
        bar = '█' * filled_len + '-' * (bar_len - filled_len)
        percent = 100 * (current / total) if total > 0 else 0
        sys.stdout.write(f'\r{get_ts()} {prefix} |{bar}| {percent:>.1f}%')
        sys.stdout.flush()
        if current == total: sys.stdout.write('\n')
    def psql_scalar(sql:str)->int:
        p=subprocess.run(["psql",conn_str,"-tA","-v","ON_ERROR_STOP=1","-c",sql],capture_output=True,text=True)
        if p.returncode!=0:raise RuntimeError(p.stderr.strip())
        out=p.stdout.strip()
        return int(out) if out else 0
    try:
        mpw=psql_scalar("SHOW max_parallel_workers;")
        mpg=psql_scalar("SHOW max_parallel_workers_per_gather;")
    except Exception:
        mpw,mpg=0,0
    actual_parallel=min(mpw, 16) if mpw>0 else 8
    setup="SET work_mem='512MB'; SET maintenance_work_mem='1GB'; SET max_parallel_workers_per_gather=4; SET synchronous_commit=OFF;"
    meta = [
        ("🕒", "START TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ("⚙️", "FUNC", "func_postgres_sql_parallel"),
        ("🔗", "CONN_STR", conn_str.split('@')[-1] if '@' in conn_str else conn_str), 
        ("📊", "TOTAL SQL", f"{len(sql_list):,}"),
        ("⚡", "PARALLEL", f"{actual_parallel} workers (Auto-Saturated)"),
        ("🏗️", "WORKERS", f"max={mpw}, per_gather={mpg}"),
        ("📡", "STATUS", "AGGRESSIVE MODE")
    ]
    w_meta_lab = max(len(lab) for ico, lab, val in meta)
    single_width_icons = {"⚙️", "🛠️", "🛡️", "➕", "✅", "⏳", "⚠️", "🏗️", "⚡", "📡"}
    separator_len = 80
    print(f"{'-'*separator_len}")
    for ico, lab, val in meta:
        ico_norm = ico + "\uFE0F" if len(ico) == 1 else ico
        if ico_norm in single_width_icons: ico_norm += " "
        print(f"{ico_norm} {lab:<{w_meta_lab}} : {val}")
    print(f"{'-'*separator_len}")
    def run(sql:str):
        t0=time.time()
        p=subprocess.run(["psql",conn_str,"-v","ON_ERROR_STOP=1","-c",f"{setup} {sql}"],capture_output=True,text=True)
        dt=round(time.time()-t0,2)
        return {"sql":sql,"rc":p.returncode,"out":p.stdout,"err":p.stderr,"time_s":dt}
    results=[]; ok=0; fail=0
    print(f"{get_ts()} ⚡ PHASE 1: Executing SQL List in Parallel...")
    with ThreadPoolExecutor(max_workers=actual_parallel) as ex:
        futures=[ex.submit(run,s) for s in sql_list]
        for idx, f in enumerate(as_completed(futures), 1):
            r=f.result(); results.append(r)
            if r["rc"]==0:
                ok+=1
            else:
                fail+=1
                sys.stdout.write('\n')
                print(f"{get_ts()} ❌ FAIL :: {r['sql']}\n{r['err']}")
            print_progress(idx, len(sql_list), "EXECUTING")
    total_time=round(time.time()-t_start,2)
    h_duration = f"{int(total_time // 3600)}h {int((total_time % 3600) // 60)}m {int(total_time % 60)}s"
    status="success" if fail==0 else ("partial" if ok>0 else "failed")
    meta_final = [
        ("🕒", "START TIME", datetime.fromtimestamp(t_start).strftime('%Y-%m-%d %H:%M:%S')),
        ("⚙️", "FUNC", "func_postgres_sql_parallel"),
        ("📊", "TOTAL SQL", f"{len(sql_list):,}"),
        ("✅", "SUCCESS", f"{ok:,}"),
        ("❌", "FAILED", f"{fail:,}"),
        ("⏳", "DURATION", h_duration),
        ("🏆", "STATUS", status.upper()),
        ("🕒", "END TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ]
    w_meta_f_lab = max(len(lab) for ico, lab, val in meta_final)
    print(f"\n{'-'*separator_len}")
    for ico, lab, val in meta_final:
        ico_norm = ico + "\uFE0F" if len(ico) == 1 else ico
        if ico_norm in single_width_icons: ico_norm += " "
        print(f"{ico_norm} {lab:<{w_meta_f_lab}} : {val}")
    print(f"{'-'*separator_len}\n")
    return "done"

async def func_postgres_csv_ingestion(*, csv_path: str, pg_dsn: str, table: str, crud_mode: str, validation_mode: str, rename_column: list[list] | None, ignore_column: list[str] | None, const_column: list[list] | None):
    """Performs high-performance bulk operations from a CSV to Postgres."""
    import os
    import sys
    import csv
    import time
    import itertools
    import asyncpg
    from datetime import datetime
    csv.field_size_limit(sys.maxsize)
    if crud_mode not in ("create", "update", "delete"):
        raise ValueError(f"Invalid crud_mode: '{crud_mode}'")
    if validation_mode not in ("strict", "reject", "loose"):
        raise ValueError(f"Invalid validation_mode: '{validation_mode}'")
    if crud_mode == "delete":
        if const_column:
            raise ValueError("'const_column' must be None for 'delete' mode.")
        if ignore_column:
            raise ValueError("'ignore_column' must be None for 'delete' mode.")
    if crud_mode == "update":
        if ignore_column and "id" in ignore_column:
            raise ValueError("Cannot ignore 'id' column in 'update' mode.")
    t_start = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_stem = os.path.splitext(os.path.basename(csv_path))[0]
    rej_path = f"tmp/{csv_stem}_rejected_{ts}.csv"
    staging_table = f"staging_sync_{table}"
    valid_consts = [c for c in const_column if isinstance(c, (tuple, list)) and len(c) == 2] if const_column else []
    valid_renames = [r for r in rename_column if isinstance(r, (tuple, list)) and len(r) == 2] if rename_column else []
    c_names = [c[0] for c in valid_consts]
    c_vals = [c[1] for c in valid_consts]
    rename_map = {old: new for old, new in valid_renames}
    reverse_rename_map = {new: old for old, new in valid_renames}
    conn = await asyncpg.connect(pg_dsn, timeout=60)
    try:
        # 1. Fetch Schema Info
        q = "SELECT column_name, udt_name, is_nullable FROM information_schema.columns WHERE table_name=$1"
        columns_records = await conn.fetch(q, table)
        if not columns_records:
            raise ValueError(f"Table '{table}' not found")
        col_type_map = {r['column_name']: r['udt_name'] for r in columns_records}
        db_cols_all = [r['column_name'] for r in columns_records]
        # 2. Open File for Sampling (and capture headers)
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            csv_header_original = reader.fieldnames or []
            if not csv_header_original:
                raise Exception("Missing CSV header")
            csv_header = [rename_map.get(col, col) for col in csv_header_original]
            if ignore_column:
                csv_header = [c for c in csv_header if c not in ignore_column]
            if crud_mode in ("update", "delete") and "id" not in csv_header:
                raise ValueError(f"id column is missing from CSV (required for {crud_mode})")
            # We don't need to actually sample here if we just want headers, 
            # but we'll read one row to ensure the file is valid.
            itertools.islice(reader, 1)
        # 3. Define the Ingestion Generator (Total Isolation Strategy)
        def get_csv_val(row_dict, mapped_col_name):
            original_name = reverse_rename_map.get(mapped_col_name, mapped_col_name)
            return row_dict.get(original_name)
        class RowReject(Exception): pass
        def get_converter(col_name):
            t = col_type_map.get(col_name, "text")
            def converter(v):
                v_str = str(v).strip() if v is not None else None
                if not v_str or v_str.lower() in ("","none","null","n/a"):
                    return None
                try:
                    if ("int" in t or "numeric" in t or "real" in t or "double" in t) and not t.startswith('_'):
                        float(v_str)
                    if "bool" in t:
                        v_str = "true" if v_str.lower() in ("true","1","yes","t","y") else "false"
                    if "date" in t or "timestamp" in t:
                        for fmt in ("%Y-%m-%d","%d-%m-%Y","%m/%d/%Y","%Y-%m-%d %H:%M:%S","%Y%m%d"):
                            try:
                                dt = datetime.strptime(v_str, fmt)
                                v_str = dt.isoformat()
                                break
                            except:
                                continue
                        else:
                            raise ValueError("Invalid date format")
                except Exception:
                    if validation_mode == "strict":
                        raise ValueError(f"Column '{col_name}' error")
                    if validation_mode == "reject":
                        raise RowReject(col_name)
                    return None
                return v_str
            return converter
        csv_mapped_cols = [c for c in csv_header if c in db_cols_all]
        valid_c_names = [c for c in c_names if c in db_cols_all and c not in csv_mapped_cols]
        if crud_mode == "delete":
            final_cols = ["id"] if "id" in csv_mapped_cols else []
        elif crud_mode == "update":
            final_cols = ["id"] + [c for c in csv_mapped_cols if c != "id"] + valid_c_names
        else:
            final_cols = csv_mapped_cols + valid_c_names
        col_plan = [get_converter(c) for c in final_cols]
        tracker = {"rejected": 0}
        def row_generator(offset=0):
            # TOTAL ISOLATION: Re-open the file from scratch for the ingestion phase.
            with open(csv_path, newline='', encoding='utf-8') as f_ingest:
                ingest_reader = csv.DictReader(f_ingest)
                items = itertools.islice(ingest_reader, offset, None)
                f_rej = None
                try:
                    for row in items:
                        try:
                            line = []
                            for plan, col in zip(col_plan, final_cols):
                                if col in valid_c_names:
                                    line.append(plan(c_vals[c_names.index(col)]))
                                else:
                                    line.append(plan(get_csv_val(row, col)))
                            yield tuple(line)
                        except RowReject:
                            tracker["rejected"] += 1
                            if validation_mode == "reject":
                                if not f_rej:
                                    os.makedirs("tmp", exist_ok=True)
                                    f_rej = open(rej_path,"w",encoding='utf-8')
                                    csv.writer(f_rej).writerow(csv_header_original)
                                csv.writer(f_rej).writerow(row.values())
                finally:
                    if f_rej:
                        f_rej.close()
        # 4. Execute Ingestion
        staging_cols_sql = ", ".join([f'"{c}" TEXT' for c in final_cols])
        await conn.execute(f'DROP TABLE IF EXISTS "{staging_table}"')
        await conn.execute(f'CREATE TEMP TABLE "{staging_table}" ({staging_cols_sql})')
        await conn.copy_records_to_table(staging_table, records=row_generator(0), columns=final_cols, timeout=28800)
        async with conn.transaction():
            def get_cast(cl):
                ct = col_type_map[cl]
                if ct in ("int2", "int4", "int8"):
                    return f'ROUND(s."{cl}"::numeric)::{ct}'
                return f's."{cl}"::{ct}'
            if crud_mode == "delete":
                await conn.execute(f'DELETE FROM "{table}" m USING "{staging_table}" s WHERE m."id" = {get_cast("id")}')
            elif crud_mode == "create":
                c_sql = ", ".join([f'"{c}"' for c in final_cols])
                ct_sql = ", ".join([get_cast(c) for c in final_cols])
                await conn.execute(f'INSERT INTO "{table}" ({c_sql}) SELECT {ct_sql} FROM "{staging_table}" s')
            else:
                s_sql = ", ".join([f'"{c}" = {get_cast(c)}' for c in [x for x in final_cols if x != "id"]])
                await conn.execute(f'UPDATE "{table}" m SET {s_sql} FROM "{staging_table}" s WHERE m."id" = {get_cast("id")}')
            await conn.execute(f'DROP TABLE IF EXISTS "{staging_table}"')
        return "done"
    finally:
        await conn.close()