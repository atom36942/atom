#import
from extend import *

#api
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



