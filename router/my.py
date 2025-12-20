#import
from core.route import *

#api
@router.get("/my/profile")
async def func_api_my_profile(request:Request):
   param=await func_request_obj_read(request,"query",[["is_metadata","int",0,None]])
   user=await func_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   metadata={}
   if param["is_metadata"]==1:metadata=await func_user_sql_read(request.app.state.client_postgres_pool,config_sql,request.state.user["id"])
   asyncio.create_task(func_postgres_obj_list_update(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,"users",[{"id":request.state.user["id"],"last_active_at":datetime.utcnow()}],None,None))
   return {"status":1,"message":user|metadata}

@router.get("/my/token-refresh")
async def func_api_my_token_refresh(request:Request):
   user=await func_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   token=await func_token_encode(user,config_key_jwt,config_token_expire_sec,config_token_user_key_list)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(request:Request):
   param=await func_request_obj_read(request,"query",[["days","int",0,7]])
   obj_list=await func_api_usage(request.app.state.client_postgres_pool,param["days"],request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def func_api_my_account_delete(request:Request):
   param=await func_request_obj_read(request,"query",[["mode","str",1,None]])
   user=await func_user_read_single(request.app.state.client_postgres_pool,request.state.user["id"])
   if user["api_access"]:raise Exception("not allowed as you have api_access")
   await func_user_delete_single(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/message-received")
async def func_api_my_message_received(request:Request):
   param=await func_request_obj_read(request,"query",[["is_unread","int",0,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   obj_list=await func_message_received(request.app.state.client_postgres_pool,request.state.user["id"],param["is_unread"],param["order"],param["limit"],param["page"])
   if obj_list:asyncio.create_task(func_postgres_ids_update(request.app.state.client_postgres_pool,"message",','.join(str(item['id']) for item in obj_list),"is_read",1,None,request.state.user["id"]))
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(request:Request):
   param=await func_request_obj_read(request,"query",[["is_unread","int",0,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   obj_list=await func_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],param["is_unread"],param["order"],param["limit"],param["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(request:Request):
   param=await func_request_obj_read(request,"query",[["user_id","int",1,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   obj_list=await func_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"],param["order"],param["limit"],param["page"])
   asyncio.create_task(func_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],param["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete-single")
async def func_api_my_message_delete_single(request:Request):
   param=await func_request_obj_read(request,"query",[["id","int",1,None]])
   await func_message_delete_single_user(request.app.state.client_postgres_pool,param["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.delete("/my/message-delete-bulk")
async def func_api_my_message_delete_bulk(request:Request):
   param=await func_request_obj_read(request,"query",[["mode","str",1,None]])
   await func_message_delete_bulk(param["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/parent-read")
async def func_api_my_parent_read(request:Request):
   param=await func_request_obj_read(request,"query",[["table","str",1,None],["parent_table","str",1,None],["parent_column","str",1,None],["order","str",0,None],["limit","int",0,None],["page","int",0,None]])
   output=await func_postgres_parent_read(request.app.state.client_postgres_pool,param["table"],param["parent_column"],param["parent_table"],request.state.user["id"],param["order"],param["limit"],param["page"])
   return {"status":1,"message":output}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(request:Request):
   param=await func_request_obj_read(request,"query",[["database","str",1,None],["table","str",1,None]])
   obj=await func_request_obj_read(request,"body",[])
   obj_list=obj["obj_list"] if "obj_list" in obj else [obj]
   for i,x in enumerate(obj_list):
      if len(x)<=1:raise Exception("obj key length issue")
      if any(key in config_column_disabled_list for key in x):raise Exception("obj key not allowed")
      x["created_by_id"]=request.state.user["id"]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   output=await func_mongodb_object_create(request.app.state.client_mongodb,param["database"],param["table"],obj_list)
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def func_api_my_object_create(request:Request):
   param=await func_request_obj_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0],["queue","str",0,None]])
   obj=await func_request_obj_read(request,"body",[])
   obj_list=obj["obj_list"] if "obj_list" in obj else [obj]
   if param["table"] in ["users"]:raise Exception("table not allowed")
   for i,x in enumerate(obj_list):
      if len(x)<=1:raise Exception("obj key length issue")
      if any(key in config_column_disabled_list for key in x):raise Exception("obj key not allowed")
      x["created_by_id"]=request.state.user["id"]
   if not param["queue"]:output=await func_postgres_obj_list_create(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,"now",param["table"],obj_list,param["is_serialize"])
   elif param["queue"]=="buffer":output=await func_postgres_obj_list_create(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,"buffer",param["table"],obj_list,param["is_serialize"],config_table.get(param['table'],{}).get("buffer",10))
   else:
      func_name="func_postgres_obj_list_create"
      param_list=[param["table"],obj_list]
      payload={"function":func_name,"table":param["table"],"obj_list":obj_list}
      if param["queue"]=="celery":output=await func_celery_producer(request.app.state.client_celery_producer,func_name,param_list)
      elif param["queue"]=="kafka":output=await func_kafka_producer(request.app.state.client_kafka_producer,config_channel_name,payload)
      elif param["queue"]=="rabbitmq":output=await func_rabbitmq_producer(request.app.state.client_rabbitmq_producer,config_channel_name,payload)
      elif param["queue"]=="redis":output=await func_redis_producer(request.app.state.client_redis_producer,config_channel_name,payload)
   return {"status":1,"message":output}
 
@router.put("/my/object-update")
async def func_api_my_object_update(request:Request):
   param=await func_request_obj_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0],["otp","int",0,0]])
   obj=await func_request_obj_read(request,"body",[])
   obj_list=obj["obj_list"] if "obj_list" in obj else [obj]
   for i,x in enumerate(obj_list):
      if "id" not in x:raise Exception("id missing")
      x["updated_by_id"]=request.state.user["id"]
      if len(x)<=2:raise Exception("obj key length issue")
      if any(key in config_column_disabled_list for key in x):raise Exception("obj key not allowed")
   if param["table"]=="users":
      if len(obj_list)!=1:raise Exception("obj length issue")
      if obj_list[0]["id"]!=request.state.user["id"]:raise Exception("ownership issue")
      if any(key in obj_list[0] and len(obj_list[0])!=3 for key in ["password","email","mobile"]):raise Exception("obj length should be 2")
      if config_is_otp_verify_profile_update and any(key in obj_list[0] and not param["otp"] for key in ["email","mobile"]):raise Exception("otp missing")
      if param["otp"]:await func_otp_verify(request.app.state.client_postgres_pool,param["otp"],obj_list[0].get("email"),obj_list[0].get("mobile"),config_otp_expire_sec)
   output=await func_postgres_obj_list_update(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,param["table"],obj_list,param["is_serialize"],None if param["table"]=="users" else request.state.user["id"])
   return {"status":1,"message":output}

@router.put("/my/ids-update")
async def func_api_my_ids_update(request:Request):
   param=await func_request_obj_read(request,"body",[["table","str",1,None],["ids","str",1,None],["column","str",1,None],["value","any",1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if param["column"] in config_column_disabled_list:raise Exception("column not allowed")
   await func_postgres_ids_update(request.app.state.client_postgres_pool,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.post("/my/ids-delete")
async def func_api_my_ids_delete(request:Request):
   param=await func_request_obj_read(request,"body",[["table","str",1,None],["ids","str",1,None]])
   if param["table"] in ["users"]:raise Exception("table not allowed")
   if len(param["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await func_postgres_ids_delete(request.app.state.client_postgres_pool,param["table"],param["ids"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/object-read")
async def func_api_my_object_read(request:Request):
   param=await func_request_obj_read(request,"query",[["table","str",1,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   obj_list=await func_postgres_object_read(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,func_add_creator_data,func_add_action_count,param["table"],param)
   return {"status":1,"message":obj_list}
