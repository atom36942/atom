#import
from extend import *

#api
@router.get("/admin/object-read")
async def function_api_admin_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["creator_key","list",0,[]]])
   client_postgres=request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres
   object_list=await function_object_read_postgres(client_postgres,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if param["creator_key"]:object_list=await function_add_creator_data(object_list,param["creator_key"],client_postgres)
   return {"status":1,"message":object_list}

@router.put("/admin/ids-update")
async def function_api_admin_ids_update(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None],["column",None,1,None],["value",None,1,None]])
   await function_update_ids(request.app.state.client_postgres,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],None)
   return {"status":1,"message":"done"}

@router.post("/admin/ids-delete")
async def function_api_admin_ids_delete(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None]])
   await function_delete_ids(request.app.state.client_postgres,param["table"],param["ids"],None)
   return {"status":1,"message":"done"}

@router.post("/admin/postgres-export")
async def function_api_root_postgres_export(request:Request):
   param=await function_param_read(request,"body",[["query",None,1,None]])
   stream=function_postgres_query_read_stream(request.app.state.client_postgres_asyncpg_pool,param["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition": "attachment; filename=export_postgres.csv"})

@router.post("/admin/postgres-query-runner")
async def function_api_admin_postgres_query_runner(request:Request):
   param=await function_param_read(request,"body",[["query",None,1,None]])
   obj=await function_param_read(request,"query",[["queue",None,0,None]])
   if not obj["queue"]:output=await function_postgres_query_runner(request.app.state.client_postgres,param["query"],request.state.user["id"])
   elif obj["queue"]=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_postgres_query_runner",[param["query"],request.state.user["id"]])
   elif obj["queue"]=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   elif obj["queue"]=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   elif obj["queue"]=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   if False:request.app.state.client_posthog.capture(distinct_id=request.state.user["id"],event="postgres_query_runner",properties={"query":param["query"]})
   return {"status":1,"message":output}

@router.post("/admin/object-create")
async def function_api_admin_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["is_serialize","int",0,0]])
   obj=await function_param_read(request,"body",[])
   if request.app.state.cache_postgres_schema.get(param["table"]).get("created_by_id"):obj["created_by_id"]=request.state.user["id"]
   if len(obj)<=1:return function_return_error("obj issue")
   output=await function_object_create_postgres(request.app.state.client_postgres,param["table"],[obj],param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@router.put("/admin/object-update")
async def function_api_admin_object_update(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["queue",None,0,None]])
   obj=await function_param_read(request,"body",[])
   if "id" not in obj:return function_return_error("id missing")
   if len(obj)<=1:return function_return_error("obj length issue")
   if request.app.state.cache_postgres_schema.get(param["table"]).get("updated_by_id"):obj["updated_by_id"]=request.state.user["id"]
   if not param["queue"]:output=await function_object_update_postgres(request.app.state.client_postgres,param["table"],[obj],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   elif param["queue"]=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_object_update_postgres",[param["table"],[obj],1])
   elif param["queue"]=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   return {"status":1,"message":output}

