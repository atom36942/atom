#import
from core.route import *

#api
@router.post("/private/s3-upload-file")
async def func_api_private_s3_upload_file(request:Request):
   param=await func_request_param_read(request,"form",[["bucket","str",1,None],["file","file",1,[]],["key","list",0,[]]])
   output={}
   for index,file_api in enumerate(param["file"]):
      key_single=param["key"][index] if index<len(param["key"]) else None
      output[file_api.filename]=await func_s3_upload(request.app.state.client_s3,config_s3_region_name,param["bucket"],file_api,key_single,config_limit_s3_kb)
   return {"status":1,"message":output}

@router.get("/private/s3-upload-presigned")
async def func_api_private_s3_upload_presigned(request:Request):
   param=await func_request_param_read(request,"query",[["bucket","str",1,None],["key","str",0,None]])
   output=func_s3_upload_presigned(request.app.state.client_s3,config_s3_region_name,param["bucket"],param["key"],config_limit_s3_kb,config_s3_presigned_expire_sec)
   return {"status":1,"message":output}


