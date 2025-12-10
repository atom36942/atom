#import
from file.route import *

#api
@router.get("/root/postgres-init")
async def function_api_root_postgres_init(request:Request):
   await function_postgres_schema_init(request.app.state.client_postgres_pool,config_postgres_schema,function_postgres_schema_read)
   return {"status":1,"message":"done"}

@router.get("/root/postgres-clean")
async def function_api_root_postgres_clean(request:Request):
   await function_postgres_clean(request.app.state.client_postgres_pool,config_table)
   return {"status":1,"message":"done"}

@router.post("/root/postgres-runner")
async def function_api_root_postgres_runner(request:Request):
    param=await function_request_param_read(request,"body",[["mode","str",1,None],["query","str",1,None]])
    output=await function_postgres_runner(request.app.state.client_postgres_pool,param["mode"],param["query"])
    return {"status":1,"message":output}

@router.post("/root/postgres-export")
async def function_api_root_postgres_export(request:Request):
   param=await function_request_param_read(request,"body",[["query","str",1,None]])
   stream=function_postgres_stream(request.app.state.client_postgres_pool,param["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition": "attachment; filename=export_postgres.csv"})

@router.post("/root/postgres-import")
async def function_api_root_postgres_import(request:Request):
   param=await function_request_param_read(request,"form",[["mode","str",1,None],["table","str",1,None],["file","file",1,[]]])
   obj_list=await function_csv_api_to_object_list(param["file"][-1])
   obj_list=await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,obj_list)
   if param["mode"]=="create":output=await function_postgres_object_create("now",request.app.state.client_postgres_pool,param["table"],obj_list)
   elif param["mode"]=="update":output=await function_postgres_object_update(request.app.state.client_postgres_pool,param["table"],obj_list)
   elif param["mode"]=="delete":output=await function_postgres_ids_delete(request.app.state.client_postgres_pool,param["table"],",".join(str(obj["id"]) for obj in obj_list))
   return {"status":1,"message":output}

@router.post("/root/redis-import-create")
async def function_api_root_redis_import_create(request:Request):
   param=await function_request_param_read(request,"form",[["table","str",1,None],["expiry_sec","int",0,None],["file","file",1,[]]])
   obj_list=await function_csv_api_to_object_list(param["file"][-1])
   key_list=[f"{param['table']}_{item['id']}" for item in obj_list]
   await function_redis_object_create(request.app.state.client_redis,key_list,obj_list,param["expiry_sec"])
   return {"status":1,"message":"done"}

@router.post("/root/redis-import-delete")
async def function_api_root_redis_import_delete(request:Request):
   param=await function_request_param_read(request,"form",[["file","file",1,[]]])
   obj_list=await function_csv_api_to_object_list(param["file"][-1])
   await function_redis_object_delete(request.app.state.client_redis,obj_list)
   return {"status":1,"message":"done"}

@router.post("/root/mongodb-import-create")
async def function_api_root_mongodb_import_create(request:Request):
   param=await function_request_param_read(request,"form",[["database","str",1,None],["table","str",1,None],["file","file",1,[]]])
   obj_list=await function_csv_api_to_object_list(param["file"][-1])
   output=await function_mongodb_object_create(request.app.state.client_mongodb,param["database"],param["table"],obj_list)
   return {"status":1,"message":output}

@router.post("/root/s3-url-delete")
async def function_api_root_s3_url_delete(request:Request):
    param=await function_request_param_read(request,"body",[["url","list",1,[]]])
    for url in param["url"]:output=await function_s3_url_delete(request.app.state.client_s3_resource,url)
    return {"status":1,"message":output}
 
@router.get("/root/s3-bucket-ops")
async def function_api_root_s3_bucket_ops(request:Request):
   param=await function_request_param_read(request,"query",[["mode","str",1,None],["bucket","str",1,None]])
   if param["mode"]=="create":output=await function_s3_bucket_create(request.app.state.client_s3,config_s3_region_name,param["bucket"])
   elif param["mode"]=="public":output=await function_s3_bucket_public(request.app.state.client_s3,param["bucket"])
   elif param["mode"]=="empty":output=await function_s3_bucket_empty(request.app.state.client_s3_resource,param["bucket"])
   elif param["mode"]=="delete":output=await function_s3_bucket_delete(request.app.state.client_s3,param["bucket"])
   return {"status":1,"message":output}

@router.get("/root/reset-global")
async def function_api_root_reset_global(request:Request):
   request.app.state.cache_postgres_schema,request.app.state.cache_postgres_column_datatype=await function_postgres_schema_read(request.app.state.client_postgres_pool)
   request.app.state.cache_users_api_access=await function_postgres_map_query(request.app.state.client_postgres_pool,config_query.get("cache_users_api_access")) if request.app.state.client_postgres_pool and request.app.state.cache_postgres_schema.get("users",{}).get("api_access") else {}
   request.app.state.cache_users_is_active=await function_postgres_map_query(request.app.state.client_postgres_pool,config_query.get("cache_users_is_active")) if request.app.state.client_postgres_pool and request.app.state.cache_postgres_schema.get("users",{}).get("is_active") else {}
   request.app.state.cache_config=await function_postgres_map_query(request.app.state.client_postgres_pool,config_query.get("cache_config")) if request.app.state.client_postgres_pool and request.app.state.cache_postgres_schema.get("config",{}) else {}
   await function_postgres_object_create("flush",request.app.state.client_postgres_pool)
   return {"status":1,"message":"done"}

