#import
from extend import *

#api
@router.get("/root/postgres-init")
async def function_api_root_postgres_init(request:Request):
   await function_postgres_schema_init(request.app.state.client_postgres,request.app.state.config_postgres_schema,function_postgres_schema_read)
   return {"status":1,"message":"done"}

@router.delete("/root/postgres-clean")
async def function_api_root_postgres_clean(request:Request):
   await function_postgres_clean(request.app.state.client_postgres,request.app.state.config_postgres_clean)
   return {"status":1,"message":"done"}

@router.post("/root/postgres-export")
async def function_api_root_postgres_export(request:Request):
   param=await function_param_read(request,"body",[["query",None,1,None]])
   stream=function_postgres_query_read_stream(request.app.state.client_postgres_asyncpg_pool,param.get("query"))
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition": "attachment; filename=export_postgres.csv"})

@router.post("/root/postgres-import-create")
async def function_api_root_postgres_import_create(request:Request):
   param=await function_param_read(request,"form",[["table",None,1,None],["file","file",1,[]]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   output=await function_object_create_postgres(request.app.state.client_postgres,param.get("table"),object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@router.post("/root/postgres-import-update")
async def function_api_root_postgres_import_update(request:Request):
   param=await function_param_read(request,"form",[["table",None,1,None],["file","file",1,[]]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   output=await function_object_update_postgres(request.app.state.client_postgres,param.get("table"),object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@router.post("/root/postgres-import-delete")
async def function_api_root_postgres_import_delete(request:Request):
   param=await function_param_read(request,"form",[["table",None,1,None],["file","file",1,[]]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   output=await function_object_delete_postgres(request.app.state.client_postgres,param.get("table"),object_list,1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@router.post("/root/redis-import-create")
async def function_api_root_redis_import_create(request:Request):
   param=await function_param_read(request,"form",[["table",None,1,None],["expiry_sec","int",0,None],["file","file",1,[]]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   key_list=[f"{param.get('table')}_{item['id']}" for item in object_list]
   await function_object_create_redis(request.app.state.client_redis,key_list,object_list,param.get("expiry_sec"))
   return {"status":1,"message":"done"}

@router.post("/root/mongodb-import-create")
async def function_api_root_mongodb_import_create(request:Request):
   param=await function_param_read(request,"form",[["database",None,1,None],["table",None,1,None],["file","file",1,[]]])
   object_list=await function_file_to_object_list(param.get("file")[-1])
   output=await function_object_create_mongodb(request.app.state.client_mongodb,param.get("database"),param.get("table"),object_list)
   return {"status":1,"message":output}




