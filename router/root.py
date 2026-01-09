#import
from core.route import *

#api
@router.get("/root/postgres-init")
async def func_api_35ccd536b313494d9043ddee84bb7b9e(request:Request):
   output=await func_postgres_init_schema(request.app.state.client_postgres_pool,config_postgres,func_postgres_schema_read,config_postgres_is_extension,0)
   await fund_handler_reset_cache_postgres(request)
   return {"status":1,"message":output}

@router.get("/root/reset-global")
async def func_api_f5c4a2f6e328454e84732f36743916ee(request:Request):
   await fund_handler_reset_cache_postgres(request)
   await fund_handler_reset_cache_users(request)
   if config_is_reset_export_folder:func_folder_reset("export")
   await func_postgres_obj_create(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,"flush")
   return {"status":1,"message":"done"}

@router.get("/root/postgres-clean")
async def func_api_45757110c9f7404cae6629a33cc8b2b1(request:Request):
   output=await func_postgres_clean(request.app.state.client_postgres_pool,config_table)
   return {"status":1,"message":output}

@router.post("/root/postgres-runner")
async def func_api_ccb985fc962349e4a2961d4bb030718c(request:Request):
    obj_body=await func_request_param_read(request,"body",[["mode","str",1,None],["query","str",1,None]])
    output=await func_postgres_runner(request.app.state.client_postgres_pool,obj_body["mode"],obj_body["query"])
    return {"status":1,"message":output}

@router.post("/root/postgres-export")
async def func_api_4eb43535bb05413c967fc18bfe93ac10(request:Request):
   obj_body=await func_request_param_read(request,"body",[["query","str",1,None]])
   stream=func_postgres_stream(request.app.state.client_postgres_pool,obj_body["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment;filename=file.csv"})

@router.post("/root/postgres-import")
async def func_api_5f4c0fdf16244ca084cd6a07687b245f(request:Request):
   obj_form=await func_request_param_read(request,"form",[["mode","str",1,None],["table","str",1,None],["file","file",1,[]]])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   if obj_form["mode"]=="create":output=await func_postgres_obj_create(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,"now",obj_form["table"],obj_list,1,None)
   elif obj_form["mode"]=="update":output=await func_postgres_obj_update(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,obj_form["table"],obj_list,1,None)
   elif obj_form["mode"]=="delete":output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_form["table"],",".join(str(obj["id"]) for obj in obj_list),None)
   return {"status":1,"message":output}

@router.post("/root/redis-import-create")
async def func_api_08d1ca28b2d54be29d9e9064a8a148a4(request:Request):
   obj_form=await func_request_param_read(request,"form",[["table","str",1,None],["file","file",1,[]],["expiry_sec","int",0,None]])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   key_list=[f"{obj_form['table']}_{item['id']}" for item in obj_list]
   output=await func_redis_object_create(request.app.state.client_redis,key_list,obj_list,obj_form["expiry_sec"])
   return {"status":1,"message":output}

@router.post("/root/redis-import-delete")
async def func_api_c3768e7ff7f441d7a5bcccfbc8dfaf15(request:Request):
   obj_form=await func_request_param_read(request,"form",[["file","file",1,[]]])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   output=await func_redis_object_delete(request.app.state.client_redis,obj_list)
   return {"status":1,"message":output}

@router.post("/root/mongodb-import-create")
async def func_api_4519b1151a0e428aa1b781ec61ed8fb0(request:Request):
   obj_form=await func_request_param_read(request,"form",[["database","str",1,None],["table","str",1,None],["file","file",1,[]]])
   obj_list=await func_api_file_to_obj_list(obj_form["file"][-1])
   output=await func_mongodb_object_create(request.app.state.client_mongodb,obj_form["database"],obj_form["table"],obj_list)
   return {"status":1,"message":output}

@router.get("/root/s3-bucket-ops")
async def func_api_ca7ecbd9afdc46e39e4267bd2c33290c(request:Request):
   obj_query=await func_request_param_read(request,"query",[["mode","str",1,None],["bucket","str",1,None]])
   if obj_query["mode"]=="create":output=await func_s3_bucket_create(request.app.state.client_s3,config_s3_region_name,obj_query["bucket"])
   elif obj_query["mode"]=="public":output=await func_s3_bucket_public(request.app.state.client_s3,obj_query["bucket"])
   elif obj_query["mode"]=="empty":output=await func_s3_bucket_empty(request.app.state.client_s3_resource,obj_query["bucket"])
   elif obj_query["mode"]=="delete":output=await func_s3_bucket_delete(request.app.state.client_s3,obj_query["bucket"])
   return {"status":1,"message":output}

@router.post("/root/s3-url-delete")
async def func_api_ece7d0b10f9b4cb29167defe3b471f71(request:Request):
    obj_body=await func_request_param_read(request,"body",[["url","list",1,[]]])
    for item in obj_body["url"]:output=await func_s3_url_delete(request.app.state.client_s3_resource,item)
    return {"status":1,"message":output}
