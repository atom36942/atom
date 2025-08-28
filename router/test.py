#import
from extend import *

#test
@router.get("/test")
async def route_test():
   return {"status":1,"message":f"welcome to test"}

#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def websocket_endpoint(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         data=await websocket.receive_text()
         await function_object_create_postgres(websocket.app.state.client_postgres,"test",[{"title":data}],0,None,None)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")


