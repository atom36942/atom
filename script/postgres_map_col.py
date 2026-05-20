#!/usr/bin/env python3
"""
Highly Optimized Parallel PostgreSQL Batch Update Script for 300M+ Rows.
Uses asyncpg for direct high-performance binary-protocol communication with PostgreSQL.
"""

import os
import sys
import json
import time
import asyncio
from urllib.parse import urlparse, unquote
import pandas as pd
import asyncpg

# ==========================================
# CONFIGURATION
# ==========================================
DB_URL = ""
TABLE_NAME = "master"
CSV_FILE = "mapping.csv"

# Concurrency & Batch Settings
CONCURRENT_WORKERS = 4       # Reduced to 4 workers for optimal stability on Azure DB
CHUNK_SIZE_PK = 20000        # Reduced chunk size to 20,000 rows to ensure rapid execution and prevent any database statement timeouts
CHUNK_SIZE_TID = 2000        # Reduced page chunk size for safety
MAX_RETRIES = 5              # Max retry attempts for transient DB connections
RETRY_DELAY = 3              # Seconds to wait between retries
PROGRESS_FILE = "migration_progress.json"
STATEMENT_TIMEOUT_MS = 0     # 0 disables PostgreSQL statement_timeout for long-running chunks
LOCK_TIMEOUT_MS = 0          # 0 waits for row locks instead of failing long-running chunks
MIN_SPLIT_SIZE_PK = 100      # Smallest PK range to try when a large chunk keeps timing out
MIN_SPLIT_SIZE_TID = 1       # Smallest CTID page range to try when a large chunk keeps timing out

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def parse_db_url(url):
    """
    Safely parses the connection URL, unquoting URL-encoded passwords (like %26 -> &).
    """
    parsed = urlparse(url)
    kwargs = {
        'user': unquote(parsed.username) if parsed.username else None,
        'password': unquote(parsed.password) if parsed.password else None,
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/') if parsed.path else None,
    }
    
    # Configure SSL
    if 'sslmode' in parsed.query:
        query_params = dict(q.split('=') for q in parsed.query.split('&')) if parsed.query else {}
        ssl_mode = query_params.get('sslmode', 'require')
        if ssl_mode in ('require', 'verify-full', 'verify-ca'):
            kwargs['ssl'] = 'require'
    else:
        kwargs['ssl'] = 'require'
        
    return kwargs

def load_mapping_csv(filepath):
    """
    Loads mapping.csv and cleans input columns, handling missing values.
    """
    if not os.path.exists(filepath):
        print(f"[Error] CSV file '{filepath}' not found!")
        sys.exit(1)
        
    df = pd.read_csv(filepath)
    df.columns = [col.strip() for col in df.columns]
    
    hs_col = 'HS Code 2 Digit'
    group_col = 'Commodity Group Cleaned'
    
    if hs_col not in df.columns or group_col not in df.columns:
        print(f"[Error] CSV must contain columns: '{hs_col}' and '{group_col}'")
        print(f"Available columns: {list(df.columns)}")
        sys.exit(1)
        
    mapping_list = []
    for _, row in df.iterrows():
        val1 = row[hs_col]
        val2 = row[group_col]
        
        if pd.isna(val1):
            continue
            
        code_str = str(val1).strip()
        # Clean any float conversions (e.g. 1.0 -> 1)
        if code_str.endswith('.0'):
            code_str = code_str[:-2]
            
        cleaned_str = str(val2).strip() if pd.notna(val2) else None
        
        mapping_list.append({
            "code": code_str,
            "cleaned": cleaned_str
        })
        
    print(f"[CSV] Loaded {len(mapping_list)} mappings from '{filepath}'")
    return mapping_list

def load_progress():
    """
    Loads checkpoint state to resume seamlessly.
    """
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get('completed_chunks', []))
        except Exception as e:
            print(f"[Warning] Failed to load progress file: {e}. Starting fresh.")
    return set()

def save_progress(completed_chunks):
    """
    Saves checkpoint state to disk.
    """
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump({'completed_chunks': list(completed_chunks)}, f)
    except Exception as e:
        print(f"[Warning] Failed to save progress file: {e}")

# ==========================================
# SCHEMA DISCOVERY
# ==========================================

async def detect_column_type(conn, table_name, column_name):
    """
    Detects if a column is an integer or character type to construct precise queries.
    """
    query = """
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = $1 AND column_name = $2;
    """
    row = await conn.fetchrow(query, table_name, column_name)
    if row:
        dt = row['data_type'].lower()
        if 'int' in dt:
            return 'integer'
        elif 'numeric' in dt or 'decimal' in dt:
            return 'numeric'
        else:
            return 'text'
    return 'text'

