#router
from fastapi import APIRouter
router=APIRouter()

#import
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#admin
@router.get("/admin/sync")
async def func_api_admin_sync(*, request:Request):
   st = request.app.state
   await st.func_postgres_init(client_postgres_pool=st.client_postgres_pool, config_postgres=st.config_postgres)
   await st.func_postgres_create(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, mode="flush", table="", obj_list=[], is_serialize=0, buffer_limit=0, cache_postgres_buffer=st.cache_postgres_buffer)
   st.cache_postgres_schema = await st.func_postgres_schema_read(client_postgres_pool=st.client_postgres_pool) if st.client_postgres_pool else {}
   st.cache_postgres_schema_tables = list(st.cache_postgres_schema.keys())
   st.cache_postgres_schema_columns = sorted(list(set(col for table in st.cache_postgres_schema.values() for col in table.keys())))
   st.cache_users_role = await st.func_postgres_map_column(client_postgres_pool=st.client_postgres_pool, config_sql=st.config_sql.get("cache_users_role")) if st.client_postgres_pool else {}
   st.cache_users_is_active = await st.func_postgres_map_column(client_postgres_pool=st.client_postgres_pool, config_sql=st.config_sql.get("cache_users_is_active")) if st.client_postgres_pool else {}
   await st.func_postgres_clean(client_postgres_pool=st.client_postgres_pool, config_table=st.config_table)
   st.cache_openapi = st.func_openapi_spec_generate(app_routes=request.app.routes, config_api_roles_auth=st.config_api_roles_auth, app_state=st)
   return {"status":1,"message":"done"}
   
@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("mode","str",1,["read","write"],None,None,None,None),("query","str",1,None,None,None,None,None)], strict=0)
   output=await st.func_postgres_runner(client_postgres_pool=st.client_postgres_pool, mode=obj_body["mode"], query=obj_body["query"])
   return {"status":1,"message":output}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("query","str",1,None,None,None,None,None)], strict=0)
   stream=st.func_postgres_stream(client_postgres_pool=st.client_postgres_pool, query=obj_body["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment;filename=file.csv"})

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request:Request):
   st, count = request.app.state, 0
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("mode","str",1,["create","update","delete"],None,None,None,None),("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("file","file",1,[],None,None,None,None)], strict=0)
   async for obj_list in st.func_api_file_to_chunks(upload_file=obj_form["file"][-1], chunk_size=st.config_limit_obj_list):
      if obj_form["mode"]=="create":
         await st.func_postgres_create(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, mode="now", table=obj_form["table"], obj_list=obj_list, is_serialize=1, buffer_limit=0, cache_postgres_buffer=st.cache_postgres_buffer)
      elif obj_form["mode"]=="update":
         await st.func_postgres_update(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, table=obj_form["table"], obj_list=obj_list, is_serialize=1, created_by_id=None, is_return_ids=0)
      elif obj_form["mode"]=="delete":
         await st.func_postgres_delete(client_postgres_pool=st.client_postgres_pool, table=obj_form["table"], ids=",".join(str(obj["id"]) for obj in obj_list), created_by_id=None, config_postgres_ids_delete_limit=st.config_postgres_ids_delete_limit)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("mode","str",0,["now","buffer"],"now",None,None,None),("is_serialize","int",0,[0,1],0,None,None,None),("queue","str",0,None,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   return {"status":1,"message":await st.func_orchestrator_obj_create(api_role="admin", obj_query=obj_query, obj_body=obj_body, user_id=request.state.user.get("id"), config_table_create_my=st.config_table_create_my, config_table_create_public=st.config_table_create_public, config_column_blocked=st.config_column_blocked, client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, config_table=st.config_table, func_orchestrator_producer=st.func_orchestrator_producer, producer_obj={"config_channel_allowed":st.config_channel_allowed, "client_celery_producer":st.client_celery_producer, "client_kafka_producer":st.client_kafka_producer, "client_rabbitmq_producer":st.client_rabbitmq_producer, "client_redis_producer":st.client_redis_producer}, func_postgres_create=st.func_postgres_create, config_limit_obj_list=st.config_limit_obj_list, cache_postgres_buffer=st.cache_postgres_buffer)}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("is_serialize","int",0,[0,1],0,None,None,None),("otp","int",0,None,None,None,None,None),("queue","str",0,None,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   return {"status":1,"message":await st.func_orchestrator_obj_update(api_role="admin", obj_query=obj_query, obj_body=obj_body, user_id=request.state.user.get("id"), config_column_blocked=st.config_column_blocked, config_column_single_update=st.config_column_single_update, client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, func_orchestrator_producer=st.func_orchestrator_producer, producer_obj={"config_channel_allowed":st.config_channel_allowed, "client_celery_producer":st.client_celery_producer, "client_kafka_producer":st.client_kafka_producer, "client_rabbitmq_producer":st.client_rabbitmq_producer, "client_redis_producer":st.client_redis_producer}, func_postgres_update=st.func_postgres_update, func_otp_verify=st.func_otp_verify, config_expiry_sec_otp=st.config_expiry_sec_otp, config_is_otp_users_update_admin=st.config_is_otp_users_update_admin, config_limit_obj_list=st.config_limit_obj_list)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("limit","int",0,None,100,None,None,None),("page","int",0,None,1,None,None,None),("order","str",0,None,"id desc",None,None,None),("column","str",0,None,"*",None,None,None),("creator_key","str",0,None,None,None,None,None),("action_key","str",0,None,None,None,None,None)], strict=0)
   obj_list=await st.func_postgres_read(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, table=obj_query["table"], filter_obj=obj_query, limit=obj_query["limit"], page=obj_query["page"], order=obj_query["order"], column=obj_query["column"], creator_key=obj_query["creator_key"], action_key=obj_query["action_key"])
   return {"status":1,"message":obj_list}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("ids","str",1,None,None,None,None,None)], strict=0)
   output=await st.func_postgres_delete(client_postgres_pool=st.client_postgres_pool, table=obj_body["table"], ids=obj_body["ids"], created_by_id=None, config_postgres_ids_delete_limit=st.config_postgres_ids_delete_limit)
   return {"status":1,"message":output}

