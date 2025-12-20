#import
from core.route import *

#api
@router.get("/test")
async def func_api_test(request:Request):
   return {"status":1,"message":"welcome to test"}

@router.get("/protected/test")
async def func_api_test(request:Request):
   return {"status":1,"message":"welcome to test protected"}

@router.get("/page/{name}")
async def func_api_page(name: str):
    target_file_path = None
    for file_path in Path("html").rglob("*.html"):
        if file_path.stem == name:
            target_file_path = file_path
            break
    if not target_file_path:raise Exception("page not found")
    html_content = await func_render_html(str(target_file_path))
    return responses.HTMLResponse(content=html_content)
 
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def func_api_websocket(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         output=await func_postgres_obj_list_create(websocket.app.state.client_postgres_pool,func_postgres_obj_list_serialize,websocket.app.state.cache_postgres_column_datatype,"buffer","test",[{"title":message}],0)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")

#test
@router.get("/test2")
async def func_api_test2(request:Request):
   output=None
   if False:await func_postgres_create_fake_data(request.app.state.client_postgres_pool)
   if True:output=await func_postgres_export(func_outpath_path_create,request.app.state.client_postgres_pool,"select * from test limit 1000")
   if True:await func_ocr_tesseract_export(func_outpath_path_create,"sample/ocr.png")
   if True:output=await func_folder_filename_export(func_outpath_path_create,".")
   if True:output=func_converter_csv_obj_list("sample/postgres.csv")
   if False:output=await func_sftp_folder_filename_read(request.app.state.client_sftp,"mgh/amazon")
   if False:await func_sftp_file_upload(request.app.state.client_sftp,"sample/postgres.csv","mgh/amazon/file.csv")
   if False:output=await func_sftp_file_download(func_outpath_path_create,request.app.state.client_sftp,"mgh/amazon/file.csv")
   if False:await func_sftp_file_delete(request.app.state.client_sftp,"mgh/amazon/file.csv")
   if False:
      obj_list=[]
      async for chunk in func_sftp_csv_read_to_obj_list_stream(request.app.state.client_sftp,"file.csv"):
         obj_list.extend(chunk)
         await func_postgres_obj_list_create(request.app.state.client_postgres_pool,func_postgres_obj_list_serialize,request.app.state.cache_postgres_column_datatype,"now","test",obj_list,1)
   return {"status":1,"message":output}

@router.post("/test3")
async def func_api_test3(request:Request):
   param=await func_request_param_read(request,"form",[["file","file",1,[]]])
   for file_api in param["file"]:output=await func_save_file_api(func_outpath_path_create,file_api)
   return {"status":1,"message":output}

