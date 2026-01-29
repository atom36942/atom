#import
from core.route import *

#api
@router.get("/public/info")
async def func_api_05a7908253e14b7b8e37fc034d5dab95(request:Request):
   obj_query=await func_request_param_read(request,"query",[("key","str",0,None)])
   output={
   "request_state_app":{k:type(v).__name__ for k, v in request.app.state._state.items()},
   "api_list":[route.path for route in request.app.routes],
   "cache_postgres_schema":request.app.state.cache_postgres_schema,
   "cache_postgres_column_datatype":request.app.state.cache_postgres_column_datatype,
   "postgres_datatype_used_app":set(sorted({k["datatype"] for cols in config_postgres["table"].values() for k in cols})),
   "postgres_datatype_used_db":set(request.app.state.cache_postgres_column_datatype.values()),
   "config_postgres_column_setting":set([k for cols in config_postgres["table"].values() for col in cols for k in col]),
   }
   return {"status":1,"message":output if not obj_query["key"] else output[obj_query["key"]]}

@router.get("/public/converter-number")
async def func_api_8759a1e7a3cd4ed882dded3920fd998a(request:Request):
   obj_query=await func_request_param_read(request,"query",[("datatype","str",1,None),("mode","str",1,None),("x","str",1,None)])
   output=await func_converter_number(obj_query["datatype"],obj_query["mode"],obj_query["x"])
   return {"status":1,"message":output}

@router.post("/public/object-create")
async def func_api_f48100707a724b979ccc5582a9bd0e28(request:Request):
   output=await func_handler_obj_create("public",request)
   return {"status":1,"message":output}

@router.get("/public/object-read")
async def func_api_88fdc8850b714b9db5fcac36cabf446d(request:Request):
   obj_query=await func_request_param_read(request,"query",[("table","str",1,None)])
   if obj_query["table"] not in config_public_table_read_list:raise Exception("table not allowed")
   obj_list=await func_postgres_obj_read(request.app.state.client_postgres_pool,func_postgres_obj_serialize,request.app.state.cache_postgres_column_datatype,func_creator_data_add,func_action_count_add,obj_query["table"],obj_query)
   return {"status":1,"message":obj_list}

@router.get("/public/otp-verify")
async def func_api_c5119024bc5346d9a8ada54ee6dfdaed(request:Request):
   obj_query=await func_request_param_read(request,"query",[("otp","int",1,None),("email","str",0,None),("mobile","str",0,None)])
   output=await func_otp_verify(request.app.state.client_postgres_pool,obj_query["otp"],obj_query["email"],obj_query["mobile"],config_otp_expire_sec)
   return {"status":1,"message":output}

