#router
from fastapi import APIRouter
router=APIRouter()

#import
from core.config import *
from function import *
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#admin
@router.get("/admin/sync")
async def func_api_admin_sync(request:Request):
   if request.app.state.client_postgres_pool:
      await func_postgres_init(request.app.state.client_postgres_pool, config_postgres)
   await func_postgres_create(request.app.state.client_postgres_pool,func_postgres_obj_serialize,"flush",None,None)
   request.app.state.cache_postgres_schema=await func_postgres_schema_read(request.app.state.client_postgres_pool) if request.app.state.client_postgres_pool else {}
   request.app.state.cache_postgres_schema_tables=list(request.app.state.cache_postgres_schema.keys())
   request.app.state.cache_postgres_schema_columns=sorted(list(set(col for table in request.app.state.cache_postgres_schema.values() for col in table.keys())))
   request.app.state.cache_users_role=await func_sql_map_column(request.app.state.client_postgres_pool,config_sql.get("cache_users_role")) if request.app.state.client_postgres_pool else {}
   request.app.state.cache_users_is_active=await func_sql_map_column(request.app.state.client_postgres_pool,config_sql.get("cache_users_is_active")) if request.app.state.client_postgres_pool else {}
   await func_postgres_clean(request.app.state.client_postgres_pool,config_table)
   request.app.state.cache_openapi=request.app.state.func_openapi_spec_generate(request.app.routes, request.app.state.config_api_roles_auth, request.app.state)
   return {"status":1,"message":"done"}
   
@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(request:Request):
   obj_body=await func_request_param_read(request,"body",[("mode","str",1,["read","write"],None,None,None),("query","str",1,None,None,None,None)])
   output=await func_postgres_runner(request.app.state.client_postgres_pool,obj_body["mode"],obj_body["query"])
   return {"status":1,"message":output}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(request:Request):
   obj_body=await func_request_param_read(request,"body",[("query","str",1,None,None,None,None)])
   stream=func_postgres_stream(request.app.state.client_postgres_pool,obj_body["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment;filename=file.csv"})

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("mode","str",1,["create","update","delete"],None,None,None),("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      if obj_form["mode"]=="create":
         await func_postgres_create(st.client_postgres_pool,func_postgres_obj_serialize,"now",obj_form["table"],obj_list,1,None)
      elif obj_form["mode"]=="update":
         await func_postgres_update(st.client_postgres_pool,func_postgres_obj_serialize,obj_form["table"],obj_list,1,None)
      elif obj_form["mode"]=="delete":
         await func_postgres_ids_delete(st.client_postgres_pool,obj_form["table"],",".join(str(obj["id"]) for obj in obj_list),None)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/object-create")
async def func_api_admin_object_create(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("mode","str",0,["now","buffer"],"now",None,None),("is_serialize","int",0,[0,1],0,None,None),("queue","str",0,None,None,None,None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_orchestrator_object_create("admin",obj_query,obj_body,request.state.user.get("id"),st.config_table_create_my,st.config_table_create_public,st.config_column_blocked,st.client_postgres_pool,st.func_postgres_obj_serialize,st.config_table,st.func_orchestrator_producer_dispatch,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_allowed,st.func_postgres_create,st.config_postgres_batch_limit)}

@router.put("/admin/object-update")
async def func_api_admin_object_update(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("is_serialize","int",0,[0,1],0,None,None),("otp","int",0,None,None,None,None),("queue","str",0,None,None,None,None)])
   obj_body=await func_request_param_read(request,"body",[])
   return {"status":1,"message":await func_orchestrator_object_update("admin",obj_query,obj_body,request.state.user.get("id"),st.config_column_blocked,st.config_column_single_update,st.client_postgres_pool,st.func_postgres_obj_serialize,st.func_orchestrator_producer_dispatch,st.client_celery_producer,st.client_kafka_producer,st.client_rabbitmq_producer,st.client_redis_producer,st.config_channel_allowed,st.func_postgres_update,st.func_otp_verify,st.config_expiry_sec_otp,st.config_is_otp_users_update_admin,st.config_postgres_batch_limit)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(request:Request):
   st=request.app.state
   obj_query=await func_request_param_read(request,"query",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None),("order","str",0,None,"id desc",None,None),("column","str",0,None,"*",None,None),("creator_key","str",0,None,None,None,None),("action_key","str",0,None,None,None,None)])
   obj_list=await func_postgres_read(st.client_postgres_pool,func_postgres_obj_serialize,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(request:Request):
   st=request.app.state
   obj_body=await func_request_param_read(request,"body",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("ids","str",1,None,None,None,None)])
   output=await func_postgres_ids_delete(st.client_postgres_pool,obj_body["table"],obj_body["ids"],None,config_table_system,config_postgres_ids_delete_limit)
   return {"status":1,"message":output}

@router.post("/admin/redis-import-create")
async def func_api_admin_redis_import_create(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None),("expiry_sec","int",0,None,None,None,None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      key_list=[f"""{obj_form["table"]}_{item["id"]}""" for item in obj_list]
      await func_redis_object_create(st.client_redis,key_list,obj_list,obj_form["expiry_sec"])
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/redis-import-delete")
async def func_api_admin_redis_import_delete(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      key_list=[f"""{obj_form["table"]}_{item["id"]}""" for item in obj_list]
      await func_redis_object_delete(st.client_redis,key_list)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(request:Request):
   st, count = request.app.state, 0
   obj_form=await func_request_param_read(request,"form",[("mode","str",1,["create","delete"],None,None,None),("database","str",1,None,None,None,None),("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None)])
   async for obj_list in func_api_file_to_chunks(obj_form["file"][-1]):
      if obj_form["mode"]=="create":
         await func_mongodb_object_create(st.client_mongodb,obj_form["database"],obj_form["table"],obj_list)
      elif obj_form["mode"]=="delete":
         await func_mongodb_object_delete(st.client_mongodb,obj_form["database"],obj_form["table"],obj_list)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/s3-bucket-ops")
async def func_api_admin_s3_bucket_ops(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mode","str",1,["create","public","empty","delete"],None,None,None),("bucket","str",1,None,None,None,None)])
   st=request.app.state
   if obj_query["mode"]=="create":
      output=await func_s3_bucket_create(st.client_s3,config_s3_region_name,obj_query["bucket"])
   elif obj_query["mode"]=="public":
      output=await func_s3_bucket_public(st.client_s3,obj_query["bucket"])
   elif obj_query["mode"]=="empty":
      output=func_s3_bucket_empty(st.client_s3_resource,obj_query["bucket"])
   elif obj_query["mode"]=="delete":
      output=await func_s3_bucket_delete(st.client_s3,obj_query["bucket"])
   return {"status":1,"message":output}

@router.post("/admin/s3-url-delete")
async def func_api_admin_s3_url_delete(request:Request):
   st=request.app.state
   obj_body=await func_request_param_read(request,"body",[("url","list",1,[],None,None,None)])
   output=func_s3_url_delete(st.client_s3_resource,obj_body["url"])
   return {"status":1,"message":output}
