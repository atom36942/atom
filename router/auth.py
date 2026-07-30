# packages
import asyncio
import orjson
from fastapi import APIRouter, Request
from google.auth.transport import requests
from google.oauth2 import id_token

# router
router = APIRouter()

# api
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(*, request:Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[("role","int",1,app_state.config_allowed_users_role,None),("username","str",1,None,None),("password","str",1,None,None),("source","int",0,None,None)])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    if app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
    if ob["role"] == 1: raise Exception("role 1 not allowed for user creation")
    async with app_state.client_postgres.acquire() as conn:
        user = dict((await conn.fetch("INSERT INTO users (role, username, password, source) VALUES ($1, $2, $3, $4) RETURNING *;", ob["role"], ob["username"], app_state.client_password_hasher.hash(str(ob["password"])), ob["source"]))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status":1,"message":token}

@router.post("/auth/login-username-password")
async def func_api_auth_login_username_password(*, request:Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[["role","int",0,app_state.config_allowed_users_role,None],["username","str",1,None,None],["password","str",1,None,None]])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    async with app_state.client_postgres.acquire() as conn:
        user = await app_state.func_auth_user_login_fetch(conn=conn, field="username", value=ob["username"], role=ob["role"])
        try: app_state.client_password_hasher.verify(user["password"], str(ob["password"]))
        except Exception: raise Exception("incorrect password")
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status":1,"message":token}

@router.post("/auth/login-email-password")
async def func_api_auth_login_email_password(*, request:Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[("role","int",0,app_state.config_allowed_users_role,None),("email","str",1,None,None),("password","str",1,None,None)])
    if ob.get("email"): ob["email"] = ob["email"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    async with app_state.client_postgres.acquire() as conn:
        user = await app_state.func_auth_user_login_fetch(conn=conn, field="email", value=ob["email"], role=ob["role"])
        try: app_state.client_password_hasher.verify(user["password"], str(ob["password"]))
        except Exception: raise Exception("incorrect password")
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status":1,"message":token}

@router.post("/auth/login-mobile-password")
async def func_api_auth_login_mobile_password(*, request:Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[("role","int",0,app_state.config_allowed_users_role,None),("mobile","str",1,None,None),("password","str",1,None,None)])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    async with app_state.client_postgres.acquire() as conn:
        user = await app_state.func_auth_user_login_fetch(conn=conn, field="mobile", value=ob["mobile"], role=ob["role"])
        try: app_state.client_password_hasher.verify(user["password"], str(ob["password"]))
        except Exception: raise Exception("incorrect password")
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status":1,"message":token}

@router.post("/auth/login-email-otp")
async def func_api_auth_login_email_otp(*, request:Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[("role","int",1,app_state.config_allowed_users_role,None),("email","str",1,None,None),("otp","int",1,None,None),("source","int",0,None,None)])
    if ob.get("email"): ob["email"] = ob["email"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=ob["otp"], email=ob["email"], mobile=None, config_otp_expiry_sec=app_state.config_otp_expiry_sec)
    async with app_state.client_postgres.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE role=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", ob["role"], ob["email"])
        if not records and app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
        if not records and ob["role"] == 1: raise Exception("role 1 not allowed for user creation")
        user = dict(records[0]) if records else dict((await conn.fetch("INSERT INTO users (role, email, source) VALUES ($1, $2, $3) RETURNING *;", ob["role"], ob["email"], ob["source"]))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status":1,"message":token}

@router.post("/auth/login-mobile-otp")
async def func_api_auth_login_mobile_otp(*, request:Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[("role","int",1,app_state.config_allowed_users_role,None),("mobile","str",1,None,None),("otp","int",1,None,None),("source","int",0,None,None)])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=ob["otp"], mobile=ob["mobile"], email=None, config_otp_expiry_sec=app_state.config_otp_expiry_sec)
    async with app_state.client_postgres.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE role=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", ob["role"], ob["mobile"])
        if not records and app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
        if not records and ob["role"] == 1: raise Exception("role 1 not allowed for user creation")
        user = dict(records[0]) if records else dict((await conn.fetch("INSERT INTO users (role, mobile, source) VALUES ($1, $2, $3) RETURNING *;", ob["role"], ob["mobile"], ob["source"]))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status":1,"message":token}

@router.post("/auth/login-google")
async def func_api_auth_login_google(*, request:Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[("role","int",1,app_state.config_allowed_users_role,None),("google_token","str",1,None,None),("source","int",0,None,None)])
    id_info = await asyncio.to_thread(id_token.verify_oauth2_token, id_token=ob["google_token"], request=requests.Request(), audience=app_state.config_google_login_client_id)
    if not id_info: raise Exception("invalid google token")
    async with app_state.client_postgres.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE google_login_id=$1 AND role=$2;", id_info["sub"], ob["role"])
        if not records and app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
        if not records and ob["role"] == 1: raise Exception("role 1 not allowed for user creation")
        user = dict(records[0]) if records else dict((await conn.fetch("INSERT INTO users (role, google_login_id, email, name, google_login_metadata, source) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *;", ob["role"], id_info["sub"], id_info.get("email"), id_info.get("name"), orjson.dumps(id_info).decode("utf-8"), ob["source"]))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status":1,"message":token}