@router.get("/public/otp-send-email-ses")
async def func_api_244d67aedf2743d0a507560d2f1bae14(request:Request):
   obj_query=await func_request_param_read(request,"query",[("sender","str",1,None),("email","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=await func_ses_send_email(request.app.state.client_ses,obj_query["sender"],[obj_query["email"]],"your otp code",str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-email-resend")
async def func_api_ab8787cbe2e84442b805b2d4fc755643(request:Request):
   obj_query=await func_request_param_read(request,"query",[("sender","str",1,None),("email","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,obj_query["email"],None)
   output=await func_resend_send_email(config_resend_url,config_resend_key,obj_query["sender"],[obj_query["email"]],"your otp code",f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>")
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-sns")
async def func_api_99803968df144a38b8d5293c8e3fa33e(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mobile","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=await func_sns_send_mobile_message(request.app.state.client_sns,obj_query["mobile"],str(otp))
   return {"status":1,"message":output}

@router.post("/public/otp-send-mobile-sns-template")
async def func_api_8ba3a3e8f4d94450bdcd444bf7336c76(request:Request):
   obj_body=await func_request_param_read(request,"body",[("mobile","str",1,None),("message","str",1,None),("template_id","str",1,None),("entity_id","str",1,None),("sender_id","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_body["mobile"])
   message=obj_body["message"].format(otp=otp)
   output=await func_sns_send_mobile_message_template(request.app.state.client_sns,obj_body["mobile"],message,obj_body["template_id"],obj_body["entity_id"],obj_body["sender_id"])
   return {"status":1,"message":output}

@router.get("/public/otp-send-mobile-fast2sms")
async def func_api_42ce5231ca4e40cc9474938029bd40c5(request:Request):
   obj_query=await func_request_param_read(request,"query",[("mobile","str",1,None)])
   otp=await func_otp_generate(request.app.state.client_postgres_pool,"str",obj_query["mobile"])
   output=await func_fast2sms_send_otp_mobile(config_fast2sms_url,config_fast2sms_key,obj_query["mobile"],otp)
   return {"status":1,"message":output}

@router.post("/public/object-create-gsheet")
async def func_api_ea356533d48f44bb9d7e79479fc43649(request:Request):
   obj_query=await func_request_param_read(request,"query",[("url","str",1,None)])
   obj_body=await func_request_param_read(request,"body",[])
   obj_list=obj_body["obj_list"] if "obj_list" in obj_body else [obj_body]
   output=func_gsheet_object_create(request.app.state.client_gsheet,obj_query["url"],obj_list)
   return {"status":1,"message":output}

@router.get("/public/object-read-gsheet")
async def func_api_1c353211ef09455687a617b909eeaa7f(request:Request):
   obj_query=await func_request_param_read(request,"query",[("url","str",1,None)])
   obj_list=await func_gsheet_object_read(obj_query["url"])
   return {"status":1,"message":obj_list}

@router.post("/public/jira-worklog-export")
async def func_api_4a7af87fdb264c41ac62514a908fd0ef(request:Request):
   obj_body=await func_request_param_read(request,"body",[("jira_base_url","str",1,None),("jira_email","str",1,None),("jira_token","str",1,None),("start_date","str",0,None),("end_date","str",0,None)])
   output_path=func_jira_worklog_export(obj_body["jira_base_url"],obj_body["jira_email"],obj_body["jira_token"],obj_body["start_date"],obj_body["end_date"],None)
   return await func_client_download_file(output_path)

@router.get("/public/person-intel")
async def func_api_5aa65182abea4af6bd266efc05ac611f(request:Request,q:str):
    CONFIG_SEARCH_URL="https://www.searchapi.io/api/v1/search";CONFIG_SEARCH_ENGINE="google";CONFIG_MAX_URLS=5;CONFIG_LLM_MODEL="gemini-2.0-flash";CONFIG_HTML_LIMIT=6000;CONFIG_PROMPT_SIGNAL="""From the text below, extract up to 10 distinct factual statements about:\n"{query}"\n\nRules:\n- Each fact must be a separate bullet starting with "-"\n- Do NOT merge facts into one sentence\n- Do NOT repeat the same fact twice\n- Copy only what is explicitly stated\n\nText:\n{html}""";CONFIG_PROMPT_SUMMARY="""You are given factual bullet points from multiple sources about:\n"{query}"\n\nGroup them into 5-10 short paragraphs.\nUse only the facts. No inference, no filler.\nDont start with here is the summary type of text.\n\nFacts:\n{merged}"""
    async with aiohttp.ClientSession() as s:
        async with s.get(CONFIG_SEARCH_URL,params={"engine":CONFIG_SEARCH_ENGINE,"q":q,"api_key":config_searchapi_key}) as r:j=await r.json();urls=[x["link"] for x in j.get("organic_results",[])[:CONFIG_MAX_URLS]]
    fragments=[];used=[]
    for u in urls:
        async with aiohttp.ClientSession() as s:
            async with s.get(u,headers={"User-Agent":"Mozilla/5.0"}) as r:raw=await r.read();html=raw.decode("utf-8","ignore") if True else raw.decode("latin1","ignore")
        soup=BeautifulSoup(html,"html.parser")
        for t in soup(["script","style","noscript"]):t.decompose()
        clean=" ".join(soup.stripped_strings);client=genai.Client(api_key=config_gemini_key);prompt=CONFIG_PROMPT_SIGNAL.format(query=q,html=clean[:CONFIG_HTML_LIMIT]);r=client.models.generate_content(model=CONFIG_LLM_MODEL,contents=prompt);frag=r.text.strip()
        if frag:fragments.append(frag);used.append(u)
    client=genai.Client(api_key=config_gemini_key);merged="\n".join([f for f in fragments if f]);prompt=CONFIG_PROMPT_SUMMARY.format(query=q,merged=merged);r=client.models.generate_content(model=CONFIG_LLM_MODEL,contents=prompt);output={"summary":r.text.strip(),"sources":len(fragments),"urls":used}
    return {"status":1,"message":output}
