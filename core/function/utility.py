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
    if chunk:
        yield chunk

def func_file_size_read(*, file_path: str) -> str:
    """Read and format the size of a file in a human-readable string."""
    import os
    if not os.path.exists(file_path):
        return "0 B"
    size = os.path.getsize(file_path)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def func_converter_number(*, type: str, mode: str, x: any) -> any:
    """Encode strings into specific-size integers or decode them back using a custom charset."""
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}
    charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"
    if type not in type_limits:
        raise ValueError(f"invalid type: {type}, allowed: {list(type_limits.keys())}")
    base = len(charset)
    max_len = type_limits[type]
    if mode == "encode":
        val_str = str(x)
        val_len = len(val_str)
        if val_len > max_len:
            raise ValueError(f"input too long {val_len} > {max_len}")
        result_num = val_len
        for char in val_str:
            char_idx = charset.find(char)
            if char_idx == -1:
                raise ValueError("invalid character in input")
            result_num = result_num * base + char_idx
        return result_num
    if mode == "decode":
        try:
            num_val = int(x)
        except Exception:
            raise ValueError("invalid integer for decoding")
        decoded_chars = []
        while num_val > 0:
            num_val, reminder = divmod(num_val, base)
            decoded_chars.append(charset[reminder])
        return "".join(decoded_chars[::-1][1:]) if decoded_chars else ""

def func_folder_reset(*, folder_path: str) -> None:
    """Safely clear all contents of a directory while maintaining the directory itself."""
    import os, shutil
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception:
                pass
    else:
        os.makedirs(folder_path, exist_ok=True)
    return None

async def func_token_encode(*, user: dict, config_token_secret_key: str, config_token_expiry_sec: int, config_token_refresh_expiry_sec: int, config_token_key: list) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    import jwt, orjson, time
    if user is None:
        return None
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
    if not otp:
        raise Exception("otp code missing")
    if not email and not mobile:
        raise Exception("missing both email and mobile")
    if email and mobile:
        raise Exception("provide only one identifier")
    if email:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email.strip().lower()
    else:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile.strip()
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, identifier)
        if not records:
            raise Exception("otp not found")
        if records[0]["otp"] != otp:
            raise Exception("invalid otp code")
        if not records[0]["is_active"]:
            raise Exception("otp code expired")
    return None