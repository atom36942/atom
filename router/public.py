#import
from core.route import *

#api
@router.get("/public/info")
async def func_api_05a7908253e14b7b8e37fc034d5dab95(request:Request):
   output={
   "api_list":[route.path for route in request.app.routes],
   "postgres_schema":request.app.state.cache_postgres_schema,
   "postgres_column_datatype":request.app.state.cache_postgres_column_datatype,
   "request_state_app":{k:type(v).__name__ for k, v in request.app.state._state.items()}
   }
   return {"status":1,"message":output}

@router.get("/public/converter-integer")
async def func_api_8759a1e7a3cd4ed882dded3920fd998a(request:Request):
   obj_query=await func_request_param_read(request,"query",[["mode","str",1,None],["x","str",1,None],["max_length","int",0,None]])
   output=await func_converter_integer(obj_query["mode"],obj_query["x"],obj_query["max_length"])
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def func_api_f48100707a724b979ccc5582a9bd0e28(request:Request):
   output=await func_handler_obj_create("public",request)
   return {"status":1,"message":output}

@router.get("/public/object-read")
async def func_api_88fdc8850b714b9db5fcac36cabf446d(request:Request):
   obj_query=await func_request_param_read(request,"query",[["table","str",1,None]])
   if obj_query["table"] not in config_public_table_read_list:raise Exception("table not allowed")
   obj_list=await func_postgres_obj_list_read(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,func_creator_data_add,func_action_count_add,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.get("/public/otp-verify")
async def func_api_c5119024bc5346d9a8ada54ee6dfdaed(request:Request):
   obj_query=await func_request_param_read(request,"query",[["otp","int",1,None],["email","str",0,None],["mobile","str",0,None]])
   output=await func_otp_verify(request.app.state.client_postgres_pool,obj_query["otp"],obj_query["email"],obj_query["mobile"],config_otp_expire_sec)
   return {"status":1,"message":output}

@router.get("/public/otp-send-email-ses")
async def func_api_244d67aedf2743d0a507560d2f1bae14(request:Request):
   obj_query=await func_request_param_read(request,"query",[["sender","str",1,None],["email","str",1,None]])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=await func_ses_send_email(request.app.state.client_ses,obj_query["sender"],[obj_query["email"]],"your otp code",str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-resend")
async def func_api_ab8787cbe2e84442b805b2d4fc755643(request:Request):
   obj_query=await func_request_param_read(request,"query",[["sender","str",1,None],["email","str",1,None]])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=await func_resend_send_email(config_resend_url,config_resend_key,obj_query["sender"],[obj_query["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-sns")
async def func_api_99803968df144a38b8d5293c8e3fa33e(request:Request):
   obj_query=await func_request_param_read(request,"query",[["mobile","str",1,None]])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=await func_sns_send_mobile_message(request.app.state.client_sns,obj_query["mobile"],str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_8ba3a3e8f4d94450bdcd444bf7336c76(request:Request):
   obj_body=await func_request_param_read(request,"body",[["mobile","str",1,None],["message","str",1,None],["template_id","str",1,None],["entity_id","str",1,None],["sender_id","str",1,None]])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_body["mobile"])
   message=obj_body["message"].format(otp=otp)
   output=await func_sns_send_mobile_message_template(request.app.state.client_sns,obj_body["mobile"],message,obj_body["template_id"],obj_body["entity_id"],obj_body["sender_id"])
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-fast2sms")
async def func_api_42ce5231ca4e40cc9474938029bd40c5(request:Request):
   obj_query=await func_request_param_read(request,"query",[["mobile","str",1,None]])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=await func_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,obj_query["mobile"],otp)
   return {"status":1,"message":output}

@router.post("/public/object-create-gsheet")
async def func_api_ea356533d48f44bb9d7e79479fc43649(request:Request):
   obj_query=await func_request_param_read(request,"query",[["url","str",1,None]])
   obj_body=await func_request_param_read(request,"body",[])
   obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
   output=func_gsheet_object_create(request.app.state.client_gsheet,obj_query["url"],obj_list)
   return {"status":1,"message":output}

@router.get("/public/object-read-gsheet")
async def func_api_1c353211ef09455687a617b909eeaa7f(request:Request):
   obj_query=await func_request_param_read(request,"query",[["url","str",1,None]])
   obj_list=await func_gsheet_object_read(obj_query["url"])
   return {"status":1,"message":obj_list}

@router.post("/public/jira-worklog-export")
async def func_api_4a7af87fdb264c41ac62514a908fd0ef(request:Request):
   obj_body=await func_request_param_read(request,"body",[["jira_base_url","str",1,None],["jira_email","str",1,None],["jira_token","str",1,None],["start_date","str",0,None],["end_date","str",0,None]])
   output_path=func_jira_worklog_export(obj_body["jira_base_url"],obj_body["jira_email"],obj_body["jira_token"],obj_body["start_date"],obj_body["end_date"],None)
   return await func_client_download_file(output_path)



