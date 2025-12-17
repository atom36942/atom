#import
from core.route import *

#api
@router.post("/admin/object-create")
async def function_api_admin_object_create(request:Request):
   param=await function_request_param_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0]])
   obj=await function_request_param_read(request,"body",[])
   obj_list=obj["object_list"] if "object_list" in obj else [obj]
   for i,x in enumerate(obj_list):
      if request.app.state.cache_postgres_schema.get(param["table"]).get("created_by_id"):x["created_by_id"]=request.state.user["id"]
      if len(x)<=1:raise Exception("obj key length issue")
   output=await function_postgres_object_create(request.app.state.client_postgres_pool,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,"now",param["table"],obj_list,param["is_serialize"])
   return {"status":1,"message":output}

@router.put("/admin/object-update")
async def function_api_admin_object_update(request:Request):
   param=await function_request_param_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0],["queue","str",0,None]])
   obj=await function_request_param_read(request,"body",[])
   obj_list=obj["object_list"] if "object_list" in obj else [obj]
   for i,x in enumerate(obj_list):
      if request.app.state.cache_postgres_schema.get(param["table"]).get("updated_by_id"):x["updated_by_id"]=request.state.user["id"]
      if "id" not in x:raise Exception("id missing")
   if not param["queue"]:output=await function_postgres_object_update(request.app.state.client_postgres_pool,param["table"],obj_list)
   else:
      function_name="function_postgres_object_update"
      param_list=[param["table"],obj_list]
      payload={"function":function_name,"table":param["table"],"obj_list":obj_list}
      if param["queue"]=="celery":output=await function_celery_producer(request.app.state.client_celery_producer,function_name,param_list)
      elif param["queue"]=="kafka":output=await function_kafka_producer(request.app.state.client_kafka_producer,config_channel_name,payload)
      elif param["queue"]=="rabbitmq":output=await function_rabbitmq_producer(request.app.state.client_rabbitmq_producer,config_channel_name,payload)
      elif param["queue"]=="redis":output=await function_redis_producer(request.app.state.client_redis_producer,config_channel_name,payload)
   return {"status":1,"message":output}

@router.get("/admin/object-read")
async def function_api_admin_object_read(request:Request):
   param=await function_request_param_read(request,"query",[["table","str",1,None]])
   obj_list=await function_postgres_object_read(request.app.state.client_postgres_pool,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,function_add_creator_data,function_add_action_count,param["table"],param)
   return {"status":1,"message":obj_list}

@router.put("/admin/ids-update")
async def function_api_admin_ids_update(request:Request):
   param=await function_request_param_read(request,"body",[["table","str",1,None],["ids","str",1,None],["column","str",1,None],["value","any",1,None]])
   await function_postgres_ids_update(request.app.state.client_postgres_pool,param["table"],param["ids"],param["column"],param["value"],None,request.state.user["id"] if request.app.state.cache_postgres_schema.get(param["table"]).get("updated_by_id") else None)
   return {"status":1,"message":"done"}

@router.post("/admin/ids-delete")
async def function_api_admin_ids_delete(request:Request):
   param=await function_request_param_read(request,"body",[["table","str",1,None],["ids","str",1,None]])
   if len(param["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await function_postgres_ids_delete(request.app.state.client_postgres_pool,param["table"],param["ids"],None)
   return {"status":1,"message":"done"}

@router.post("/admin/jira-jql-output-save")
async def function_api_admin_jira_jql_output_save(request:Request):
   param=await function_request_param_read(request,"body",[["type","int",1,None],["jira_base_url","str",1,None],["jira_email","str",1,None],["jira_token","str",1,None],["jql","str",1,None],["column","str",0,None]])
   __import__("os").makedirs("export", exist_ok=True)
   output_path = f"export/jira_jql_{__import__('time').time():.0f}.csv"
   function_jira_jql_output_export(param["jira_base_url"],param["jira_email"],param["jira_token"],param["jql"],param["column"],"str",output_path)
   obj_list=await function_csv_path_to_object_list(output_path)
   obj_list=[item | {"type": param["type"]} for item in obj_list]
   __import__("os").remove(output_path)
   output=await function_postgres_object_create(request.app.state.client_postgres_pool,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,"now","jira",obj_list,0)
   return {"status":1,"message":output}