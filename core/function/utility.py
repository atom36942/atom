async def func_token_encode(*, user: dict, config_token_secret_key: str, config_token_expiry_sec: int, config_token_refresh_expiry_sec: int, config_token_key: list) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    import jwt, orjson, time
    if user is None: return None
    payload_dict = {k: user.get(k) for k in config_token_key} if config_token_key else dict(user) if isinstance(user, dict) else user
    serialized_payload = orjson.dumps(payload_dict, default=str).decode("utf-8")
    now_ts = int(time.time())
    access_token = jwt.encode({"exp": now_ts + config_token_expiry_sec, "data": serialized_payload, "type": "access"}, config_token_secret_key)
    refresh_token = jwt.encode({"exp": now_ts + config_token_refresh_expiry_sec, "data": serialized_payload, "type": "refresh"}, config_token_secret_key)
    return {"token": access_token, "token_refresh": refresh_token, "token_expiry_sec": config_token_expiry_sec, "token_refresh_expiry_sec": config_token_refresh_expiry_sec}

async def func_otp_generate(*, client_postgres_pool: any, email: str, mobile: str) -> int:
    """Generate a random 6-digit OTP and store it in PostgreSQL for a given email or mobile."""
    import random
    otp = random.randint(100000, 999999)
    query = "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3);"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, otp, email.strip().lower() if email else None, mobile.strip() if mobile else None)
    return otp

async def func_otp_verify(*, client_postgres_pool: any, otp: int, email: str, mobile: str, config_expiry_sec_otp: int) -> None:
    """Verify an OTP for email or mobile within its expiration window."""
    if not otp: raise Exception("otp code missing")
    if not email and not mobile: raise Exception("missing both email and mobile")
    if email and mobile: raise Exception("provide only one identifier")
    if email:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email.strip().lower()
    else:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile.strip()
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, identifier)
        if not records: raise Exception("otp not found")
        if records[0]["otp"] != otp: raise Exception("invalid otp code")
        if not records[0]["is_active"]: raise Exception("otp code expired")
    return None

async def func_api_file_to_chunks(*, upload_file: any, chunk_size: int):
    """Generator: reads an uploaded CSV file in chunks and yields lists of dictionaries."""
    import csv, io
    content = await upload_file.read()
    f = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(f)
    chunk = []
    for row in reader:
        chunk.append(row)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk: yield chunk

async def func_regex_check(*, config_regex: dict, obj_list: list):
    """Validate fields in a list of objects against regex patterns defined in config."""
    import re
    if not config_regex: return
    for obj in obj_list:
        for key, regex_info in config_regex.items():
            val = obj.get(key)
            if val is not None:
                pattern = regex_info[0]
                error_msg = regex_info[1]
                if not re.match(pattern, str(val)):
                    raise Exception(error_msg)
