#import
from extend import *

#api
@router.post("/private/s3-upload-file")
async def function_api_private_s3_upload_file(request:Request):
   param=await function_param_read(request,"form",[["bucket",None,1,None],["key_list","list",0,[]],["file","file",1,[]]])
   output={}
   for index,f in enumerate(param["file"]):
      key=param["key_list"][index] if index<len(param["key_list"]) else None
      output[f.filename]=await function_s3_upload_file(param["bucket"],key,f,request.app.state.client_s3,request.app.state.config_s3_region_name,request.app.state.config_limit_s3_kb)
   return {"status":1,"message":output}

@router.get("/private/s3-upload-presigned")
async def function_api_private_s3_upload_presigned(request:Request):
   param=await function_param_read(request,"query",[["bucket",None,1,None],["key",None,0,None]])
   output=function_s3_upload_presigned(param["bucket"],param["key"],request.app.state.client_s3,request.app.state.config_s3_region_name,request.app.state.config_limit_s3_kb,request.app.state.config_s3_presigned_expire_sec)
   return {"status":1,"message":output}


