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
   await request.app.state.func_orchestrator_admin_sync(request=request)
   return {"status":1,"message":"done"}

@router.post("/admin/postgres-runner")
async def func_api_admin_postgres_runner(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("mode","str",1,["read","write"],None,None,None),("query","str",1,None,None,None,None)], strict=0)
   output=await st.func_postgres_runner(client_postgres_pool=st.client_postgres_pool, mode=obj_body["mode"], query=obj_body["query"])
   return {"status":1,"message":output}

@router.post("/admin/postgres-export")
async def func_api_admin_postgres_export(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("query","str",1,None,None,None,None)], strict=0)
   stream=st.func_postgres_export(client_postgres_pool=st.client_postgres_pool, query=obj_body["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment;filename=file.csv"})

@router.post("/admin/postgres-import")
async def func_api_admin_postgres_import(*, request:Request):
   st=request.app.state
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("mode","str",1,["create","update","delete"],None,None,None),("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None),("is_serialize","int",0,[0,1],1,None,None)], strict=0)
   return {"status":1,"message":await st.func_orchestrator_postgres_import(request=request, obj_form=obj_form)}

@router.post("/admin/object-create")
async def func_api_admin_object_create(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("mode","str",0,["now","buffer"],"now",None,None),("is_serialize","int",0,[0,1],0,None,None),("queue","str",0,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   return {"status":1,"message":await st.func_orchestrator_obj_create(request=request, api_role="admin", obj_query=obj_query, obj_body=obj_body)}

@router.put("/admin/object-update")
async def func_api_admin_object_update(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("is_serialize","int",0,[0,1],0,None,None),("otp","int",0,None,None,None,None),("queue","str",0,None,None,None,None)], strict=0)
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[], strict=0)
   return {"status":1,"message":await st.func_orchestrator_obj_update(request=request, api_role="admin", obj_query=obj_query, obj_body=obj_body)}

@router.get("/admin/object-read")
async def func_api_admin_object_read(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("limit","int",0,None,100,None,None),("page","int",0,None,1,None,None),("order","str",0,None,"id desc",None,None),("column","str",0,None,"*",None,None),("creator_key","str",0,None,None,None,None),("action_key","str",0,None,None,None,None)], strict=0)
   obj_list=await st.func_postgres_read(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, table=obj_query["table"], filter_obj=obj_query, limit=obj_query["limit"], page=obj_query["page"], order=obj_query["order"], column=obj_query["column"], creator_key=obj_query["creator_key"], action_key=obj_query["action_key"])
   return {"status":1,"message":obj_list}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(*, request:Request):
   st=request.app.state
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("ids","str",1,None,None,None,None)], strict=0)
   output=await st.func_postgres_delete(client_postgres_pool=st.client_postgres_pool, table=obj_body["table"], ids=obj_body["ids"], created_by_id=None, config_postgres_ids_delete_limit=st.config_postgres_ids_delete_limit)
   return {"status":1,"message":output}

@router.post("/admin/redis-import-create")
async def func_api_admin_redis_import_create(*, request:Request):
   st=request.app.state
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None),("expiry_sec","int",0,None,None,None,None)], strict=0)
   return {"status":1,"message":await st.func_orchestrator_redis_import(request=request, mode="create", obj_form=obj_form)}

@router.post("/admin/redis-import-delete")
async def func_api_admin_redis_import_delete(*, request:Request):
   st=request.app.state
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None)], strict=0)
   return {"status":1,"message":await st.func_orchestrator_redis_import(request=request, mode="delete", obj_form=obj_form)}

@router.post("/admin/mongodb-import")
async def func_api_admin_mongodb_import(*, request:Request):
   st=request.app.state
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("mode","str",1,["create","delete"],None,None,None),("database","str",1,None,None,None,None),("table","str",1,st.cache_postgres_schema_tables,None,None,None),("file","file",1,[],None,None,None)], strict=0)
   return {"status":1,"message":await st.func_orchestrator_mongodb_import(request=request, obj_form=obj_form)}

@router.post("/admin/s3-bucket-ops")
async def func_api_admin_s3_bucket_ops(*, request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("mode","str",1,["create","public","empty","delete"],None,None,None),("bucket","str",1,None,None,None,None)], strict=0)
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
   obj_body=await st.func_request_param_read(request=request, mode="body", config=[("url","list",1,[],None,None,None)], strict=0)
   output=st.func_s3_url_delete(client_s3_resource=st.client_s3_resource, url=obj_body["url"])
   return {"status":1,"message":output}
