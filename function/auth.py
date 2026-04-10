async def func_authenticate(headers: dict, request_path: str, config_token_secret_key: str, config_api_roles_auth: list) -> dict:
    """Validate request authentication using JWT tokens or external provider keys if required for the endpoint path."""
    if not any(request_path.startswith(prefix) for prefix in config_api_roles_auth):
        return {}
    import jwt
    auth_header = headers.get("authorization")
    if not auth_header:
        raise Exception("authentication required (authorization header missing)")
    try:
        token = auth_header.split(" ")[1]
        return jwt.decode(token, config_token_secret_key, algorithms=["HS256"])
    except Exception:
        raise Exception("authentication token invalid or expired")

async def func_otp_generate(client_postgres_pool: any, email: str, mobile: str, func_postgres_create: callable, func_postgres_obj_serialize: callable, config_table: dict) -> int:
    """Generate and store a random 6-digit OTP for email or mobile verification."""
    import random
    otp = random.randint(100000, 999999)
    await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "now", "otp", [{"otp": otp, "email": email, "mobile": mobile}], is_serialize=0, config_table=config_table)
    return otp

async def func_otp_verify(client_postgres_pool: any, otp: int, email: str, mobile: str, expiry_sec: int) -> None:
    """Verify an OTP against the database and ensure it's within the expiration window."""
    if not otp:
        raise Exception("otp required")
    query = f"SELECT id FROM otp WHERE otp=$1 AND (email=$2 OR (email IS NULL AND $2 IS NULL)) AND (mobile=$3 OR (mobile IS NULL AND $3 IS NULL)) AND created_at > NOW() - INTERVAL '{expiry_sec} seconds' ORDER BY created_at DESC LIMIT 1;"
    async with client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow(query, int(otp), email, mobile)
    if not record:
        raise Exception("otp invalid or expired")

async def func_auth_signup_username_password(client_postgres_pool: any, func_postgres_create: callable, func_postgres_obj_serialize: callable, username: str, password: str, role: int = None) -> any:
    """Standard username/password signup with role assignment (defaults to type 1 user)."""
    return await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "now", "users", [{"type": 1, "username": username, "password": password, "role": role, "is_active": 1}], is_serialize=1)

async def func_auth_signup_username_password_bigint(client_postgres_pool: any, func_postgres_create: callable, func_postgres_obj_serialize: callable, username_bigint: int, password_bigint: int, role: int = None) -> any:
    """BigInt based signup for username and password identifiers (defaults to type 2 user)."""
    return await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "now", "users", [{"type": 2, "username_bigint": username_bigint, "password_bigint": password_bigint, "role": role, "is_active": 1}], is_serialize=1)

async def func_auth_login_password_username(client_postgres_pool: any, username: str, password: str, config_token_secret_key: str, config_token_expiry_sec: int, config_token_key: list) -> dict:
    """Authenticate type 1 user (username/password) and return session tokens."""
    from .utils import func_password_hash
    query = "SELECT * FROM users WHERE username=$1 AND type=1;"
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow(query, username)
    if not user:
        raise Exception("user not found")
    if user["password"] != func_password_hash(password):
        raise Exception("password invalid")
    payload = {k: user[k] for k in config_token_key if k in user}
    return {"status": 1, "token": func_token_encode(payload, config_token_secret_key, config_token_expiry_sec)}

async def func_auth_login_password_username_bigint(client_postgres_pool: any, username_bigint: int, password_bigint: int, config_token_secret_key: str, config_token_expiry_sec: int, config_token_key: list) -> dict:
    """Authenticate type 2 user (bigint username/password) and return session tokens."""
    query = "SELECT * FROM users WHERE username_bigint=$1 AND type=2;"
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow(query, username_bigint)
    if not user:
        raise Exception("user not found")
    if user["password_bigint"] != password_bigint:
        raise Exception("password invalid")
    payload = {k: user[k] for k in config_token_key if k in user}
    return {"status": 1, "token": func_token_encode(payload, config_token_secret_key, config_token_expiry_sec)}

