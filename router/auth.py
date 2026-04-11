#router
from fastapi import APIRouter
router=APIRouter()

#import
from function import *
from core.config import *
import orjson
from google.oauth2 import id_token
from google.auth.transport import requests
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#auth
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None),("username","str",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces")])
   user=await func_auth_signup_username_password(request.app.state.client_postgres_pool,func_password_hash,obj_body["type"],obj_body["username"],obj_body["password"],config_is_signup=config_is_signup,config_auth_type=config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_auth_signup_username_password_bigint(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None),("username_bigint","int",1,None,None,None),("password_bigint","int",1,None,None,"^[0-9]{6,12}$", "Password must be 6-12 digits")])
   user=await func_auth_signup_username_password_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username_bigint"],obj_body["password_bigint"],config_is_signup,config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def func_api_auth_login_password_username(request:Request):
   obj_body=await func_request_param_read(request,"body",[["type","int",1,None,None,None],["password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"],["username","str",1,None,None,None]])
   user=await func_auth_login_password_username(request.app.state.client_postgres_pool,func_password_hash,obj_body["type"],obj_body["password"],obj_body["username"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username-bigint")
async def func_api_auth_login_password_username_bigint(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None),("password_bigint","int",1,None,None,"^[0-9]{6,12}$", "Password must be 6-12 digits"),("username_bigint","int",1,None,None,None)])
   user=await func_auth_login_password_username_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password_bigint"],obj_body["username_bigint"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-email")
async def func_api_auth_login_password_email(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"),("email","str",1,None,None,None)])
   user=await func_auth_login_password_email(request.app.state.client_postgres_pool,func_password_hash,obj_body["type"],obj_body["password"],obj_body["email"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-mobile")
async def func_api_auth_login_password_mobile(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None),("password","str",1,None,None,"^\\S{8,32}$", "Password must be 8-32 characters and contain no spaces"),("mobile","str",1,None,None,None)])
   user=await func_auth_login_password_mobile(request.app.state.client_postgres_pool,func_password_hash,obj_body["type"],obj_body["password"],obj_body["mobile"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-email")
async def func_api_auth_login_otp_email(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None,None),("email","str",1,None,None,None,None),("otp","int",1,None,None,None,None)])
   await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],obj_body["email"],None,config_expiry_sec_otp=config_expiry_sec_otp)
   user=await func_auth_login_otp_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["email"],config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-otp-mobile")
async def func_api_auth_login_otp_mobile(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None,None),("mobile","str",1,None,None,None,None),("otp","int",1,None,None,None,None)])
   await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],None,obj_body["mobile"],config_expiry_sec_otp=config_expiry_sec_otp)
   user=await func_auth_login_otp_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["mobile"],config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-google")
async def func_api_auth_login_google(request:Request):
   obj_body=await func_request_param_read(request,"body",[("type","int",1,None,None,None,None),("google_token","str",1,None,None,None,None)])
   def func_google_verify_wrapper(token, client_id):
       return id_token.verify_oauth2_token(token, requests.Request(), client_id)
   user=await func_auth_login_google(request.app.state.client_postgres_pool,func_google_verify_wrapper,orjson.dumps,config_google_login_client_id,obj_body["type"],obj_body["google_token"],config_auth_type=config_auth_type)
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":{"user":user,"token":token}}
