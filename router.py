#router
from fastapi import APIRouter
router=APIRouter()

#env
import os
from dotenv import load_dotenv
load_dotenv()

#function
from function import *

#ratelimiter
from fastapi import Depends
from fastapi_limiter.depends import RateLimiter

#test
@router.get("/api",dependencies=[Depends(RateLimiter(times=1,seconds=1))])
async def test(request:Request):
   table="test"
   object={"title":"test_api"}
   await postgres_create(table,[object],1,request.app.state.global_state["postgres_client"],request.app.state.global_state["postgres_column_datatype"],object_serialize)
   return {"status":1,"message":"welcome to test"}

#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
   await websocket.accept()
   postgres_client = websocket.app.state.global_state["postgres_client"]
   print("WebSocket -> postgres_client:", postgres_client)
   try:
      while True:
         data = await websocket.receive_text()
         await websocket.send_text(f"Echo: {data}")
   except WebSocketDisconnect:
      print("Client disconnected")

