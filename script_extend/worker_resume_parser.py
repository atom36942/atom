# command: venv/bin/python -m script_extend.worker_resume_parser

# info: Polls resume files from S3/Azure storage and parses them with LLM providers into PostgreSQL.

# import
import asyncio
import contextlib
import json
import os
import tempfile
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import aiohttp
import asyncpg
import boto3
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from google.genai import types
from function import func_client_postgres
from function import func_client_openai
from function import func_client_gemini

# config
from config import config_postgres_url_dict
from config import config_openai_key
from config import config_gemini_key
from config import config_ai_services
from config import config_azure_account_name
from config import config_azure_account_key
from config import config_aws_access_key_id
from config import config_aws_secret_access_key

# setting
AI_SERVICE = "gemini"
TABLE_NAME = "jobseeker"
BASE_COLUMNS = {"id", "created_at", "created_by_id", "updated_at", "updated_by_id", "deleted_at", "deleted_by_id", "deactivated_at", "deactivated_by_id", "verified_at", "verified_by_id", "resume_url", "resume_content", "status", "worker_status", "worker_last_error", "metadata", "worker_retry_count", "worker_next_retry_at", "worker_processed_at", "rating", "remark"}
BATCH_LIMIT = 100
WORKER_RETRY_DELAY_SEC = [60, 300, 3600, 86400]
CONCURRENCY_LIMIT = 20
POLL_INTERVAL_SEC = 5
GEMINI_MODEL = "gemini-2.5-flash"
RESUME_EXTENSIONS = (".pdf", ".docx", ".txt", ".doc")
RESUME_PROMPT = """You are an expert Talent Acquisition Specialist evaluating a candidate's resume.
INSTRUCTIONS:
1. Extract the candidate's information from their resume exactly as per the JSON schema provided.
2. For any missing numeric values (like current/expected CTC), output null. For missing arrays, output empty array [].
3. For 'company_current', extract ONLY the most recent or active employer. Do not list past companies.
4. For 'company_past', extract an array of all past companies.
5. For 'college', extract an array of all colleges attended.
6. For 'profile', extract a relevant and concise professional profile or headline for the candidate (e.g. 'Software Engineer', 'Product Manager').
7. Evaluate the candidate's overall profile strength, skills, and experience. Be a STRICT, highly critical Recruiter.
8. Provide an 'ai_rating' (1.0 to 10.0). Grading must be strict: an average, standard resume is a 5.0. Only the top 1% of elite candidates get above 8.5. Penalize for lack of measurable achievements, bad formatting, or unexplained gaps.
9. Provide an 'ai_remark' detailing your feedback. Format it clearly as: "Pros: [1-2 key strengths]. Cons: [1-2 weaknesses, missing skills, or red flags]." Be ruthlessly honest."""

# logic
def retry_delay_sec(*, retry_count: int) -> int:
    return WORKER_RETRY_DELAY_SEC[min(max(retry_count, 0), len(WORKER_RETRY_DELAY_SEC) - 1)]

def ai_client_open(*, ai_service: str, ai_service_list: list, openai_key: str, gemini_key: str):
    """The Gemini client the worker parses with; exits when the chosen service isn't usable."""
    if ai_service not in ai_service_list: raise SystemExit(f"Error: AI_SERVICE must be one of {ai_service_list}.")
    client_openai, client_gemini = func_client_openai(api_key=openai_key), func_client_gemini(api_key=gemini_key)
    if ai_service == "gemini" and not client_gemini: raise SystemExit("Error: config_gemini_key is not set. Worker requires Gemini.")
    if ai_service == "openai" and not client_openai: raise SystemExit("Error: config_openai_key is not set. Worker requires OpenAI.")
    return client_gemini

async def column_read(*, pool) -> dict:
    """{column: data type} of TABLE_NAME."""
    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name = $1", TABLE_NAME)
    if not records: raise SystemExit(f"Error: Table '{TABLE_NAME}' not found in database.")
    return {r["column_name"]: r["data_type"].lower() for r in records}

