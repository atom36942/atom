async def func_auth_signup_username_password(*, client_postgres_pool: any, client_password_hasher: any, type: int, username: str, password: str, config_is_signup: int, config_auth_type: list) -> dict:
    """Handle user signup with username and password, including validation of global signup toggle and allowed identifier types."""
    if config_is_signup == 0:
        raise Exception("signup disabled")
    if type not in config_auth_type:
        raise Exception(f"authentication type {type} not allowed")
    username = username.strip().lower()
    password = client_password_hasher.hash(str(password))
    query = "INSERT INTO users (type, username, password) VALUES ($1, $2, $3) RETURNING *;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, type, username, password)
        return dict(records[0])

async def func_auth_login_username_password(*, client_postgres_pool: any, client_password_hasher: any, type: int, username: str, password: str) -> dict:
    """Authenticate a user using username and password with Argon2id verification."""
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username=$2 ORDER BY id DESC LIMIT 1;", type, username)
        if not records:
            raise Exception("username not found")
        try:
            client_password_hasher.verify(records[0]["password"], str(password))
        except Exception:
            raise Exception("incorrect password")
        return dict(records[0])

async def func_auth_login_email_password(*, client_postgres_pool: any, client_password_hasher: any, type: int, email: str, password: str) -> dict:
    """Authenticate a user using email address and password with Argon2id verification."""
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", type, email)
        if not records:
            raise Exception("email not found")
        try:
            client_password_hasher.verify(records[0]["password"], str(password))
        except Exception:
            raise Exception("incorrect password")
    return dict(records[0])

async def func_auth_login_mobile_password(*, client_postgres_pool: any, client_password_hasher: any, type: int, mobile: str, password: str) -> dict:
    """Authenticate a user using mobile number and password with Argon2id verification."""
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", type, mobile)
        if not records:
            raise Exception("mobile not found")
        try:
            client_password_hasher.verify(records[0]["password"], str(password))
        except Exception:
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
