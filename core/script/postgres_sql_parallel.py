# import
import os
import subprocess
import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# config
PG_URL = os.getenv("PG_URL")
SQL_LIST = [
    "SELECT 1;",
    "SELECT 2;",
    "SELECT 3;"
]

# func
def func_postgres_sql_parallel(*, conn_str: str, sql_list: list[str]) -> dict:
    """Execute SQL list in parallel, automatically saturating the database's parallel worker pool."""
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
    separator_len = 80
    single_width_icons = {"⚙️", "🛠️", "🛡️", "➕", "✅", "⏳", "⚠️", "🏗️", "⚡", "📡"}
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

# init
if __name__ == "__main__":
    print("Starting sample parallel SQL execution...")
    if not PG_URL:
        raise ValueError("PG_URL environment variable is not set. Please set it before running this script.")
        
    try:
        result = func_postgres_sql_parallel(
            conn_str=PG_URL,
            sql_list=SQL_LIST
        )
        print(f"Parallel SQL execution result: {result}")
    except Exception as e:
        print(f"Execution failed: {e}")
        print("\nNote: Make sure to set the PG_URL environment variable with a valid, running PostgreSQL connection string.")
