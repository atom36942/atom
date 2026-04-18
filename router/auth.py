#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#auth
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("username","str",1,None,None,None,None),("password","str",1,None,None,["^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"],None)])
   user=await app_state.func_auth_signup_username_password(client_postgres_pool=app_state.client_postgres_pool, func_password_hash=app_state.func_password_hash, type=obj_body["type"], username=obj_body["username"], password=obj_body["password"], config_is_signup=app_state.config_is_signup, config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_auth_signup_username_password_bigint(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("username_bigint","int",1,None,None,None,None),("password_bigint","int",1,None,None,["^[0-9]{6,12}$", "Password must be 6-12 digits"],None)])
   user=await app_state.func_auth_signup_username_password_bigint(client_postgres_pool=app_state.client_postgres_pool, type=obj_body["type"], username_bigint=obj_body["username_bigint"], password_bigint=obj_body["password_bigint"], config_is_signup=app_state.config_is_signup, config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-username-password")
async def func_api_auth_login_username_password(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[["type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"],["username","str",1,None,None,None,None],["password","str",1,None,None,["^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"],None]])
   user=await app_state.func_auth_login_username_password(client_postgres_pool=app_state.client_postgres_pool, func_password_hash=app_state.func_password_hash, type=obj_body["type"], username=obj_body["username"], password=obj_body["password"])
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-username-password-bigint")
async def func_api_auth_login_username_password_bigint(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("username_bigint","int",1,None,None,None,None),("password_bigint","int",1,None,None,["^[0-9]{6,12}$", "Password must be 6-12 digits"],None)])
   user=await app_state.func_auth_login_username_password_bigint(client_postgres_pool=app_state.client_postgres_pool, type=obj_body["type"], username_bigint=obj_body["username_bigint"], password_bigint=obj_body["password_bigint"])
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-email-password")
async def func_api_auth_login_email_password(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("email","str",1,None,None,None,None),("password","str",1,None,None,["^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"],None)])
   user=await app_state.func_auth_login_email_password(client_postgres_pool=app_state.client_postgres_pool, func_password_hash=app_state.func_password_hash, type=obj_body["type"], email=obj_body["email"], password=obj_body["password"])
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-mobile-password")
async def func_api_auth_login_mobile_password(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("mobile","str",1,None,None,None,None),("password","str",1,None,None,["^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"],None)])
   user=await app_state.func_auth_login_mobile_password(client_postgres_pool=app_state.client_postgres_pool, func_password_hash=app_state.func_password_hash, type=obj_body["type"], mobile=obj_body["mobile"], password=obj_body["password"])
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-email-otp")
async def func_api_auth_login_email_otp(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("email","str",1,None,None,None,None),("otp","int",1,None,None,None,"Enter the OTP sent to your Email")])
   await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=obj_body["otp"], email=obj_body["email"], mobile=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)
   user=await app_state.func_auth_login_email_otp(client_postgres_pool=app_state.client_postgres_pool, type=obj_body["type"], email=obj_body["email"], config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-mobile-otp")
async def func_api_auth_login_mobile_otp(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("mobile","str",1,None,None,None,None),("otp","int",1,None,None,None,"Enter the OTP sent to your Mobile")])
   await app_state.func_otp_verify(client_postgres_pool=app_state.client_postgres_pool, otp=obj_body["otp"], mobile=obj_body["mobile"], email=None, config_expiry_sec_otp=app_state.config_expiry_sec_otp)
   user=await app_state.func_auth_login_mobile_otp(client_postgres_pool=app_state.client_postgres_pool, type=obj_body["type"], mobile=obj_body["mobile"], config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(*, request:Request):
   app_state=request.app.state
   obj_body=await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("type","int",1,app_state.config_auth_type,None,None,"Enter Login Type, Example: 1, 2, 3"),("google_token","str",1,None,None,None,None)])
   def func_google_verify_wrapper(token, client_id):
       from google.oauth2 import id_token
       from google.auth.transport import requests
       return id_token.verify_oauth2_token(id_token=token, request=requests.Request(), audience=client_id)
   user=await app_state.func_auth_login_google(client_postgres_pool=app_state.client_postgres_pool, func_google_verify=func_google_verify_wrapper, func_serialize=app_state.func_serialize, config_google_login_client_id=app_state.config_google_login_client_id, type=obj_body["type"], google_token=obj_body["google_token"], config_auth_type=app_state.config_auth_type)
   token=await app_state.func_token_encode(user=user, config_token_secret_key=app_state.config_token_secret_key, config_token_expiry_sec=app_state.config_token_expiry_sec, config_token_refresh_expiry_sec=app_state.config_token_refresh_expiry_sec, config_token_key=app_state.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}
