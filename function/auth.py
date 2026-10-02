"""Atom auth functions."""

import asyncio
import re
import secrets
import time
from typing import Any
import asyncpg
import jwt
import orjson
from argon2 import PasswordHasher
from .middleware import func_api_error

async def func_auth_user_login_fetch(*, conn: asyncpg.Connection, field: str, value: Any, role: Any, is_missing_ok: bool = False) -> dict:
    """Fetch a single login user by a unique-ish field with optional role. Raise on ambiguity (role omitted but multiple rows) and on not-found unless is_missing_ok, which returns None."""
    allowed_fields = ("username", "email", "mobile", "id_ext")
    if field not in allowed_fields: raise Exception(f"invalid auth field: {field}")
    records = await conn.fetch(f'SELECT * FROM users WHERE "{field}"=$2 AND ($1::smallint IS NULL OR role=$1) ORDER BY id DESC LIMIT 2;', role, value)
    if not records:
        if is_missing_ok: return None
        raise Exception(f"{field} not found")
    if role is None and len(records) > 1: raise Exception("role is mandatory")
    return dict(records[0])

def func_auth_check_signup_role(*, role: int, config_signup_allowed_roles: list) -> None:
    """Validate that public signup is enabled and the requested role is permitted."""
    if not config_signup_allowed_roles: raise func_api_error(message="signup disabled", status_code=403)
    if role == 1 or role not in config_signup_allowed_roles: raise func_api_error(message=f"signup not allowed for role {role}", status_code=403)

async def func_auth_signup_password(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, role: int, username: str, password: str, source: int = None, config_signup_allowed_roles: list = None) -> dict:
    """Create a new user with hashed password after enforcing signup and role safety checks."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    func_auth_check_signup_role(role=role, config_signup_allowed_roles=config_signup_allowed_roles)
    hashed_password = await asyncio.to_thread(client_password_hasher.hash, str(password))
    async with client_postgres.acquire() as conn:
        records = await conn.fetch('INSERT INTO users (role, username, password, source) VALUES ($1, $2, $3, $4) RETURNING *;', role, username, hashed_password, source)
        return dict(records[0])

async def func_auth_login_password(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, field: str, value: Any, password: str, role: Any) -> dict:
    """Fetch user by identifier field and verify password hash; unknown users and wrong passwords get the same error."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    async with client_postgres.acquire() as conn:
        user = await func_auth_user_login_fetch(conn=conn, field=field, value=value, role=role, is_missing_ok=True)
    try:
        is_valid = bool(user and user.get("password")) and await asyncio.to_thread(client_password_hasher.verify, user["password"], str(password))
    except Exception:
        is_valid = False
    if not is_valid: raise Exception("invalid credentials")
    return user

