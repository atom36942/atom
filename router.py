#function
from function import *

#router
from fastapi import APIRouter
router=APIRouter()

#test
@router.get("/test")
async def test(request:Request):
   await function_postgres_object_create("test",[{"title":"router"}],1,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   return {"status":1,"message":"test"}

#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def websocket_endpoint(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         data=await websocket.receive_text()
         await function_postgres_object_create("test",[{"title":data}],1,websocket.app.state.cache_postgres_column_datatype,websocket.app.state.client_postgres,function_postgres_object_serialize)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")