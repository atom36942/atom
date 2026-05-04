async def func_table_tag_read(*, client_postgres_pool: any, table: str, column: str, limit: int, page: int, filter_column: str, filter_value: any) -> list:
    """Read unique tags/items from an array column with occurrence counts."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(column)):
        raise Exception(f"invalid identifier {column}")
    if filter_column and not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(filter_column)):
        raise Exception(f"invalid identifier {filter_column}")
    where_clause = ""
    query_args = []
    if filter_column and filter_value is not None:
        where_clause = f"WHERE x.{filter_column}=$1"
        query_args = [filter_value]
    query = f"SELECT tag_item, count(*) FROM {table} x CROSS JOIN LATERAL unnest(x.{column}) tag_item {where_clause} GROUP BY tag_item ORDER BY count(*) DESC LIMIT {limit} OFFSET {(page-1)*limit}"
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch(query, *query_args)
    return [{"tag": row["tag_item"], "count": row["count"]} for row in rows]

async def func_parent_read(*, client_postgres_pool: any, table: str, parent_column: str, parent_table: str, created_by_id: int, order: str, limit: int, page: int) -> list:
    """Read parent records based on child table's foreign key column (identifier validated)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(parent_column)):
        raise Exception(f"invalid identifier {parent_column}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(parent_table)):
        raise Exception(f"invalid identifier {parent_table}")
    query = f"WITH x AS (SELECT {parent_column} FROM {table} WHERE ($1::bigint IS NULL OR created_by_id=$1) ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit}) SELECT ct.* FROM x LEFT JOIN {parent_table} ct ON x.{parent_column}=ct.id;"
    async with client_postgres_pool.acquire() as conn:
        return [dict(r) for r in (await conn.fetch(query, created_by_id))]

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
        if mode == "read" or ql.startswith(("select", "with", "explain", "show", "describe")) or "returning" in ql:
            rows = await conn.fetch(query, timeout=15)
            return [dict(r) for r in rows]
        return await conn.execute(query, timeout=15)

async def func_postgres_export(*, client_postgres_pool: any, query: str) -> any:
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

def func_postgres_sql_parallel(*,conn_str:str,sql_list:list[str])->dict:
    import subprocess,time,sys
    from datetime import datetime
    from concurrent.futures import ThreadPoolExecutor,as_completed
    t_start = time.time()
    def get_ts(): return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
    if not sql_list:
        print(f"{get_ts()} ⚠️  No SQL statements provided.")
        return {"status":"no_sql","total":0,"success":0,"failed":0,"details":[]}
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
    auto=max(1,mpw//mpg) if mpw>0 and mpg>0 else 2
    max_parallel=min(auto,3)
    setup="SET work_mem='256MB'; SET max_parallel_workers_per_gather=4;"
    # 1. Metadata Dashboard
    meta = [
        ("🕒", "START TIME", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ("⚙️", "FUNC", "func_postgres_sql_parallel"),
        ("🔗", "CONN_STR", conn_str.split('@')[-1] if '@' in conn_str else conn_str), 
        ("📊", "TOTAL SQL", f"{len(sql_list):,}"),
        ("⚡", "PARALLEL", f"{max_parallel} workers"),
        ("🏗️", "WORKERS", f"max={mpw}, per_gather={mpg}"),
        ("📡", "STATUS", "READY")
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
    with ThreadPoolExecutor(max_workers=max_parallel) as ex:
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
    # Final Receipt
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
    return {"status":status,"total":len(sql_list),"success":ok,"failed":fail,"elapsed_s":total_time,"parallel":max_parallel,"details":results}