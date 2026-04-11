#router
from fastapi import APIRouter
router=APIRouter()

#import
from core.config import *
from core.function import *
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#private
@router.post("/private/s3-upload-file")
async def func_api_private_s3_upload_file(request:Request):
   obj_form=await func_request_param_read(request,"form",[("bucket","str",1,None,None,None,None),("file","file",1,[],None,None,None)])
   st,output=request.app.state,{}
   if len(obj_form["file"])>config_s3_upload_limit_count:
      raise Exception(f"maximum {config_s3_upload_limit_count} files allowed")
   for item in obj_form["file"]:
      output[item.filename]=await func_s3_upload(st.client_s3,obj_form["bucket"],item,config_s3_limit_kb=config_s3_limit_kb)
   return {"status":1,"message":output}

@router.post("/private/s3-upload-presigned")
async def func_api_private_s3_upload_presigned(request:Request):
   obj_query=await func_request_param_read(request,"query",[("bucket","str",1,None,None,None,None),("count","int",0,None,1,None,None)])
   if obj_query["count"]>config_s3_upload_limit_count:
      raise Exception(f"maximum {config_s3_upload_limit_count} allowed")
   st,output=request.app.state,[]
   for _ in range(obj_query["count"]):
      output.append(func_s3_upload_presigned(st.client_s3,config_s3_region_name,obj_query["bucket"],config_s3_limit_kb=config_s3_limit_kb,config_s3_presigned_expire_sec=config_s3_presigned_expire_sec))
   return {"status":1,"message":output}