async def func_auth_login_password_email(client_postgres_pool: any, email: str, password: str, config_token_secret_key: str, config_token_expiry_sec: int, config_token_key: list) -> dict:
    """Authenticate user via email/password and return session tokens."""
    from .utils import func_password_hash
    query = "SELECT * FROM users WHERE email=$1 AND type=1;"
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow(query, email)
    if not user:
        raise Exception("user not found")
    if user["password"] != func_password_hash(password):
        raise Exception("password invalid")
    payload = {k: user[k] for k in config_token_key if k in user}
    return {"status": 1, "token": func_token_encode(payload, config_token_secret_key, config_token_expiry_sec)}

async def func_auth_login_password_mobile(client_postgres_pool: any, mobile: str, password: str, config_token_secret_key: str, config_token_expiry_sec: int, config_token_key: list) -> dict:
    """Authenticate user via mobile/password and return session tokens."""
    from .utils import func_password_hash
    query = "SELECT * FROM users WHERE mobile=$1 AND type=1;"
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow(query, mobile)
    if not user:
        raise Exception("user not found")
    if user["password"] != func_password_hash(password):
        raise Exception("password invalid")
    payload = {k: user[k] for k in config_token_key if k in user}
    return {"status": 1, "token": func_token_encode(payload, config_token_secret_key, config_token_expiry_sec)}

async def func_auth_login_otp_email(client_postgres_pool: any, email: str, otp: int, config_token_secret_key: str, config_token_expiry_sec: int, config_token_key: list, func_otp_verify: callable, config_expiry_sec_otp: int, func_postgres_create: callable, func_postgres_obj_serialize: callable) -> dict:
    """Authenticate user via email OTP, creating a new record if it's their first login."""
    await func_otp_verify(client_postgres_pool, otp, email, None, config_expiry_sec_otp)
    query = "SELECT * FROM users WHERE email=$1 AND type=1;"
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow(query, email)
    if not user:
        ids = await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "now", "users", [{"type": 1, "email": email, "is_active": 1}], is_serialize=1)
        async with client_postgres_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE id=$1", ids[0])
    payload = {k: user[k] for k in config_token_key if k in user}
    return {"status": 1, "token": func_token_encode(payload, config_token_secret_key, config_token_expiry_sec)}

async def func_auth_login_otp_mobile(client_postgres_pool: any, mobile: str, otp: int, config_token_secret_key: str, config_token_expiry_sec: int, config_token_key: list, func_otp_verify: callable, config_expiry_sec_otp: int, func_postgres_create: callable, func_postgres_obj_serialize: callable) -> dict:
    """Authenticate user via mobile OTP, creating a new record if it's their first login."""
    await func_otp_verify(client_postgres_pool, otp, None, mobile, config_expiry_sec_otp)
    query = "SELECT * FROM users WHERE mobile=$1 AND type=1;"
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow(query, mobile)
    if not user:
        ids = await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "now", "users", [{"type": 1, "mobile": mobile, "is_active": 1}], is_serialize=1)
        async with client_postgres_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE id=$1", ids[0])
    payload = {k: user[k] for k in config_token_key if k in user}
    return {"status": 1, "token": func_token_encode(payload, config_token_secret_key, config_token_expiry_sec)}

async def func_auth_login_google(client_postgres_pool: any, google_token: str, google_client_id: str, config_token_secret_key: str, config_token_expiry_sec: int, config_token_key: list, func_postgres_create: callable, func_postgres_obj_serialize: callable) -> dict:
    """Authenticate user via Google OAuth2 token, mapping Google profile metadata to the internal user record."""
    from google.oauth2 import id_token
    from google.auth.transport import requests
    try:
        id_info = id_token.verify_oauth2_token(google_token, requests.Request(), google_client_id)
    except Exception:
        raise Exception("google token invalid")
    google_id = id_info.get("sub")
    query = "SELECT * FROM users WHERE google_login_id=$1 AND type=1;"
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow(query, google_id)
    if not user:
        new_user = {"type": 1, "username": google_id, "google_login_id": google_id, "google_login_metadata": id_info, "email": id_info.get("email"), "name": id_info.get("name"), "is_active": 1}
        ids = await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, "now", "users", [new_user], is_serialize=1)
        async with client_postgres_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE id=$1", ids[0])
    payload = {k: user[k] for k in config_token_key if k in user}
    return {"status": 1, "token": func_token_encode(payload, config_token_secret_key, config_token_expiry_sec)}

async def func_account_delete(client_postgres_pool: any, user_id: int) -> str:
    """Permanently delete a user account and all associated data records across the database."""
    async with client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id = $1;", user_id)
    return "account deleted"