async def detect_chunking_strategy(conn, table_name):
    """
    Determines the best chunking strategy based on database indexes and primary keys.
    """
    # 1. Search for primary key
    pk_query = """
        SELECT a.attname AS pk_column, format_type(a.atttypid, a.atttypmod) AS pk_type
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = $1::regclass AND i.indisprimary;
    """
    try:
        row = await conn.fetchrow(pk_query, table_name)
        if row:
            pk_col = row['pk_column']
            pk_type = row['pk_type'].lower()
            if 'int' in pk_type:
                print(f"[Schema] Found integer Primary Key: \"{pk_col}\" ({pk_type})")
                return {'type': 'pk', 'column': pk_col, 'data_type': 'integer'}
    except Exception as e:
        print(f"[Schema] Primary Key query skipped or failed: {e}")

    # 2. Check if a column named 'id' exists and is an integer
    id_query = """
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = $1 AND column_name = 'id';
    """
    try:
        row = await conn.fetchrow(id_query, table_name)
        if row:
            dt = row['data_type'].lower()
            if 'int' in dt:
                print(f"[Schema] Found non-PK numeric column \"id\" ({dt}). Using it for chunking.")
                return {'type': 'pk', 'column': 'id', 'data_type': 'integer'}
    except Exception as e:
        print(f"[Schema] ID check failed: {e}")

    # 3. Fallback to physical CTID chunking
    print("[Schema] No suitable integer Primary Key found. Using physical CTID-based page chunking.")
    return {'type': 'ctid'}

# ==========================================
# WORKER EXECUTION
# ==========================================

def is_statement_timeout(exc):
    """
    True when PostgreSQL cancelled the query because statement_timeout was hit.
    """
    sqlstate = getattr(exc, 'sqlstate', None)
    return sqlstate == '57014' or 'statement timeout' in str(exc).lower()

async def setup_connection(conn):
    """
    Applies per-session settings once for every connection in the pool.
    """
    await conn.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS};")
    await conn.execute(f"SET lock_timeout = {LOCK_TIMEOUT_MS};")
    await conn.execute("SET idle_in_transaction_session_timeout = 0;")

