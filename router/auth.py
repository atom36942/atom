#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#auth
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None),("username","str",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces")])
   user=await st.func_auth_signup_username_password(st.client_postgres_pool,st.func_password_hash,obj_body["type"],obj_body["username"],obj_body["password"],config_is_signup=st.config_is_signup,config_auth_type=st.config_auth_type)
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_auth_signup_username_password_bigint(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None),("username_bigint","int",1,None,None,None),("password_bigint","int",1,None,None,"^[0-9]{6,12}$", "Password must be 6-12 digits")])
   user=await st.func_auth_signup_username_password_bigint(st.client_postgres_pool,obj_body["type"],obj_body["username_bigint"],obj_body["password_bigint"],st.config_is_signup,st.config_auth_type)
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def func_api_auth_login_password_username(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[["type","int",1,None,None,None],["password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"],["username","str",1,None,None,None]])
   user=await st.func_auth_login_password_username(st.client_postgres_pool,st.func_password_hash,obj_body["type"],obj_body["password"],obj_body["username"])
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username-bigint")
async def func_api_auth_login_password_username_bigint(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None),("password_bigint","int",1,None,None,"^[0-9]{6,12}$", "Password must be 6-12 digits"),("username_bigint","int",1,None,None,None)])
   user=await st.func_auth_login_password_username_bigint(st.client_postgres_pool,obj_body["type"],obj_body["password_bigint"],obj_body["username_bigint"])
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-email")
async def func_api_auth_login_password_email(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"),("email","str",1,None,None,None)])
   user=await st.func_auth_login_password_email(st.client_postgres_pool,st.func_password_hash,obj_body["type"],obj_body["password"],obj_body["email"])
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-mobile")
async def func_api_auth_login_password_mobile(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"),("mobile","str",1,None,None,None)])
   user=await st.func_auth_login_password_mobile(st.client_postgres_pool,st.func_password_hash,obj_body["type"],obj_body["password"],obj_body["mobile"])
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-email")
async def func_api_auth_login_otp_email(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None,None),("email","str",1,None,None,None,None),("otp","int",1,None,None,None,None)])
   await st.func_otp_verify(st.client_postgres_pool,obj_body["otp"],obj_body["email"],None,config_expiry_sec_otp=st.config_expiry_sec_otp)
   user=await st.func_auth_login_otp_email(st.client_postgres_pool,obj_body["type"],obj_body["email"],st.config_auth_type)
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-mobile")
async def func_api_auth_login_otp_mobile(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None,None),("mobile","str",1,None,None,None,None),("otp","int",1,None,None,None,None)])
   await st.func_otp_verify(st.client_postgres_pool,obj_body["otp"],None,obj_body["mobile"],config_expiry_sec_otp=st.config_expiry_sec_otp)
   user=await st.func_auth_login_otp_mobile(st.client_postgres_pool,obj_body["type"],obj_body["mobile"],st.config_auth_type)
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request,"body",[("type","int",1,None,None,None,None),("google_token","str",1,None,None,None,None)])
   def func_google_verify_wrapper(token, client_id):
       from google.oauth2 import id_token
       from google.auth.transport import requests
       return id_token.verify_oauth2_token(token, requests.Request(), client_id)
   user=await st.func_auth_login_google(st.client_postgres_pool,func_google_verify_wrapper,st.func_serialize,st.config_google_login_client_id,obj_body["type"],obj_body["google_token"],config_auth_type=st.config_auth_type)
   token=await st.func_token_encode(user,st.config_token_secret_key,st.config_token_expiry_sec,st.config_token_refresh_expiry_sec,st.config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}
