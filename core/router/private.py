#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#private
@router.post("/private/blob-upload-file")
async def func_api_private_blob_upload_file(request:Request):
   app_state=request.app.state
   of=await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("service","str",1,["s3","azure"],None),("file","file",1,[],None),("container","str",0,None,None)])
   if of["service"] == "s3":
      output=await app_state.func_s3_upload_file(client_s3=app_state.client_s3, bucket=of.get("container") or app_state.config_s3_bucket_name_default, file_list=of["file"], config_blob_limit_kb=app_state.config_blob_limit_kb, config_blob_upload_limit_count=app_state.config_blob_upload_limit_count)
   elif of["service"] == "azure":
      output=await app_state.func_azure_blob_upload_file(client_azure_blob=app_state.client_azure_blob, container=of.get("container") or app_state.config_azure_container_name_default, file_list=of["file"], config_blob_limit_kb=app_state.config_blob_limit_kb, config_blob_upload_limit_count=app_state.config_blob_upload_limit_count)
   return {"status":1,"message":output}

@router.post("/private/blob-upload-url")
async def func_api_private_blob_upload_url(request:Request):
   app_state=request.app.state
   oq=await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service","str",1,["s3","azure"],None),("container","str",0,None,None),("count","int",0,None,1)])
   if oq["service"] == "s3":
      output=app_state.func_s3_upload_url_presigned(client_s3=app_state.client_s3, config_s3_region_name=app_state.config_s3_region_name, bucket=oq.get("container") or app_state.config_s3_bucket_name_default, config_blob_limit_kb=app_state.config_blob_limit_kb, config_blob_expire_sec=app_state.config_blob_expire_sec, count=oq["count"], config_blob_upload_limit_count=app_state.config_blob_upload_limit_count)
   elif oq["service"] == "azure":
      output=app_state.func_azure_blob_upload_url_sas(client_azure_blob=app_state.client_azure_blob, config_azure_account_name=app_state.config_azure_account_name, config_azure_account_key=app_state.config_azure_account_key, container=oq.get("container") or app_state.config_azure_container_name_default, config_blob_limit_kb=app_state.config_blob_limit_kb, config_blob_expire_sec=app_state.config_blob_expire_sec, count=oq["count"], config_blob_upload_limit_count=app_state.config_blob_upload_limit_count)
   return {"status":1,"message":output}
