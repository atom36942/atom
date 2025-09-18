#import
from route import *

#test
@router.get("/test")
async def function_api_test():
   return {"status":1,"message":f"welcome to test"}

#page
@router.get("/page/{name}")
async def function_api_page(name: str):
    filename = name if name.endswith(".html") else f"{name}.html"
    html_content = await function_render_html(filename)
    return responses.HTMLResponse(content=html_content)
 
#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def function_api_websocket(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         await function_postgres_object_create(websocket.app.state.client_postgres_pool,"test",[{"title":message}],"buffer")
         await websocket.send_text(f"message stored")
   except WebSocketDisconnect:
      print("client disconnected")

