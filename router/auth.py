# router
from fastapi import APIRouter
router = APIRouter()

# import
from fastapi import Request
from google.oauth2 import id_token
from google.auth.transport import requests
import orjson
import asyncio

# api
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_allowed_auth_types,None),("username","str",1,None,None),("password","str",1,None,None)])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    if app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
    if ob["type"] not in app_state.config_allowed_auth_types: raise Exception(f"authentication type {ob['type']} not allowed")
    async with app_state.client_postgres_pool.acquire() as conn:
        user = dict((await conn.fetch("INSERT INTO users (type, username, password) VALUES ($1, $2, $3) RETURNING *;", ob["type"], ob["username"], app_state.client_password_hasher.hash(str(ob["password"]))))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    asyncio.create_task(app_state.func_notification_create(type=3, app_state=app_state, payload={"table": "users", "obj_list": [user]}))
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-username-password")
async def func_api_auth_login_username_password(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[["type","int",1,app_state.config_allowed_auth_types,None],["username","str",1,None,None],["password","str",1,None,None]])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND username=$2 ORDER BY id DESC LIMIT 1;", ob["type"], ob["username"])
        if not records: raise Exception("username not found")
        try: app_state.client_password_hasher.verify(records[0]["password"], str(ob["password"]))
        except Exception: raise Exception("incorrect password")
        user = dict(records[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-email-password")
async def func_api_auth_login_email_password(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_allowed_auth_types,None),("email","str",1,None,None),("password","str",1,None,None)])
    if ob.get("email"): ob["email"] = ob["email"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", ob["type"], ob["email"])
        if not records: raise Exception("email not found")
        try: app_state.client_password_hasher.verify(records[0]["password"], str(ob["password"]))
        except Exception: raise Exception("incorrect password")
        user = dict(records[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-mobile-password")
async def func_api_auth_login_mobile_password(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_allowed_auth_types,None),("mobile","str",1,None,None),("password","str",1,None,None)])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", ob["type"], ob["mobile"])
        if not records: raise Exception("mobile not found")
        try: app_state.client_password_hasher.verify(records[0]["password"], str(ob["password"]))
        except Exception: raise Exception("incorrect password")
        user = dict(records[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-email-otp")
async def func_api_auth_login_email_otp(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_allowed_auth_types,None),("email","str",1,None,None),("otp","int",1,None,None)])
    if ob.get("email"): ob["email"] = ob["email"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=ob["otp"], email=ob["email"], mobile=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)
    if ob["type"] not in app_state.config_allowed_auth_types: raise Exception(f"type not allowed: {ob['type']}, allowed: {app_state.config_allowed_auth_types}")
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND email=$2 ORDER BY id DESC LIMIT 1;", ob["type"], ob["email"])
        if not records and app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
        user = dict(records[0]) if records else dict((await conn.fetch("INSERT INTO users (type, email) VALUES ($1, $2) RETURNING *;", ob["type"], ob["email"]))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-mobile-otp")
async def func_api_auth_login_mobile_otp(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_allowed_auth_types,None),("mobile","str",1,None,None),("otp","int",1,None,None)])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=ob["otp"], mobile=ob["mobile"], email=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)
    if ob["type"] not in app_state.config_allowed_auth_types: raise Exception(f"type not allowed: {ob['type']}, allowed: {app_state.config_allowed_auth_types}")
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE type=$1 AND mobile=$2 ORDER BY id DESC LIMIT 1;", ob["type"], ob["mobile"])
        if not records and app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
        user = dict(records[0]) if records else dict((await conn.fetch("INSERT INTO users (type, mobile) VALUES ($1, $2) RETURNING *;", ob["type"], ob["mobile"]))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_allowed_auth_types,None),("google_token","str",1,None,None)])
    if ob["type"] not in app_state.config_allowed_auth_types: raise Exception(f"authentication type {ob['type']} not allowed")
    id_info = id_token.verify_oauth2_token(id_token=ob["google_token"], request=requests.Request(), audience=app_state.config_google_login_client_id)
    if not id_info: raise Exception("invalid google token")
    async with app_state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users WHERE google_login_id=$1 AND type=$2;", id_info["sub"], ob["type"])
        if not records and app_state.config_is_enable_signup == 0: raise Exception("signup disabled")
        user = dict(records[0]) if records else dict((await conn.fetch("INSERT INTO users (type, google_login_id, email, name, google_login_metadata) VALUES ($1, $2, $3, $4, $5) RETURNING *;", ob["type"], id_info["sub"], id_info.get("email"), id_info.get("name"), orjson.dumps(id_info).decode("utf-8")))[0])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
    return {"status":1,"message":{"user":user,"token":token}}
