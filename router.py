#function
from function import *

#env
env=function_load_env(".env")

#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request
from fastapi.responses import StreamingResponse

#test
@router.get("/test")
async def test(request:Request):
   await function_postgres_object_create("test",[{"created_by_id":request.state.user.get("id"),"title":"test"}],1,request.app.state.cache_postgres_column_datatype,request.app.state.client_postgres,function_postgres_object_serialize)
   await function_postgres_object_create_minimal("test",[{"title":"minimal"}],request.app.state.client_postgres)
   task_celery_1=request.app.state.client_celery_producer.send_task("tasks.celery_task_postgres_object_create",args=["test",[{"title": "celery"}]])
   task_celery_2=request.app.state.client_celery_producer.send_task("tasks.celery_add_num",args=[2,3])
   request.app.state.client_posthog.capture(distinct_id="user_1",event="test")
   request.app.state.client_posthog.capture(distinct_id="user_2",event="posthog kt",properties={"name":"atom","title":"testing"})
   return {"status":1,"message":"done"}

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

#streaming
@router.get("/stream")
async def stream():
   async def generator():
      for i in range(1, 101):
         yield f"{i}\n"
         await asyncio.sleep(0.05)
   return StreamingResponse(generator(),media_type="text/plain")
