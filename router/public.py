#import
from file.route import *

#api
@router.get("/public/info")
async def function_api_public_info(request:Request):
   output={
   "api_list":[route.path for route in request.app.routes],
   "postgres_schema":request.app.state.cache_postgres_schema,
   "postgres_column_datatype":request.app.state.cache_postgres_column_datatype
   }
   return {"status":1,"message":output}

@router.get("/public/otp-verify")
async def function_api_public_otp_verify(request:Request):
   param=await function_param_read("query",request,[["otp","int",1,None],["email",None,0,None],["mobile",None,0,None]])
   await function_otp_verify(request.app.state.client_postgres_pool,param["otp"],param["email"],param["mobile"],config_otp_expire_sec)
   return {"status":1,"message":"done"}

@router.get("/public/otp-send-email-ses")
async def function_api_public_otp_send_email_ses(request:Request):
   param=await function_param_read("query",request,[["sender",None,1,None],["email",None,1,None]])
   otp=await function_otp_generate(request.app.state.client_postgres_pool,param["email"],None)
   await function_ses_send_email(request.app.state.client_ses,param["sender"],[param["email"]],"your otp code",str(otp))
   return {"status":1,"message":"done"}

@router.post("/public/otp-send-email-resend")
async def function_api_public_otp_send_email_resend(request:Request):
   param=await function_param_read("query",request,[["sender",None,1,None],["email",None,1,None]])
   otp=await function_otp_generate(request.app.state.client_postgres_pool,param["email"],None)
   await function_resend_send_email(config_resend_url,config_resend_key,param["sender"],[param["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":"done"}

@router.get("/public/otp-send-mobile-sns")
async def function_api_public_otp_send_mobile_sns(request:Request):
   param=await function_param_read("query",request,[["mobile",None,1,None]])
   otp=await function_otp_generate(request.app.state.client_postgres_pool,None,param["mobile"])
   await function_sns_send_mobile_message(request.app.state.client_sns,param["mobile"],str(otp))
   return {"status":1,"message":"done"}

@router.post("/public/otp-send-mobile-sns-template")
async def function_api_public_otp_send_mobile_sns_template(request:Request):
   param=await function_param_read("body",request,[["mobile",None,1,None],["message",None,1,None],["template_id",None,1,None],["entity_id",None,1,None],["sender_id",None,1,None]])
   otp=await function_otp_generate(request.app.state.client_postgres_pool,None,param["mobile"])
   message=param["message"].format(otp=otp)
   await function_sns_send_mobile_message_template(request.app.state.client_sns,param["mobile"],message,param["template_id"],param["entity_id"],param["sender_id"])
   return {"status":1,"message":"done"}

@router.get("/public/otp-send-mobile-fast2sms")
async def function_api_public_otp_send_mobile_fast2sms(request:Request):
   param=await function_param_read("query",request,[["mobile",None,1,None]])
   otp=await function_otp_generate(request.app.state.client_postgres_pool,None,param["mobile"])
   output=await function_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,param["mobile"],otp)
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def function_api_public_object_create(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None],["is_serialize","int",0,0]])
   obj=await function_param_read("body",request,[])
   obj_list=obj["object_list"] if "object_list" in obj else [obj]
   for i,x in enumerate(obj_list):
      if len(x)<=1:raise Exception("obj key length issue")
      if any(key in config_column_disabled_list for key in x):raise Exception("obj key not allowed")
      if param["is_serialize"]==1 or "password" in x:obj_list[i]=(await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,[x]))[0]
   if param["table"] not in config_public_table_create_list:raise Exception("table not allowed")
   output=await function_postgres_object_create("now",request.app.state.client_postgres_pool,param["table"],obj_list)
   return {"status":1,"message":output}

@router.get("/public/object-read")
async def function_api_public_object_read(request:Request):
   param=await function_param_read("query",request,[["table",None,1,None]])
   if param["table"] not in config_public_table_read_list:raise Exception("table not allowed")
   obj_list=await function_postgres_object_read(request.app.state.client_postgres_pool,param["table"],param,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,function_add_creator_data,function_add_action_count)
   return {"status":1,"message":obj_list}

@router.get("/public/object-read-gsheet")
async def function_api_public_object_read_gsheet(request:Request):
   param=await function_param_read("query",request,[["url",None,1,None]])
   obj_list=await function_gsheet_object_read(param["url"])
   return {"status":1,"message":obj_list}

@router.post("/public/object-create-gsheet")
async def function_api_public_object_create_gsheet(request:Request):
   param=await function_param_read("query",request,[["url",None,1,None]])
   obj=await function_param_read("body",request,[])
   obj_list=obj["object_list"] if "object_list" in obj else [obj]
   output=function_gsheet_object_create(request.app.state.client_gsheet,param["url"],obj_list)
   return {"status":1,"message":output}

@router.post("/public/jira-worklog-export")
async def function_api_public_jira_worklog_export(request:Request):
   param=await function_param_read("body",request,[["jira_base_url",None,1,None],["jira_email",None,1,None],["jira_token",None,1,None],["start_date",None,0,None],["end_date",None,0,None]])
   output_path=f"export_{__import__('time').time():.0f}.csv"
   function_jira_worklog_export(param["jira_base_url"],param["jira_email"],param["jira_token"],param["start_date"],param["end_date"],output_path)
   stream=function_stream_file(output_path)
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment; name=export_jira_worklog.csv"},background=BackgroundTask(lambda: os.remove(output_path)))

@router.get("/public/converter-integer")
async def function_api_public_converter_integer(request:Request):
   param=await function_param_read("query",request,[["mode",None,1,None],["x",None,1,None],["max_length","int",0,None]])
   output=await function_converter_integer(param["mode"],param["x"],param["max_length"])
   return {"status":1,"message":output}
