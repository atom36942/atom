#function
from function import *

#router
from fastapi import APIRouter
router=APIRouter()

#env
env=function_load_env(".env")

#import
from fastapi import Request

#postgres create
@router.get("/postgres-create")
async def route_postgres_create(request:Request):
   table="test"
   object={"created_by_id":request.state.user.get("id"),"title":"postgres-create"}
   await function_postgres_object_create(table,[object],request.app.state.client_postgres,0,None,None)
   return {"status":1,"message":"done"}

#celery
@router.get("/celery")
async def route_celery(request:Request):
   task_celery_1=request.app.state.client_celery_producer.send_task("tasks.celery_task_postgres_object_create",args=["test",[{"title": "celery"}]])
   task_celery_2=request.app.state.client_celery_producer.send_task("tasks.celery_add_num",args=[2,3])
   return {"status":1,"message":"done"}

#posthog
@router.get("/posthog")
async def route_posthog(request:Request):
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
         table="test"
         object={"title":data}
         await function_postgres_object_create(table,[object],websocket.app.state.client_postgres,0,None,None)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")

