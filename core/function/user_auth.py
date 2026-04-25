def func_password_hash(*, password_raw: any) -> str:
    """Generate SHA-256 hash of the provided password string."""
    import hashlib
    return hashlib.sha256(str(password_raw).encode()).hexdigest()

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

async def func_auth_signup_username_password(*, client_postgres_pool: any, func_password_hash: callable, type: int, username: str, password: str, config_is_signup: int, config_auth_type: list) -> dict:
    """Handle user signup with username and password, including validation of global signup toggle and allowed identifier types."""
    if config_is_signup == 0:
        raise Exception("signup disabled")
    if type not in config_auth_type:
        raise Exception(f"authentication type {type} not allowed")
    username = username.strip().lower()
    password = func_password_hash(password_raw=password)
    query = "INSERT INTO users (type, username, password) VALUES ($1, $2, $3) RETURNING *;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, type, username, password)
        return dict(records[0])

async def func_auth_signup_username_password_bigint(*, client_postgres_pool: any, type: int, username_bigint: int, password_bigint: int, config_is_signup: int, config_auth_type: list) -> dict:
    """Register a new user with bigint identifier and bigint password (for specialized devices)."""
    if config_is_signup == 0:
        raise Exception("signup disabled")
    if type not in config_auth_type:
        raise Exception(f"type not allowed: {type}, allowed: {config_auth_type}")
    query = "INSERT INTO users (type, username_bigint, password_bigint) VALUES ($1, $2, $3) RETURNING *;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, type, username_bigint, password_bigint)
        return dict(records[0])

async def func_auth_login_username_password(*, client_postgres_pool: any, func_password_hash: callable, type: int, username: str, password: str) -> dict:
    """Authenticate a user using username and password."""
    hashed_pwd = func_password_hash(password_raw=password)
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username=$2 ORDER BY id DESC LIMIT 1;", type, username)
        if not records:
            raise Exception("username not found")
        if records[0]["password"] != hashed_pwd:
            raise Exception("incorrect password")
        return dict(records[0])

async def func_auth_login_username_password_bigint(*, client_postgres_pool: any, type: int, username_bigint: int, password_bigint: int) -> dict:
    """Authenticate a user using bigint identifier and bigint password."""
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username_bigint=$2 ORDER BY id DESC LIMIT 1;", type, username_bigint)
        if not records:
            raise Exception("username not found")
        if int(records[0]["password_bigint"]) != int(password_bigint):
            raise Exception("incorrect password")
    return dict(records[0])

async def func_auth_login_email_password(*, client_postgres_pool: any, func_password_hash: callable, type: int, email: str, password: str) -> dict:
    """Authenticate a user using email address and password."""
    hashed_pwd = func_password_hash(password_raw=password)
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", type, email)
        if not records:
            raise Exception("email not found")
        if records[0]["password"] != hashed_pwd:
            raise Exception("incorrect password")
    return dict(records[0])

async def func_auth_login_mobile_password(*, client_postgres_pool: any, func_password_hash: callable, type: int, mobile: str, password: str) -> dict:
    """Authenticate a user using mobile number and password."""
    hashed_pwd = func_password_hash(password_raw=password)
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", type, mobile)
        if not records:
            raise Exception("mobile not found")
        if records[0]["password"] != hashed_pwd:
            raise Exception("incorrect password")
    return dict(records[0])

async def func_auth_login_email_otp(*, client_postgres_pool: any, type: int, email: str, config_auth_type: list) -> dict:
    """Authenticate or register a user using email OTP with type validation."""
    if type not in config_auth_type:
        raise Exception(f"type not allowed: {type}, allowed: {config_auth_type}")
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", type, email)
        if records:
            return dict(records[0])
        new_records = await conn.fetch("INSERT INTO users (type, email) VALUES ($1, $2) RETURNING *;", type, email)
        return dict(new_records[0])

async def func_auth_login_mobile_otp(*, client_postgres_pool: any, type: int, mobile: str, config_auth_type: list) -> dict:
    """Authenticate or register a user using mobile OTP with type validation."""
    if type not in config_auth_type:
        raise Exception(f"type not allowed: {type}, allowed: {config_auth_type}")
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", type, mobile)
        if records:
            return dict(records[0])
        new_records = await conn.fetch("INSERT INTO users (type, mobile) VALUES ($1, $2) RETURNING *;", type, mobile)
        return dict(new_records[0])

async def func_auth_login_google(*, client_postgres_pool: any, func_serialize: callable, config_google_login_client_id: str, type: int, google_token: str, config_auth_type: list) -> dict:
    """Validate a Google ID token and perform user login or signup based on the verified identity."""
    if type not in config_auth_type:
        raise Exception(f"authentication type {type} not allowed")
    from google.oauth2 import id_token
    from google.auth.transport import requests
    id_info = id_token.verify_oauth2_token(id_token=google_token, request=requests.Request(), audience=config_google_login_client_id)
    if not id_info:
        raise Exception("invalid google token")
    google_id = id_info["sub"]
    email = id_info.get("email")
    name = id_info.get("name")
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE google_login_id=$1 AND type=$2;", google_id, type)
        if records:
            return dict(records[0])
        records = await conn.fetch("INSERT INTO users (type, google_login_id, email, name, google_login_metadata) VALUES ($1, $2, $3, $4, $5) RETURNING *;", type, google_id, email, name, func_serialize(id_info).decode('utf-8'))
        return dict(records[0])
