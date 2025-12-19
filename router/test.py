#import
from core.route import *

#api

@router.get("/test2")
async def function_api_test2(request:Request):
   output=None
   if False:await function_postgres_create_fake_data(request.app.state.client_postgres_pool)
   if True:output=await function_postgres_export(function_outpath_path_create,request.app.state.client_postgres_pool,"select * from test limit 1000")
   if True:await function_ocr_tesseract_export(function_outpath_path_create,"sample/ocr.png")
   if True:output=await function_folder_filename_export(function_outpath_path_create,".")
   if True:output=function_converter_csv_obj_list("sample/postgres.csv")
   if False:output=await function_sftp_folder_filename_read(request.app.state.client_sftp,"mgh/amazon")
   if False:await function_sftp_file_upload(request.app.state.client_sftp,"sample/postgres.csv","mgh/amazon/file.csv")
   if False:output=await function_sftp_file_download(function_outpath_path_create,request.app.state.client_sftp,"mgh/amazon/file.csv")
   if False:await function_sftp_file_delete(request.app.state.client_sftp,"mgh/amazon/file.csv")
   if False:
      obj_list=[]
      async for chunk in function_sftp_csv_read_to_obj_list_stream(request.app.state.client_sftp,"file.csv"):
         obj_list.extend(chunk)
         await function_postgres_object_create(request.app.state.client_postgres_pool,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,"now","test",obj_list,1)
   return {"status":1,"message":output}

@router.post("/test3")
async def function_api_test3(request:Request):
   param=await function_request_param_read(request,"form",[["file","file",1,[]]])
   for file_api in param["file"]:output=await function_save_file_api(function_outpath_path_create,file_api)
   return {"status":1,"message":output}
      