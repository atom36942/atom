#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#auth
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None),("username","str",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces")], is_strict=0)
   user=await st.func_auth_signup_username_password(client_postgres_pool=st.client_postgres_pool, func_password_hash=st.func_password_hash, user_type=obj_body["type"], username_raw=obj_body["username"], password_raw=obj_body["password"], config_is_signup=st.config_is_signup, config_auth_type=st.config_auth_type)
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_auth_signup_username_password_bigint(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None),("username_bigint","int",1,None,None,None),("password_bigint","int",1,None,None,"^[0-9]{6,12}$", "Password must be 6-12 digits")], is_strict=0)
   user=await st.func_auth_signup_username_password_bigint(client_postgres_pool=st.client_postgres_pool, user_type=obj_body["type"], username_bigint=obj_body["username_bigint"], password_bigint=obj_body["password_bigint"], config_is_signup=st.config_is_signup, config_auth_type=st.config_auth_type)
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def func_api_auth_login_password_username(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[["type","int",1,None,None,None],["password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"],["username","str",1,None,None,None]], is_strict=0)
   user=await st.func_auth_login_password_username(client_postgres_pool=st.client_postgres_pool, func_password_hash=st.func_password_hash, user_type=obj_body["type"], password_raw=obj_body["password"], username=obj_body["username"])
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username-bigint")
async def func_api_auth_login_password_username_bigint(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None),("password_bigint","int",1,None,None,"^[0-9]{6,12}$", "Password must be 6-12 digits"),("username_bigint","int",1,None,None,None)], is_strict=0)
   user=await st.func_auth_login_password_username_bigint(client_postgres_pool=st.client_postgres_pool, user_type=obj_body["type"], password_bigint=obj_body["password_bigint"], username_bigint=obj_body["username_bigint"])
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-email")
async def func_api_auth_login_password_email(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"),("email","str",1,None,None,None)], is_strict=0)
   user=await st.func_auth_login_password_email(client_postgres_pool=st.client_postgres_pool, func_password_hash=st.func_password_hash, user_type=obj_body["type"], password_raw=obj_body["password"], email_address=obj_body["email"])
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-mobile")
async def func_api_auth_login_password_mobile(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"),("mobile","str",1,None,None,None)], is_strict=0)
   user=await st.func_auth_login_password_mobile(client_postgres_pool=st.client_postgres_pool, func_password_hash=st.func_password_hash, user_type=obj_body["type"], password_raw=obj_body["password"], mobile_number=obj_body["mobile"])
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-email")
async def func_api_auth_login_otp_email(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None,None),("email","str",1,None,None,None,None),("otp","int",1,None,None,None,None)], is_strict=0)
   await st.func_otp_verify(client_postgres_pool=st.client_postgres_pool, otp=obj_body["otp"], email=obj_body["email"], config_expiry_sec_otp=st.config_expiry_sec_otp)
   user=await st.func_auth_login_otp_email(client_postgres_pool=st.client_postgres_pool, user_type=obj_body["type"], email_address=obj_body["email"], config_auth_type=st.config_auth_type)
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-mobile")
async def func_api_auth_login_otp_mobile(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None,None),("mobile","str",1,None,None,None,None),("otp","int",1,None,None,None,None)], is_strict=0)
   await st.func_otp_verify(client_postgres_pool=st.client_postgres_pool, otp=obj_body["otp"], mobile=obj_body["mobile"], config_expiry_sec_otp=st.config_expiry_sec_otp)
   user=await st.func_auth_login_otp_mobile(client_postgres_pool=st.client_postgres_pool, user_type=obj_body["type"], mobile_number=obj_body["mobile"], config_auth_type=st.config_auth_type)
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request_obj=request, parsing_mode="body", param_config=[("type","int",1,None,None,None,None),("google_token","str",1,None,None,None,None)], is_strict=0)
   def func_google_verify_wrapper(token, client_id):
       from google.oauth2 import id_token
       from google.auth.transport import requests
       return id_token.verify_oauth2_token(id_token=token, request=requests.Request(), audience=client_id)
   user=await st.func_auth_login_google(client_postgres_pool=st.client_postgres_pool, func_google_verify=func_google_verify_wrapper, func_serialize=st.func_serialize, config_google_login_client_id=st.config_google_login_client_id, user_type=obj_body["type"], google_token=obj_body["google_token"], config_auth_type=st.config_auth_type)
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}
