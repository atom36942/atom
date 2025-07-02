#env
import os
from dotenv import load_dotenv
load_dotenv()

#config
config_redis_url=os.getenv("config_redis_url")
config_postgres_url=os.getenv("config_postgres_url")

#import
import asyncio,traceback

#celery
from celery import Celery
client_celery_consumer=Celery("worker",broker=config_redis_url,backend=config_redis_url)

#postgres client
from databases import Database

#task 1
@client_celery_consumer.task(name="tasks.celery_task_postgres_object_create")
def celery_task_postgres_object_create(table,object_list):
   try:
      def run_wrapper():
         async def wrapper():
            client_postgres=Database(config_postgres_url,min_size=1,max_size=100)
            await client_postgres.connect()
            try:
               column_insert_list=list(object_list[0].keys())
               query=f"insert into {table} ({','.join(column_insert_list)}) values ({','.join([':'+item for item in column_insert_list])}) on conflict do nothing returning *;"
               if len(object_list)==1:
                  output=await client_postgres.execute(query=query,values=object_list[0])
               else:
                  async with client_postgres.transaction():
                     output=await client_postgres.execute_many(query=query,values=object_list)
               return output
            finally:
               await client_postgres.disconnect()
         return asyncio.run(wrapper())
      return run_wrapper()
   except Exception as e:
      print("Exception occurred:",str(e))
      traceback.print_exc()
      return None

#task 2
@client_celery_consumer.task(name="tasks.celery_add_num")
def celery_add_num(x,y):
   print(x+y)
   return None