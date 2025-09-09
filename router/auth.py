#import
from extend import *

#api
@router.post("/auth/signup-username-password")
async def function_api_auth_signup_username_password(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    param=await function_param_read("body",request,[["type","int",1,None],["username",None,1,None],["password",None,1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await function_auth_signup_username_password(request.app.state.client_postgres_pool,param["type"],param["username"],param["password"])
    token=await function_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def function_api_auth_signup_username_password_bigint(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    param=await function_param_read("body",request,[["type","int",1,None],["username_bigint","int",1,None],["password_bigint","int",1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await function_auth_signup_username_password_bigint(request.app.state.client_postgres_pool,param["type"],param["username_bigint"],param["password_bigint"])
    token=await function_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def function_api_auth_login_password_username(request:Request):
    param=await function_param_read("body",request,[["type","int",1,None],["password",None,1,None],["username",None,1,None]])
    token=await function_auth_login_password_username(request.app.state.client_postgres_pool,param["type"],param["password"],param["username"],function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-username-bigint")
async def function_api_auth_login_password_username_bigint(request:Request):
    param=await function_param_read("body",request,[["type","int",1,None],["password_bigint","int",1,None],["username_bigint","int",1,None]])
    token=await function_auth_login_password_username_bigint(request.app.state.client_postgres_pool,param["type"],param["password_bigint"],param["username_bigint"],function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-email")
async def function_api_auth_login_password_email(request:Request):
    param=await function_param_read("body",request,[["type","int",1,None],["password",None,1,None],["email",None,1,None]])
    token=await function_auth_login_password_email(request.app.state.client_postgres_pool,param["type"],param["password"],param["email"],function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-mobile")
async def function_api_auth_login_password_mobile(request:Request):
    param=await function_param_read("body",request,[["type","int",1,None],["password",None,1,None],["mobile",None,1,None]])
    token=await function_auth_login_password_mobile(request.app.state.client_postgres_pool,param["type"],param["password"],param["mobile"],function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-email")
async def function_api_auth_login_otp_email(request:Request):
    param=await function_param_read("body",request,[["type","int",1,None],["otp","int",1,None],["email",None,1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    token=await function_auth_login_otp_email(request.app.state.client_postgres_pool,param["type"],param["email"],param["otp"],function_otp_verify,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-mobile")
async def function_api_auth_login_otp_mobile(request:Request):
    param=await function_param_read("body",request,[["type","int",1,None],["otp","int",1,None],["mobile",None,1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    token=await function_auth_login_otp_mobile(request.app.state.client_postgres_pool,param["type"],param["mobile"],param["otp"],function_otp_verify,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-google")
async def function_api_auth_login_google(request:Request):
    param=await function_param_read("body",request,[["type","int",1,None],["google_token",None,1,None]])
    if param["type"] not in config_auth_type_list:raise Exception("type not allowed")
    token=await function_auth_login_google(request.app.state.client_postgres_pool,param["type"],param["google_token"],config_google_login_client_id,function_token_encode,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}
