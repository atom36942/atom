#import
from extend import *

#api
@router.get("/my/profile")
async def function_api_my_profile(request:Request):
   user=await function_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   output=await function_user_query_count_read(request.app.state.client_postgres_pool,request.state.user["id"],config_user_count_query)
   asyncio.create_task(function_user_update_last_active_at(request.app.state.client_postgres_pool,request.state.user["id"]))
   return {"status":1,"message":user|output}

@router.get("/my/token-refresh")
async def function_api_my_token_refresh(request:Request):
   user=await function_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def function_api_my_api_usage(request:Request):
   param=await function_param_read("query",request,[["days","int",0,7]])
   obj_list=await function_api_usage(request.app.state.client_postgres_pool,param["days"],request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def function_api_my_account_delete(request:Request):
   param=await function_param_read("query",request,[["mode",None,1,None]])
   user=await function_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   if user["api_access"]:raise Exception("not allowed as you have api_access")
   await function_user_delete_single(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.put("/my/ids-update")
async def function_api_my_ids_update(request:Request):
   param=await function_param_read("body",request,[["table",None,1,None],["ids",None,1,None],["column",None,1,None],["value",None,1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if param["column"] in config_column_disabled_list:raise Exception("column not allowed")
   await function_postgres_update_ids(request.app.state.client_postgres_pool,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.post("/my/ids-delete")
async def function_api_my_ids_delete(request:Request):
   param=await function_param_read("body",request,[["table",None,1,None],["ids",None,1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(param["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await function_postgres_delete_ids(request.app.state.client_postgres_pool,param["table"],param["ids"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/message-received")
async def function_api_my_message_received(request:Request):
   param=await function_param_read("query",request,[["is_unread","int",0,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   obj_list=await function_message_received(request.app.state.client_postgres_pool,request.state.user["id"],param["is_unread"],param["order"],param["limit"],param["page"])
   if obj_list:asyncio.create_task(function_message_object_mark_read(request.app.state.client_postgres_pool,obj_list))
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def function_api_my_message_inbox(request:Request):
   param=await function_param_read("query",request,[["is_unread","int",0,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   obj_list=await function_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],param["is_unread"],param["order"],param["limit"],param["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def function_api_my_message_thread(request:Request):
   param=await function_param_read("query",request,[["user_id","int",1,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   obj_list=await function_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"],param["order"],param["limit"],param["page"])
   asyncio.create_task(function_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete-single")
async def function_api_my_message_delete_single(request:Request):
   param=await function_param_read("query",request,[["id","int",1,None]])
   await function_message_delete_single(request.app.state.client_postgres_pool,param["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.delete("/my/message-delete-bulk")
async def function_api_my_message_delete_bulk(request:Request):
   param=await function_param_read("query",request,[["mode",None,1,None]])
   await function_message_delete_bulk(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/parent-read")
async def function_api_my_parent_read(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None],["parent_table",None,1,None],["parent_column",None,1,None],["order",None,0,"id desc"],["limit","int",0,100],["page","int",0,1]])
   output=await function_postgres_parent_read(request.app.state.client_postgres_pool,param["table"],param["parent_column"],param["parent_table"],request.state.user["id"],param["order"],param["limit"],param["page"])
   return {"status":1,"message":output}

@router.delete("/my/object-delete-any")
async def function_api_my_object_delete_any(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   if param["table"] in ["users"]:raise Exception("table not allowed")
   await function_postgres_object_delete(request.app.state.client_postgres_pool,param["table"],param)
   return {"status":1,"message":"done"}

@router.get("/my/object-read")
async def function_api_my_object_read(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None],["creator_key_list","list",0,[]]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   obj_list=await function_postgres_object_read(request.app.state.client_postgres_pool,param["table"],param)
   if param["creator_key_list"]:obj_list=await function_add_creator_data(request.app.state.client_postgres_pool,obj_list,param["creator_key_list"])
   return {"status":1,"message":obj_list}

@router.post("/my/object-create-mongodb")
async def function_api_my_object_create_mongodb(request:Request):
   param=await function_param_read("query",request,[["database",None,1,None],["table",None,1,None]])
   obj=await function_param_read("body",request,[])
   obj["created_by_id"]=request.state.user["id"]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(obj)<=1:raise Exception("obj issue")
   if any(key in config_column_disabled_list for key in obj):raise Exception("obj key not allowed")
   output=await function_mongodb_object_create(request.app.state.client_mongodb,param["database"],param["table"],[obj])
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def function_api_my_object_create(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None],["queue",None,0,None]])
   obj=await function_param_read("body",request,[])
   obj["created_by_id"]=request.state.user["id"]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(obj)<=1:raise Exception("obj issue")
   if any(key in config_column_disabled_list for key in obj):raise Exception("obj key not allowed")
   if not param["queue"]:output=await function_postgres_object_create(request.app.state.client_postgres_pool,param["table"],[obj])
   elif param["queue"]=="buffer":output=await function_postgres_object_create(request.app.state.client_postgres_pool,param["table"],[obj],"buffer")
   else:
      payload={"function":"function_postgres_object_create","table":param["table"],"obj_list":[obj]}
      if param["queue"]=="celery":output=await function_celery_producer(request.app.state.client_celery_producer,"function_postgres_object_create",[param["table"],[obj]])
      elif param["queue"]=="kafka":output=await function_kafka_producer(request.app.state.client_kafka_producer,"channel_1",payload)
      elif param["queue"]=="rabbitmq":output=await function_rabbitmq_producer(request.app.state.client_rabbitmq_producer,"channel_1",payload)
      elif param["queue"]=="redis":output=await function_redis_producer(request.app.state.client_redis_producer,"channel_1",payload)
   return {"status":1,"message":output}

@router.put("/my/object-update")
async def function_api_my_object_update(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None],["otp","int",0,0]])
   obj=await function_param_read("body",request,[])
   obj["updated_by_id"]=request.state.user["id"]
   if "id" not in obj:raise Exception("id missing")
   if len(obj)<=2:raise Exception("obj length issue")
   if any(key in config_column_disabled_list for key in obj):raise Exception("obj key not allowed")
   if param["table"]=="users":
      if obj["id"]!=request.state.user["id"]:raise Exception("ownership issue")
      if any(key in obj and len(obj)!=3 for key in ["password"]):raise Exception("obj length should be 2")
      if config_is_otp_verify_profile_update and any(key in obj and not param["otp"] for key in ["email","mobile"]):raise Exception("otp missing")
   if param["otp"]:
      email,mobile=obj.get("email"),obj.get("mobile")
      if email:await function_otp_verify(request.app.state.client_postgres_pool,param["otp"],email,None)
      elif mobile:await function_otp_verify(request.app.state.client_postgres_pool,param["otp"],None,mobile)
   if param["table"]=="users":output=await function_postgres_object_update(request.app.state.client_postgres_pool,"users",[obj])
   else:output=await function_postgres_object_update(request.app.state.client_postgres_pool,param["table"],[obj],request.state.user["id"])
   return {"status":1,"message":output}

