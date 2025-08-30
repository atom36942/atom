#import
from function import *
from config import *

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import traceback
@asynccontextmanager
async def lifespan(app:FastAPI):
   try:
      #client init
      client_postgres=await function_client_read_postgres(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
      client_postgres_asyncpg=await function_client_read_postgres_asyncpg(config_postgres_url) if config_postgres_url else None
      client_postgres_asyncpg_pool=await function_client_read_postgres_asyncpg_pool(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
      client_postgres_read=await function_client_read_postgres(config_postgres_url_read,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url_read else None
      client_redis=await function_client_read_redis(config_redis_url) if config_redis_url else None
      client_redis_ratelimiter=await function_client_read_redis(config_redis_url_ratelimiter) if config_redis_url_ratelimiter else None
      client_mongodb=await function_client_read_mongodb(config_mongodb_url) if config_mongodb_url else None
      client_s3,client_s3_resource=(await function_client_read_s3(config_aws_access_key_id,config_aws_secret_access_key,config_s3_region_name)) if config_s3_region_name else (None, None)
      client_sns=await function_client_read_sns(config_aws_access_key_id,config_aws_secret_access_key,config_sns_region_name) if config_sns_region_name else None
      client_ses=await function_client_read_ses(config_aws_access_key_id,config_aws_secret_access_key,config_ses_region_name) if config_ses_region_name else None
      client_openai=function_client_read_openai(config_openai_key) if config_openai_key else None
      client_posthog=await function_client_read_posthog(config_posthog_project_host,config_posthog_project_key)
      client_celery_producer=await function_client_read_celery_producer(config_celery_broker_url,config_celery_backend_url) if config_celery_broker_url else None
      client_kafka_producer=await function_client_read_kafka_producer(config_kafka_url,config_kafka_username,config_kafka_password) if config_kafka_url else None
      client_rabbitmq,client_rabbitmq_producer=await function_client_read_rabbitmq_producer(config_rabbitmq_url) if config_rabbitmq_url else (None, None)
      client_redis_producer=await function_client_read_redis(config_redis_pubsub_url) if config_redis_pubsub_url else None
      #cache init
      cache_postgres_schema,cache_postgres_column_datatype=await function_postgres_schema_read(client_postgres) if client_postgres else (None, None)
      cache_users_api_access=await function_column_mapping_read(client_postgres_asyncpg,"users","id","api_access",config_limit_cache_users_api_access,0,"split_int") if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("api_access") else {}
      cache_users_is_active=await function_column_mapping_read(client_postgres_asyncpg,"users","id","is_active",config_limit_cache_users_api_access,1,None) if client_postgres_asyncpg and cache_postgres_schema.get("users",{}).get("is_active") else {}
      #app state set
      function_add_app_state({**globals(),**locals()},app,("config_","client_","cache_"))
      #app shutdown
      yield
      await function_log_create_postgres("flush",function_object_create_postgres,client_postgres,None,None)
      await function_object_create_postgres_batch("flush",function_object_create_postgres,client_postgres,None,None,None,1,function_object_serialize,cache_postgres_column_datatype)
      if client_postgres:await client_postgres.disconnect()
      if client_postgres_asyncpg:await client_postgres_asyncpg.close()
      if client_postgres_asyncpg_pool:await client_postgres_asyncpg_pool.close()
      if client_postgres_read:await client_postgres_read.close()
      if client_redis:await client_redis.aclose()
      if client_redis_ratelimiter:await client_redis_ratelimiter.aclose()
      if client_redis_producer:await client_redis_producer.aclose()
      if client_mongodb:client_mongodb.close()
      if client_kafka_producer:await client_kafka_producer.stop()
      if client_rabbitmq_producer and not client_rabbitmq_producer.is_closed:await client_rabbitmq_producer.close()
      if client_rabbitmq and not client_rabbitmq.is_closed:await client_rabbitmq.close()
      if client_posthog:client_posthog.flush()
      if client_posthog:client_posthog.shutdown()
      function_delete_files(".",[".csv"],["export_"])
   except Exception as e:
      print(str(e))
      print(traceback.format_exc())

#app
app=function_fastapi_app_read(True,lifespan)
function_add_cors(app,config_cors_origin_list,config_cors_method_list,config_cors_headers_list,config_cors_allow_credentials)
function_add_router(app,"router")
if config_sentry_dsn:function_add_sentry(config_sentry_dsn)
if config_is_prometheus:function_add_prometheus(app)

#middleware
from fastapi import Request,responses
from starlette.background import BackgroundTask
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
   try:
      #start
      start=time.time()
      response_type=None
      response=None
      error=None
      api=request.url.path
      request.state.user={}
      #auth check
      request.state.user=await function_token_check(request,request.app.state.config_key_root,request.app.state.config_key_jwt,request.app.state.config_api,function_token_decode)
      #admin check
      if "admin/" in api:await function_check_api_access(request.app.state.config_mode_check_api_access,request,request.app.state.cache_users_api_access,request.app.state.client_postgres,request.app.state.config_api)
      #active check
      if request.app.state.config_api.get(api,{}).get("is_active_check")==1 and request.state.user:await function_check_is_active(request.app.state.config_mode_check_is_active,request,request.app.state.cache_users_is_active,request.app.state.client_postgres)
      #ratelimiter check
      if request.app.state.config_api.get(api,{}).get("ratelimiter_times_sec"):await function_check_ratelimiter(request,request.app.state.client_redis_ratelimiter,request.app.state.config_api)
      #background response
      if request.query_params.get("is_background")=="1":
         response=await function_api_response_background(request,api_function)
         response_type=1
      #cache response
      elif request.app.state.config_api.get(api,{}).get("cache_sec"):
         response=await function_cache_api_response("get",request,None,request.app.state.client_redis,request.app.state.config_api)
         response_type=2
      #default response
      if not response:
         response=await api_function(request)
         response_type=3
         if request.app.state.config_api.get(api,{}).get("cache_sec"):
            response=await function_cache_api_response("set",request,response,request.app.state.client_redis,request.app.state.config_api)
            response_type=4
   #error
   except Exception as e:
      error=str(e)
      if config_is_traceback:print(traceback.format_exc())
      response=function_return_error(error)
      if request.app.state.config_sentry_dsn:sentry_sdk.capture_exception(e)
      response_type=5
      print(error)
   #log api
   if request.app.state.config_is_log_api and getattr(request.app.state, "cache_postgres_schema", None) and request.app.state.cache_postgres_schema.get("log_api"):
      obj_log={"response_type":response_type,"ip_address":request.client.host,"created_by_id":request.state.user.get("id"),"api":api,"api_id":request.app.state.config_api.get(api,{}).get("id"),"method":request.method,"query_param":json.dumps(dict(request.query_params)),"status_code":response.status_code,"response_time_ms":(time.time()-start)*1000,"description":error}
      asyncio.create_task(function_log_create_postgres("append",function_object_create_postgres,request.app.state.client_postgres,request.app.state.config_batch_log_api,obj_log))
   #final
   return response

#root
@app.get("/")
async def function_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"}

#api













@app.get("/my/object-read")
async def function_api_my_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   object_list=await function_object_read_postgres(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":object_list}

@app.delete("/my/object-delete-any")
async def function_api_my_object_delete_any(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None]])
   param["created_by_id"]=f"=,{request.state.user['id']}"
   if param["table"] in ["users"]:return function_return_error("table not allowed")
   await function_object_delete_postgres_any(request.app.state.client_postgres,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":"done"}











@app.post("/public/otp-send-mobile-sns")
async def function_api_public_otp_send_mobile_sns(request:Request):
   param=await function_param_read(request,"body",[["mobile",1,None,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   await function_send_mobile_message_sns(request.app.state.client_sns,param["mobile"],str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-sns-template")
async def function_api_public_otp_send_mobile_sns_template(request:Request):
   param=await function_param_read(request,"body",[["mobile",1,None,None],["message",1,None,None],["template_id",1,None,None],["entity_id",1,None,None],["sender_id",1,None,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   message=param["message"].format(otp=otp)
   await function_send_mobile_message_sns_template(request.app.state.client_sns,param["mobile"],message,param["template_id"],param["entity_id"],param["sender_id"])
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-mobile-fast2sms")
async def function_api_public_otp_send_mobile_fast2sms(request:Request):
   param=await function_param_read(request,"body",[["mobile",1,None,None]])
   otp=await function_otp_generate("mobile",param["mobile"],request.app.state.client_postgres)
   output=await function_send_mobile_otp_fast2sms(request.app.state.config_fast2sms_url,request.app.state.config_fast2sms_key,param["mobile"],otp)
   return {"status":1,"message":output}

@app.post("/public/otp-send-email-ses")
async def function_api_public_otp_send_email_ses(request:Request):
   param=await function_param_read(request,"body",[["email",1,None,None],["sender_email",1,None,None]])
   otp=await function_otp_generate("email",param["email"],request.app.state.client_postgres)
   await function_send_email_ses(request.app.state.client_ses,param["sender_email"],[param["email"]],"your otp code",str(otp))
   return {"status":1,"message":"done"}

@app.post("/public/otp-send-email-resend")
async def function_api_public_otp_send_email_resend(request:Request):
   param=await function_param_read(request,"body",[["email",1,None,None],["sender_email",1,None,None]])
   otp=await function_otp_generate("email",param["email"],request.app.state.client_postgres)
   await function_send_email_resend(request.app.state.config_resend_url,request.app.state.config_resend_key,param["sender_email"],[param["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-email")
async def function_api_public_otp_verify_email(request:Request):
   param=await function_param_read(request,"body",[["otp",1,"int",None],["email",1,None,None]])
   await function_otp_verify("email",param["otp"],param["email"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/otp-verify-mobile")
async def function_api_public_otp_verify_mobile(request:Request):
   param=await function_param_read(request,"body",[["otp",1,"int",None],["mobile",1,None,None]])
   await function_otp_verify("mobile",param["otp"],param["mobile"],request.app.state.client_postgres)
   return {"status":1,"message":"done"}

@app.post("/public/object-create")
async def function_api_public_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["is_serialize",0,"int",0]])
   obj=await function_param_read(request,"body",[])
   if param["table"] not in request.app.state.config_public_table_create_list:return function_return_error("table not allowed")
   output=await function_object_create_postgres(request.app.state.client_postgres,param["table"],[obj],param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.get("/public/object-read")
async def function_api_public_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["creator_key",0,None,None]])
   if param["table"] not in request.app.state.config_public_table_read_list:return function_return_error("table not allowed")
   object_list=await function_object_read_postgres(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,param["table"],param,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   if object_list and param["creator_key"]:object_list=await function_add_creator_data(request.app.state.client_postgres_read if request.app.state.client_postgres_read else request.app.state.client_postgres,param["creator_key"],object_list)
   return {"status":1,"message":object_list}

@app.get("/public/info")
async def function_api_public_info(request:Request):
   output={
   "api_list":[route.path for route in request.app.routes],
   "postgres_schema":request.app.state.cache_postgres_schema
   }
   return {"status":1,"message":output}

@app.get("/public/page/{filename}")
async def function_api_public_page(filename:str):
   file_path=os.path.join(".",f"{filename}.html")
   if ".." in filename or "/" in filename:return function_return_error("invalid filename")
   if not os.path.isfile(file_path):return function_return_error("file not found")
   with open(file_path,"r",encoding="utf-8") as file:html_content=file.read()
   return responses.HTMLResponse(content=html_content)

@app.post("/public/jira-worklog-export")
async def function_api_public_jira_worklog_export(request:Request):
   param=await function_param_read(request,"body",[["jira_base_url",1,None,None],["jira_email",1,None,None],["jira_token",1,None,None],["start_date",0,None,None],["end_date",0,None,None]])
   output_path=f"export_jira_worklog_{__import__('time').time():.0f}.csv"
   function_export_jira_worklog(param["jira_base_url"],param["jira_email"],param["jira_token"],param["start_date"],param["end_date"],output_path)
   stream=function_stream_file(output_path)
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment; filename=export_jira_worklog.csv"},background=BackgroundTask(lambda: os.remove(output_path)))

@app.post("/private/file-upload-s3-direct")
async def function_api_private_file_upload_s3_direct(request:Request):
   param=await function_param_read(request,"form",[["bucket",1,None,None],["file_list",1,None,None],["key",0,None,None]])
   key_list=param["key"].split("---") if param["key"] else None
   output=await function_s3_file_upload_direct(request.app.state.config_s3_region_name,request.app.state.client_s3,param["bucket"],key_list,param["file_list"])
   return {"status":1,"message":output}

@app.post("/private/file-upload-s3-presigned")
async def function_api_private_file_upload_s3_presigned(request:Request):
   param=await function_param_read(request,"body",[["bucket",1,None,None],["key",1,None,None]])
   output=await function_s3_file_upload_presigned(request.app.state.config_s3_region_name,request.app.state.client_s3,param["bucket"],param["key"],1000,100)
   return {"status":1,"message":output}

@app.post("/admin/object-create")
async def function_api_admin_object_create(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["is_serialize",0,"int",1]])
   obj=await function_param_read(request,"body",[])
   if request.app.state.cache_postgres_schema.get(param["table"]).get("created_by_id"):obj["created_by_id"]=request.state.user["id"]
   output=await function_object_create_postgres(request.app.state.client_postgres,param["table"],[obj],param["is_serialize"],function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":output}

@app.put("/admin/object-update")
async def function_api_admin_object_update(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None],["queue",0,"str",None]])
   obj=await function_param_read(request,"body",[])
   if "id" not in obj:return function_return_error("id missing")
   if len(obj)<=1:return function_return_error("obj length issue")
   if request.app.state.cache_postgres_schema.get(param["table"]).get("updated_by_id"):obj["updated_by_id"]=request.state.user["id"]
   if not param["queue"]:output=await function_object_update_postgres(request.app.state.client_postgres,param["table"],[obj],1,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   elif param["queue"]=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_object_update_postgres",[param["table"],[obj],1])
   elif param["queue"]=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   elif param["queue"]=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_object_update_postgres","table":param["table"],"object_list":[obj],"is_serialize":1})
   return {"status":1,"message":output}

@app.put("/admin/ids-update")
async def function_api_admin_ids_update(request:Request):
   param=await function_param_read(request,"body",[["table",1,None,None],["ids",1,None,None],["column",1,None,None],["value",1,None,None]])
   await function_update_ids(request.app.state.client_postgres,param["table"],param["ids"],param["column"],param["value"],request.state.user["id"],None)
   return {"status":1,"message":"done"}

@app.delete("/admin/ids-delete")
async def function_api_admin_ids_delete(request:Request):
   param=await function_param_read(request,"body",[["table",1,None,None],["ids",1,None,None]])
   await function_delete_ids(request.app.state.client_postgres,param["table"],param["ids"],None)
   return {"status":1,"message":"done"}

@app.get("/admin/object-read")
async def function_api_admin_object_read(request:Request):
   param=await function_param_read(request,"query",[["table",1,None,None]])
   obj=await function_param_read(request,"query",[])
   object_list=await function_object_read_postgres(request.app.state.client_postgres,param["table"],obj,function_create_where_string,function_object_serialize,request.app.state.cache_postgres_column_datatype)
   return {"status":1,"message":object_list}

@app.post("/admin/postgres-query-runner")
async def function_api_admin_postgres_query_runner(request:Request):
   param=await function_param_read(request,"body",[["query",1,None,None],["queue",0,"str",None]])
   if not param["queue"]:output=await function_postgres_query_runner(request.app.state.client_postgres,param["query"],request.state.user["id"])
   elif param["queue"]=="celery":output=await function_producer_celery(request.app.state.client_celery_producer,"function_postgres_query_runner",[param["query"],request.state.user["id"]])
   elif param["queue"]=="kafka":output=await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   elif param["queue"]=="rabbitmq":output=await function_producer_rabbitmq(request.app.state.client_rabbitmq_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   elif param["queue"]=="redis":output=await function_producer_redis(request.app.state.client_redis_producer,"channel_1",{"function":"function_postgres_query_runner","query":param["query"],"user_id":request.state.user["id"]})
   if False:request.app.state.client_posthog.capture(distinct_id=request.state.user["id"],event="postgres_query_runner",properties={"query":param["query"]})
   return {"status":1,"message":output}

@app.post("/admin/postgres-export")
async def function_api_root_postgres_export(request:Request):
   param=await function_param_read(request,"body",[["query",1,None,None]])
   stream=function_postgres_query_read_stream(request.app.state.client_postgres_asyncpg_pool,param["query"])
   return responses.StreamingResponse(stream,media_type="text/csv",headers={"Content-Disposition":"attachment; filename=export_postgres.csv"})

#server start
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_server_start(app))
   except KeyboardInterrupt:print("exit")