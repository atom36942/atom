#import
from file.route import *

#test
@router.get("/test")
async def function_api_test(request:Request):
   return {"status":1,"message":"welcome to test"}

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
         await function_postgres_object_create("buffer",websocket.app.state.client_postgres_pool,"test",[{"title":message}])
         await websocket.send_text(f"message stored")
   except WebSocketDisconnect:
      print("client disconnected")

#zzz      
@router.get("/zzz")
async def function_api_test2(request:Request):
   output=None
   if False:await function_postgres_create_fake_data(request.app.state.client_postgres_pool)
   if False:output=await function_postgres_export(request.app.state.client_postgres_pool,"select * from test limit 1000")
   if False:await function_ocr_tesseract_export("sample/ocr.png")
   if False:await function_dir_filename_export()
   if False:output=await function_sftp_folder_filename_read(request.app.state.client_sftp,"mgh/amazon")
   if False:await function_sftp_file_upload(request.app.state.client_sftp,"sample/postgres.csv","file.csv")
   if False:await function_sftp_file_download(request.app.state.client_sftp,"mgh/amazon/filename.csv","file.csv")
   if False:await function_sftp_file_delete(request.app.state.client_sftp,"mgh/amazon/AMZON_INVOICE__20251214_080720_177.csv")
   if False:output=function_csv_file_to_obj_list("file.csv")
   if False:
      obj_list=[]
      async for obj_list_chunk in function_sftp_csv_read_to_obj_list_stream(request.app.state.client_sftp,"file.csv"):
         obj_list.extend(obj_list_chunk)
         obj_list=await function_postgres_object_serialize(request.app.state.cache_postgres_column_datatype,obj_list)
         await function_postgres_object_create("now",request.app.state.client_postgres_pool,"test",obj_list)
   return {"status":1,"message":output}