async def execute_chunk_with_retry(pool, query, mapping_json, start_val, end_val):
    """
    Runs the update query on a chunk with built-in retry and connection recovery.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with pool.acquire() as conn:
                result = await conn.execute(query, mapping_json, start_val, end_val)
                
                # Parse rows updated (Postgres returns "UPDATE count")
                parts = result.split()
                if len(parts) >= 2:
                    return int(parts[1])
                return 0
        except Exception as e:
            if is_statement_timeout(e):
                raise
            if attempt == MAX_RETRIES:
                raise e
            print(f"\n[Warning] Chunk update failed (attempt {attempt}/{MAX_RETRIES}): {e}. Retrying in {RETRY_DELAY}s...")
            await asyncio.sleep(RETRY_DELAY)

async def execute_chunk_adaptive(pool, query, mapping_json, chunk, strategy):
    """
    Executes a chunk. If PostgreSQL still cancels it, split only that chunk into
    smaller ranges so existing checkpoint indexes remain valid.
    """
    pending_ranges = [chunk]
    total_affected = 0
    min_split_size = MIN_SPLIT_SIZE_PK if strategy['type'] == 'pk' else MIN_SPLIT_SIZE_TID

    while pending_ranges:
        start_raw, end_raw = pending_ranges.pop()

        if strategy['type'] == 'pk':
            start_val, end_val = start_raw, end_raw
        else:
            start_val, end_val = f"({start_raw}, 0)", f"({end_raw}, 0)"

        try:
            total_affected += await execute_chunk_with_retry(pool, query, mapping_json, start_val, end_val)
        except Exception as e:
            range_size = end_raw - start_raw
            if is_statement_timeout(e) and range_size > min_split_size:
                midpoint = start_raw + (range_size // 2)
                print(
                    f"\n[Warning] Chunk range {start_raw}-{end_raw} timed out. "
                    f"Splitting into {start_raw}-{midpoint} and {midpoint}-{end_raw}."
                )
                pending_ranges.append((midpoint, end_raw))
                pending_ranges.append((start_raw, midpoint))
                continue
            raise

    return total_affected

# ==========================================
# CORE ORCHESTRATION
# ==========================================

async def main():
    print("=" * 60)
    print("    POSTGRESQL HIGH-PERFORMANCE MIGRATION UTILITY")
    print("=" * 60)
    
    # 1. Parse connection string
    db_kwargs = parse_db_url(DB_URL)
    print(f"[DB] Connecting to host: {db_kwargs['host']} as user {db_kwargs['user']}...")
    
    # Create single inspection connection
    try:
        conn = await asyncpg.connect(**db_kwargs)
    except Exception as e:
        print(f"[Error] Failed to connect to database: {e}")
        sys.exit(1)
        
    # 2. Inspect table columns and types
    print(f"[Schema] Analysing columns on table \"{TABLE_NAME}\"...")
    
    hs_code_db_type = await detect_column_type(conn, TABLE_NAME, "HS Code 2 Digit")
    target_col_db_type = await detect_column_type(conn, TABLE_NAME, "Commodity Group Cleaned")
    
    print(f"[Schema] Column \"HS Code 2 Digit\" type: {hs_code_db_type}")
    print(f"[Schema] Column \"Commodity Group Cleaned\" type: {target_col_db_type}")
    
    # 3. Detect chunking strategy
    strategy = await detect_chunking_strategy(conn, TABLE_NAME)
    
    # 4. Load CSV data
    mapping_list = load_mapping_csv(CSV_FILE)
    mapping_json = json.dumps(mapping_list)
    
    # 5. Define Chunks
    chunks = []
    
    if strategy['type'] == 'pk':
        pk_col = strategy['column']
        print(f"[Strategy] Fetching ID bounds from \"{TABLE_NAME}\"...")
        bounds = await conn.fetchrow(f"SELECT MIN(\"{pk_col}\") AS min_id, MAX(\"{pk_col}\") AS max_id FROM \"{TABLE_NAME}\"")
        min_id, max_id = bounds['min_id'], bounds['max_id']
        
        if min_id is None or max_id is None:
            print("[Error] Table is empty or no valid numeric IDs found.")
            await conn.close()
            sys.exit(0)
            
        print(f"[Strategy] ID range: {min_id} to {max_id}")
        
        current_id = min_id
        while current_id <= max_id:
            chunks.append((current_id, current_id + CHUNK_SIZE_PK))
            current_id += CHUNK_SIZE_PK
            
        # SQL Template for Primary Key
        sql_query = f"""
            WITH mapping_data AS (
                SELECT (x->>'code')::{hs_code_db_type} AS code, x->>'cleaned' AS cleaned
                FROM jsonb_array_elements($1::jsonb) AS x
            ),
            chunk_rows AS MATERIALIZED (
                SELECT ctid, "HS Code 2 Digit", "Commodity Group Cleaned"
                FROM "{TABLE_NAME}"
                WHERE "{pk_col}" >= $2 AND "{pk_col}" < $3
            )
            UPDATE "{TABLE_NAME}" AS m
            SET "Commodity Group Cleaned" = map.cleaned
            FROM chunk_rows chunk
            JOIN mapping_data map
              ON chunk."HS Code 2 Digit" = map.code
            WHERE m.ctid = chunk.ctid
              AND chunk."Commodity Group Cleaned" IS DISTINCT FROM map.cleaned;
        """
    else:
        # Fallback CTID strategy
        print(f"[Strategy] Fetching page bounds from \"{TABLE_NAME}\"...")
        row = await conn.fetchrow(f"SELECT relpages FROM pg_class WHERE relname = $1", TABLE_NAME)
        relpages = row['relpages']
        
        if relpages < 10:
            print("[Strategy] Page count is low. Running ANALYZE to update statistics...")
            await conn.execute(f"ANALYZE \"{TABLE_NAME}\"")
            row = await conn.fetchrow(f"SELECT relpages FROM pg_class WHERE relname = $1", TABLE_NAME)
            relpages = row['relpages']
            
        print(f"[Strategy] Total physical pages: {relpages}")
        
        current_page = 0
        while current_page < relpages:
            next_page = min(current_page + CHUNK_SIZE_TID, relpages)
            chunks.append((current_page, next_page))
            current_page = next_page
            
        # SQL Template for CTID
        sql_query = f"""
            WITH mapping_data AS (
                SELECT (x->>'code')::{hs_code_db_type} AS code, x->>'cleaned' AS cleaned
                FROM jsonb_array_elements($1::jsonb) AS x
            ),
            chunk_rows AS MATERIALIZED (
                SELECT ctid, "HS Code 2 Digit", "Commodity Group Cleaned"
                FROM "{TABLE_NAME}"
                WHERE ctid >= $2::tid AND ctid < $3::tid
            )
            UPDATE "{TABLE_NAME}" AS m
            SET "Commodity Group Cleaned" = map.cleaned
            FROM chunk_rows chunk
            JOIN mapping_data map
              ON chunk."HS Code 2 Digit" = map.code
            WHERE m.ctid = chunk.ctid
              AND chunk."Commodity Group Cleaned" IS DISTINCT FROM map.cleaned;
        """
        
    await conn.close()
    
    total_chunks = len(chunks)
    print(f"[Orchestration] Created {total_chunks} chunk tasks.")
    
    # 6. Load progress
    completed_chunks = load_progress()
    pending_chunks = [i for i, chunk in enumerate(chunks) if i not in completed_chunks]
    
    if len(completed_chunks) > 0:
        print(f"[Resume] Found checkpoint file. {len(completed_chunks)}/{total_chunks} chunks already processed.")
        print(f"[Resume] Remaining chunks to process: {len(pending_chunks)}")
    
    if not pending_chunks:
        print("[Done] All chunks are already complete!")
        sys.exit(0)
        
    # 7. Start Asynchronous Pool
    pool = await asyncpg.create_pool(
        **db_kwargs,
        min_size=CONCURRENT_WORKERS,
        max_size=CONCURRENT_WORKERS,
        setup=setup_connection,
    )
    
    # Shared progress counters
    queue = asyncio.Queue()
    for chunk_idx in pending_chunks:
        await queue.put(chunk_idx)
        
    total_updated_rows = 0
    chunks_processed_this_run = 0
    start_time = time.time()
    last_logged_milestone = (len(completed_chunks) / total_chunks) * 100
    progress_lock = asyncio.Lock()
    
    # Beautiful progress printing helper
    def print_progress():
        nonlocal total_updated_rows, chunks_processed_this_run, last_logged_milestone
        elapsed = time.time() - start_time
        overall_completed = len(completed_chunks)
        percent = (overall_completed / total_chunks) * 100
        
        # Calculate speed (chunks/sec)
        speed = chunks_processed_this_run / elapsed if elapsed > 0 else 0
        eta_sec = (total_chunks - overall_completed) / speed if speed > 0 else 0
        
        # Format ETA
        if eta_sec > 3600:
            eta_str = f"{eta_sec/3600:.1f}h"
        elif eta_sec > 60:
            eta_str = f"{eta_sec/60:.1f}m"
        else:
            eta_str = f"{eta_sec:.1f}s"
            
        # Permanent milestone logging every 5% of overall progress
        if percent - last_logged_milestone >= 5.0 or (percent == 100.0 and last_logged_milestone < 100.0):
            sys.stdout.write(
                f"\n[Milestone] {percent:6.2f}% complete | Chunks: {overall_completed}/{total_chunks} | "
                f"Updated Rows: {total_updated_rows:,} | Speed: {speed:5.2f} chk/s | ETA: {eta_str}\n"
            )
            last_logged_milestone = percent
            
        sys.stdout.write(
            f"\rProgress: {percent:6.2f}% | Chunks: {overall_completed}/{total_chunks} | "
            f"Updated Rows: {total_updated_rows:,} | Speed: {speed:5.2f} chk/s | ETA: {eta_str}     "
        )
        sys.stdout.flush()

    # Worker Task
    async def worker():
        nonlocal total_updated_rows, chunks_processed_this_run
        while not queue.empty():
            try:
                idx = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
            chunk = chunks[idx]
                
            try:
                affected = await execute_chunk_adaptive(pool, sql_query, mapping_json, chunk, strategy)
                
                async with progress_lock:
                    # Update stats
                    total_updated_rows += affected
                    completed_chunks.add(idx)
                    chunks_processed_this_run += 1
                    
                    # Checkpoint save progress
                    save_progress(completed_chunks)
                        
                    print_progress()
            except Exception as e:
                print(f"\n[Fatal Error] Chunk {idx} ({chunk}) failed permanently: {e}")
                # Save progress and quit
                save_progress(completed_chunks)
                sys.exit(1)
            finally:
                queue.task_done()
                
    # Run workers
    print(f"[Orchestration] Spawning {CONCURRENT_WORKERS} concurrent workers...")
    print_progress()
    
    workers = [asyncio.create_task(worker()) for _ in range(CONCURRENT_WORKERS)]
    
    try:
        await asyncio.gather(*workers)
    except KeyboardInterrupt:
        print("\n[Interrupt] Execution halted by user. Saving checkpoints...")
        save_progress(completed_chunks)
        print("[Interrupt] Progress saved. You can resume by running the script again.")
        sys.exit(0)
    finally:
        await pool.close()
        
    save_progress(completed_chunks)
    print_progress()
    print("\n" + "=" * 60)
    print("    MIGRATION SUCCESSFULLY COMPLETED!")
    print(f"    Total Rows Updated: {total_updated_rows:,}")
    print(f"    Total Elapsed Time: {time.time() - start_time:.1f} seconds")
    print("=" * 60)

if __name__ == "__main__":
    # Ensure pandas loaded cleanly
    pd.set_option('display.max_columns', None)
    
    # Run loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Interrupt] Exiting cleanly.")
        sys.exit(0)
