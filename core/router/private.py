#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#private
@router.post("/private/s3-upload-file")
async def func_api_private_s3_upload_file(request:Request):
   app_state=request.app.state
   of=await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("bucket","str",1,None,None),("file","file",1,[],None)])
   output=await app_state.func_s3_upload_file(client_s3=app_state.client_s3, bucket=of["bucket"], file_list=of["file"], config_s3_limit_kb=app_state.config_s3_limit_kb, config_s3_upload_limit_count=app_state.config_s3_upload_limit_count)
   return {"status":1,"message":output}

@router.post("/private/s3-upload-presigned")
async def func_api_private_s3_upload_presigned(request:Request):
   app_state=request.app.state
   oq=await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("bucket","str",1,None,None),("count","int",0,None,1)])
   output=app_state.func_s3_upload_url_presigned(client_s3=app_state.client_s3, config_s3_region_name=app_state.config_s3_region_name, bucket=oq["bucket"], config_s3_limit_kb=app_state.config_s3_limit_kb, config_s3_presigned_expire_sec=app_state.config_s3_presigned_expire_sec, count=oq["count"], config_s3_upload_limit_count=app_state.config_s3_upload_limit_count)
   return {"status":1,"message":output}
