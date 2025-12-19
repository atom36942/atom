#import
from core.route import *

#test
@router.get("/test")
async def function_api_test(request:Request):
   return {"status":1,"message":"welcome to test"}

@router.get("/protected/test")
async def function_api_test(request:Request):
   return {"status":1,"message":"welcome to test protected"}

@router.get("/zzz")
async def function_api_test2(request:Request):
   output=None
   if False:await function_postgres_create_fake_data(request.app.state.client_postgres_pool)
   if True:output=await function_postgres_export(function_outpath_path_create,request.app.state.client_postgres_pool,"select * from test limit 1000")
   if True:await function_ocr_tesseract_export(function_outpath_path_create,"sample/ocr.png")
   if True:output=await function_folder_filename_export(function_outpath_path_create,".")
   if False:output=await function_sftp_folder_filename_read(request.app.state.client_sftp,"mgh/amazon")
   if False:await function_sftp_file_upload(request.app.state.client_sftp,"sample/postgres.csv","file.csv")
   if False:output=await function_sftp_file_download(function_outpath_path_create,request.app.state.client_sftp,"mgh/amazon/filename.csv")
   if False:await function_sftp_file_delete(request.app.state.client_sftp,"mgh/amazon/AMZON_INVOICE__20251214_080720_177.csv")
   if False:output=function_csv_file_to_obj_list("file.csv")
   if False:
      obj_list=[]
      async for chunk in function_sftp_csv_read_to_obj_list_stream(request.app.state.client_sftp,"file.csv"):
         obj_list.extend(chunk)
         await function_postgres_object_create(request.app.state.client_postgres_pool,function_postgres_object_serialize,request.app.state.cache_postgres_column_datatype,"now","test",obj_list,1)
   return {"status":1,"message":output}

#page
@router.get("/page/{name}")
async def function_api_page(name: str):
    target_file_path = None
    for file_path in Path("html").rglob("*.html"):
        if file_path.stem == name:
            target_file_path = file_path
            break
    if not target_file_path:raise Exception("page not found")
    html_content = await function_render_html(str(target_file_path))
    return responses.HTMLResponse(content=html_content)
 
#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def function_api_websocket(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         output=await function_postgres_object_create(websocket.app.state.client_postgres_pool,function_postgres_object_serialize,websocket.app.state.cache_postgres_column_datatype,"buffer","test",[{"title":message}],0)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")

