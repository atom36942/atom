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
async def func_api_auth_signup_username_password(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "username", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "password", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": True, "allowed": app_state.config_allowed_users_role, "default": None}, {"name": "source", "type": "int", "required": False, "allowed": None, "default": None}])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    user = await app_state.func_auth_signup_password(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, role=ob["role"], username=ob["username"], password=ob["password"], source=ob.get("source"), config_is_signup=app_state.config_is_signup)
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-username-password")
async def func_api_auth_login_username_password(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "username", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "password", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": False, "allowed": app_state.config_allowed_users_role, "default": None}])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="username", value=ob["username"], password=ob["password"], role=ob["role"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-email-password")
async def func_api_auth_login_email_password(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "email", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "password", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": False, "allowed": app_state.config_allowed_users_role, "default": None}])
    if ob.get("email"): ob["email"] = ob["email"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="email", value=ob["email"], password=ob["password"], role=ob["role"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-mobile-password")
async def func_api_auth_login_mobile_password(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "mobile", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "password", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": False, "allowed": app_state.config_allowed_users_role, "default": None}])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="mobile", value=ob["mobile"], password=ob["password"], role=ob["role"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-id-ext-password")
async def func_api_auth_login_id_ext_password(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "id_ext", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "password", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": False, "allowed": app_state.config_allowed_users_role, "default": None}])
    if ob.get("id_ext"): ob["id_ext"] = ob["id_ext"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="id_ext", value=ob["id_ext"], password=ob["password"], role=ob["role"])
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-email-otp")
async def func_api_auth_login_email_otp(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "email", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "otp", "type": "int", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": True, "allowed": app_state.config_allowed_users_role, "default": None}, {"name": "source", "type": "int", "required": False, "allowed": None, "default": None}])
    if ob.get("email"): ob["email"] = ob["email"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=ob["otp"], email=ob["email"], mobile=None, config_otp_expiry_sec=app_state.config_otp_expiry_sec, config_otp_static=app_state.config_otp_static)
    user = await app_state.func_auth_user_find_or_create(client_postgres=app_state.client_postgres, field="email", value=ob["email"], role=ob["role"], source=ob.get("source"), config_is_signup=app_state.config_is_signup)
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-mobile-otp")
async def func_api_auth_login_mobile_otp(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "mobile", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "otp", "type": "int", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": True, "allowed": app_state.config_allowed_users_role, "default": None}, {"name": "source", "type": "int", "required": False, "allowed": None, "default": None}])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres=app_state.client_postgres, otp=ob["otp"], mobile=ob["mobile"], email=None, config_otp_expiry_sec=app_state.config_otp_expiry_sec, config_otp_static=app_state.config_otp_static)
    user = await app_state.func_auth_user_find_or_create(client_postgres=app_state.client_postgres, field="mobile", value=ob["mobile"], role=ob["role"], source=ob.get("source"), config_is_signup=app_state.config_is_signup)
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-google")
async def func_api_auth_login_google(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "google_token", "type": "str", "required": True, "allowed": None, "default": None}, {"name": "role", "type": "int", "required": True, "allowed": app_state.config_allowed_users_role, "default": None}, {"name": "source", "type": "int", "required": False, "allowed": None, "default": None}])
    id_info = await asyncio.to_thread(id_token.verify_oauth2_token, id_token=ob["google_token"], request=requests.Request(), audience=app_state.config_google_login_client_id)
    if not id_info: raise Exception("invalid google token")
    extra_cols = {"email": id_info.get("email"), "name": id_info.get("name"), "google_login_metadata": orjson.dumps(id_info).decode("utf-8")}
    user = await app_state.func_auth_user_find_or_create(client_postgres=app_state.client_postgres, field="google_login_id", value=id_info["sub"], role=ob["role"], source=ob.get("source"), config_is_signup=app_state.config_is_signup, extra_cols=extra_cols)
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-password")
async def func_api_auth_login_password(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[{"name": "password", "type": "str", "required": True, "allowed": None, "default": None}])
    if ob["password"] != str(app_state.config_login_password): raise Exception("incorrect password")
    return {"status": 1, "message": "ok"}
