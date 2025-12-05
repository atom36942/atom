#import
from file.route import *

#api
@router.post("/protected/jira-jql-output-save")
async def function_api_protected_jira_jql_output_save(request:Request):
   param=await function_param_read("body",request,[["type","int",1,None],["jira_base_url",None,1,None],["jira_email",None,1,None],["jira_token",None,1,None],["jql",None,1,None],["column",None,0,None]])
   output_path=f"export_{__import__('time').time():.0f}.csv"
   function_jira_jql_output_export(param["jira_base_url"],param["jira_email"],param["jira_token"],param["jql"],param["column"],None,output_path)
   obj_list=await function_csv_path_to_object_list(output_path)
   obj_list=[item | {"type": param["type"]} for item in obj_list]
   __import__("os").remove(output_path)
   output=await function_postgres_object_create("now",request.app.state.client_postgres_pool,"jira",obj_list)
   return {"status":1,"message":output}