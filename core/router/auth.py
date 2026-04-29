#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#auth
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(*, request:Request):
   app_state=request.app.state
   ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None),("username","str",1,None,None),("password","str",1,None,None)])
   await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=app_state.func_request_obj_list_read(obj_body=ob))
   user=await app_state.func_auth_signup_username_password(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, type=ob["type"], username=ob["username"], password=ob["password"], config_is_signup=app_state.config_is_signup, config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-username-password")
async def func_api_auth_login_username_password(*, request:Request):
   app_state=request.app.state
   ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[["type","int",1,app_state.config_auth_type,None],["username","str",1,None,None],["password","str",1,None,None]])
   await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=app_state.func_request_obj_list_read(obj_body=ob))
   user=await app_state.func_auth_login_username_password(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, type=ob["type"], username=ob["username"], password=ob["password"])
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-email-password")
async def func_api_auth_login_email_password(*, request:Request):
   app_state=request.app.state
   ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None),("email","str",1,None,None),("password","str",1,None,None)])
   await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=app_state.func_request_obj_list_read(obj_body=ob))
   user=await app_state.func_auth_login_email_password(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, type=ob["type"], email=ob["email"], password=ob["password"])
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-mobile-password")
async def func_api_auth_login_mobile_password(*, request:Request):
   app_state=request.app.state
   ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None),("mobile","str",1,None,None),("password","str",1,None,None)])
   await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=app_state.func_request_obj_list_read(obj_body=ob))
   user=await app_state.func_auth_login_mobile_password(client_postgres_pool=app_state.client_postgres_pool, client_password_hasher=app_state.client_password_hasher, type=ob["type"], mobile=ob["mobile"], password=ob["password"])
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-email-otp")
async def func_api_auth_login_email_otp(*, request:Request):
   app_state=request.app.state
   ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None),("email","str",1,None,None),("otp","int",1,None,None)])
   await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=app_state.func_request_obj_list_read(obj_body=ob))
   await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=ob["otp"], email=ob["email"], mobile=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)
   user=await app_state.func_auth_login_email_otp(client_postgres_pool=app_state.client_postgres_pool, type=ob["type"], email=ob["email"], config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-mobile-otp")
async def func_api_auth_login_mobile_otp(*, request:Request):
   app_state=request.app.state
   ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None),("mobile","str",1,None,None),("otp","int",1,None,None)])
   await app_state.func_regex_check(config_regex=app_state.config_regex, obj_list=app_state.func_request_obj_list_read(obj_body=ob))
   await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=ob["otp"], mobile=ob["mobile"], email=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)
   user=await app_state.func_auth_login_mobile_otp(client_postgres_pool=app_state.client_postgres_pool, type=ob["type"], mobile=ob["mobile"], config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(*, request:Request):
   app_state=request.app.state
   ob=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None),("google_token","str",1,None,None)])
   user=await app_state.func_auth_login_google(client_postgres_pool=app_state.client_postgres_pool, func_serialize=app_state.func_serialize, config_google_login_client_id=app_state.config_google_login_client_id, type=ob["type"], google_token=ob["google_token"], config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}
