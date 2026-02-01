#router
from fastapi import APIRouter
router=APIRouter()

#import
from config import *
from function import *
import asyncio
from datetime import datetime
from fastapi import Request,responses,WebSocket,WebSocketDisconnect

#index
@router.get("/")
async def func_api_5e118e61a6c348328913f14722d76af6():
   return await func_html_serve(config_folder_html,config_index_html)

#root
@router.get("/root/postgres-init")
async def func_api_35ccd536b313494d9043ddee84bb7b9e(request:Request):
   output=await func_postgres_init_schema(request.app.state.client_postgres_pool,config_postgres,func_postgres_schema_read,config_postgres_is_extension,0)
   await fund_reset_postgres_cache(request)
   return {"status":1,"message":output}

@router.get("/root/sync")
async def func_api_f5c4a2f6e328454e84732f36743916ee(request:Request):
   await func_postgres_flush(request.app)
   await fund_reset_postgres_cache(request)
   await fund_reset_cache_users(request)
   await func_postgres_clean(request.app.state.client_postgres_pool,config_table)
   return {"status":1,"message":"done"}

@router.post("/root/postgres-runner")
async def func_api_ccb985fc962349e4a2961d4bb030718c(request:Request):
   obj_body=await func_request_param_read(request,"body",[("mode","str",1,None),("query","str",1,None)])
   output=await func_postgres_runner(request.app.state.client_postgres_pool,obj_body["mode"],obj_body["query"])
   return {"status":1,"message":output}

@router.post("/root/postgres-export")
async def func_api_4eb43535bb05413c967fc18bfe93ac10(request:Request):
   obj_body=await func_request_param_read(request,"body",[("query","str",1,None)])
   stream=func_postgres_stream(request.app.state.client_postgres_pool,obj_body["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment;filename=file.csv"})

@router.post("/root/postgres-import")
async def func_api_5f4c0fdf16244ca084cd6a07687b245f(request:Request):
   obj_form=await func_request_param_read(request,"form",[("mode","str",1,None),("table","str",1,None),("file","file",1,[])])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   if obj_form["mode"]=="create":output=await func_postgres_obj_create(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,"now",obj_form["table"],obj_list,1,None)
   elif obj_form["mode"]=="update":output=await func_postgres_obj_update(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,obj_form["table"],obj_list,1,None)
   elif obj_form["mode"]=="delete":output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_form["table"],",".join(str(obj["id"]) for obj in obj_list),None)
   return {"status":1,"message":output}

@router.post("/root/redis-import")
async def func_api_08d1ca28b2d54be29d9e9064a8a148a4(request:Request):
   obj_form=await func_request_param_read(request,"form",[("mode","str",1,None),("table","str",1,None),("file","file",1,[]),("expiry_sec","int",0,None)])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   if obj_form["mode"]=="create":
      key_list=[f"{obj_form['table']}_{item['id']}" for item in obj_list]
      output=await func_redis_object_create(request.app.state.client_redis,key_list,obj_list,obj_form["expiry_sec"])
   return {"status":1,"message":output}

@router.post("/root/mongodb-import")
async def func_api_4519b1151a0e428aa1b781ec61ed8fb0(request:Request):
   obj_form=await func_request_param_read(request,"form",[("mode","str",1,None),("database","str",1,None),("table","str",1,None),("file","file",1,[])])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   if obj_form["mode"]=="create":output=await func_mongodb_object_create(request.app.state.client_mongodb,obj_form["database"],obj_form["table"],obj_list)
   return {"status":1,"message":output}

@router.get("/root/s3-bucket-ops")
async def func_api_ca7ecbd9afdc46e39e4267bd2c33290c(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,None),("bucket","str",1,None)])
   if obj_query["mode"]=="create":output=await func_s3_bucket_create(request.app.state.client_s3,config_s3_region_name,obj_query["bucket"])
   elif obj_query["mode"]=="public":output=await func_s3_bucket_public(request.app.state.client_s3,obj_query["bucket"])
   elif obj_query["mode"]=="empty":output=await func_s3_bucket_empty(request.app.state.client_s3_resource,obj_query["bucket"])
   elif obj_query["mode"]=="delete":output=await func_s3_bucket_delete(request.app.state.client_s3,obj_query["bucket"])
   return {"status":1,"message":output}

