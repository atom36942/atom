#import
from extend import *

#api
@router.post("/admin/object-create")
async def function_api_admin_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None]])
   obj=await function_param_read(request,"body",[])
   if request.app.state.cache_postgres_schema.get(param["table"]).get("created_by_id"):obj["created_by_id"]=request.state.user["id"]
   if len(obj)<=1:raise Exception("obj issue")
   output=await function_postgres_object_create("now",request.app.state.client_postgres_pool,param["table"],[obj])
   return {"status":1,"message":output}

@router.put("/admin/object-update")
async def function_api_admin_object_update(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["queue",None,0,None]])
   obj=await function_param_read(request,"body",[])
   if "id" not in obj:raise Exception("id missing")
   if len(obj)<=1:raise Exception("obj length issue")
   if request.app.state.cache_postgres_schema.get(param["table"]).get("updated_by_id"):obj["updated_by_id"]=request.state.user["id"]
   if not param["queue"]:output=await function_postgres_object_update(request.app.state.client_postgres_pool,param["table"],[obj])
   elif param["queue"]=="celery":output=await function_celery_producer(request.app.state.client_celery_producer,"function_postgres_object_update",[param["table"],[obj],1])
   elif param["queue"]=="kafka":output=await function_kafka_producer(request.app.state.client_kafka_producer,"channel_1",{"function":"function_postgres_object_update","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="rabbitmq":output=await function_rabbitmq_producer(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_postgres_object_update","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="redis":output=await function_redis_producer(request.app.state.client_redis_producer,"channel_1",{"function":"function_postgres_object_update","table":param["table"],"object_list":[obj],"is_serialize":1})
   return {"status":1,"message":output}

@router.get("/admin/object-read")
async def function_api_admin_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["creator_key","list",0,[]]])
   object_list=await function_postgres_object_read(request.app.state.client_postgres_pool,param)
   if param["creator_key"]:object_list=await function_add_creator_data(request.app.state.client_postgres_pool,object_list,param["creator_key"])
   return {"status":1,"message":object_list}

@router.put("/admin/ids-update")
async def function_api_admin_ids_update(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None],["column",None,1,None],["value",None,1,None]])
   await function_update_ids(request.app.state.client_postgres_pool,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],None)
   return {"status":1,"message":"done"}

@router.post("/admin/ids-delete")
async def function_api_admin_ids_delete(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None]])
   if len(param["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await function_delete_ids(request.app.state.client_postgres_pool,param["table"],param["ids"],None)
   return {"status":1,"message":"done"}





