#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request

#private
@router.post("/private/s3-upload-file")
async def func_api_private_s3_upload_file(request:Request):
   st=request.app.state
   obj_form=await st.func_request_param_read(request=request, mode="form", config=[("bucket","str",1,None,None,None,None),("file","file",1,[],None,None,None)], strict=1)
   output={}
   if len(obj_form["file"])>st.config_s3_upload_limit_count:
      raise Exception(f"maximum {st.config_s3_upload_limit_count} files allowed")
   for item in obj_form["file"]:
      output[item.filename]=await st.func_s3_upload(client_s3=st.client_s3, bucket=obj_form["bucket"], file_obj=item, config_s3_limit_kb=st.config_s3_limit_kb)
   return {"status":1,"message":output}

@router.post("/private/s3-upload-presigned")
async def func_api_private_s3_upload_presigned(request:Request):
   st=request.app.state
   obj_query=await st.func_request_param_read(request=request, mode="query", config=[("bucket","str",1,None,None,None,None),("count","int",0,None,1,None,None)], strict=1)
   if obj_query["count"]>st.config_s3_upload_limit_count:
      raise Exception(f"maximum {st.config_s3_upload_limit_count} allowed")
   output=[]
   for _ in range(obj_query["count"]):
      output.append(st.func_s3_upload_presigned(client_s3=st.client_s3, config_s3_region_name=st.config_s3_region_name, bucket=obj_query["bucket"], config_s3_limit_kb=st.config_s3_limit_kb, config_s3_presigned_expire_sec=st.config_s3_presigned_expire_sec))
   return {"status":1,"message":output}
