# import
import asyncio
import hashlib
import re
import secrets
import time
from collections import OrderedDict
from datetime import UTC
from datetime import datetime
from typing import Any
import asyncpg
import jwt
import orjson
from argon2 import PasswordHasher
from .middleware import func_api_error

# function
async def func_auth_user_login_fetch(*, conn: asyncpg.Connection, field: str, value: Any, role: Any, is_missing_ok: bool = False) -> dict:
    """Fetch a single login user by a unique-ish field with optional role. Raise on ambiguity (role omitted but multiple rows) and on not-found unless is_missing_ok, which returns None."""
    allowed_fields = ("username", "email", "mobile", "id_ext")
    if field not in allowed_fields: raise Exception(f"invalid auth field: {field}")
    column = 'lower("email")' if field == "email" else f'"{field}"'    # emails match whatever their case
    records = await conn.fetch(f'SELECT * FROM users WHERE {column}=$2 AND ($1::smallint IS NULL OR role=$1) ORDER BY id DESC LIMIT 2;', role, str(value).lower() if field == "email" else value)  # noqa: S608 - column from a fixed allow-list
    if not records:
        if is_missing_ok: return None
        raise Exception(f"{field} not found")
    if role is None and len(records) > 1: raise Exception("role is mandatory")
    return dict(records[0])

def func_auth_check_user_active(*, user: dict) -> None:
    """Refuse login for a deleted or deactivated user (checked after their credentials, so it reveals nothing to a stranger)."""
    if user.get("deleted_at"): raise func_api_error(message="account deleted", status_code=403)
    if user.get("deactivated_at"): raise func_api_error(message="account deactivated", status_code=403)

def func_auth_check_signup_role(*, role: int, config_signup_allowed_roles: list) -> None:
    """Validate that public signup is enabled and the requested role is permitted."""
    if not config_signup_allowed_roles: raise func_api_error(message="signup disabled", status_code=403)
    if role == 1 or role not in config_signup_allowed_roles: raise func_api_error(message=f"signup not allowed for role {role}", status_code=403)

async def func_auth_signup_password(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, role: int, username: str, password: str, source: int = None, config_signup_allowed_roles: list = None) -> dict:
    """Create a new user with hashed password after enforcing signup and role safety checks."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    func_auth_check_signup_role(role=role, config_signup_allowed_roles=config_signup_allowed_roles)
    if not client_password_hasher: raise func_api_error(message="password hasher not initialized", status_code=500)
    hashed_password = await asyncio.to_thread(client_password_hasher.hash, str(password))
    async with client_postgres.acquire() as conn:
        records = await conn.fetch('INSERT INTO users (role, username, password, source) VALUES ($1, $2, $3, $4) RETURNING *;', role, username, hashed_password, source)
        return dict(records[0])

async def func_auth_login_password(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, field: str, value: Any, password: str, role: Any) -> dict:
    """Fetch user by identifier field and verify password hash; unknown users and wrong passwords get the same error."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not client_password_hasher: raise func_api_error(message="password hasher not initialized", status_code=500)
    async with client_postgres.acquire() as conn:
        user = await func_auth_user_login_fetch(conn=conn, field=field, value=value, role=role, is_missing_ok=True)
    try:
        is_valid = bool(user and user.get("password")) and await asyncio.to_thread(client_password_hasher.verify, user["password"], str(password))
    except Exception:
        is_valid = False
    if not is_valid: raise Exception("invalid credentials")
    func_auth_check_user_active(user=user)
    return user

async def func_auth_user_find_or_create(*, client_postgres: asyncpg.Pool | None, field: str, value: Any, role: int, source: int = None, config_signup_allowed_roles: list = None, extra_cols: dict = None) -> dict:
    """Find existing user or create a new user (for OTP logins) with signup policy enforcement."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(field)): raise Exception(f"invalid identifier {field}")
    if field == "email": value = str(value).strip().lower()
    column = 'lower("email")' if field == "email" else f'"{field}"'    # emails match whatever their case
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(f'SELECT * FROM users WHERE {column}=$1 AND role=$2 ORDER BY id DESC LIMIT 1;', value, role)  # noqa: S608 - column name pattern-checked
        if records:
            func_auth_check_user_active(user=dict(records[0]))
            return dict(records[0])
        func_auth_check_signup_role(role=role, config_signup_allowed_roles=config_signup_allowed_roles)
        insert_dict = {"role": role, field: value, "source": source}
        if extra_cols:
            for k, v in extra_cols.items():
                if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(k)):
                    insert_dict[k] = v
        cols = list(insert_dict.keys())
        placeholders = [f"${i+1}" for i in range(len(cols))]
        sql = f'INSERT INTO users ({", ".join(f"{c}" for c in cols)}) VALUES ({", ".join(placeholders)}) RETURNING *;'  # noqa: S608 - column names pattern-checked
        created = await conn.fetch(sql, *list(insert_dict.values()))
        return dict(created[0])

def func_auth_check_config(*, client_postgres: asyncpg.Pool | None, config_token_secret_key: str) -> None:
    """Check authentication prerequisites in order before any side effects."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    func_token_check_secret_key(config_token_secret_key=config_token_secret_key)

