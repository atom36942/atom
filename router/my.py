#import
from file.route import *

#api
@router.get("/my/profile")
async def function_api_my_profile(request:Request):
   param=await function_request_param_read(request,"query",[["is_metadata","int",0,None]])
   user=await function_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   metadata={}
   if param["is_metadata"]==1:metadata=await function_user_query_read(request.app.state.client_postgres_pool,config_query,request.state.user["id"])
   asyncio.create_task(function_postgres_object_update(request.app.state.client_postgres_pool,"users",[{"id":request.state.user["id"],"last_active_at":datetime.utcnow()}]))
   return {"status":1,"message":user|metadata}

@router.get("/my/token-refresh")
async def function_api_my_token_refresh(request:Request):
   user=await function_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   token=await function_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def function_api_my_api_usage(request:Request):
   param=await function_request_param_read(request,"query",[["days","int",0,7]])
   obj_list=await function_api_usage(request.app.state.client_postgres_pool,param["days"],request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def function_api_my_account_delete(request:Request):
   param=await function_request_param_read(request,"query",[["mode","str",1,None]])
   user=await function_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   if user["api_access"]:raise Exception("not allowed as you have api_access")
   await function_user_delete_single(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/message-received")
async def function_api_my_message_received(request:Request):
   param=await function_request_param_read(request,"query",[["is_unread","int",0,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   obj_list=await function_message_received(request.app.state.client_postgres_pool,request.state.user["id"],param["is_unread"],param["order"],param["limit"],param["page"])
   if obj_list:asyncio.create_task(function_postgres_ids_update(request.app.state.client_postgres_pool,"message",','.join(str(item['id']) for item in obj_list),"is_read",1,None,request.state.user["id"]))
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def function_api_my_message_inbox(request:Request):
   param=await function_request_param_read(request,"query",[["is_unread","int",0,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   obj_list=await function_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],param["is_unread"],param["order"],param["limit"],param["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def function_api_my_message_thread(request:Request):
   param=await function_request_param_read(request,"query",[["user_id","int",1,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   obj_list=await function_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"],param["order"],param["limit"],param["page"])
   asyncio.create_task(function_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete-single")
async def function_api_my_message_delete_single(request:Request):
   param=await function_request_param_read(request,"query",[["id","int",1,None]])
   await function_message_delete_single_user(request.app.state.client_postgres_pool,param["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.delete("/my/message-delete-bulk")
async def function_api_my_message_delete_bulk(request:Request):
   param=await function_request_param_read(request,"query",[["mode","str",1,None]])
   await function_message_delete_bulk(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/parent-read")
async def function_api_my_parent_read(request:Request):
   param=await function_request_param_read(request,"query",[["table","str",1,None],["parent_table","str",1,None],["parent_column","str",1,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   output=await function_postgres_parent_read(request.app.state.client_postgres_pool,param["table"],param["parent_column"],param["parent_table"],request.state.user["id"],param["order"],param["limit"],param["page"])
   return {"status":1,"message":output}

@router.post("/my/object-create-mongodb")
async def function_api_my_object_create_mongodb(request:Request):
   param=await function_request_param_read(request,"query",[["database","str",1,None],["table","str",1,None]])
   obj=await function_request_param_read(request,"body",[])
   obj_list=obj["object_list"] if "object_list" in obj else [obj]
   for i,x in enumerate(obj_list):
      if len(x)<=1:raise Exception("obj key length issue")
      if any(key in config_column_disabled_list for key in x):raise Exception("obj key not allowed")
      x["created_by_id"]=request.state.user["id"]
      if "password" in x:obj_list[i]=(await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,[x]))[0]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   output=await function_mongodb_object_create(request.app.state.client_mongodb,param["database"],param["table"],obj_list)
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def function_api_my_object_create(request:Request):
   param=await function_request_param_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0],["queue","str",0,None]])
   obj=await function_request_param_read(request,"body",[])
   obj_list=obj["object_list"] if "object_list" in obj else [obj]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   for i,x in enumerate(obj_list):
      if len(x)<=1:raise Exception("obj key length issue")
      if any(key in config_column_disabled_list for key in x):raise Exception("obj key not allowed")
      x["created_by_id"]=request.state.user["id"]
      if param["is_serialize"]==1 or "password" in x:obj_list[i]=(await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,[x]))[0]
   if not param["queue"]:output=await function_postgres_object_create("now",request.app.state.client_postgres_pool,param["table"],obj_list)
   elif param["queue"]=="buffer":output=await function_postgres_object_create("buffer",request.app.state.client_postgres_pool,param["table"],obj_list,config_table.get(param['table'],{}).get("buffer",10))
   else:
      function_name="function_postgres_object_create"
      param_list=[param["table"],obj_list]
      payload={"function":function_name,"table":param["table"],"obj_list":obj_list}
      if param["queue"]=="celery":output=await function_celery_producer(request.app.state.client_celery_producer,function_name,param_list)
      elif param["queue"]=="kafka":output=await function_kafka_producer(request.app.state.client_kafka_producer,config_channel_name,payload)
      elif param["queue"]=="rabbitmq":output=await function_rabbitmq_producer(request.app.state.client_rabbitmq_producer,config_channel_name,payload)
      elif param["queue"]=="redis":output=await function_redis_producer(request.app.state.client_redis_producer,config_channel_name,payload)
   return {"status":1,"message":output}
 
@router.put("/my/object-update")
async def function_api_my_object_update(request:Request):
   param=await function_request_param_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0],["otp","int",0,0]])
   obj=await function_request_param_read(request,"body",[])
   obj_list=obj["object_list"] if "object_list" in obj else [obj]
   for i,x in enumerate(obj_list):
      if "id" not in x:raise Exception("id missing")
      x["updated_by_id"]=request.state.user["id"]
      if len(x)<=2:raise Exception("obj key length issue")
      if any(key in config_column_disabled_list for key in x):raise Exception("obj key not allowed")
      if param["is_serialize"]==1 or "password" in x:obj_list[i]=(await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,[x]))[0]
   if param["table"]=="users":
      if len(obj_list)!=1:raise Exception("obj length issue")
      if obj_list[0]["id"]!=request.state.user["id"]:raise Exception("ownership issue")
      if any(key in obj_list[0] and len(obj_list[0])!=3 for key in ["password","email","mobile"]):raise Exception("obj length should be 2")
      if config_is_otp_verify_profile_update and any(key in obj_list[0] and not param["otp"] for key in ["email","mobile"]):raise Exception("otp missing")
      if param["otp"]:await function_otp_verify(request.app.state.client_postgres_pool,param["otp"],obj_list[0].get("email"),obj_list[0].get("mobile"),config_otp_expire_sec)
   output=await function_postgres_object_update(request.app.state.client_postgres_pool,param["table"],obj_list,None if param["table"]=="users" else request.state.user["id"])
   return {"status":1,"message":output}

@router.put("/my/ids-update")
async def function_api_my_ids_update(request:Request):
   param=await function_request_param_read(request,"body",[["table","str",1,None],["ids","str",1,None],["column","str",1,None],["value","any",1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if param["column"] in config_column_disabled_list:raise Exception("column not allowed")
   await function_postgres_ids_update(request.app.state.client_postgres_pool,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.post("/my/ids-delete")
async def function_api_my_ids_delete(request:Request):
   param=await function_request_param_read(request,"body",[["table","str",1,None],["ids","str",1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(param["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await function_postgres_ids_delete(request.app.state.client_postgres_pool,param["table"],param["ids"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/object-read")
async def function_api_my_object_read(request:Request):
   param=await function_request_param_read(request,"query",[["table","str",1,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   obj_list=await function_postgres_object_read(request.app.state.client_postgres_pool,param["table"],param,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,function_add_creator_data,function_add_action_count)
   return {"status":1,"message":obj_list}
