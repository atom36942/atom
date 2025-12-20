#import
from core.route import *

#api
@router.post("/auth/signup-username-password")
async def func_api_auth_signup_username_password(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["username","str",1,None],["password","str",1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await func_auth_signup_username_password(request.app.state.client_postgres_pool,param["type"],param["username"],param["password"])
    token=await func_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_auth_signup_username_password_bigint(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["username_bigint","int",1,None],["password_bigint","int",1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await func_auth_signup_username_password_bigint(request.app.state.client_postgres_pool,param["type"],param["username_bigint"],param["password_bigint"])
    token=await func_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def func_api_auth_login_password_username(request:Request):
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["password","str",1,None],["username","str",1,None]])
    token=await func_auth_login_password_username(request.app.state.client_postgres_pool,param["type"],param["password"],param["username"],func_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-username-bigint")
async def func_api_auth_login_password_username_bigint(request:Request):
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["password_bigint","int",1,None],["username_bigint","int",1,None]])
    token=await func_auth_login_password_username_bigint(request.app.state.client_postgres_pool,param["type"],param["password_bigint"],param["username_bigint"],func_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-email")
async def func_api_auth_login_password_email(request:Request):
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["password","str",1,None],["email","str",1,None]])
    token=await func_auth_login_password_email(request.app.state.client_postgres_pool,param["type"],param["password"],param["email"],func_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-mobile")
async def func_api_auth_login_password_mobile(request:Request):
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["password","str",1,None],["mobile","str",1,None]])
    token=await func_auth_login_password_mobile(request.app.state.client_postgres_pool,param["type"],param["password"],param["mobile"],func_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-email")
async def func_api_auth_login_otp_email(request:Request):
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["otp","int",1,None],["email","str",1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    token=await func_auth_login_otp_email(request.app.state.client_postgres_pool,param["type"],param["email"],param["otp"],func_otp_verify,func_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list,config_otp_expire_sec)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-mobile")
async def func_api_auth_login_otp_mobile(request:Request):
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["otp","int",1,None],["mobile","str",1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    token=await func_auth_login_otp_mobile(request.app.state.client_postgres_pool,param["type"],param["mobile"],param["otp"],func_otp_verify,func_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list,config_otp_expire_sec)
    return {"status":1,"message":token}

@router.post("/auth/login-google")
async def func_api_auth_login_google(request:Request):
    param=await func_request_obj_read(request,"body",[["type","int",1,None],["google_token","str",1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    token=await func_auth_login_google(request.app.state.client_postgres_pool,param["type"],param["google_token"],config_google_login_client_id,func_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}
