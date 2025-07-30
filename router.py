#import
from extend import *

#test
@router.get("/test")
async def route_test():
   value=config.get("your_config_key")
   return {"status":1,"message":f"welcome to test"}

#celery
@router.get("/celery-producer")
async def route_celery(request:Request):
   await function_producer_celery(request.app.state.client_celery_producer,"function_object_create_postgres",["test",[{"title": "celery2"},{"title": "celery3"}],0])
   await function_producer_celery(request.app.state.client_celery_producer,"function_object_update_postgres",["users",[{"id":1,"email":"celery4"}],0])
   await function_producer_celery(request.app.state.client_celery_producer,"function_postgres_query_runner",["update test set title='celery4' where id=109;",1])
   return {"status":1,"message":"done"}

#kafka publish
@router.get("/kafka-producer")
async def route_kafka_publish(request:Request):
   payload_1={"function":"function_object_create_postgres","table":"test","object_list":[{"title":"kafka2"},{"title":"kafka3"}]}
   payload_2={"function":"function_object_update_postgres","table":"users","object_list":[{"id":1,"email":"kafka4"}]}
   payload_3={"function":"function_postgres_query_runner","query":"update test set title='celery100' where id=109;","user_id":1}
   for payload in [payload_1,payload_2,payload_3]:
      await function_producer_kafka(request.app.state.client_kafka_producer,"channel_1",payload)
   return {"status":1,"message":"done"}

#rabbitmq publish
@router.get("/rabbitmq-producer")
async def route_rabbitmq_publish(request:Request):
   payload_1={"function":"function_object_create_postgres","table":"test","object_list":[{"title":"rabbitmq2"},{"title":"rabbitmq3"}]}
   payload_2={"function":"function_object_update_postgres","table":"users","object_list":[{"id":1,"email":"rabbitmq"}]}
   payload_3={"function":"function_postgres_query_runner","query":"update test set title='rabbitmq100' where id=337;","user_id":1}
   for payload in [payload_1,payload_2,payload_3]:
      await function_producer_rabbitmq(request.app.state.client_rabbitmq_channel,"channel_1",payload)
   return {"status":1,"message":"done"}

#redis publish
@router.get("/redis-producer")
async def route_redis_publish(request:Request):
   payload_1={"function":"function_object_create_postgres","table":"test","object_list":[{"title":"redis2"},{"title":"redis3"}]}
   payload_2={"function":"function_object_update_postgres","table":"users","object_list":[{"id":1,"email":"redis"}]}
   payload_3={"function":"function_postgres_query_runner","query":"update test set title='redis100' where id=355;","user_id":1}
   for payload in [payload_1,payload_2,payload_3]:
      await function_producer_redis(request.app.state.client_redis_pubsub,"channel_1",payload)
   return {"status":1,"message":"done"}

#posthog
@router.get("/posthog")
async def route_posthog(request:Request):
   request.app.state.client_posthog.capture(distinct_id="user_1",event="test")
   request.app.state.client_posthog.capture(distinct_id="user_2",event="posthog kt",properties={"name":"atom","title":"testing"})
   return {"status":1,"message":"done"}

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

