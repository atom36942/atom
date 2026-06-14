# packages
import asyncio
import json
import os
import sys
import tempfile
import time
import traceback
import urllib.parse
from datetime import datetime, timedelta, timezone
import aiohttp
import asyncpg
import boto3
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from google import genai
from google.genai import types

# config
from config import config_postgres_url
from config import config_gemini_key
from config import config_azure_account_name
from config import config_azure_account_key
from config import config_aws_access_key_id
from config import config_aws_secret_access_key

# logic
async def execute():
    TABLE_NAME = "jobseeker"
    BASE_COLUMNS = {"id", "created_at", "created_by_id", "updated_at", "updated_by_id", "deleted_at", "deleted_by_id", "deactivated_at", "deactivated_by_id", "verified_at", "verified_by_id", "resume_url", "resume_content", "status", "worker_status", "worker_last_error", "metadata", "worker_retry_count", "worker_next_retry_at", "worker_processed_at", "rating", "remark"}
    BATCH_LIMIT = 5
    worker_retry_delay_sec = [60, 300, 3600, 86400]
    CONCURRENCY_LIMIT = 3
    if not config_gemini_key:
        print("Error: config_gemini_key is not set. Worker requires Gemini.")
        return
    print(f"Starting Dynamic Resume Parser Worker Script... batch_limit={BATCH_LIMIT} concurrency_limit={CONCURRENCY_LIMIT}")
    client_gemini = genai.Client(api_key=config_gemini_key)
    pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=1, max_size=5, server_settings={"application_name": "atom-daemon-resume-parser"})
    async with pool.acquire() as conn:
        records = await conn.fetch(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1", TABLE_NAME)
        if not records:
            print(f"Error: Table '{TABLE_NAME}' not found in database.")
            return
        candidate_cols = [{"name": r["column_name"], "datatype": r["data_type"]} for r in records]
        candidate_col_names = {r["name"] for r in candidate_cols}
    def func_get_dynamic_schema() -> dict:
        properties = {}
        for col in candidate_cols:
            col_name = col["name"]
            if col_name in BASE_COLUMNS:
                continue
            datatype = col["datatype"].lower()
            if datatype.startswith("int") or datatype.startswith("bigint") or datatype.startswith("smallint"):
                properties[col_name] = {"type": "INTEGER", "nullable": True}
            elif datatype.startswith("numeric") or datatype.startswith("float") or datatype.startswith("real"):
                properties[col_name] = {"type": "NUMBER", "nullable": True}
            elif datatype.startswith("boolean"):
                properties[col_name] = {"type": "BOOLEAN", "nullable": True}
            elif datatype == "array" or datatype.endswith("[]"):
                properties[col_name] = {"type": "ARRAY", "items": {"type": "STRING"}, "nullable": True}
            else:
                properties[col_name] = {"type": "STRING", "nullable": True}
        return {"type": "OBJECT", "properties": properties}
    async def func_claim_candidates(conn: asyncpg.Connection, batch_limit: int) -> list:
        return await conn.fetch(f"WITH claim AS (SELECT c.id FROM {TABLE_NAME} c WHERE (c.worker_status IS NULL OR c.worker_status IN (1, 3)) AND (c.worker_next_retry_at <= NOW() OR c.worker_next_retry_at IS NULL) AND (c.resume_url IS NOT NULL OR c.resume_content IS NOT NULL) AND c.deleted_at IS NULL ORDER BY c.created_at, c.id LIMIT $1 FOR UPDATE OF c SKIP LOCKED) UPDATE {TABLE_NAME} u SET worker_status = 1, worker_next_retry_at = NOW() + INTERVAL '15 minutes' FROM claim JOIN {TABLE_NAME} c ON c.id = claim.id WHERE u.id = claim.id RETURNING u.id, u.resume_url, c.resume_content, c.worker_retry_count", batch_limit)
    async def func_mark_completed(conn: asyncpg.Connection, candidate_id: int, data: dict) -> None:
        update_data = {k: v for k, v in data.items() if k in candidate_col_names and k not in BASE_COLUMNS}
        if not update_data:
            await conn.execute(f"UPDATE {TABLE_NAME} SET worker_status = 2, worker_processed_at = NOW(), worker_last_error = NULL, updated_at = NOW() WHERE id = $1", candidate_id)
            return
        set_clauses = ["worker_status = 2", "worker_processed_at = NOW()", "worker_last_error = NULL", "updated_at = NOW()"]
        values = [candidate_id]
        for i, (key, value) in enumerate(update_data.items(), start=2):
            if value in ("", "null", "None"):
                value = None
            if key in ("ctc_current", "ctc_expected") and value == 0:
                value = None
            set_clauses.append(f'"{key}" = ${i}')
            values.append(value)
        set_query = ", ".join(set_clauses)
        query = f"UPDATE {TABLE_NAME} SET {set_query} WHERE id = $1"
        await conn.execute(query, *values)
    def func_retry_delay_sec(retry_count: int) -> int:
        index = min(max(retry_count, 0), len(worker_retry_delay_sec) - 1)
        return worker_retry_delay_sec[index]
    async def func_mark_failed(conn: asyncpg.Connection, candidate_id: int, retry_count: int, error: Exception) -> None:
        error_str = str(error)[:1000]
        if retry_count >= len(worker_retry_delay_sec):
            await conn.execute(f"UPDATE {TABLE_NAME} SET worker_status = 4, worker_last_error = $2, worker_retry_count = worker_retry_count + 1, updated_at = NOW() WHERE id = $1", candidate_id, f"AI Parsing Failed (DEAD): {error_str}")
        else:
            delay_sec = func_retry_delay_sec(retry_count)
            await conn.execute(f"UPDATE {TABLE_NAME} SET worker_status = 3, worker_last_error = $2, worker_retry_count = worker_retry_count + 1, worker_next_retry_at = NOW() + ($3 * INTERVAL '1 second'), updated_at = NOW() WHERE id = $1", candidate_id, f"AI Parsing Failed: {error_str}", delay_sec)
    async def func_process_candidate(candidate: asyncpg.Record) -> dict:
        candidate_id = candidate["id"]
        resume_url = candidate["resume_url"]
        resume_content = candidate["resume_content"]
        temp_file_path = None
        gemini_contents_input = []
        if resume_content:
            gemini_contents_input.append(f"Here is the parsed text content of the candidate's resume:\n\n{resume_content}")
        elif resume_url:
            parsed_url = urllib.parse.urlparse(resume_url.split('?')[0])
            ext = os.path.splitext(parsed_url.path)[1].lower()
            if ext not in ['.pdf', '.docx', '.txt', '.doc']:
                ext = '.pdf'
            temp_file_path = f"/tmp/resume_parser_{candidate_id}{ext}"
            download_url = resume_url
            if "blob.core.windows.net" in download_url and "?" not in download_url and config_azure_account_name and config_azure_account_key:
                try:
                    parsed = urllib.parse.urlparse(download_url)
                    parts = parsed.path.lstrip("/").split("/", 1)
                    if len(parts) == 2:
                        container, blob_name = parts
                        sas_token = generate_blob_sas(account_name=config_azure_account_name, account_key=config_azure_account_key, container_name=container, blob_name=urllib.parse.unquote(blob_name), permission=BlobSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(minutes=5))
                        download_url = f"{download_url}?{sas_token}"
                except ImportError:
                    pass
            elif "amazonaws.com" in download_url and "?" not in download_url and config_aws_access_key_id and config_aws_secret_access_key:
                try:
                    parsed = urllib.parse.urlparse(download_url)
                    host_parts = parsed.netloc.split(".")
                    if host_parts[0] != "s3":
                        bucket = host_parts[0]
                        key = parsed.path.lstrip("/")
                    else:
                        parts = parsed.path.lstrip("/").split("/", 1)
                        bucket, key = parts[0], parts[1]
                    s3_client = boto3.client('s3', aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
                    download_url = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': urllib.parse.unquote(key)}, ExpiresIn=300)
                except Exception:
                    pass
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as resp:
                        if resp.status != 200:
                            raise Exception(f"HTTP {resp.status} downloading {resume_url}")
                        file_bytes = await resp.read()
                with open(temp_file_path, "wb") as f:
                    f.write(file_bytes)
            except Exception as e:
                raise Exception(f"Failed to download resume: {e}")
        else:
            raise Exception("Neither resume_url nor resume_content was provided")

        try:
            def process_with_gemini():
                schema = func_get_dynamic_schema()
                prompt = f"""
                You are an expert Talent Acquisition Specialist evaluating a candidate's resume.
                
                INSTRUCTIONS:
                1. Extract the candidate's information from their resume exactly as per the JSON schema provided.
                2. For any missing numeric values (like current/expected CTC), output null. For missing arrays, output empty array [].
                3. For 'company_current', extract ONLY the most recent or active employer. Do not list past companies.
                4. For 'company_past', extract all past companies and combine them as a comma-separated string (e.g. "Google, Facebook").
                5. If there are multiple colleges, combine them as a comma-separated string (e.g. "MIT, Harvard").
                6. For 'profile', extract a relevant and concise professional profile or headline for the candidate (e.g. 'Software Engineer', 'Product Manager').
                7. Evaluate the candidate's overall profile strength, skills, and experience. 
                8. Provide an objective 'ai_rating' (1.0 to 10.0) indicating their general employability and strength of their resume.
                9. Provide an 'ai_remark' (max 2 sentences) justifying the rating and highlighting their key strengths or areas for improvement.
                """
                
                contents_to_send = gemini_contents_input.copy()
                if temp_file_path and os.path.exists(temp_file_path):
                    uploaded_file = client_gemini.files.upload(file=temp_file_path)
                    contents_to_send.append(uploaded_file)
                contents_to_send.append(prompt)

                for attempt in range(5):
                    try:
                        response = client_gemini.models.generate_content(model='gemini-2.5-flash', contents=contents_to_send, config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=0.1))
                        return response.text
                    except Exception as e:
                        if "429" in str(e) and attempt < 4:
                            sleep_time = 10 * (2 ** attempt)
                            print(f"[resume-parser-worker] API Rate Limit (429) hit. Pausing for {sleep_time} seconds before retrying...")
                            time.sleep(sleep_time)
                        else:
                            raise e
            extracted_text = await asyncio.to_thread(process_with_gemini)
            return json.loads(extracted_text)
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    async def process_and_update(candidate: asyncpg.Record):
        try:
            data = await func_process_candidate(candidate)
            async with pool.acquire() as task_conn:
                async with task_conn.transaction():
                    await func_mark_completed(task_conn, candidate["id"], data)
            print(f"[resume-parser-worker] completed candidate_id={candidate['id']}")
        except Exception as exc:
            async with pool.acquire() as task_conn:
                async with task_conn.transaction():
                    retry_count = candidate["worker_retry_count"] or 0
                    await func_mark_failed(task_conn, candidate["id"], retry_count, exc)
            print(f"[resume-parser-worker] failed candidate_id={candidate['id']} error={str(exc)[:300]}")
    async def func_resume_parser_worker_once() -> int:
        async with pool.acquire() as conn:
            async with conn.transaction():
                candidates = await func_claim_candidates(conn, BATCH_LIMIT)
        if candidates:
            print(f"[resume-parser-worker] claimed {len(candidates)} candidate(s)")
            semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
            async def process_with_limit(candidate: asyncpg.Record):
                async with semaphore:
                    await process_and_update(candidate)
            results = await asyncio.gather(*(process_with_limit(candidate) for candidate in candidates), return_exceptions=True)
            for candidate, result in zip(candidates, results):
                if isinstance(result, Exception):
                    print(f"[resume-parser-worker] unexpected task error candidate_id={candidate['id']} error={str(result)[:300]}")
        return len(candidates)
    try:
        idle_count = 0
        while True:
            processed = await func_resume_parser_worker_once()
            if processed:
                idle_count = 0
                await asyncio.sleep(1)
            else:
                idle_count += 1
                if idle_count == 1 or idle_count % 12 == 0:
                    print("[resume-parser-worker] no pending candidates; sleeping...")
                await asyncio.sleep(5)
    finally:
        await pool.close()

# init
if __name__ == "__main__":
    asyncio.run(execute())
