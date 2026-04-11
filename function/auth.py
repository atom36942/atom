
async def func_auth_signup_username_password(client_postgres_pool: any, func_password_hash: callable, user_type: int, username_raw: str, password_raw: str, name_raw: str = None, config_is_signup: int = None, config_auth_type: list = None) -> dict:
    """Handle user signup with username and password, including validation of global signup toggle and allowed identifier types."""
    config_is_signup = config_is_signup if config_is_signup is not None else 1
    config_auth_type = config_auth_type or [1, 2, 3]
    if config_is_signup == 0:
        raise Exception("signup disabled")
    if user_type not in config_auth_type:
        raise Exception(f"authentication type {user_type} not allowed")
    username = username_raw.strip().lower()
    password = func_password_hash(password_raw)
    query = "INSERT INTO users (type, username, password, name) VALUES ($1, $2, $3, $4) RETURNING *;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_type, username, password, name_raw)
        return dict(records[0])

async def func_auth_signup_username_password_bigint(client_postgres_pool: any, user_type: int, username_bigint: int, password_bigint: int, config_is_signup: int, config_auth_type: list) -> dict:
    """Register a new user with bigint identifier and bigint password (for specialized devices)."""
    if config_is_signup == 0:
        raise Exception("signup disabled")
    if user_type not in config_auth_type:
        raise Exception(f"type not allowed: {user_type}, allowed: {config_auth_type}")
    query = "INSERT INTO users (type, username_bigint, password_bigint) VALUES ($1, $2, $3) RETURNING *;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_type, username_bigint, password_bigint)
        return dict(records[0])

async def func_auth_login_password_username(client_postgres_pool: any, func_password_hash: callable, user_type: int, password_raw: str, username: str) -> dict:
    """Authenticate a user using username and password."""
    hashed_pwd = func_password_hash(password_raw)
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username=$2 ORDER BY id DESC LIMIT 1;", user_type, username)
        if not records:
            raise Exception("username not found")
        if records[0]["password"] != hashed_pwd:
            raise Exception("incorrect password")
        return dict(records[0])

async def func_auth_login_password_username_bigint(client_postgres_pool: any, user_type: int, password_bigint: int, username_bigint: int) -> dict:
    """Authenticate a user using bigint identifier and bigint password."""
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username_bigint=$2 ORDER BY id DESC LIMIT 1;", user_type, username_bigint)
        if not records:
            raise Exception("username not found")
        if int(records[0]["password_bigint"]) != int(password_bigint):
            raise Exception("incorrect password")
    return dict(records[0])

async def func_auth_login_password_email(client_postgres_pool: any, func_password_hash: callable, user_type: int, password_raw: str, email_address: str) -> dict:
    """Authenticate a user using email address and password."""
    hashed_pwd = func_password_hash(password_raw)
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", user_type, email_address)
        if not records:
            raise Exception("email not found")
        if records[0]["password"] != hashed_pwd:
            raise Exception("incorrect password")
    return dict(records[0])

async def func_auth_login_password_mobile(client_postgres_pool: any, func_password_hash: callable, user_type: int, password_raw: str, mobile_number: str) -> dict:
    """Authenticate a user using mobile number and password."""
    hashed_pwd = func_password_hash(password_raw)
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", user_type, mobile_number)
        if not records:
            raise Exception("mobile not found")
        if records[0]["password"] != hashed_pwd:
            raise Exception("incorrect password")
    return dict(records[0])

async def func_auth_login_otp_email(client_postgres_pool: any, user_type: int, email_address: str, config_auth_type: list) -> dict:
    """Authenticate or register a user using email OTP with type validation."""
    if config_auth_type and user_type not in config_auth_type:
        raise Exception(f"type not allowed: {user_type}, allowed: {config_auth_type}")
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", user_type, email_address)
        if records:
            return dict(records[0])
        new_records = await conn.fetch("INSERT INTO users (type, email) VALUES ($1, $2) RETURNING *;", user_type, email_address)
        return dict(new_records[0])

async def func_auth_login_otp_mobile(client_postgres_pool: any, user_type: int, mobile_number: str, config_auth_type: list) -> dict:
    """Authenticate or register a user using mobile OTP with type validation."""
    if config_auth_type and user_type not in config_auth_type:
        raise Exception(f"type not allowed: {user_type}, allowed: {config_auth_type}")
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", user_type, mobile_number)
        if records:
            return dict(records[0])
        new_records = await conn.fetch("INSERT INTO users (type, mobile) VALUES ($1, $2) RETURNING *;", user_type, mobile_number)
        return dict(new_records[0])

async def func_auth_login_google(client_postgres_pool: any, func_google_verify: callable, func_serialize: callable, config_google_login_client_id: str, user_type: int, google_token: str, config_auth_type: list) -> dict:
    """Validate a Google ID token and perform user login or signup based on the verified identity."""
    if user_type not in config_auth_type:
        raise Exception(f"authentication type {user_type} not allowed")
    id_info = func_google_verify(google_token, config_google_login_client_id)
    if not id_info:
        raise Exception("invalid google token")
    google_id = id_info["sub"]
    email = id_info.get("email")
    name = id_info.get("name")
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE google_login_id=$1 AND type=$2;", google_id, user_type)
        if records:
            return dict(records[0])
        records = await conn.fetch("INSERT INTO users (type, google_login_id, email, name, google_login_metadata) VALUES ($1, $2, $3, $4, $5) RETURNING *;", user_type, google_id, email, name, func_serialize(id_info).decode('utf-8'))
        return dict(records[0])
