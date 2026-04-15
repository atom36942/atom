#router
from fastapi import APIRouter
router=APIRouter()

#import
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#my
@router.get("/my/profile")
async def func_api_my_profile(*, request:Request):
   st=request.app.state
   profile=await st.func_user_profile_read(client_postgres_pool=st.client_postgres_pool, user_id=request.state.user["id"], config_sql=st.config_sql)
   token=await st.func_token_encode(user=profile, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":profile|token}

@router.post("/my/token-refresh")
async def func_api_my_token_refresh(*, request:Request):
   st=request.app.state
   user=await st.func_user_single_read(client_postgres_pool=st.client_postgres_pool, user_id=request.state.user["id"])
   token=await st.func_token_encode(user=user, config_token_secret_key=st.config_token_secret_key, config_token_expiry_sec=st.config_token_expiry_sec, config_token_refresh_expiry_sec=st.config_token_refresh_expiry_sec, config_token_key=st.config_token_key)
   return {"status":1,"message":token}

@router.get("/my/api-usage")
async def func_api_my_api_usage(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("days","int",1,None,None,None,None)], strict=0)
   # RENAMED: days_limit -> days
   obj_list=await st.func_user_api_usage_read(client_postgres_pool=st.client_postgres_pool, days=obj_query["days"], user_id=request.state.user["id"])
   return {"status":1,"message":obj_list}

@router.delete("/my/account-delete")
async def func_api_my_account_delete(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("mode","str",1,["soft","hard"],None,None,None)], strict=0)
   # RENAMED: delete_mode -> mode
   output=await st.func_user_account_delete(mode=obj_query["mode"], client_postgres_pool=st.client_postgres_pool, user_id=request.state.user["id"])
   return {"status":1,"message":output}

@router.get("/my/message-received")
async def func_api_my_message_received(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("mode","str",1,["all","unread","read"],None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)], strict=0)
   # RENAMED: sort_order -> order, limit_count -> limit, page_number -> page
   obj_list=await st.func_message_received(client_postgres_pool=st.client_postgres_pool, user_id=request.state.user["id"], mode=obj_query["mode"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-inbox")
async def func_api_my_message_inbox(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("mode","str",1,["all","unread","read"],None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)], strict=0)
   # RENAMED: sort_order -> order, limit_count -> limit, page_number -> page
   obj_list=await st.func_message_inbox(client_postgres_pool=st.client_postgres_pool, user_id=request.state.user["id"], mode=obj_query["mode"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
   return {"status":1,"message":obj_list}

@router.get("/my/message-thread")
async def func_api_my_message_thread(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("user_id","int",1,None,None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)], strict=0)
   # RENAMED: sort_order -> order, limit_count -> limit, page_number -> page
   obj_list=await st.func_message_thread(client_postgres_pool=st.client_postgres_pool, user_one_id=request.state.user["id"], user_id=obj_query["user_id"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
   asyncio.create_task(st.func_message_thread_mark_read(client_postgres_pool=st.client_postgres_pool, current_user_id=request.state.user["id"], partner_id=obj_query["user_id"]))
   return {"status":1,"message":obj_list}

@router.delete("/my/message-delete-single")
async def func_api_my_message_delete_single(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("id","int",1,None,None,None,None)], strict=0)
   # RENAMED: message_id -> id
   output=await st.func_message_delete_single(client_postgres_pool=st.client_postgres_pool, id=obj_query["id"], user_id=request.state.user["id"])
   return {"status":1,"message":output}

@router.delete("/my/message-delete-bulk")
async def func_api_my_message_delete_bulk(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("mode","str",1,["sent","received","all"],None,None,None)], strict=0)
   # RENAMED: delete_mode -> mode
   output=await st.func_message_delete_bulk(client_postgres_pool=st.client_postgres_pool, user_id=request.state.user["id"], mode=obj_query["mode"])
   return {"status":1,"message":output}

@router.get("/my/parent-read")
async def func_api_my_parent_read(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("parent_table","str",1,st.cache_postgres_schema_tables,None,None,None),("parent_column","str",1,st.cache_postgres_schema_columns,None,None,None),("order","str",0,None,"id desc",None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None)], strict=0)
   # RENAMED: table_name -> table, sort_order -> order, limit_count -> limit, page_number -> page
   output=await st.func_parent_read(client_postgres_pool=st.client_postgres_pool, table=obj_query["table"], parent_column=obj_query["parent_column"], parent_table=obj_query["parent_table"], created_by_id=request.state.user["id"], order=obj_query["order"], limit=obj_query["limit"], page=obj_query["page"])
   return {"status":1,"message":output}

@router.post("/my/ids-delete")
async def func_api_my_ids_delete(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("ids","str",1,None,None,None,None)], strict=0)
   # RENAMED: table_name -> table, record_ids -> ids
   output=await st.func_postgres_delete(client_postgres_pool=st.client_postgres_pool, table=obj_body["table"], ids=obj_body["ids"], created_by_id=request.state.user.get("id",0), config_postgres_ids_delete_limit=st.config_postgres_ids_delete_limit)
   return {"status":1,"message":output}

@router.post("/my/object-create")
async def func_api_my_object_create(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("mode","str",0,["now","buffer"],"now",None,None),("is_serialize","int",0,[0,1],0,None,None),("queue","str",0,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   return {"status":1,"message":await st.func_orchestrator_obj_create(request=request, api_role="my", obj_query=obj_query, obj_body=obj_body)}

@router.put("/my/object-update")
async def func_api_my_object_update(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("is_serialize","int",0,[0,1],0,None,None),("otp","int",0,None,None,None,None),("queue","str",0,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   return {"status":1,"message":await st.func_orchestrator_obj_update(request=request, api_role="my", obj_query=obj_query, obj_body=obj_body)}

@router.get("/my/object-read")
async def func_api_my_object_read(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None),("order","str",0,None,"id desc",None,None),("column","str",0,None,"*",None,None),("creator_key","str",0,None,None,None,None),("action_key","str",0,None,None,None,None)], strict=0)
   obj_query["created_by_id"]=f"""=,{request.state.user["id"]}"""
   obj_list=await st.func_postgres_read(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, table=obj_query["table"], filter_obj=obj_query, limit=obj_query["limit"], page=obj_query["page"], order=obj_query["order"], column=obj_query["column"], creator_key=obj_query["creator_key"], action_key=obj_query["action_key"])
   return {"status":1,"message":obj_list}

@router.post("/my/object-create-mongodb")
async def func_api_my_object_create_mongodb(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("database","str",1,None,None,None,None),("table","str",1,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   obj_list=obj_body.get("obj_list", [obj_body])
   output=await st.func_mongodb_object_create(client_mongodb=st.client_mongodb, database=obj_query["database"], table=obj_query["table"], obj_list=obj_list)
   return {"status":1,"message":output}