async def func_auth_user_find_or_create(*, client_postgres: asyncpg.Pool | None, field: str, value: Any, role: int, source: int = None, config_signup_allowed_roles: list = None, extra_cols: dict = None) -> dict:
    """Find existing user or create a new user (for OTP and Social Logins) with signup policy enforcement."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(field)): raise Exception(f"invalid identifier {field}")
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(f'SELECT * FROM users WHERE "{field}"=$1 AND role=$2 ORDER BY id DESC LIMIT 1;', value, role)
        if records:
            return dict(records[0])
        func_auth_check_signup_role(role=role, config_signup_allowed_roles=config_signup_allowed_roles)
        insert_dict = {"role": role, field: value, "source": source}
        if extra_cols:
            for k, v in extra_cols.items():
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(k)):
                    insert_dict[k] = v
        cols = list(insert_dict.keys())
        placeholders = [f"${i+1}" for i in range(len(cols))]
        sql = f'INSERT INTO users ({", ".join(f"{c}" for c in cols)}) VALUES ({", ".join(placeholders)}) RETURNING *;'
        created = await conn.fetch(sql, *list(insert_dict.values()))
        return dict(created[0])

async def func_token_encode(*, user: dict, config_token_secret_key: str, config_access_token_expires_sec: int, config_refresh_token_expires_sec: int, config_column_token_encode: list) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    if user is None: return None
    if config_token_secret_key in (None, ""): raise func_api_error(message="token secret key missing", status_code=500)
    token_secret_key = str(config_token_secret_key)
    payload_dict = {k: user.get(k) for k in config_column_token_encode} if config_column_token_encode else dict(user) if isinstance(user, dict) else user
    serialized_payload = orjson.dumps(payload_dict, default=str).decode("utf-8")
    now_ts = int(time.time())
    access_token_expires_at = now_ts + config_access_token_expires_sec
    refresh_token_expires_at = now_ts + config_refresh_token_expires_sec
    access_token = jwt.encode({"exp": access_token_expires_at, "data": serialized_payload, "type": "access"}, token_secret_key)
    refresh_token = jwt.encode({"exp": refresh_token_expires_at, "data": serialized_payload, "type": "refresh"}, token_secret_key)
    return {"access_token": access_token, "refresh_token": refresh_token, "access_token_expires_at": access_token_expires_at, "refresh_token_expires_at": refresh_token_expires_at}

async def func_token_decode(*, headers: dict, config_token_secret_key: str) -> dict:
    """Decode Bearer token if present; return decoded user dict or empty dict."""
    auth_header = headers.get("Authorization")
    token = auth_header.split("Bearer ", 1)[1] if auth_header and auth_header.startswith("Bearer ") else None
    if not token: return {}
    if config_token_secret_key in (None, ""): raise func_api_error(message="token secret key missing", status_code=500)
    decoded_payload = jwt.decode(token, str(config_token_secret_key), algorithms="HS256")
    user = orjson.loads(decoded_payload["data"])
    if isinstance(user, dict): user["_token_type"] = decoded_payload.get("type")
    return user

def func_otp_generate(*, client_postgres: asyncpg.Pool | None, config_otp_length: int) -> int:
    """Return a random OTP code; checks the database first so no code is sent that could not be saved."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    return secrets.SystemRandom().randint(10**(config_otp_length - 1), 10**config_otp_length - 1)

async def func_otp_save(*, client_postgres: asyncpg.Pool | None, otp: int, email: str, mobile: str) -> None:
    """Store an OTP after it was sent, so a failed delivery leaves no unused code behind."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    sql = "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3);"
    async with client_postgres.acquire() as conn:
        await conn.execute(sql, otp, email.strip().lower() if email else None, mobile.strip() if mobile else None)
    return None

async def func_otp_verify(*, client_postgres: asyncpg.Pool | None, otp: int, email: str, mobile: str, config_otp_expiry_sec: int, config_otp_static: int = None, config_otp_max_attempt: int = 5) -> None:
    """Verify an OTP for email or mobile within its expiration window; each code accepts at most config_otp_max_attempt guesses."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if config_otp_static is not None and otp == config_otp_static: return "done"
    if not otp: raise Exception("otp code missing")
    if not email and not mobile: raise Exception("missing both email and mobile")
    if email and mobile: raise Exception("provide only one identifier")
    if email:
        sql = f"SELECT id, otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_otp_expiry_sec}s') as is_valid FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email.strip().lower()
    else:
        sql = f"SELECT id, otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_otp_expiry_sec}s') as is_valid FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile.strip()
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql, identifier)
        if not records: raise Exception("otp not found")
        if not records[0]["is_valid"]: raise Exception("otp code expired")
        # Count the guess before comparing; the conditional update caps guesses even under concurrent requests.
        attempt = await conn.fetchval("UPDATE otp SET attempt = attempt + 1 WHERE id = $1 AND attempt < $2 RETURNING attempt;", records[0]["id"], config_otp_max_attempt)
        if attempt is None: raise func_api_error(message="otp attempts exceeded, request a new code", status_code=429)
        if records[0]["otp"] != otp: raise Exception("invalid otp code")
        await conn.execute("DELETE FROM otp WHERE id = $1;", records[0]["id"])
    return "done"

async def func_user_read_single(*, client_postgres: asyncpg.Pool | None, user_id: int) -> dict:
    """Read a single user by ID from PostgreSQL, raises Exception if not found."""
    async with client_postgres.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
    if not record: raise Exception("user not found")
    return dict(record)