def response_schema_build(*, column_type: dict) -> dict:
    """Gemini's JSON schema: one nullable property per non-base column, typed from the database."""
    properties = {}
    for col_name, datatype in column_type.items():
        if col_name in BASE_COLUMNS: continue
        if col_name == "projects": properties[col_name] = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "description": {"type": "STRING"}, "technologies": {"type": "ARRAY", "items": {"type": "STRING"}}, "url": {"type": "STRING"}}}, "nullable": True}
        elif col_name == "certifications": properties[col_name] = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"name": {"type": "STRING"}, "issuer": {"type": "STRING"}, "year": {"type": "INTEGER"}}}, "nullable": True}
        elif datatype.startswith(("int", "bigint", "smallint")): properties[col_name] = {"type": "INTEGER", "nullable": True}
        elif datatype.startswith(("numeric", "float", "real")): properties[col_name] = {"type": "NUMBER", "nullable": True}
        elif datatype.startswith("boolean"): properties[col_name] = {"type": "BOOLEAN", "nullable": True}
        elif datatype == "array" or datatype.endswith("[]"): properties[col_name] = {"type": "ARRAY", "items": {"type": "STRING"}, "nullable": True}
        else: properties[col_name] = {"type": "STRING", "nullable": True}
    return {"type": "OBJECT", "properties": properties}

async def candidate_claim(*, conn: asyncpg.Connection, batch_limit: int) -> list:
    return await conn.fetch(f"WITH claim AS (SELECT c.id FROM {TABLE_NAME} c WHERE (c.worker_status IS NULL OR c.worker_status IN (1, 3)) AND (c.worker_next_retry_at <= NOW() OR c.worker_next_retry_at IS NULL) AND (c.resume_url IS NOT NULL OR c.resume_content IS NOT NULL) AND c.deleted_at IS NULL AND c.deactivated_at IS NULL ORDER BY c.created_at, c.id LIMIT $1 FOR UPDATE OF c SKIP LOCKED) UPDATE {TABLE_NAME} u SET worker_status = 1, worker_next_retry_at = NOW() + INTERVAL '15 minutes' FROM claim JOIN {TABLE_NAME} c ON c.id = claim.id WHERE u.id = claim.id RETURNING u.id, u.resume_url, c.resume_content, c.worker_retry_count", batch_limit)  # noqa: S608 - constant table

async def candidate_complete(*, conn: asyncpg.Connection, candidate_id: int, data: dict, column_type: dict) -> None:
    """Saves the parsed values that match a non-base column and marks the row done."""
    set_clauses, values = ["worker_status = 2", "worker_processed_at = NOW()", "worker_last_error = NULL", "updated_at = NOW()"], [candidate_id]
    for key, value in data.items():
        if key not in column_type or key in BASE_COLUMNS: continue
        if value in ("", "null", "None") or (key in ("ctc_current", "ctc_expected") and value == 0): value = None
        is_json = column_type[key] in ("json", "jsonb") and value is not None
        values.append(json.dumps(value) if is_json else value)
        set_clauses.append(f'"{key}" = ${len(values)}{"::jsonb" if is_json else ""}')
    await conn.execute(f"UPDATE {TABLE_NAME} SET {', '.join(set_clauses)} WHERE id = $1", *values)  # noqa: S608 - constant table, columns limited to existing database columns

async def candidate_fail(*, conn: asyncpg.Connection, candidate_id: int, retry_count: int, error: Exception) -> None:
    error_str = str(error)[:1000]
    if retry_count >= len(WORKER_RETRY_DELAY_SEC):
        await conn.execute(f"UPDATE {TABLE_NAME} SET worker_status = 4, worker_last_error = $2, worker_retry_count = worker_retry_count + 1, updated_at = NOW() WHERE id = $1", candidate_id, f"AI Parsing Failed (DEAD): {error_str}")  # noqa: S608 - constant table
    else:
        await conn.execute(f"UPDATE {TABLE_NAME} SET worker_status = 3, worker_last_error = $2, worker_retry_count = worker_retry_count + 1, worker_next_retry_at = NOW() + ($3 * INTERVAL '1 second'), updated_at = NOW() WHERE id = $1", candidate_id, f"AI Parsing Failed: {error_str}", retry_delay_sec(retry_count=retry_count))  # noqa: S608 - constant table