@router.post("/root/s3-url-delete")
async def func_api_ece7d0b10f9b4cb29167defe3b471f71(request:Request):
   obj_body=await func_request_param_read(request,"body",[("url","list",1,[])])
   for item in obj_body["url"]:output=await func_s3_url_delete(request.app.state.client_s3_resource,item)
   return {"status":1,"message":output}

#auth
@router.post("/auth/signup-username-password")
async def func_api_770160e847a341998b5b1c698e52e5c4(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("username","str",1,None),("password","str",1,None)])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await func_auth_signup_username_password(request.app.state.client_postgres_pool,obj_body["type"],obj_body["username"],obj_body["password"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":{"user":user,"token":token}}

@router.post("/auth/signup-username-password-bigint")
async def func_api_20406b7c056f42cfaeaa3a290740d804(request:Request):
    if config_is_signup==0:raise Exception("signup disabled")
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("username_bigint","int",1,None),("password_bigint","int",1,None)])
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
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("password","str",1,None),("username","str",1,None)])
    user=await func_auth_login_password_username_bigint(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password_bigint"],obj_body["username_bigint"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-email")
async def func_api_19f9214e86384b53a8a8284101b2e503(request:Request):
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("password","str",1,None),("email","str",1,None)])
    user=await func_auth_login_password_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["email"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-password-mobile")
async def func_api_bf6b5a6e72b34115add276d4639ecfa5(request:Request):
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("password","str",1,None),("mobile","str",1,None)])
    user=await func_auth_login_password_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["password"],obj_body["mobile"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-email")
async def func_api_03fd5ebf6cd84797a79d50e0c0d513d4(request:Request):
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("email","str",1,None),("otp","int",1,None)])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],obj_body["email"],None,config_otp_expire_sec)
    user=await func_auth_login_otp_email(request.app.state.client_postgres_pool,obj_body["type"],obj_body["email"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-otp-mobile")
async def func_api_10dbfd715056459eb9a54d6b57d4ec44(request:Request):
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("mobile","str",1,None),("otp","int",1,None)])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    await func_otp_verify(request.app.state.client_postgres_pool,obj_body["otp"],None,obj_body["mobile"],config_otp_expire_sec)
    user=await func_auth_login_otp_mobile(request.app.state.client_postgres_pool,obj_body["type"],obj_body["mobile"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

@router.post("/auth/login-google")
async def func_api_3cf56dd2c1b7458895585180af1b496d(request:Request):
    obj_body=await func_request_param_read(request,"body",[("type","int",1,None),("google_token","str",1,None)])
    if obj_body["type"] not in config_auth_type_list:raise Exception("type not allowed")
    user=await func_auth_login_google(request.app.state.client_postgres_pool,config_google_login_client_id,obj_body["type"],obj_body["google_token"])
    token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
    return {"status":1,"message":token}

#my
@router.get("/my/profile")
async def func_api_27860b1e950446a9b5bd28c2e9a33de4(request:Request):
   obj_query=await func_request_param_read(request,"query",[("is_metadata","int",0,None)])
   user=await func_user_single_read(request.app.state.client_postgres_pool,request.state.user["id"])
   metadata={}
   if obj_query["is_metadata"]==1:metadata=await func_user_sql_read(request.app.state.client_postgres_pool,config_sql,request.state.user["id"])
   asyncio.create_task(func_postgres_obj_update(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,"users",[{"id":request.state.user["id"],"last_active_at":datetime.utcnow()}],None,None))
   return {"status":1,"message":user|metadata}

@router.get("/my/token-refresh")
async def func_api_a39a95f6167a4ef2a33ea19a0f0e01e7(request:Request):
   user=await func_user_single_read(request.app.state.client_postgres_pool,request.state.user["id"])
   token=await func_jwt_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def func_api_12df64ab29a4486ca541c0610ef30a16(request:Request):
   obj_query=await func_request_param_read(request,"query",[("days","int",0,7)])
   obj_list=await func_api_usage_read(request.app.state.client_postgres_pool,obj_query["days"],request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def func_api_5a608eaf30a2410cadf331146b37883a(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,None)])
   user=await func_user_single_read(request.app.state.client_postgres_pool,request.state.user["id"])
   if user["api_access"]:raise Exception("not allowed as you have api_access")
   output=await func_user_single_delete(obj_query["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":output}

@router.get("/my/message-received")
async def func_api_70db90992c9143cc9208268810bc8573(request:Request):
   obj_query=await func_request_param_read(request,"query",[("is_unread","int",0,None),("order","str",0,None),("limit","int",0,None),("page","int",0,None)])
   obj_list=await func_message_received(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["is_unread"],obj_query["order"],obj_query["limit"],obj_query["page"])
   if obj_list:asyncio.create_task(func_postgres_ids_update(request.app.state.client_postgres_pool,"message",','.join(str(item['id']) for item in obj_list),"is_read",1,None,request.state.user["id"]))
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def func_api_4d24d2837d984b59a7044bc720ba1910(request:Request):
   obj_query=await func_request_param_read(request,"query",[("is_unread","int",0,None),("order","str",0,None),("limit","int",0,None),("page","int",0,None)])
   obj_list=await func_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["is_unread"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def func_api_27632b8e47c144519a8cdc38262762db(request:Request):
   obj_query=await func_request_param_read(request,"query",[("user_id","int",1,None),("order","str",0,None),("limit","int",0,None),("page","int",0,None)])
   obj_list=await func_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   asyncio.create_task(func_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete-single")
async def func_api_468c6788fdf24e749600298a5031caa4(request:Request):
   obj_query=await func_request_param_read(request,"query",[("id","int",1,None)])
   output=await func_message_delete_single_user(request.app.state.client_postgres_pool,obj_query["id"],request.state.user["id"])
   return {"status":1,"message":output}

@router.delete("/my/message-delete-bulk")
async def func_api_425899c34d174bd788b11e86981288ae(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,None)])
   output=await func_message_delete_bulk(obj_query["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":output}

@router.get("/my/parent-read")
async def func_api_c0d03f1f0c3d41969cadb97483aeb75e(request:Request):
   obj_query=await func_request_param_read(request,"query",[("table","str",1,None),("parent_table","str",1,None),("parent_column","str",1,None),("order","str",0,None),("limit","int",0,None),("page","int",0,None)])
   output=await func_postgres_parent_read(request.app.state.client_postgres_pool,obj_query["table"],obj_query["parent_column"],obj_query["parent_table"],request.state.user["id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":output}

@router.put("/my/ids-update")
async def func_api_da53d5219c094cd1ac0e55017423cedf(request:Request):
   obj_body=await func_request_param_read(request,"body",[("table","str",1,None),("ids","str",1,None),("column","str",1,None),("value","any",1,None)])
   if obj_body["table"] in ("users"):raise Exception("table not allowed")
   if obj_body["column"] in config_column_disabled_list:raise Exception("column not allowed")
   output=await func_postgres_ids_update(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],obj_body["column"],obj_body["value"],request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":output}

@router.post("/my/ids-delete")
async def func_api_9486563f3c1240c5840a251562e5a5c3(request:Request):
   obj_body=await func_request_param_read(request,"body",[("table","str",1,None),("ids","str",1,None)])
   if obj_body["table"] in ("users"):raise Exception("table not allowed")
   if len(obj_body["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],request.state.user["id"])
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def func_api_f48100707a724b979ccc5582a9bd0e28(request:Request):
   output=await func_obj_create_logic("my",request)
   return {"status":1,"message":output}

@router.put("/my/object-update")
async def func_api_a10070c5091d40ce90484ec9ec6e6587(request:Request):
   output=await func_obj_update_logic("my",request)
   return {"status":1,"message":output}

@router.get("/my/object-read")
async def func_api_4e9de78a107845b5a1ebcca0c61f7d0e(request:Request):
   obj_query=await func_request_param_read(request,"query",[("table","str",1,None)])
   obj_query["created_by_id"]=f"=,{request.state.user['id']}"
   obj_list=await func_postgres_obj_read(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,func_creator_data_add,func_action_count_add,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/my/object-create-mongodb")
async def func_api_ad13e1541fdf4aeda4702eba872afc41(request:Request):
   obj_query=await func_request_param_read(request,"query",[("database","str",1,None),("table","str",1,None)])
   obj_body=await func_request_param_read(request,"body",[])
   obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
   output=await func_mongodb_object_create(request.app.state.client_mongodb,obj_query["database"],obj_query["table"],obj_list)
   return {"status":1,"message":output}

#public
@router.get("/public/info")
async def func_api_05a7908253e14b7b8e37fc034d5dab95(request:Request):
   obj_query=await func_request_param_read(request,"query",[("key","str",0,None)])
   output={
   "request_state_app":{k:type(v).__name__ for k, v in request.app.state._state.items()},
   "api_list":[route.path for route in request.app.routes],
   "cache_postgres_schema":request.app.state.cache_postgres_schema,
   "cache_postgres_column_datatype":request.app.state.cache_postgres_column_datatype,
   "postgres_datatype_used_app":set(sorted({k["datatype"] for cols in config_postgres["table"].values() for k in cols})),
   "postgres_datatype_used_db":set(request.app.state.cache_postgres_column_datatype.values()),
   "config_postgres_column_setting":set([k for cols in config_postgres["table"].values() for col in cols for k in col]),
   }
   return {"status":1,"message":output if not obj_query["key"] else output[obj_query["key"]]}

@router.get("/public/converter-number")
async def func_api_8759a1e7a3cd4ed882dded3920fd998a(request:Request):
   obj_query=await func_request_param_read(request,"query",[("datatype","str",1,None),("mode","str",1,None),("x","str",1,None)])
   output=await func_converter_number(obj_query["datatype"],obj_query["mode"],obj_query["x"])
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def func_api_f48100707a724b979ccc5582a9bd0e28(request:Request):
   output=await func_obj_create_logic("public",request)
   return {"status":1,"message":output}

@router.get("/public/object-read")
async def func_api_88fdc8850b714b9db5fcac36cabf446d(request:Request):
   obj_query=await func_request_param_read(request,"query",[("table","str",1,None)])
   if obj_query["table"] not in config_public_table_read_list:raise Exception("table not allowed")
   obj_list=await func_postgres_obj_read(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,func_creator_data_add,func_action_count_add,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.get("/public/otp-verify")
async def func_api_c5119024bc5346d9a8ada54ee6dfdaed(request:Request):
   obj_query=await func_request_param_read(request,"query",[("otp","int",1,None),("email","str",0,None),("mobile","str",0,None)])
   output=await func_otp_verify(request.app.state.client_postgres_pool,obj_query["otp"],obj_query["email"],obj_query["mobile"],config_otp_expire_sec)
   return {"status":1,"message":output}

@router.get("/public/otp-send-email-ses")
async def func_api_244d67aedf2743d0a507560d2f1bae14(request:Request):
   obj_query=await func_request_param_read(request,"query",[("sender","str",1,None),("email","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=await func_ses_send_email(request.app.state.client_ses,obj_query["sender"],[obj_query["email"]],"your otp code",str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-resend")
async def func_api_ab8787cbe2e84442b805b2d4fc755643(request:Request):
   obj_query=await func_request_param_read(request,"query",[("sender","str",1,None),("email","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=await func_resend_send_email(config_resend_url,config_resend_key,obj_query["sender"],[obj_query["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-sns")
async def func_api_99803968df144a38b8d5293c8e3fa33e(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mobile","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=await func_sns_send_mobile_message(request.app.state.client_sns,obj_query["mobile"],str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_8ba3a3e8f4d94450bdcd444bf7336c76(request:Request):
   obj_body=await func_request_param_read(request,"body",[("mobile","str",1,None),("message","str",1,None),("template_id","str",1,None),("entity_id","str",1,None),("sender_id","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_body["mobile"])
   message=obj_body["message"].format(otp=otp)
   output=await func_sns_send_mobile_message_template(request.app.state.client_sns,obj_body["mobile"],message,obj_body["template_id"],obj_body["entity_id"],obj_body["sender_id"])
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-fast2sms")
async def func_api_42ce5231ca4e40cc9474938029bd40c5(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mobile","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=await func_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,obj_query["mobile"],otp)
   return {"status":1,"message":output}

@router.post("/public/object-create-gsheet")
async def func_api_ea356533d48f44bb9d7e79479fc43649(request:Request):
   obj_query=await func_request_param_read(request,"query",[("url","str",1,None)])
   obj_body=await func_request_param_read(request,"body",[])
   obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
   output=func_gsheet_object_create(request.app.state.client_gsheet,obj_query["url"],obj_list)
   return {"status":1,"message":output}

@router.get("/public/object-read-gsheet")
async def func_api_1c353211ef09455687a617b909eeaa7f(request:Request):
   obj_query=await func_request_param_read(request,"query",[("url","str",1,None)])
   obj_list=await func_gsheet_object_read(obj_query["url"])
   return {"status":1,"message":obj_list}

@router.post("/public/jira-worklog-export")
async def func_api_4a7af87fdb264c41ac62514a908fd0ef(request:Request):
   obj_body=await func_request_param_read(request,"body",[("jira_base_url","str",1,None),("jira_email","str",1,None),("jira_token","str",1,None),("start_date","str",0,None),("end_date","str",0,None)])
   output_path=func_jira_worklog_export(obj_body["jira_base_url"],obj_body["jira_email"],obj_body["jira_token"],obj_body["start_date"],obj_body["end_date"],None)
   return await func_client_download_file(output_path)

@router.get("/public/person-intel")
async def func_api_5aa65182abea4af6bd266efc05ac611f(request:Request,q:str):
    output=await func_person_intel_read(q,config_searchapi_key,request.app.state.client_gemini)
    return {"status":1,"message":output}

#private
@router.post("/private/s3-upload-file")
async def func_api_cf28dc32bf3c4adab8b6192cebec5e39(request:Request):
   obj_form=await func_request_param_read(request,"form",[("bucket","str",1,None),("file","file",1,[]),("key","list",0,[])])
   output={}
   for index,item in enumerate(obj_form["file"]):
      k=obj_form["key"][index] if index<len(obj_form["key"]) else None
      output[item.filename]=await func_s3_upload(request.app.state.client_s3,config_s3_region_name,obj_form["bucket"],item,k,config_limit_s3_kb)
   return {"status":1,"message":output}

@router.get("/private/s3-upload-presigned")
async def func_api_7031e803bbc544958a91c92a89187338(request:Request):
   obj_query=await func_request_param_read(request,"query",[("bucket","str",1,None),("key","str",0,None)])
   output=func_s3_upload_presigned(request.app.state.client_s3,config_s3_region_name,obj_query["bucket"],obj_query["key"],config_limit_s3_kb,config_s3_presigned_expire_sec)
   return {"status":1,"message":output}

#admin
@router.post("/admin/object-create")
async def func_api_6dba580b31ff43e6824ea4292eb9c749(request:Request):
   output=await func_obj_create_logic("admin",request)
   return {"status":1,"message":output}

@router.put("/admin/object-update")
async def func_api_febf6094467b456f8cabfb8191f1000e(request:Request):
   output=await func_obj_update_logic("admin",request)
   return {"status":1,"message":output}

@router.get("/admin/object-read")
async def func_api_bb6506520ad349f688f925055cd8b965(request:Request):
   obj_query=await func_request_param_read(request,"query",[("table","str",1,None)])
   obj_list=await func_postgres_obj_read(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,func_creator_data_add,func_action_count_add,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.put("/admin/ids-update")
async def func_api_39188c1de0d44463b2f6024b6415bb1c(request:Request):
   obj_body=await func_request_param_read(request,"body",[("table","str",1,None),("ids","str",1,None),("column","str",1,None),("value","any",1,None)])
   output=await func_postgres_ids_update(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],obj_body["column"],obj_body["value"],None,request.state.user["id"] if request.app.state.cache_postgres_schema.get(obj_body["table"]).get("updated_by_id") else None)
   return {"status":1,"message":output}

@router.post("/admin/ids-delete")
async def func_api_219e40d87ece488fb927dd4ee8f14bb9(request:Request):
   obj_body=await func_request_param_read(request,"body",[("table","str",1,None),("ids","str",1,None)])
   if len(obj_body["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],None)
   return {"status":1,"message":output}

#zzz
@router.get("/test")
async def func_api_2653353cdf3145558dae1c3ce24318e2(request:Request):
   if False:await func_sftp_file_upload(request.app.state.client_sftp,"static/ocr.png","ocr.png")
   if False:await func_sftp_file_download(request.app.state.client_sftp, "ocr.png")
   return {"status":1,"message":"welcome to test"}

@router.get("/protected/test")
async def func_api_1bd8a31e5baa4b67b6f05785f3dd52fb(request:Request):
   return {"status":1,"message":"welcome to test protected"}

@router.get("/page/{name}")
async def func_api_10f177735aac4564a0946f9088f17d9a(name):
   return await func_html_serve(config_folder_html,name)

@router.websocket("/websocket")
async def func_api_8d1ca30d92ee40c4afe50974fb3363e8(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         output=await func_postgres_obj_create(websocket.app.state.client_postgres_pool,func_postgres_obj_serialize,websocket.app.state.cache_postgres_column_datatype,"buffer","test",[{"title":message}],0,3)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")