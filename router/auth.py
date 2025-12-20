#import
from core.route import *

#api
@router.post("/auth/signup-username-password")
async def func_api_770160e847a341998b5b1c698e52e5c4(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["username","str",1,None],["password","str",1,None]])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await func_auth_signup_username_password(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username"],obj_body["password"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_20406b7c056f42cfaeaa3a290740d804(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["username_bigint","int",1,None],["password_bigint","int",1,None]])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await func_auth_signup_username_password_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username_bigint"],obj_body["password_bigint"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/login-password-username")
async def func_api_6dd2a4b658884b8e93df7b89c75a3a38(request:Request):
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["password","str",1,None],["username","str",1,None]])
    user=await func_auth_login_password_username(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["username"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-username-bigint")
async def func_api_39329b86e0ad499194916937c84ccbf2(request:Request):
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["password_bigint","int",1,None],["username_bigint","int",1,None]])
    user=await func_auth_login_password_username_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password_bigint"],obj_body["username_bigint"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-email")
async def func_api_19f9214e86384b53a8a8284101b2e503(request:Request):
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["password","str",1,None],["email","str",1,None]])
    user=await func_auth_login_password_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["email"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-mobile")
async def func_api_bf6b5a6e72b34115add276d4639ecfa5(request:Request):
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["password","str",1,None],["mobile","str",1,None]])
    user=await func_auth_login_password_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["mobile"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-email")
async def func_api_03fd5ebf6cd84797a79d50e0c0d513d4(request:Request):
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["email","str",1,None],["otp","int",1,None]])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],obj_body["email"],None,config_otp_expire_sec)
    user=await func_auth_login_otp_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["email"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-mobile")
async def func_api_10dbfd715056459eb9a54d6b57d4ec44(request:Request):
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["mobile","str",1,None],["otp","int",1,None]])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],None,obj_body["mobile"],config_otp_expire_sec)
    user=await func_auth_login_otp_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["mobile"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-google")
async def func_api_3cf56dd2c1b7458895585180af1b496d(request:Request):
    obj_body=await func_request_param_read(request,"body",[["type","int",1,None],["google_token","str",1,None]])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await func_auth_login_google(request.app.state.client_postgres_pool,config_google_login_client_id,obj_body["type"],obj_body["google_token"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}
