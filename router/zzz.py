#import
from core.route import *

#api
@router.get("/test")
async def func_api_2653353cdf3145558dae1c3ce24318e2(request:Request):
   if False:await func_sftp_file_upload(request.app.state.client_sftp,"sample/ocr.png","ocr.png")
   if False:await func_sftp_file_download(request.app.state.client_sftp, "ocr.png")
   return {"status":1,"message":"welcome to test"}

@router.get("/protected/test")
async def func_api_1bd8a31e5baa4b67b6f05785f3dd52fb(request:Request):
   return {"status":1,"message":"welcome to test protected"}

@router.get("/page/{name}")
async def func_api_10f177735aac4564a0946f9088f17d9a(name):
   html_path=await func_path_read(config_folder_html_list,f"{name}.html")
   return responses.HTMLResponse(content=await func_read_html(html_path))

@router.websocket("/websocket")
async def func_api_8d1ca30d92ee40c4afe50974fb3363e8(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         output=await func_postgres_obj_create(websocket.app.state.client_postgres_pool,func_postgres_obj_serialize,websocket.app.state.cache_postgres_column_datatype,"buffer","test",[{"title":message}],0,3)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")
      