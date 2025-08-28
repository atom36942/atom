#import
from extend import *

#api
@router.get("/my/profile")
async def function_api_my_profile(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   output=await function_read_user_query_count(request.app.state.client_postgres,request.state.user["id"],request.app.state.config_user_count_query)
   asyncio.create_task(function_update_last_active_at(request.app.state.client_postgres,request.state.user["id"]))
   return {"status":1,"message":user|output}

@router.get("/my/api-usage")
async def function_api_my_api_usage(request:Request):
   param=await function_param_read(request,"query",[["days","int",0,7]])
   object_list=await function_log_api_usage(request.app.state.client_postgres,param["days"],request.state.user["id"])
   return {"status":1,"message":object_list}

@router.get("/my/token-refresh")
async def function_api_my_token_refresh(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   token=await function_token_encode(request.app.state.config_key_jwt,request.app.state.config_token_expire_sec,request.app.state.config_token_user_key_list,user)
   return {"status":1,"message":token}

@router.get("/my/account-delete-soft")
async def function_api_my_account_delete_soft(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   if user["api_access"]:return function_return_error("not allowed as you have api_access")
   await function_delete_user_single("soft",request.app.state.client_postgres,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.get("/my/account-delete-hard")
async def function_api_my_account_delete_hard(request:Request):
   user=await function_read_user_single(request.app.state.client_postgres,request.state.user["id"])
   if user["api_access"]:return function_return_error("not allowed as you have api_access")
   await function_delete_user_single("hard",request.app.state.client_postgres,request.state.user["id"])
   return {"status":1,"message":"done"}

@router.post("/my/ids-update")
async def function_api_my_ids_update(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None],["column",None,1,None],["value",None,1,None]])
   if param["table"] in ["users"]:return function_return_error("table not allowed")
   if param["column"] in request.app.state.config_column_update_disabled_list:return function_return_error("column not allowed")
   await function_update_ids(request.app.state.client_postgres,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],request.state.user["id"])
   return {"status":1,"message":"done"}

@router.post("/my/ids-delete")
async def function_api_my_ids_delete(request:Request):
   param=await function_param_read(request,"body",[["table",None,1,None],["ids",None,1,None]])
   if param["table"] in ["users"]:return function_return_error("table not allowed")
   await function_delete_ids(request.app.state.client_postgres,param["table"],param["ids"],request.state.user["id"])
   return {"status":1,"message":"done"}


