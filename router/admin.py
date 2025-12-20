#import
from core.route import *

#api
@router.post("/admin/object-create")
async def func_api_6dba580b31ff43e6824ea4292eb9c749(request:Request):
   obj_query=await func_request_obj_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0]])
   obj_body=await func_request_obj_read(request,"body",[])
   obj_list=await func_convert_obj_body_to_obj_list(obj_body)
   obj_list=await func_set_obj_list_column(request,obj_query["table"],obj_list,"created_by_id")
   output=await func_postgres_obj_list_create(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,"now",obj_query["table"],obj_list,obj_query["is_serialize"])
   return {"status":1,"message":output}

@router.put("/admin/object-update")
async def func_api_febf6094467b456f8cabfb8191f1000e(request:Request):
   obj_query=await func_request_obj_read(request,"query",[["table","str",1,None],["is_serialize","int",0,0],["queue","str",0,None]])
   obj_body=await func_request_obj_read(request,"body",[])
   obj_list=await func_convert_obj_body_to_obj_list(obj_body)
   obj_list=await func_set_obj_list_column(request,obj_query["table"],obj_list,"updated_by_id")
   if not obj_query["queue"]:output=await func_postgres_obj_list_update(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,obj_query["table"],obj_list,obj_query["is_serialize"],None)
   elif obj_query["queue"]=="celery":output=await func_celery_producer(request.app.state.client_celery_producer,"func_postgres_obj_list_update",[obj_query["table"],obj_list,obj_query["is_serialize"],None])
   elif obj_query["queue"]=="kafka":output=await func_kafka_producer(request.app.state.client_kafka_producer,config_channel_name,{"function":"func_postgres_obj_list_update","table":obj_query["table"],"obj_list":obj_list,"is_serialize":obj_query["is_serialize"],"created_by_id":None})
   elif obj_query["queue"]=="rabbitmq":output=await func_rabbitmq_producer(request.app.state.client_rabbitmq_producer,config_channel_name,{"function":"func_postgres_obj_list_update","table":obj_query["table"],"obj_list":obj_list,"is_serialize":obj_query["is_serialize"],"created_by_id":None})
   elif obj_query["queue"]=="redis":output=await func_redis_producer(request.app.state.client_redis_producer,config_channel_name,{"function":"func_postgres_obj_list_update","table":obj_query["table"],"obj_list":obj_list,"is_serialize":obj_query["is_serialize"],"created_by_id":None})
   return {"status":1,"message":output}

@router.get("/admin/object-read")
async def func_api_admin_object_read(request:Request):
   obj_query=await func_request_obj_read(request,"query",[["table","str",1,None]])
   obj_list=await func_postgres_object_read(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,func_add_creator_data,func_add_action_count,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.put("/admin/ids-update")
async def func_api_admin_ids_update(request:Request):
   obj_query=await func_request_obj_read(request,"body",[["table","str",1,None],["ids","str",1,None],["column","str",1,None],["value","any",1,None]])
   await func_postgres_ids_update(request.app.state.client_postgres_pool,obj_query["table"],obj_query["ids"],obj_query["column"],obj_query["value"],None,request.state.user["id"] if request.app.state.cache_postgres_schema.get(obj_query["table"]).get("updated_by_id") else None)
   return {"status":1,"message":"done"}

@router.post("/admin/ids-delete")
async def func_api_admin_ids_delete(request:Request):
   obj_query=await func_request_obj_read(request,"body",[["table","str",1,None],["ids","str",1,None]])
   if len(obj_query["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_query["table"],obj_query["ids"],None)
   return {"status":1,"message":"done"}

@router.post("/admin/jira-jql-output-save")
async def func_api_admin_jira_jql_output_save(request:Request):
   obj_query=await func_request_obj_read(request,"body",[["type","int",1,None],["jira_base_url","str",1,None],["jira_email","str",1,None],["jira_token","str",1,None],["jql","str",1,None],["column","str",0,None]])
   output_path=func_jira_jql_output_export(func_outpath_path_create,obj_query["jira_base_url"],obj_query["jira_email"],obj_query["jira_token"],obj_query["jql"],obj_query["column"],"str",output_path)
   obj_list=await func_csv_path_to_obj_list(output_path)
   obj_list=[item | {"type": obj_query["type"]} for item in obj_list]
   __import__("os").remove(output_path)
   output=await func_postgres_obj_list_create(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,"now","jira",obj_list,0)
   return {"status":1,"message":output}