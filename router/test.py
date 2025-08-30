#import
from extend import *

#test
@router.get("/test")
async def function_api_test():
   return {"status":1,"message":f"welcome to test"}

#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def function_api_websocket(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         data=await websocket.receive_text()
         await function_object_create_postgres(websocket.app.state.client_postgres,"test",[{"title":data}],0,None,None)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")

@router.get("/page/{name}")
async def function_api_page(name:str):
   if ".." in name:return function_return_error("invalid name")
   match=None
   for root,dirs,files in os.walk("."):
       dirs[:] = [d for d in dirs if not d.startswith(".") and d!="venv"]
       if f"{name}.html" in files:
           match=os.path.join(root,f"{name}.html")
           break
   if not match:return function_return_error("file not found")
   with open(match,"r",encoding="utf-8") as file:html_content=file.read()
   return responses.HTMLResponse(content=html_content)
