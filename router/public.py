#import
from extend import *

#api
@router.get("/public/info")
async def function_api_public_info(request:Request):
   output={
   "api_list":[route.path for route in request.app.routes],
   "postgres_schema":request.app.state.cache_postgres_schema
   }
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def function_api_public_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",None,1,None],["is_serialize","int",0,0]])
   obj=await function_param_read(request,"body",[])
   if param["table"] not in request.app.state.config_public_table_create_list:return function_return_error("table not allowed")
   if len(obj)<=1:return function_return_error("obj issue")
   output=await function_object_create_postgres(request.app.state.client_postgres,param["table"],[obj],param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@router.get("/public/otp-verify")
async def function_api_public_otp_verify(request:Request):
   param=await function_param_read(request,"query",[["mode",None,1,None],["data",None,1,None],["otp","int",1,None]])
   await function_otp_verify(param["mode"],param["data"],param["otp"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@router.get("/public/otp-send-mobile-sns")
async def function_api_public_otp_send_mobile_sns(request:Request):
   param=await function_param_read(request,"query",[["mobile",None,1,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   await function_send_mobile_message_sns(request.app.state.client_sns,param["mobile"],str(otp))
   return {"status":1,"message":"done"}

@router.get("/public/otp-send-mobile-fast2sms")
async def function_api_public_otp_send_mobile_fast2sms(request:Request):
   param=await function_param_read(request,"query",[["mobile",None,1,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   output=await function_send_mobile_otp_fast2sms(request.app.state.config_fast2sms_url,request.app.state.config_fast2sms_key,param["mobile"],otp)
   return {"status":1,"message":output}

@router.get("/public/otp-send-email-ses")
async def function_api_public_otp_send_email_ses(request:Request):
   param=await function_param_read(request,"query",[["email",None,1,None],["sender_email",None,1,None]])
   otp=await function_otp_generate("email",param["email"],request.app.state.client_postgres)
   await function_send_email_ses(request.app.state.client_ses,param["sender_email"],[param["email"]],"your otp code",str(otp))
   return {"status":1,"message":"done"}

@router.post("/public/otp-send-email-resend")
async def function_api_public_otp_send_email_resend(request:Request):
   param=await function_param_read(request,"query",[["email",None,1,None],["sender_email",None,1,None]])
   otp=await function_otp_generate("email",param["email"],request.app.state.client_postgres)
   await function_send_email_resend(request.app.state.config_resend_url,request.app.state.config_resend_key,param["sender_email"],[param["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":"done"}

@router.post("/public/otp-send-mobile-sns-template")
async def function_api_public_otp_send_mobile_sns_template(request:Request):
   param=await function_param_read(request,"body",[["mobile",None,1,None],["message",None,1,None],["template_id",None,1,None],["entity_id",None,1,None],["sender_id",None,1,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   message=param["message"].format(otp=otp)
   await function_send_mobile_message_sns_template(request.app.state.client_sns,param["mobile"],message,param["template_id"],param["entity_id"],param["sender_id"])
   return {"status":1,"message":"done"}

@router.post("/public/jira-worklog-export")
async def function_api_public_jira_worklog_export(request:Request):
   param=await function_param_read(request,"body",[["jira_base_url",None,1,None],["jira_email",None,1,None],["jira_token",None,1,None],["start_date",None,0,None],["end_date",None,0,None]])
   output_path=f"export_jira_worklog_{__import__('time').time():.0f}.csv"
   function_export_jira_worklog(param["jira_base_url"],param["jira_email"],param["jira_token"],param["start_date"],param["end_date"],output_path)
   stream=function_stream_file(output_path)
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment; filename=export_jira_worklog.csv"},background=BackgroundTask(lambda: os.remove(output_path)))













