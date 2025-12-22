#import
from core.route import *

#api
@router.post("/admin/object-create")
async def func_api_6dba580b31ff43e6824ea4292eb9c749(request:Request):
   output=await func_handler_obj_create("admin",request)
   return {"status":1,"message":output}

@router.put("/admin/object-update")
async def func_api_febf6094467b456f8cabfb8191f1000e(request:Request):
   output=await func_handler_obj_update("admin",request)
   return {"status":1,"message":output}

@router.get("/admin/object-read")
async def func_api_bb6506520ad349f688f925055cd8b965(request:Request):
   obj_query=await func_request_param_read(request,"query",[["table","str",1,None]])
   obj_list=await func_postgres_obj_list_read(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,func_creator_data_add,func_action_count_add,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.put("/admin/ids-update")
async def func_api_39188c1de0d44463b2f6024b6415bb1c(request:Request):
   obj_body=await func_request_param_read(request,"body",[["table","str",1,None],["ids","str",1,None],["column","str",1,None],["value","any",1,None]])
   output=await func_postgres_ids_update(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],obj_body["column"],obj_body["value"],None,request.state.user["id"] if request.app.state.cache_postgres_schema.get(obj_body["table"]).get("updated_by_id") else None)
   return {"status":1,"message":output}

@router.post("/admin/ids-delete")
async def func_api_219e40d87ece488fb927dd4ee8f14bb9(request:Request):
   obj_body=await func_request_param_read(request,"body",[["table","str",1,None],["ids","str",1,None]])
   if len(obj_body["ids"].split(","))>config_limit_ids_delete:raise Exception("ids length exceeded")
   output=await func_postgres_ids_delete(request.app.state.client_postgres_pool,obj_body["table"],obj_body["ids"],None)
   return {"status":1,"message":output}
