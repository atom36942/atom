#import
from core.route import *

#api
@router.get("/test")
async def function_api_test(request:Request):
   return {"status":1,"message":"welcome to test"}

@router.get("/protected/test")
async def function_api_test(request:Request):
   return {"status":1,"message":"welcome to test protected"}

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

