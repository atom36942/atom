#import
from extend import *

#api
@router.post("/admin/object-create")
async def function_api_admin_object_create(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None],["is_serialize","int",0,0]])
   obj=await function_param_read("body",request,[])
   if request.app.state.cache_postgres_schema.get(param["table"]).get("created_by_id"):obj["created_by_id"]=request.state.user["id"]
   if len(obj)<=1:raise Exception("obj issue")
   if param["is_serialize"]:obj=(await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,[obj]))[0]
   output=await function_postgres_object_create(request.app.state.client_postgres_pool,param["table"],[obj])
   return {"status":1,"message":output}

@router.put("/admin/object-update")
async def function_api_admin_object_update(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None],["is_serialize","int",0,0],["queue",None,0,None]])
   obj=await function_param_read("body",request,[])
   if request.app.state.cache_postgres_schema.get(param["table"]).get("updated_by_id"):obj["updated_by_id"]=request.state.user["id"]
   if "id" not in obj:raise Exception("id missing")
   if len(obj)<=1:raise Exception("obj length issue")
   if param["is_serialize"] or "password" in obj:obj=(await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,[obj]))[0]
   if not param["queue"]:output=await function_postgres_object_update(request.app.state.client_postgres_pool,param["table"],[obj])
   else:
      function_name="function_postgres_object_update"
      param_list=[param["table"],[obj]]
      payload={"function":function_name,"table":param["table"],"obj_list":[obj]}
      if param["queue"]=="celery":output=await function_celery_producer(request.app.state.client_celery_producer,function_name,param_list)
      elif param["queue"]=="kafka":output=await function_kafka_producer(request.app.state.client_kafka_producer,"channel_1",payload)
      elif param["queue"]=="rabbitmq":output=await function_rabbitmq_producer(request.app.state.client_rabbitmq_producer,"channel_1",payload)
      elif param["queue"]=="redis":output=await function_redis_producer(request.app.state.client_redis_producer,"channel_1",payload)
   return {"status":1,"message":output}

@router.get("/admin/object-read")
async def function_api_admin_object_read(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None]])
   obj_list=await function_postgres_object_read(request.app.state.client_postgres_pool,param["table"],param,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,function_add_creator_data)
   return {"status":1,"message":obj_list}

@router.put("/admin/ids-update")
async def function_api_admin_ids_update(request:Request):
   param=await function_param_read("body",request,[["table",None,1,None],["ids",None,1,None],["column",None,1,None],["value",None,1,None]])
   await function_postgres_ids_update(request.app.state.client_postgres_pool,param["table"],param["ids"],param["column"],param["value"],None,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.post("/admin/ids-delete")
async def function_api_admin_ids_delete(request:Request):
   param=await function_param_read("body",request,[["table",None,1,None],["ids",None,1,None]])
   if len(param["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await function_postgres_ids_delete(request.app.state.client_postgres_pool,param["table"],param["ids"],None)
   return {"status":1,"message":"done"}
