#import
from extend import *

#test
@router.get("/test")
async def route_test():
   value=config.get("your_config_key")
   return {"status":1,"message":f"welcome to test"}

#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def websocket_endpoint(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         data=await websocket.receive_text()
         table="test"
         obj={"title":data}
         await function_object_create_postgres(websocket.app.state.client_postgres,table,[obj],0,None,None)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")


