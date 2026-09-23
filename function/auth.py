"""Atom auth functions."""

async def func_auth_user_login_fetch(*, conn: any, field: str, value: any, role: any) -> dict:
    """Fetch a single login user by a unique-ish field with optional role. Raise on not-found or ambiguity (role omitted but multiple rows)."""
    allowed_fields = ("username", "email", "mobile", "id_ext")
    if field not in allowed_fields: raise Exception(f"invalid auth field: {field}")
    records = await conn.fetch(f'SELECT * FROM users WHERE "{field}"=$2 AND ($1::smallint IS NULL OR role=$1) ORDER BY id DESC LIMIT 2;', role, value)
    if not records: raise Exception(f"{field} not found")
    if role is None and len(records) > 1: raise Exception("role is mandatory")
    return dict(records[0])

def func_auth_check_signup_role(*, role: int, config_signup_allowed_roles: list) -> None:
    """Validate that public signup is enabled and the requested role is permitted."""
    if not config_signup_allowed_roles: raise Exception("signup disabled")
    if role == 1 or role not in config_signup_allowed_roles: raise Exception(f"signup not allowed for role {role}")

async def func_auth_signup_password(*, client_postgres: any, client_password_hasher: any, func_auth_check_signup_role: callable, role: int, username: str, password: str, source: int = None, config_signup_allowed_roles: list = None) -> dict:
    """Create a new user with hashed password after enforcing signup and role safety checks."""
    if not client_postgres: raise Exception("postgres client not initialized")
    func_auth_check_signup_role(role=role, config_signup_allowed_roles=config_signup_allowed_roles)
    hashed_password = client_password_hasher.hash(str(password))
    async with client_postgres.acquire() as conn:
        records = await conn.fetch('INSERT INTO users (role, username, password, source) VALUES ($1, $2, $3, $4) RETURNING *;', role, username, hashed_password, source)
        return dict(records[0])

async def func_auth_login_password(*, client_postgres: any, client_password_hasher: any, field: str, value: any, password: str, role: any) -> dict:
    """Fetch user by identifier field and verify password hash."""
    if not client_postgres: raise Exception("postgres client not initialized")
    async with client_postgres.acquire() as conn:
        user = await func_auth_user_login_fetch(conn=conn, field=field, value=value, role=role)
        try:
            client_password_hasher.verify(user["password"], str(password))
        except Exception:
            raise Exception("incorrect password")
        return user

async def func_auth_user_find_or_create(*, client_postgres: any, func_auth_check_signup_role: callable, field: str, value: any, role: int, source: int = None, config_signup_allowed_roles: list = None, extra_cols: dict = None) -> dict:
    """Find existing user or create a new user (for OTP and Social Logins) with signup policy enforcement."""
    if not client_postgres: raise Exception("postgres client not initialized")
    import re
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
    import jwt, orjson, time
    if user is None: return None
    if config_token_secret_key in (None, ""): raise Exception("token secret key missing")
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
    import jwt, orjson
    if config_token_secret_key in (None, ""): raise Exception("token secret key missing")
    decoded_payload = jwt.decode(token, str(config_token_secret_key), algorithms="HS256")
    user = orjson.loads(decoded_payload["data"])
    if isinstance(user, dict): user["_token_type"] = decoded_payload.get("type")
    return user

async def func_otp_generate(*, client_postgres: any, email: str, mobile: str, config_otp_length: int) -> int:
    """Generate a random OTP and store it in PostgreSQL for a given email or mobile."""
    if not client_postgres: raise Exception("postgres client not initialized")
    import secrets
    otp = secrets.SystemRandom().randint(10**(config_otp_length - 1), 10**config_otp_length - 1)
    sql = "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3);"
    async with client_postgres.acquire() as conn:
        await conn.execute(sql, otp, email.strip().lower() if email else None, mobile.strip() if mobile else None)
    return otp

async def func_otp_verify(*, client_postgres: any, otp: int, email: str, mobile: str, config_otp_expiry_sec: int, config_otp_static: int = None) -> None:
    """Verify an OTP for email or mobile within its expiration window."""
    if not client_postgres: raise Exception("postgres client not initialized")
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
        if records[0]["otp"] != otp: raise Exception("invalid otp code")
        if not records[0]["is_valid"]: raise Exception("otp code expired")
        await conn.execute("DELETE FROM otp WHERE id = $1;", records[0]["id"])
    return "done"

async def func_user_read_single(*, client_postgres: any, user_id: int) -> dict:
    """Read a single user by ID from PostgreSQL, raises Exception if not found."""
    async with client_postgres.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
    if not record: raise Exception("user not found")
    return dict(record)