def download_url_sign(*, url: str, candidate_id: int, storage: dict) -> str:
    """A short-lived signed url for a private Azure or S3 file; the plain url otherwise."""
    if "?" in url: return url
    parsed = urllib.parse.urlparse(url)
    if "blob.core.windows.net" in url and storage["azure_account_name"] and storage["azure_account_key"]:
        parts = parsed.path.lstrip("/").split("/", 1)
        if len(parts) != 2: return url
        sas_token = generate_blob_sas(account_name=storage["azure_account_name"], account_key=storage["azure_account_key"], container_name=parts[0], blob_name=urllib.parse.unquote(parts[1]), permission=BlobSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(minutes=5))
        return f"{url}?{sas_token}"
    if "amazonaws.com" in url and storage["aws_access_key_id"] and storage["aws_secret_access_key"]:
        try:
            host_parts = parsed.netloc.split(".")
            bucket, key = (host_parts[0], parsed.path.lstrip("/")) if host_parts[0] != "s3" else parsed.path.lstrip("/").split("/", 1)
            s3_client = boto3.client("s3", aws_access_key_id=storage["aws_access_key_id"], aws_secret_access_key=storage["aws_secret_access_key"])
            return s3_client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": urllib.parse.unquote(key)}, ExpiresIn=300)
        except Exception as e:
            print(f"[resume-parser-worker] s3 presign failed candidate_id={candidate_id}, trying the plain url: {str(e)[:200]}")
    return url

async def resume_download(*, url: str, download_url: str, candidate_id: int) -> str:
    """Downloads the resume to a new temp file and returns its path; the caller removes it."""
    ext = os.path.splitext(urllib.parse.urlparse(url.split("?")[0]).path)[1].lower()
    fd, file_path = tempfile.mkstemp(prefix=f"resume_parser_{candidate_id}_", suffix=ext if ext in RESUME_EXTENSIONS else ".pdf")    # unique and created safely, unlike a fixed /tmp name
    os.close(fd)
    try:
        async with aiohttp.ClientSession() as session, session.get(download_url) as resp:
            if resp.status != 200: raise Exception(f"HTTP {resp.status} downloading {url}")
            file_bytes = await resp.read()
        await asyncio.to_thread(Path(file_path).write_bytes, file_bytes)    # other resumes keep parsing meanwhile
    except Exception as e:
        with contextlib.suppress(FileNotFoundError): os.remove(file_path)
        raise Exception(f"Failed to download resume: {e}") from e
    return file_path

def resume_parse(*, client_gemini, schema: dict, resume_content: str | None, file_path: str | None) -> dict:
    """Blocking Gemini call (run it in a thread); backs off and retries on 429."""
    contents = [f"Here is the parsed text content of the candidate's resume:\n\n{resume_content}"] if resume_content else []
    if file_path: contents.append(client_gemini.files.upload(file=file_path))
    contents.append(RESUME_PROMPT)
    for attempt in range(5):
        try:
            response = client_gemini.models.generate_content(model=GEMINI_MODEL, contents=contents, config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=0.1))
            return json.loads(response.text)
        except Exception as e:
            if "429" not in str(e) or attempt == 4: raise
            print(f"[resume-parser-worker] API Rate Limit (429) hit. Pausing for {10 * 2 ** attempt} seconds before retrying...")
            time.sleep(10 * 2 ** attempt)

