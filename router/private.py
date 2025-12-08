#import
from file.route import *

#api
@router.post("/private/s3-upload-file")
async def function_api_private_s3_upload_file(request:Request):
   param=await function_request_param_read(request,"form",[["bucket",None,1,None],["file","file",1,[]],["key","list",0,[]]])
   output={}
   for index,f in enumerate(param["file"]):
      k=param["key"][index] if index<len(param["key"]) else None
      output[f.filename]=await function_s3_upload_file(param["bucket"],f,request.app.state.client_s3,config_s3_region_name,k,config_limit_s3_kb)
   return {"status":1,"message":output}

@router.get("/private/s3-upload-presigned")
async def function_api_private_s3_upload_presigned(request:Request):
   param=await function_request_param_read(request,"query",[["bucket",None,1,None],["key",None,0,None]])
   output=function_s3_upload_presigned(param["bucket"],request.app.state.client_s3,config_s3_region_name,param["key"],config_limit_s3_kb,config_s3_presigned_expire_sec)
   return {"status":1,"message":output}


