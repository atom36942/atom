#env
import os
from dotenv import load_dotenv
load_dotenv()

#postgtes client
from databases import Database
postgres_client=Database(os.getenv("postgres_database_url"),min_size=1,max_size=100)

#sentry
import sentry_sdk
sentry_dsn=os.getenv("sentry_dsn")
if sentry_dsn:sentry_sdk.init(dsn=sentry_dsn,traces_sample_rate=1.0,profiles_sample_rate=1.0)

#redis key builder
from fastapi import Request,Response
def redis_key_builder(func,namespace:str="",*,request:Request=None,response:Response=None,**kwargs):
   api=request.url.path
   query_param=str(dict(sorted(request.query_params.items())))
   user_id=0
   gate=api.split("/")[1]
   token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
   if gate=="my":user_id=json.loads(jwt.decode(token,os.getenv("secret_key_jwt"),algorithms="HS256")["data"])["id"]
   key=api+"---"+str(user_id)+"---"+query_param
   return key

#lifespan
from fastapi import FastAPI
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
postgres_column_datatype=None
@asynccontextmanager
async def lifespan(app:FastAPI):
   #postgres
   if postgres_client:await postgres_client.connect()
   #redis
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(os.getenv("redis_server_url")))
   await FastAPILimiter.init(redis_client)
   FastAPICache.init(RedisBackend(redis_client),key_builder=redis_key_builder)
   #postgres column data type
   if postgres_client:
      global postgres_column_datatype
      query="select column_name,max(data_type) as data_type,max(udt_name) as udt_name from information_schema.columns where table_schema='public' group by  column_name;"
      output=await postgres_client.fetch_all(query=query,values={})
      postgres_column_datatype={item["column_name"]:item["data_type"] for item in output}
   #disconnect
   yield
   if postgres_client:await postgres_client.disconnect()
   if redis_client:await redis_client.aclose()
   
#app
from fastapi import FastAPI
app=FastAPI(lifespan=lifespan)

#cors
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

#middleware
from fastapi import Request,responses
from starlette.background import BackgroundTask
import jwt,json,time,traceback
object_list_log=[]
@app.middleware("http")
async def middleware(request:Request,api_function):
   try:
      #start
      start=time.time()
      token=request.headers.get("Authorization").split(" ",1)[1] if request.headers.get("Authorization") else None
      api=request.url.path
      gate=api.split("/")[1]
      user=None
      method=request.method
      #auth check
      if gate not in ["","docs","openapi.json","root","auth","my","public","private","admin"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"gate not allowed"})
      if gate=="root" and token!=os.getenv("secret_key_root"):return responses.JSONResponse(status_code=400,content={"status":0,"message":"token root mismatch"})
      if gate in ["my","private","admin"]:user=json.loads(jwt.decode(token,os.getenv("secret_key_jwt"),algorithms="HS256")["data"])
      if gate in ["admin"]:
         output=await postgres_client.fetch_all(query="select * from users where id=:id;",values={"id":user["id"]})
         user=output[0] if output else None
         if not user:return responses.JSONResponse(status_code=400,content={"status":0,"message":"no user"})
      if gate in ["admin"]:
         if not user["api_access"]:return responses.JSONResponse(status_code=400,content={"status":0,"message":"user not admin"})
         if api not in user["api_access"].split(","):return responses.JSONResponse(status_code=400,content={"status":0,"message":"api access denied"})
      #request state assign
      request.state.user=user
      request.state.postgres_column_datatype=postgres_column_datatype
      request.state.postgres_client=postgres_client
      #api response
      response=await api_function(request)
      #end
      end=time.time()
      response_time_ms=(end-start)*1000
      #log create
      global object_list_log
      object={"created_by_id":user["id"] if user else None,"api":api,"status_code":response.status_code,"response_time_ms":response_time_ms}
      object_list_log.append(object)
      if len(object_list_log)>=10:
         query="insert into log (created_by_id,api,status_code,response_time_ms) values (:created_by_id,:api,:status_code,:response_time_ms)"
         query_param=object_list_log
         BackgroundTask(await postgres_client.execute_many(query=query,values=query_param))
         object_list_log=[]
   except Exception as e:
      print(traceback.format_exc())
      return responses.JSONResponse(status_code=400,content={"status":0,"message":e.args})
   return response

#router
import os,glob
current_directory_path=os.path.dirname(os.path.realpath(__file__))
file_path_list=glob.glob(f"{current_directory_path}/*")
file_name_list=[item.rsplit("/",1)[-1] for item in file_path_list]
file_name_list_without_extension=[item.split(".")[0] for item in file_name_list]
for item in file_name_list_without_extension:
   if "api" in item:
      router=__import__(item).router
      app.include_router(router)

#fastapi app start
import uvicorn
async def fastapi_app_start(app):
   config=uvicorn.Config(app,host="0.0.0.0",port=8000,log_level="info")
   server=uvicorn.Server(config)
   await server.serve()
   
#kafka consumer start
from aiokafka import AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context
async def kafka_consumer_start(server_url,path_cafile,path_certfile,path_keyfile,topic):
   context=create_ssl_context(cafile=path_cafile,certfile=path_certfile,keyfile=path_keyfile)
   consumer=AIOKafkaConsumer(topic,bootstrap_servers=server_url,security_protocol="SSL",ssl_context=context,enable_auto_commit=True,auto_commit_interval_ms=10000)
   await consumer.start()
   try:
      async for msg in consumer:
         print("consumed:",msg.topic, msg.partition, msg.offset,msg.key, msg.value, msg.timestamp)
   finally:
      await consumer.stop()

#redis subscriber start
import redis.asyncio as redis
import asyncio
import async_timeout
async def redis_subscriber_start(redis_server_url,channel):
   redis_client=redis.Redis.from_pool(redis.ConnectionPool.from_url(redis_server_url))
   redis_pubsub=redis_client.pubsub()
   await redis_pubsub.psubscribe(channel)
   while True:
      try:
         async with async_timeout.timeout(1):
               message=await redis_pubsub.get_message(ignore_subscribe_messages=True)
               if message is not None:
                  print(message)
                  if message["data"].decode()=="stop":break
      except asyncio.TimeoutError:pass


#mode
import sys
mode=sys.argv

#main
import asyncio
if __name__=="__main__":
   try:
      if len(mode)==1:asyncio.run(fastapi_app_start(app))
      if len(mode)>1 and mode[1]=="redis-subscribe":asyncio.run(redis_subscriber_start(os.getenv("redis_server_url"),"atom"))
      if len(mode)>1 and mode[1]=="kafka-consumer":asyncio.run(kafka_consumer_start(os.getenv("kafka_server_url"),os.getenv("kafka_path_cafile"),os.getenv("kafka_path_certfile"),os.getenv("kafka_path_keyfile"),"atom"))
   except KeyboardInterrupt:
      print("exited")
