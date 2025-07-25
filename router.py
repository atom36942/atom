#function
from function import *

#router
from fastapi import APIRouter
router=APIRouter()

#config
import os
from dotenv import load_dotenv
load_dotenv()

#import
from fastapi import Request

#postgres create
@router.get("/postgres-create")
async def route_postgres_create(request:Request):
   table="test"
   object={"created_by_id":request.state.user.get("id"),"title":"router"}
   await function_object_create_postgres(request.app.state.client_postgres,table,[object],0,None,None)
   return {"status":1,"message":"done"}

#postgres update
@router.get("/postgres-update")
async def route_postgres_update(request:Request):
   table="users"
   object={"id":1,"email":"atom1","mobile":"atom2"}
   await function_object_update_postgres(request.app.state.client_postgres,table,[object],0,None,None)
   return {"status":1,"message":"done"}

#kafka publish
@router.get("/kafka-publish")
async def route_kafka_publish(request:Request):
   data_1={"function":"function_object_create_postgres","table":"test","object_list":[{"title":"kafka2"},{"title":"kafka3"}]}
   data_2={"function":"function_object_update_postgres","table":"users","object_list":[{"id":1,"email":"kafka"}]}
   for data in [data_1,data_2]:await function_publisher_kafka(request.app.state.client_kafka_producer,"channel_1",data)
   return {"status":1,"message":"done"}

#rabbitmq publish
@router.get("/rabbitmq-publish")
async def route_rabbitmq_publish(request:Request):
   data_1={"function":"function_object_create_postgres","table":"test","object_list":[{"title":"rabbitmq2"},{"title":"rabbitmq3"}]}
   data_2={"function":"function_object_update_postgres","table":"users","object_list":[{"id":1,"email":"rabbitmq"}]}
   for data in [data_1,data_2]:await function_publisher_rabbitmq(request.app.state.client_rabbitmq_channel,"channel_1",data)
   return {"status":1,"message":"done"}

#redis publish
@router.get("/redis-publish")
async def route_redis_publish(request:Request):
   data_1={"function":"function_object_create_postgres","table":"test","object_list":[{"title":"redis2"},{"title":"redis3"}]}
   data_2={"function":"function_object_update_postgres","table":"users","object_list":[{"id":1,"email":"redis"}]}
   for data in [data_1,data_2]:await function_publisher_redis(request.app.state.client_redis,"channel_1",data)
   return {"status":1,"message":"done"}

#celery
@router.get("/celery")
async def route_celery(request:Request):
   task_1=request.app.state.client_celery_producer.send_task("function_object_create_postgres_asyncpg",args=["test",[{"title": "celery"}]])
   task_2=request.app.state.client_celery_producer.send_task("add",args=[2,3])
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
         await function_object_create_postgres(websocket.app.state.client_postgres,table,[object],0,None,None)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")

