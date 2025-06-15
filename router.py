#function
from function import *

#env load
import os
from dotenv import load_dotenv
load_dotenv()

#router
from fastapi import APIRouter
router=APIRouter()

#ratelimiter
from fastapi import Depends
from fastapi_limiter.depends import RateLimiter

#test
@router.get("/test",dependencies=[Depends(RateLimiter(times=1,seconds=1))])
async def test(request:Request):
   await function_postgres_create("test",[{"title":"router"}],1,request.app.state.global_state["postgres_client"],request.app.state.global_state["postgres_column_datatype"],function_object_serialize)
   return {"status":1,"message":"test"}

#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def websocket_endpoint(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         data=await websocket.receive_text()
         await function_postgres_create("test",[{"title":data}],1,websocket.app.state.global_state["postgres_client"],websocket.app.state.global_state["postgres_column_datatype"],function_object_serialize)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")

