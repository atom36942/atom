#import
from extend import *

#api
@router.get("/my/profile")
async def function_api_my_profile(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres_pool,request.state.user["id"])
   output=await function_read_user_count(request.app.state.client_postgres_pool,config_user_count_query,request.state.user["id"])
   asyncio.create_task(function_update_last_active_at(request.app.state.client_postgres_pool,request.state.user["id"]))
   return {"status":1,"message":user|output}

@router.get("/my/token-refresh")
async def function_api_my_token_refresh(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres_pool,request.state.user["id"])
   token=await function_token_encode(config_key_jwt,config_token_expire_sec,config_token_user_key_list,user)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def function_api_my_api_usage(request:Request):
   param=await function_param_read(request,"query",[["days","int",0,7]])
   object_list=await function_log_api_usage(request.app.state.client_postgres_pool,param["days"],request.state.user["id"])
   return {"status":1,"message":object_list}

@router.delete("/my/account-delete")
async def function_api_my_account_delete(request:Request):
   param=await function_param_read(request,"query",[["mode",None,1,None]])
   user=await function_read_user_single(request.app.state.client_postgres_pool,request.state.user["id"])
   if user["api_access"]:raise Exception("not allowed as you have api_access")
   await function_delete_user_single(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.put("/my/ids-update")
async def function_api_my_ids_update(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None],["column",None,1,None],["value",None,1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if param["column"] in config_column_disabled_list:raise Exception("column not allowed")
   await function_update_ids(request.app.state.client_postgres_pool,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.post("/my/ids-delete")
async def function_api_my_ids_delete(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(param["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await function_delete_ids(request.app.state.client_postgres_pool,param["table"],param["ids"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/message-received")
async def function_api_my_message_received(request:Request):
   param=await function_param_read(request,"query",[["is_unread","int",0,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   object_list=await function_message_received(request.app.state.client_postgres_pool,request.state.user["id"],param["order"],param["limit"],(param["page"]-1)*param["limit"],param["is_unread"])
   if object_list:asyncio.create_task(function_message_object_mark_read(request.app.state.client_postgres_pool,object_list))
   return {"status":1,"message":object_list}

@router.get("/my/message-inbox")
async def function_api_my_message_inbox(request:Request):
   param=await function_param_read(request,"query",[["is_unread","int",0,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   object_list=await function_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],param["order"],param["limit"],(param["page"]-1)*param["limit"],param["is_unread"])
   return {"status":1,"message":object_list}

@router.get("/my/message-thread")
async def function_api_my_message_thread(request:Request):
   param=await function_param_read(request,"query",[["user_id","int",1,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   object_list=await function_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"],param["order"],param["limit"],(param["page"]-1)*param["limit"])
   asyncio.create_task(function_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"]))
   return {"status":1,"message":object_list}

@router.delete("/my/message-delete-single")
async def function_api_my_message_delete_single(request:Request):
   param=await function_param_read(request,"query",[["id","int",1,None]])
   await function_message_delete_single(request.app.state.client_postgres_pool,request.state.user["id"],param["id"])
   return {"status":1,"message":"done"}

@router.delete("/my/message-delete-bulk")
async def function_api_my_message_delete_bulk(request:Request):
   param=await function_param_read(request,"query",[["mode",None,1,None]])
   await function_message_delete_bulk(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/parent-read")
async def function_api_my_parent_read(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["parent_table",None,1,None],["parent_column",None,1,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   output=await function_parent_object_read(request.app.state.client_postgres_pool,param["table"],param["parent_column"],param["parent_table"],param["order"],param["limit"],(param["page"]-1)*param["limit"],request.state.user["id"])
   return {"status":1,"message":output}

@router.delete("/my/object-delete-any")
async def function_api_my_object_delete_any(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   if param["table"] in ["users"]:raise Exception("table not allowed")
   await function_object_delete_postgres_any(request.app.state.client_postgres_pool,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":"done"}

@router.get("/my/object-read")
async def function_api_my_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["creator_key","list",0,[]]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   object_list=await function_object_read_postgres(request.app.state.client_postgres_pool,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if param["creator_key"]:object_list=await function_add_creator_data(request.app.state.client_postgres_pool,object_list,param["creator_key"])
   return {"status":1,"message":object_list}

@router.post("/my/object-create-mongodb")
async def function_api_my_object_create_mongodb(request:Request):
   param=await function_param_read(request,"query",[["database",None,1,None],["table",None,1,None]])
   obj=await function_param_read(request,"body",[])
   obj["created_by_id"]=request.state.user["id"]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(obj)<=1:raise Exception("obj issue")
   if any(key in config_column_disabled_list for key in obj):raise Exception("obj key not allowed")
   output=await function_mongodb_object_create(request.app.state.client_mongodb,param["database"],param["table"],[obj])
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def function_api_my_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["queue",None,0,None]])
   obj=await function_param_read(request,"body",[])
   obj["created_by_id"]=request.state.user["id"]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(obj)<=1:raise Exception("obj issue")
   if any(key in config_column_disabled_list for key in obj):raise Exception("obj key not allowed")
   if not param["queue"]:output=await function_postgres_object_create("now",request.app.state.client_postgres_pool,param["table"],[obj])
   elif param["queue"]=="buffer":output=await function_postgres_object_create("buffer",request.app.state.client_postgres_pool,param["table"],obj)
   else:
      payload={"function":"function_postgres_object_create","table":param["table"],"object_list":[obj]}
      if param["queue"]=="celery":output=await function_celery_producer(request.app.state.client_celery_producer,"function_postgres_object_create",[param["table"],[obj]])
      elif param["queue"]=="kafka":output=await function_kafka_producer(request.app.state.client_kafka_producer,"channel_1",payload)
      elif param["queue"]=="rabbitmq":output=await function_rabbitmq_producer(request.app.state.client_rabbitmq_producer,"channel_1",payload)
      elif param["queue"]=="redis":output=await function_redis_producer(request.app.state.client_redis_producer,"channel_1",payload)
   return {"status":1,"message":output}

@router.put("/my/object-update")
async def function_api_my_object_update(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["otp","int",0,0]])
   obj=await function_param_read(request,"body",[])
   obj["updated_by_id"]=request.state.user["id"]
   if "id" not in obj:raise Exception("id missing")
   if len(obj)<=2:raise Exception("obj length issue")
   if any(key in config_column_disabled_list for key in obj):raise Exception("obj key not allowed")
   if param["table"]=="users":
      if obj["id"]!=request.state.user["id"]:raise Exception("wrong id")
      if any(key in obj and len(obj)!=3 for key in ["password"]):raise Exception("obj length should be 2")
      if config_is_otp_verify_profile_update and any(key in obj and not param["otp"] for key in ["email","mobile"]):raise Exception("otp missing")
   if param["otp"]:
      email,mobile=obj.get("email"),obj.get("mobile")
      if email:await function_otp_verify("email",param["otp"],email,request.app.state.client_postgres_pool)
      elif mobile:await function_otp_verify("mobile",param["otp"],mobile,request.app.state.client_postgres_pool)
   if param["table"]=="users":output=await function_object_update_postgres(request.app.state.client_postgres_pool,"users",[obj],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   else:output=await function_object_update_postgres_user(request.app.state.client_postgres_pool,param["table"],[obj],request.state.user["id"],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}