async def candidate_parse(*, candidate: asyncpg.Record, client_gemini, schema: dict, storage: dict) -> dict:
    """Parses the stored resume text, or else the file at resume_url."""
    if candidate["resume_content"]: return await asyncio.to_thread(resume_parse, client_gemini=client_gemini, schema=schema, resume_content=candidate["resume_content"], file_path=None)
    if not candidate["resume_url"]: raise Exception("Neither resume_url nor resume_content was provided")
    download_url = download_url_sign(url=candidate["resume_url"], candidate_id=candidate["id"], storage=storage)
    file_path = await resume_download(url=candidate["resume_url"], download_url=download_url, candidate_id=candidate["id"])
    try: return await asyncio.to_thread(resume_parse, client_gemini=client_gemini, schema=schema, resume_content=None, file_path=file_path)
    finally:
        with contextlib.suppress(FileNotFoundError): os.remove(file_path)

async def candidate_handle(*, pool, candidate: asyncpg.Record, client_gemini, schema: dict, column_type: dict, storage: dict) -> None:
    try:
        data = await candidate_parse(candidate=candidate, client_gemini=client_gemini, schema=schema, storage=storage)
        async with pool.acquire() as conn, conn.transaction(): await candidate_complete(conn=conn, candidate_id=candidate["id"], data=data, column_type=column_type)
        print(f"[resume-parser-worker] completed candidate_id={candidate['id']}")
    except Exception as exc:
        async with pool.acquire() as conn, conn.transaction(): await candidate_fail(conn=conn, candidate_id=candidate["id"], retry_count=candidate["worker_retry_count"] or 0, error=exc)
        print(f"[resume-parser-worker] failed candidate_id={candidate['id']} error={str(exc)[:300]}")

async def worker_run_once(*, pool, client_gemini, schema: dict, column_type: dict, storage: dict) -> int:
    """Claims one batch and parses it, CONCURRENCY_LIMIT at a time; returns the candidates claimed."""
    async with pool.acquire() as conn, conn.transaction(): candidates = await candidate_claim(conn=conn, batch_limit=BATCH_LIMIT)
    if not candidates: return 0
    print(f"[resume-parser-worker] claimed {len(candidates)} candidate(s)")
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    async def candidate_handle_limited(candidate):
        async with semaphore: await candidate_handle(pool=pool, candidate=candidate, client_gemini=client_gemini, schema=schema, column_type=column_type, storage=storage)
    results = await asyncio.gather(*(candidate_handle_limited(candidate) for candidate in candidates), return_exceptions=True)
    for candidate, result in zip(candidates, results, strict=True):
        if isinstance(result, Exception): print(f"[resume-parser-worker] unexpected task error candidate_id={candidate['id']} error={str(result)[:300]}")
    return len(candidates)

async def main():
    client_gemini = ai_client_open(ai_service=AI_SERVICE, ai_service_list=config_ai_services, openai_key=config_openai_key, gemini_key=config_gemini_key)
    storage = {"azure_account_name": config_azure_account_name, "azure_account_key": config_azure_account_key, "aws_access_key_id": config_aws_access_key_id, "aws_secret_access_key": config_aws_secret_access_key}
    print(f"Starting Dynamic Resume Parser Worker Script... ai={AI_SERVICE} batch_limit={BATCH_LIMIT} concurrency_limit={CONCURRENCY_LIMIT}")
    pool = await func_client_postgres(dsn=config_postgres_url_dict["master"], min_size=1, max_size=20)
    try:
        column_type = await column_read(pool=pool)
        schema = response_schema_build(column_type=column_type)
        idle_count = 0
        while True:
            if await worker_run_once(pool=pool, client_gemini=client_gemini, schema=schema, column_type=column_type, storage=storage):
                idle_count = 0
                await asyncio.sleep(1)
                continue
            idle_count += 1
            if idle_count == 1 or idle_count % 12 == 0: print("[resume-parser-worker] no pending candidates; sleeping...")
            await asyncio.sleep(POLL_INTERVAL_SEC)
    finally:
        await pool.close()

# main
if __name__ == "__main__":
    asyncio.run(main())