@router.post("/admin/redis-import-create")
async def func_api_admin_redis_import_create(*, request:Request):
   st, count = request.app.state, 0
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("file","file",1,[],None,None,None,None),("expiry_sec","int",0,None,None,None,None,None)], strict=0)
   async for obj_list in st.func_api_file_to_chunks(upload_file=obj_form["file"][-1], chunk_size=st.config_limit_obj_list):
      key_list=[f"""{obj_form["table"]}_{item["id"]}""" for item in obj_list]
      await st.func_redis_object_create(client_redis=st.client_redis, keys=key_list, objects=obj_list, config_redis_cache_ttl_sec=obj_form["expiry_sec"])
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/redis-import-delete")
async def func_api_admin_redis_import_delete(*, request:Request):
   st, count = request.app.state, 0
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("file","file",1,[],None,None,None,None)], strict=0)
   async for obj_list in st.func_api_file_to_chunks(upload_file=obj_form["file"][-1], chunk_size=st.config_limit_obj_list):
      key_list=[f"""{obj_form["table"]}_{item["id"]}""" for item in obj_list]
      await st.func_redis_object_delete(client_redis=st.client_redis, keys=key_list)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request:Request):
   st, count = request.app.state, 0
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("mode","str",1,["create","delete"],None,None,None,None),("database","str",1,None,None,None,None,None),("table","str",1,st.cache_postgres_schema_tables,None,None,None,None),("file","file",1,[],None,None,None,None)], strict=0)
   async for obj_list in st.func_api_file_to_chunks(upload_file=obj_form["file"][-1], chunk_size=st.config_limit_obj_list):
      if obj_form["mode"]=="create":
         await st.func_mongodb_object_create(client_mongodb=st.client_mongodb, database=obj_form["database"], table=obj_form["table"], obj_list=obj_list)
      elif obj_form["mode"]=="delete":
         await st.func_mongodb_object_delete(client_mongodb=st.client_mongodb, database=obj_form["database"], table=obj_form["table"], obj_list=obj_list)
      count += len(obj_list)
   return {"status":1,"message":f"{count} rows processed"}

@router.post("/admin/s3-bucket-ops")
async def func_api_admin_s3_bucket_ops(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("mode","str",1,["create","public","empty","delete"],None,None,None,None),("bucket","str",1,None,None,None,None,None)], strict=0)
   if obj_query["mode"]=="create":
      output=await st.func_s3_bucket_create(client_s3=st.client_s3, config_s3_region_name=st.config_s3_region_name, bucket=obj_query["bucket"])
   elif obj_query["mode"]=="public":
      output=await st.func_s3_bucket_public(client_s3=st.client_s3, bucket=obj_query["bucket"])
   elif obj_query["mode"]=="empty":
      output=st.func_s3_bucket_empty(client_s3_resource=st.client_s3_resource, bucket=obj_query["bucket"])
   elif obj_query["mode"]=="delete":
      output=await st.func_s3_bucket_delete(client_s3=st.client_s3, bucket=obj_query["bucket"])
   return {"status":1,"message":output}

@router.post("/admin/s3-url-delete")
async def func_api_admin_s3_url_delete(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("url","list",1,[],None,None,None,None)], strict=0)
   output=st.func_s3_url_delete(client_s3_resource=st.client_s3_resource, url=obj_body["url"])
   return {"status":1,"message":output}
