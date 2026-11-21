# import
import base64
import hashlib
import hmac
import os
import re
import secrets
import struct
import time
from typing import Any
from urllib.parse import quote
import asyncpg
import jwt
import orjson
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .auth import func_auth_check_user_active
from .auth import func_token_check_secret_key
from .auth import func_token_encode
from .middleware import func_api_error

TOTP_STEP_SEC = 30
TOTP_DIGITS = 6
TOTP_RECOVERY_COUNT = 10
TOTP_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"    # no 0/O or 1/I, so a printed code reads back right
TOTP_MFA_TOKEN_SEC = 300

# function
def func_totp_code(*, secret: bytes, step: int) -> str:
    """RFC 6238 TOTP for one 30-second step: HMAC-SHA1(secret, step) cut to 6 digits by RFC 4226 dynamic truncation (the defaults every authenticator app supports)."""
    digest = hmac.new(secret, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10 ** TOTP_DIGITS).zfill(TOTP_DIGITS)

def func_totp_match(*, secret: bytes, code: str, now: float | None = None) -> int | None:
    """The step (now, one before or one after, for clock drift) whose code equals code, compared in constant time; None when none does."""
    step = int((now if now is not None else time.time()) // TOTP_STEP_SEC)
    found = None
    for candidate in (step - 1, step, step + 1):
        if hmac.compare_digest(func_totp_code(secret=secret, step=candidate), code): found = candidate
    return found

def func_totp_key(*, config_totp_encryption_key: str | None) -> bytes:
    """The 32-byte AES key from config_totp_encryption_key (any string of 32+ characters, hashed to 32 bytes); 2FA is off for the app until it is set."""
    if not config_totp_encryption_key: raise func_api_error(message="2FA not configured: set config_totp_encryption_key", status_code=400)
    if len(str(config_totp_encryption_key)) < 32: raise func_api_error(message="config_totp_encryption_key must be 32 characters or more", status_code=500)
    return hashlib.sha256(str(config_totp_encryption_key).encode()).digest()

def func_totp_encrypt(*, key: bytes, user_id: int, secret: bytes) -> str:
    """AES-GCM encrypt a user's TOTP secret: base64(nonce + ciphertext), bound to the user id so a value copied to another user's row fails to decrypt."""
    nonce = os.urandom(12)
    return base64.b64encode(nonce + AESGCM(key).encrypt(nonce, secret, str(user_id).encode())).decode()

def func_totp_decrypt(*, key: bytes, user_id: int, value: str) -> bytes:
    """Decrypt what func_totp_encrypt stored; a wrong key, user or edited value is refused."""
    try:
        raw = base64.b64decode(value)
        return AESGCM(key).decrypt(raw[:12], raw[12:], str(user_id).encode())
    except Exception: raise func_api_error(message="2FA secret cannot be read: config_totp_encryption_key changed or the value was edited; an admin resets this user's 2FA", status_code=500) from None

def func_totp_uri(*, secret: bytes, issuer: str, username: str) -> str:
    """The otpauth:// link an authenticator app reads from a QR code (SHA1, 6 digits, 30 s: the defaults every app supports)."""
    label = quote(f"{issuer}:{username}", safe=":@")
    return f"otpauth://totp/{label}?secret={base64.b32encode(secret).decode().rstrip('=')}&issuer={quote(issuer)}&algorithm=SHA1&digits={TOTP_DIGITS}&period={TOTP_STEP_SEC}"

def func_totp_recovery_normalize(*, code: str) -> str:
    """A recovery code as compared: upper case, no dashes or spaces."""
    return re.sub(r"[\s-]", "", str(code or "")).upper()

def func_totp_recovery_hash(*, key: bytes, code: str) -> str:
    """HMAC-SHA256 of a normalized recovery code with the 2FA key, so a database copy alone cannot test guesses."""
    return hmac.new(key, func_totp_recovery_normalize(code=code).encode(), hashlib.sha256).hexdigest()

def func_totp_recovery_create(*, key: bytes) -> tuple[list, list]:
    """10 new recovery codes (XXXXX-XXXXX, 50 random bits each) and their hashes."""
    codes = []
    for _ in range(TOTP_RECOVERY_COUNT):
        raw = "".join(secrets.choice(TOTP_RECOVERY_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes, [func_totp_recovery_hash(key=key, code=c) for c in codes]

async def func_totp_user_read(*, client_postgres: asyncpg.Pool, user_id: int) -> dict:
    """The user row's 2FA columns (and username, for the app label)."""
    row = await client_postgres.fetchrow("SELECT id, username, email, totp_secret, totp_enabled_at, totp_last_step, totp_recovery FROM users WHERE id = $1", user_id)
    if not row: raise func_api_error(message="user not found", status_code=404)
    return dict(row)

async def func_totp_check(*, client_postgres: asyncpg.Pool, key: bytes, user: dict, code: str, is_recovery_allowed: bool) -> str:
    """Check a 2FA code for a user with 2FA on and spend it: a 6-digit code must be for a step after the last one used (saved atomically, so the same code never works twice, even on two workers at once); a recovery code is removed when used. Returns totp or recovery; a wrong or used code is 401."""
    code = str(code or "").replace(" ", "")
    if re.fullmatch(r"\d{6}", code):
        step = func_totp_match(secret=func_totp_decrypt(key=key, user_id=user["id"], value=user["totp_secret"]), code=code)
        if step is not None and await client_postgres.fetchval("UPDATE users SET totp_last_step = $2 WHERE id = $1 AND totp_enabled_at IS NOT NULL AND (totp_last_step IS NULL OR totp_last_step < $2) RETURNING id", user["id"], step): return "totp"
    elif is_recovery_allowed and code:
        if await client_postgres.fetchval("UPDATE users SET totp_recovery = array_remove(totp_recovery, $2) WHERE id = $1 AND totp_enabled_at IS NOT NULL AND $2 = ANY(totp_recovery) RETURNING id", user["id"], func_totp_recovery_hash(key=key, code=code)): return "recovery"
    raise func_api_error(message="code invalid", status_code=401)

async def func_totp_setup(*, client_postgres: asyncpg.Pool, user_id: int, config_totp_encryption_key: str | None, issuer: str) -> dict:
    """Start 2FA for a user: a new secret saved encrypted (2FA still off until func_totp_enable), returned once with its otpauth:// link for the QR code."""
    key = func_totp_key(config_totp_encryption_key=config_totp_encryption_key)
    user = await func_totp_user_read(client_postgres=client_postgres, user_id=user_id)
    if user["totp_enabled_at"]: raise func_api_error(message="2FA is already on; turn it off first to set it up again", status_code=400)
    secret = secrets.token_bytes(20)
    await client_postgres.execute("UPDATE users SET totp_secret = $2, totp_last_step = NULL, totp_recovery = NULL WHERE id = $1 AND totp_enabled_at IS NULL", user_id, func_totp_encrypt(key=key, user_id=user_id, secret=secret))
    return {"secret": base64.b32encode(secret).decode().rstrip("="), "uri": func_totp_uri(secret=secret, issuer=issuer, username=user["username"] or user["email"] or str(user_id))}

async def func_totp_enable(*, client_postgres: asyncpg.Pool, user_id: int, code: str, config_totp_encryption_key: str | None) -> dict:
    """Turn 2FA on once the user shows a code from the secret func_totp_setup gave; returns 10 recovery codes, shown only here."""
    key = func_totp_key(config_totp_encryption_key=config_totp_encryption_key)
    user = await func_totp_user_read(client_postgres=client_postgres, user_id=user_id)
    if user["totp_enabled_at"]: raise func_api_error(message="2FA is already on", status_code=400)
    if not user["totp_secret"]: raise func_api_error(message="call /my/totp-setup first", status_code=400)
    step = func_totp_match(secret=func_totp_decrypt(key=key, user_id=user_id, value=user["totp_secret"]), code=str(code or "").replace(" ", ""))
    if step is None: raise func_api_error(message="code invalid", status_code=400)
    codes, hashes = func_totp_recovery_create(key=key)
    if not await client_postgres.fetchval("UPDATE users SET totp_enabled_at = now(), totp_last_step = $2, totp_recovery = $3 WHERE id = $1 AND totp_enabled_at IS NULL AND totp_secret IS NOT NULL RETURNING id", user_id, step, hashes): raise func_api_error(message="2FA is already on", status_code=400)
    return {"recovery_codes": codes}

async def func_totp_disable(*, client_postgres: asyncpg.Pool, user_id: int, code: str, config_totp_encryption_key: str | None) -> str:
    """Turn 2FA off with a current or recovery code; clearing totp_enabled_at clears the secret, last step and recovery codes (trigger users_totp_clear)."""
    key = func_totp_key(config_totp_encryption_key=config_totp_encryption_key)
    user = await func_totp_user_read(client_postgres=client_postgres, user_id=user_id)
    if not user["totp_enabled_at"]: raise func_api_error(message="2FA is not on", status_code=400)
    await func_totp_check(client_postgres=client_postgres, key=key, user=user, code=code, is_recovery_allowed=True)
    await client_postgres.execute("UPDATE users SET totp_enabled_at = NULL WHERE id = $1", user_id)
    return "2FA off"

def func_mfa_token_encode(*, user_id: int, config_token_secret_key: str) -> str:
    """A 5-minute JWT of type mfa holding only the user id: proof the first login step passed. The middleware opens routes only for access tokens, so it works on /auth/login-totp alone."""
    func_token_check_secret_key(config_token_secret_key=config_token_secret_key)
    return jwt.encode({"exp": int(time.time()) + TOTP_MFA_TOKEN_SEC, "data": orjson.dumps({"id": user_id}).decode(), "type": "mfa"}, str(config_token_secret_key))

def func_mfa_token_decode(*, mfa_token: str, config_token_secret_key: str) -> int:
    """The user id in an mfa token; expired, forged or another type is 401."""
    func_token_check_secret_key(config_token_secret_key=config_token_secret_key)
    try: payload = jwt.decode(str(mfa_token or ""), str(config_token_secret_key), algorithms="HS256")
    except jwt.PyJWTError: raise func_api_error(message="mfa token invalid or expired", status_code=401) from None
    if payload.get("type") != "mfa": raise func_api_error(message="mfa token invalid or expired", status_code=401)
    return orjson.loads(payload["data"])["id"]

async def func_auth_login_finish(*, user: dict, config_token_secret_key: str, config_access_token_expires_sec: int, config_refresh_token_expires_sec: int, config_column_token_encode: list) -> dict:
    """The end of every login: access and refresh tokens, or, for a user with 2FA on, {"mfa_required": true, "mfa_token"} for /auth/login-totp."""
    if user and user.get("totp_enabled_at"): return {"mfa_required": True, "mfa_token": func_mfa_token_encode(user_id=user["id"], config_token_secret_key=config_token_secret_key)}
    return await func_token_encode(user=user, config_token_secret_key=config_token_secret_key, config_access_token_expires_sec=config_access_token_expires_sec, config_refresh_token_expires_sec=config_refresh_token_expires_sec, config_column_token_encode=config_column_token_encode)

async def func_auth_login_totp(*, client_postgres: asyncpg.Pool, mfa_token: str, code: str, config_totp_encryption_key: str | None, config_token_secret_key: str, config_access_token_expires_sec: int, config_refresh_token_expires_sec: int, config_column_token_encode: list) -> Any:
    """The second login step: a valid mfa token and a current or recovery code give the same tokens as a login without 2FA."""
    user_id = func_mfa_token_decode(mfa_token=mfa_token, config_token_secret_key=config_token_secret_key)
    key = func_totp_key(config_totp_encryption_key=config_totp_encryption_key)
    user = dict(await client_postgres.fetchrow("SELECT * FROM users WHERE id = $1", user_id) or {})
    if not user: raise func_api_error(message="mfa token invalid or expired", status_code=401)
    func_auth_check_user_active(user=user)
    if not user.get("totp_enabled_at"): raise func_api_error(message="2FA is no longer on for this user: log in again", status_code=401)
    await func_totp_check(client_postgres=client_postgres, key=key, user=user, code=code, is_recovery_allowed=True)
    return await func_token_encode(user=user, config_token_secret_key=config_token_secret_key, config_access_token_expires_sec=config_access_token_expires_sec, config_refresh_token_expires_sec=config_refresh_token_expires_sec, config_column_token_encode=config_column_token_encode)
