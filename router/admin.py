#import
from common import *

#api
@router.post("/admin/object-create")
async def func_api_6dba580b31ff43e6824ea4292eb9c749(request:Request):
   return {"status":1,"message":await func_obj_create_logic(request,"admin")}

@router.put("/admin/object-update")
async def func_api_febf6094467b456f8cabfb8191f1000e(request:Request):
   return {"status":1,"message":await func_obj_update_logic(request,"admin")}

@router.get("/admin/object-read")
async def func_api_bb6506520ad349f688f925055cd8b965(request:Request):
   obj_query=await func_request_param_read(request,"query",[("table","str",1,None)])
   obj_list=await func_postgres_obj_read(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,func_creator_data_add,func_action_count_add,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.post("/admin/ids-delete")
async def func_api_219e40d87ece488fb927dd4ee8f14bb9(request:Request):
   obj_body=await func_request_param_read(request,"body",[("table","str",1,None),("ids","str",1,None)])
   if obj_body["table"] in config_table_system_list:raise Exception("table not allowed")
   if len(obj_body["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],None)
   return {"status":1,"message":output}