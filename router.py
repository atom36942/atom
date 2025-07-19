#function
from function import *

#router
from fastapi import APIRouter
router=APIRouter()

#config
import os
from dotenv import load_dotenv
load_dotenv()
config_channel_name=os.getenv("config_channel_name","ch1")

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
   task_1=request.app.state.client_celery_producer.send_task("function_postgres_object_create_asyncpg",args=["test",[{"title": "celery"}]])
   task_2=request.app.state.client_celery_producer.send_task("add",args=[2,3])
   return {"status":1,"message":"done"}

#posthog
@router.get("/posthog")
async def route_posthog(request:Request):
   request.app.state.client_posthog.capture(distinct_id="user_1",event="test")
   request.app.state.client_posthog.capture(distinct_id="user_2",event="posthog kt",properties={"name":"atom","title":"testing"})
   return {"status":1,"message":"done"}

#redis publish
@router.get("/redis-publish")
async def route_redis_publish(request:Request):
   data_1={"function":"function_postgres_object_create","table":"test","object_list":[{"title":"redis2"},{"title":"redis3"}]}
   data_2={"function":"function_postgres_object_update","table":"users","object_list":[{"id":1,"email":"atom"}]}
   for data in [data_1,data_2]:await function_publish_redis(data,request.app.state.client_redis,config_channel_name)
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

