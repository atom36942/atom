#router
from fastapi import APIRouter
router=APIRouter()

#import
from core.config import *
from function import *
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#my
@router.get("/my/profile")
async def func_api_my_profile(request:Request):
   st=request.app.state
   profile=await func_my_profile_read(st.client_postgres_pool,request.state.user["id"],config_sql)
   token=await func_token_encode(profile,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":profile|token}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(request:Request):
   user=await func_user_single_read(request.app.state.client_postgres_pool,request.state.user["id"])
   token=await func_token_encode(user,config_token_secret_key,config_token_expiry_sec,config_token_refresh_expiry_sec,config_token_key)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(request:Request):
   obj_query=await func_request_param_read(request,"query",[("days","int",1,None,None,None,None)])
   obj_list=await func_api_usage_read(request.app.state.client_postgres_pool,obj_query["days"],request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def func_api_my_account_delete(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["soft","hard"],None,None,None)])
   output=await func_account_delete(obj_query["mode"],request.app.state.client_postgres_pool,request.state.user["id"])
   return {"status":1,"message":output}

@router.get("/my/message-received")
async def func_api_my_message_received(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["all","unread","read"],None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)])
   obj_list=await func_message_received(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["mode"],obj_query["order"],obj_query["limit"],obj_query["page"],request.app.state.func_postgres_ids_update)
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["all","unread","read"],None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)])
   obj_list=await func_message_inbox(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["mode"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(request:Request):
   obj_query=await func_request_param_read(request,"query",[("user_id","int",1,None,None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)])
   obj_list=await func_message_thread(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   asyncio.create_task(func_message_thread_mark_read(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete-single")
async def func_api_my_message_delete_single(request:Request):
   obj_query=await func_request_param_read(request,"query",[("id","int",1,None,None,None,None)])
   output=await func_message_delete_single(request.app.state.client_postgres_pool,obj_query["id"],request.state.user["id"])
   return {"status":1,"message":output}

@router.delete("/my/message-delete-bulk")
async def func_api_my_message_delete_bulk(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["sent","received","all"],None,None,None)])
   output=await func_message_delete_bulk(request.app.state.client_postgres_pool,request.state.user["id"],obj_query["mode"])
   return {"status":1,"message":output}

@router.get("/my/parent-read")
async def func_api_my_parent_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("parent_table","str",1,st.cache_postgres_schema_tables,None,None,None),("parent_column","str",1,st.cache_postgres_schema_columns,None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)])
   output=await func_postgres_parent_read(st.client_postgres_pool,obj_query["table"],obj_query["parent_column"],obj_query["parent_table"],request.state.user["id"],obj_query["order"],obj_query["limit"],obj_query["page"])
   return {"status":1,"message":output}

@router.post("/my/ids-delete")
async def func_api_my_ids_delete(request:Request):
   st=request.app.state
   obj_body=await func_request_param_read(request,"body",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("ids","str",1,None,None,None,None)])
   output=await func_postgres_ids_delete(st.client_postgres_pool,obj_body["table"],obj_body["ids"],request.state.user.get("id",0),config_table_system,config_postgres_ids_delete_limit)
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def func_api_my_object_create(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("mode","str",0,["now","buffer"],"now",None,None),("is_serialize","int",0,[0,1],0,None,None),("queue","str",0,None,None,None,None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_orchestrator_object_create("my",obj_query,obj_body,request.state.user.get("id"),st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_orchestrator_producer_dispatch,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_allowed,st.func_postgres_create,st.config_postgres_batch_limit)}

@router.put("/my/object-update")
async def func_api_my_object_update(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("is_serialize","int",0,[0,1],0,None,None),("otp","int",0,None,None,None,None),("queue","str",0,None,None,None,None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_orchestrator_object_update("my",obj_query,obj_body,request.state.user.get("id"),st.config_column_blocked,st.config_column_single_update,st.client_postgres_pool,st.func_postgres_obj_serialize,st.func_orchestrator_producer_dispatch,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_allowed,st.func_postgres_update,st.func_otp_verify,st.config_expiry_sec_otp,0,st.config_postgres_batch_limit)}

@router.get("/my/object-read")
async def func_api_my_object_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None),("order","str",0,None,"id desc",None,None),("column","str",0,None,"*",None,None),("creator_key","str",0,None,None,None,None),("action_key","str",0,None,None,None,None)])
   obj_query["created_by_id"]=f"""=,{request.state.user["id"]}"""
   obj_list=await func_postgres_read(st.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(request:Request):
   obj_query=await func_request_param_read(request,"query",[("database","str",1,None,None,None,None),("table","str",1,None,None,None,None)])
   obj_body=await func_request_param_read(request,"body",[])
   obj_list=obj_body.get("obj_list", [obj_body])
   output=await func_mongodb_object_create(request.app.state.client_mongodb,obj_query["database"],obj_query["table"],obj_list)
   return {"status":1,"message":output}
