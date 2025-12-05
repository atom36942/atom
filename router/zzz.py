#import
from file.route import *

#test
@router.get("/test")
async def function_api_test():
   return {"status":1,"message":f"welcome to test"}

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
