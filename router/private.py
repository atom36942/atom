#import
from core.route import *

#api
@router.post("/private/s3-upload-file")
async def func_api_cf28dc32bf3c4adab8b6192cebec5e39(request:Request):
   obj_form=await func_request_param_read(request,"form",[("bucket","str",1,None),("file","file",1,[]),("key","list",0,[])])
   output={}
   for index,item in enumerate(obj_form["file"]):
      k=obj_form["key"][index] if index<len(obj_form["key"]) else None
      output[item.filename]=await func_s3_upload(request.app.state.client_s3,config_s3_region_name,obj_form["bucket"],item,k,config_limit_s3_kb)
   return {"status":1,"message":output}

@router.get("/private/s3-upload-presigned")
async def func_api_7031e803bbc544958a91c92a89187338(request:Request):
   obj_query=await func_request_param_read(request,"query",[("bucket","str",1,None),("key","str",0,None)])
   output=func_s3_upload_presigned(request.app.state.client_s3,config_s3_region_name,obj_query["bucket"],obj_query["key"],config_limit_s3_kb,config_s3_presigned_expire_sec)
   return {"status":1,"message":output}