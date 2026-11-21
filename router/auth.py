# import
import hmac
from fastapi import APIRouter
from fastapi import Request

# router
router = APIRouter()

# api
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "role", "type": "int", "required": True, "allowed": app_state.config_signup_allowed_roles}, {"name": "username", "type": "str", "required": True}, {"name": "password", "type": "str", "required": True}, {"name": "source", "type": "int"}])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_column_regex=app_state.config_column_regex, obj_list=[ob])
    user = await app_state.func_auth_signup_password(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, role=ob["role"], username=ob["username"], password=ob["password"], source=ob.get("source"), config_signup_allowed_roles=app_state.config_signup_allowed_roles)
    token = await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-username-password")
async def func_api_auth_login_username_password(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "role", "type": "int", "allowed": app_state.config_login_allowed_roles}, {"name": "username", "type": "str", "required": True}, {"name": "password", "type": "str", "required": True}])
    if ob.get("username"): ob["username"] = ob["username"].strip()
    await app_state.func_regex_check(config_column_regex=app_state.config_column_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="username", value=ob["username"], password=ob["password"], role=ob["role"])
    token = await app_state.func_auth_login_finish(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-email-password")
async def func_api_auth_login_email_password(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "role", "type": "int", "allowed": app_state.config_login_allowed_roles}, {"name": "email", "type": "str", "required": True}, {"name": "password", "type": "str", "required": True}])
    if ob.get("email"): ob["email"] = ob["email"].strip().lower()
    await app_state.func_regex_check(config_column_regex=app_state.config_column_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="email", value=ob["email"], password=ob["password"], role=ob["role"])
    token = await app_state.func_auth_login_finish(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-mobile-password")
async def func_api_auth_login_mobile_password(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "role", "type": "int", "allowed": app_state.config_login_allowed_roles}, {"name": "mobile", "type": "str", "required": True}, {"name": "password", "type": "str", "required": True}])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_column_regex=app_state.config_column_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="mobile", value=ob["mobile"], password=ob["password"], role=ob["role"])
    token = await app_state.func_auth_login_finish(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-id-ext-password")
async def func_api_auth_login_id_ext_password(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "role", "type": "int", "allowed": app_state.config_login_allowed_roles}, {"name": "id_ext", "type": "str", "required": True}, {"name": "password", "type": "str", "required": True}])
    if ob.get("id_ext"): ob["id_ext"] = ob["id_ext"].strip()
    await app_state.func_regex_check(config_column_regex=app_state.config_column_regex, obj_list=[ob])
    user = await app_state.func_auth_login_password(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, field="id_ext", value=ob["id_ext"], password=ob["password"], role=ob["role"])
    token = await app_state.func_auth_login_finish(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-email-otp")
async def func_api_auth_login_email_otp(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "role", "type": "int", "required": True, "allowed": app_state.config_login_allowed_roles}, {"name": "email", "type": "str", "required": True}, {"name": "otp", "type": "int", "required": True}, {"name": "source", "type": "int"}])
    if ob.get("email"): ob["email"] = ob["email"].strip().lower()
    await app_state.func_regex_check(config_column_regex=app_state.config_column_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres=request.state.client_postgres, otp=ob["otp"], email=ob["email"], mobile=None, config_otp_expiry_sec=app_state.config_otp_expiry_sec, config_otp_static=app_state.config_otp_static, config_otp_max_attempt=app_state.config_otp_max_attempt)
    user = await app_state.func_auth_user_find_or_create(client_postgres=request.state.client_postgres, field="email", value=ob["email"], role=ob["role"], source=ob.get("source"), config_signup_allowed_roles=app_state.config_signup_allowed_roles)
    token = await app_state.func_auth_login_finish(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-mobile-otp")
async def func_api_auth_login_mobile_otp(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "role", "type": "int", "required": True, "allowed": app_state.config_login_allowed_roles}, {"name": "mobile", "type": "str", "required": True}, {"name": "otp", "type": "int", "required": True}, {"name": "source", "type": "int"}])
    if ob.get("mobile"): ob["mobile"] = ob["mobile"].strip()
    await app_state.func_regex_check(config_column_regex=app_state.config_column_regex, obj_list=[ob])
    await app_state.func_otp_verify(client_postgres=request.state.client_postgres, otp=ob["otp"], mobile=ob["mobile"], email=None, config_otp_expiry_sec=app_state.config_otp_expiry_sec, config_otp_static=app_state.config_otp_static, config_otp_max_attempt=app_state.config_otp_max_attempt)
    user = await app_state.func_auth_user_find_or_create(client_postgres=request.state.client_postgres, field="mobile", value=ob["mobile"], role=ob["role"], source=ob.get("source"), config_signup_allowed_roles=app_state.config_signup_allowed_roles)
    token = await app_state.func_auth_login_finish(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-oidc")
async def func_api_auth_login_oidc(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    if not app_state.config_oidc_provider: raise app_state.func_api_error(message="OIDC not configured: set config_oidc_provider", status_code=400)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "provider", "type": "str", "required": True, "allowed": list(app_state.config_oidc_provider)}, {"name": "id_token", "type": "str", "required": True}, {"name": "role", "type": "int", "required": True, "allowed": app_state.config_login_allowed_roles}, {"name": "nonce", "type": "str"}, {"name": "source", "type": "int"}])
    provider = app_state.config_oidc_provider[ob["provider"]]
    claims = await app_state.func_oidc_verify(client_http=app_state.client_http, cache_oidc=app_state.cache_oidc, provider=provider, id_token=ob["id_token"], nonce=ob.get("nonce"))
    user = await app_state.func_auth_oidc_user(client_postgres=request.state.client_postgres, name=ob["provider"], provider=provider, claims=claims, role=ob["role"], source=ob.get("source"), config_signup_allowed_roles=app_state.config_signup_allowed_roles)
    token = await app_state.func_auth_login_finish(user=user, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-totp")
async def func_api_auth_login_totp(*, request: Request):
    app_state = request.app.state
    app_state.func_auth_check_config(client_postgres=request.state.client_postgres, config_token_secret_key=app_state.config_token_secret_key)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "mfa_token", "type": "str", "required": True}, {"name": "code", "type": "str", "required": True}], strict=True, reject_unknown=True)
    token = await app_state.func_auth_login_totp(client_postgres=app_state.client_postgres_dict.get("master"), mfa_token=ob["mfa_token"], code=ob["code"], config_totp_encryption_key=app_state.config_totp_encryption_key, config_token_secret_key=app_state.config_token_secret_key, config_access_token_expires_sec=app_state.config_access_token_expires_sec, config_refresh_token_expires_sec=app_state.config_refresh_token_expires_sec, config_column_token_encode=app_state.config_column_token_encode)
    return {"status": 1, "message": token}

@router.post("/auth/login-password")
async def func_api_auth_login_password(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "password", "type": "str", "required": True}])
    if not app_state.config_login_password: raise app_state.func_api_error(message="config_login_password not configured", status_code=500)
    if not hmac.compare_digest(str(ob["password"]), str(app_state.config_login_password)): raise Exception("incorrect password")
    return {"status": 1, "message": "ok"}
