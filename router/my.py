#import
from route import *

#api
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