def func_token_check_secret_key(*, config_token_secret_key: str) -> None:
    """Reject missing JWT configuration before authentication side effects."""
    if config_token_secret_key in (None, ""): raise func_api_error(message="token secret key missing", status_code=500)

async def func_token_encode(*, user: dict, config_token_secret_key: str, config_access_token_expires_sec: int, config_refresh_token_expires_sec: int, config_column_token_encode: list) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    if user is None: return None
    func_token_check_secret_key(config_token_secret_key=config_token_secret_key)
    token_secret_key = str(config_token_secret_key)
    payload_dict = {k: user.get(k) for k in config_column_token_encode} if config_column_token_encode else dict(user) if isinstance(user, dict) else user
    serialized_payload = orjson.dumps(payload_dict, default=str).decode("utf-8")
    now_ts = int(time.time())
    access_token_expires_at = now_ts + config_access_token_expires_sec
    refresh_token_expires_at = now_ts + config_refresh_token_expires_sec
    access_token = jwt.encode({"exp": access_token_expires_at, "data": serialized_payload, "type": "access"}, token_secret_key)
    refresh_token = jwt.encode({"exp": refresh_token_expires_at, "data": serialized_payload, "type": "refresh"}, token_secret_key)
    return {"access_token": access_token, "refresh_token": refresh_token, "access_token_expires_at": access_token_expires_at, "refresh_token_expires_at": refresh_token_expires_at}

async def func_token_decode(*, headers: dict, config_token_secret_key: str, cache_token: OrderedDict | None = None, config_token_cache_max: int = 0) -> dict:
    """Decode a Bearer JWT if present (an atk_ API key is left to func_api_key_decode); return decoded user dict or empty dict. With a cache, a verified token is reused until its own exp (the key is the full signed token, so an edited token misses and is verified again)."""
    auth_header = headers.get("Authorization")
    token = auth_header.split("Bearer ", 1)[1] if auth_header and auth_header.startswith("Bearer ") else None
    if not token or token.startswith("atk_"): return {}    # an API key (func_api_key_decode)
    is_cache = cache_token is not None and config_token_cache_max > 0
    if is_cache:
        entry = cache_token.get(token)
        if entry and entry[1] > time.time(): return {k: v.copy() if isinstance(v, (list, dict)) else v for k, v in entry[0].items()}
        cache_token.pop(token, None)
    func_token_check_secret_key(config_token_secret_key=config_token_secret_key)
    decoded_payload = jwt.decode(token, str(config_token_secret_key), algorithms="HS256")
    user = orjson.loads(decoded_payload["data"])
    if isinstance(user, dict): user["_token_type"] = decoded_payload.get("type")
    if is_cache and isinstance(user, dict) and isinstance(decoded_payload.get("exp"), (int, float)):
        while len(cache_token) >= config_token_cache_max: cache_token.popitem(last=False)
        cache_token[token] = (user, decoded_payload["exp"])
        return {k: v.copy() if isinstance(v, (list, dict)) else v for k, v in user.items()}
    return user

def func_api_key_hash(*, key: str) -> str:
    """sha256 hex of an API key: the only form stored, so a database copy holds no usable key."""
    return hashlib.sha256(key.encode()).hexdigest()

