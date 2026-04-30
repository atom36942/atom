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

async def func_user_profile_read(*, client_postgres_pool: any, user_id: int, config_sql: dict, func_user_single_read: callable) -> dict:
    """Read full user profile and update last activity status."""
    import asyncio
    user = await func_user_single_read(client_postgres_pool=client_postgres_pool, user_id=user_id)
    metadata = {}
    queries_metadata = config_sql.get("profile_metadata")
    if queries_metadata:
        async with client_postgres_pool.acquire() as conn:
            for key, sql_query in queries_metadata.items():
                records = await conn.fetch(sql_query, user_id)
                metadata[key] = [dict(record) for record in records]
    asyncio.create_task(client_postgres_pool.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", user_id))
    return {**user, **metadata}

async def func_user_account_delete(*, mode: str, client_postgres_pool: any, user_id: int) -> str:
    """Delete a user account either softly (flag) or hardly (row removal)."""
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT role FROM users WHERE id=$1", user_id)
        if not user:
            raise Exception("user not found")
        if user["role"] is not None:
            raise Exception("account with role cannot be deleted")
        if mode == "soft":
            query = "UPDATE users SET is_deleted=1 WHERE id=$1"
        elif mode == "hard":
            query = "DELETE FROM users WHERE id=$1"
        else:
            raise Exception(f"invalid delete mode: {mode}, allowed: soft, hard")
        await conn.execute(query, user_id)
    return "account deleted"

async def func_user_single_read(*, client_postgres_pool: any, user_id: int) -> dict:
    """Read a single user's full record by their ID."""
    async with client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
        if not record:
            raise Exception("user not found")
        return dict(record)

async def func_user_api_usage_read(*, client_postgres_pool: any, days: int, user_id: int) -> list:
    """Read API usage logs for a specific user within a day limit."""
    query = "SELECT api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY api LIMIT 1000;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, days, user_id)
        return [dict(r) for r in records]

async def func_message_inbox(*, client_postgres_pool: any, user_id: int, mode: str, order: str, limit: int, page: int) -> list:
    """Read a conversation-summarized inbox for a user with unread filtering."""
    where_clause = "user_id=$1 AND is_read=1" if mode == "read" else "user_id=$1 AND is_read IS DISTINCT FROM 1" if mode == "unread" else "1=1"
    query = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - user_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR user_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_id)
        return [dict(r) for r in records]

async def func_message_received(*, client_postgres_pool: any, user_id: int, mode: str, order: str, limit: int, page: int) -> list:
    """Read all messages received by a specific user and optionally mark unread ones as read (identifier validated)."""
    import asyncio
    unread_filter = "AND is_read=1" if mode == "read" else "AND is_read IS DISTINCT FROM 1" if mode == "unread" else ""
    query = f"SELECT * FROM message WHERE user_id=$1 {unread_filter} ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_id)
        obj_list = [dict(r) for r in records]
        if obj_list:
            mark_read_ids = [r["id"] for r in obj_list if r.get("is_read") != 1]
            if mark_read_ids:
                async def _mark_read():
                    async with client_postgres_pool.acquire() as conn:
                        await conn.execute(f"UPDATE message SET is_read=1 WHERE id IN ({','.join(map(str, mark_read_ids))})")
                asyncio.create_task(_mark_read())
    return obj_list

async def func_message_thread(*, client_postgres_pool: any, user_one_id: int, user_id: int, order: str, limit: int, page: int) -> list:
    """Read the full message thread between two users."""
    query = f"SELECT * FROM message WHERE ((created_by_id=$1 AND user_id=$2) OR (created_by_id=$2 AND user_id=$1)) ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_one_id, user_id)
        return [dict(r) for r in records]

async def func_message_thread_mark_read(*, client_postgres_pool: any, current_user_id: int, partner_id: int) -> None:
    """Mark all messages in a thread as read for the current user."""
    async with client_postgres_pool.acquire() as conn:
        await conn.execute("UPDATE message SET is_read=1 WHERE created_by_id=$1 AND user_id=$2;", partner_id, current_user_id)
    return None

async def func_message_delete_single(*, client_postgres_pool: any, id: int, user_id: int) -> str:
    """Delete a single message given its ID and user context."""
    async with client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM message WHERE id=$1 AND (created_by_id=$2 OR user_id=$2)", id, user_id)
    return "message deleted"

async def func_message_delete_bulk(*, client_postgres_pool: any, user_id: int, mode: str) -> str:
    """Delete multiple messages for a user based on context (sent, received, all)."""
    if mode == "sent":
        query = "DELETE FROM message WHERE created_by_id=$1"
        args = (user_id,)
    elif mode == "received":
        query = "DELETE FROM message WHERE user_id=$1"
        args = (user_id,)
    elif mode == "all":
        query = "DELETE FROM message WHERE (created_by_id=$1 OR user_id=$1)"
        args = (user_id,)
    else:
        raise Exception(f"invalid delete mode: {mode}, allowed: sent, received, all")
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, *args)
    return "messages deleted"