async def func_api_key_create(*, client_postgres: asyncpg.Pool | None, user_id: int, name: str, scopes: list | None, expire_days: int | None, config_api_key_max: int) -> dict:
    """Create an API key for user_id: an opaque atk_<random> string, returned once, stored as its sha256. A user holds at most config_api_key_max keys."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    key = "atk_" + secrets.token_urlsafe(32)
    async with client_postgres.acquire() as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(hashtext('api_key'), $1::int)", user_id % 2147483647)    # one create at a time per user, so the count below holds
        if await conn.fetchval("SELECT count(*) FROM api_key WHERE created_by_id=$1", user_id) >= config_api_key_max: raise func_api_error(message=f"api key limit reached ({config_api_key_max}): delete one first", status_code=400)
        row = await conn.fetchrow("INSERT INTO api_key (created_by_id, name, key_hash, key_prefix, scopes, expires_at) VALUES ($1, $2, $3, $4, $5, CASE WHEN $6::int IS NULL THEN NULL ELSE NOW() + make_interval(days => $6::int) END) RETURNING id, created_at, name, key_prefix, scopes, expires_at", user_id, name, func_api_key_hash(key=key), key[:12], scopes or None, expire_days)
    return {**dict(row), "key": key}

async def func_api_key_decode(*, headers: dict, client_postgres: asyncpg.Pool | None, cache_token: OrderedDict | None, config_token_cache_max: int, config_api_key_cache_sec: int, config_column_token_encode: list) -> dict:
    """Resolve an `Authorization: Bearer atk_...` header to its owner's user dict, the same columns a JWT carries (config_column_token_encode) plus _token_type "api_key", _api_key_id and _api_key_scopes; {} without that header. A key is looked up by its sha256 and cached per worker for config_api_key_cache_sec (never past its expiry); an unknown or expired key, or a deleted or deactivated owner, is 401."""
    auth_header = headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer atk_"): return {}
    key_hash = func_api_key_hash(key=auth_header[7:].strip())
    cache_key, now = f"apikey:{key_hash}", time.time()
    is_cache = cache_token is not None and config_token_cache_max > 0 and config_api_key_cache_sec > 0
    if is_cache:
        entry = cache_token.get(cache_key)
        if entry and entry[1] > now: return {k: v.copy() if isinstance(v, (list, dict)) else v for k, v in entry[0].items()}
        cache_token.pop(cache_key, None)
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    columns = ", ".join('u."' + str(c).replace('"', '""') + '"' for c in (config_column_token_encode or ["id", "role"]))
    row = await client_postgres.fetchrow(f"SELECT {columns}, u.deleted_at AS _deleted_at, u.deactivated_at AS _deactivated_at, k.id AS _api_key_id, k.scopes AS _api_key_scopes, k.expires_at AS _expires_at FROM api_key k JOIN users u ON u.id=k.created_by_id WHERE k.key_hash=$1", key_hash)  # noqa: S608 - column names from config, quoted
    if not row or (row["_expires_at"] and row["_expires_at"] <= datetime.now(UTC)): raise func_api_error(message="api key invalid or expired", status_code=401)
    if row["_deleted_at"] or row["_deactivated_at"]: raise func_api_error(message="api key owner is deleted or deactivated", status_code=401)
    user = orjson.loads(orjson.dumps({k: v for k, v in dict(row).items() if k not in ("_deleted_at", "_deactivated_at", "_expires_at")}, default=str))    # the same JSON types a decoded JWT has
    user["_api_key_scopes"], user["_token_type"] = user["_api_key_scopes"] or [], "api_key"
    if is_cache:
        expires_at = now + config_api_key_cache_sec
        if row["_expires_at"]: expires_at = min(expires_at, row["_expires_at"].timestamp())
        while len(cache_token) >= config_token_cache_max: cache_token.popitem(last=False)
        cache_token[cache_key] = (user, expires_at)
        return {k: v.copy() if isinstance(v, (list, dict)) else v for k, v in user.items()}
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
    return

async def func_otp_verify(*, client_postgres: asyncpg.Pool | None, otp: int, email: str, mobile: str, config_otp_expiry_sec: int, config_otp_static: int = None, config_otp_max_attempt: int = 5) -> None:
    """Verify an OTP for email or mobile within its expiration window; each code accepts at most config_otp_max_attempt guesses."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if config_otp_static is not None and otp == config_otp_static: return "done"
    if not otp: raise Exception("otp code missing")
    if not email and not mobile: raise Exception("missing both email and mobile")
    if email and mobile: raise Exception("provide only one identifier")
    if email:
        sql = "SELECT id, otp, (created_at > CURRENT_TIMESTAMP - make_interval(secs => $2)) as is_valid FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email.strip().lower()
    else:
        sql = "SELECT id, otp, (created_at > CURRENT_TIMESTAMP - make_interval(secs => $2)) as is_valid FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile.strip()
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql, identifier, float(config_otp_expiry_sec))
        if not records: raise Exception("otp not found")
        if not records[0]["is_valid"]: raise Exception("otp code expired")
        # Count the guess before comparing; the conditional update caps guesses even under concurrent requests.
        attempt = await conn.fetchval("UPDATE otp SET attempt = attempt + 1 WHERE id = $1 AND attempt < $2 RETURNING attempt;", records[0]["id"], config_otp_max_attempt)
        if attempt is None: raise func_api_error(message="otp attempts exceeded, request a new code", status_code=429)
        if records[0]["otp"] != otp: raise Exception("invalid otp code")
        await conn.execute("DELETE FROM otp WHERE id = $1;", records[0]["id"])
    return "done"

def func_user_last_active_is_due(*, last_active_at: datetime | None, interval_sec: int = 300) -> bool:
    """Whether last_active_at (as just read with the user's row) is old enough for func_user_last_active_update to write: a caller that already has the row skips the update, and its round trip, within interval_sec. A replica's older copy only means one update that writes nothing."""
    if last_active_at is None: return True
    if last_active_at.tzinfo is None: last_active_at = last_active_at.replace(tzinfo=UTC)
    return (datetime.now(UTC) - last_active_at).total_seconds() >= interval_sec

async def func_user_last_active_update(*, client_postgres: asyncpg.Pool | None, user_id: int, interval_sec: int = 300) -> None:
    """Set users.last_active_at to now for one user, at most once per interval_sec: a page open within it writes nothing (no new row version, no triggers), so last_active_at is accurate to 5 minutes. Pass the master pool, since read replicas cannot write."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    await client_postgres.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1 AND (last_active_at IS NULL OR last_active_at < NOW() - make_interval(secs => $2))", user_id, interval_sec)
    return

async def func_user_read_single(*, client_postgres: asyncpg.Pool | None, user_id: int) -> dict:
    """Read a single user by ID from PostgreSQL, raises Exception if not found."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    async with client_postgres.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
    if not record: raise Exception("user not found")
    return dict(record)
