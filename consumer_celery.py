#function
from function import function_client_read_postgres_asyncpg_pool
from function import function_postgres_object_create_asyncpg

#config
import os
from dotenv import load_dotenv
load_dotenv()
config_redis_url=os.getenv("config_redis_url")
config_postgres_url=os.getenv("config_postgres_url")

#import
import asyncio,traceback
from celery import Celery,signals

#client
client_celery_consumer=Celery("worker",broker=config_redis_url,backend=config_redis_url)
client_postgres_asyncpg_pool=None

#startup
@signals.worker_process_init.connect
def init_worker(**kwargs):
    global client_postgres_asyncpg_pool
    loop=asyncio.get_event_loop()
    client_postgres_asyncpg_pool=loop.run_until_complete(function_client_read_postgres_asyncpg_pool(config_postgres_url))

#shutdown
@signals.worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global client_postgres_asyncpg_pool
    loop=asyncio.get_event_loop()
    loop.run_until_complete(client_postgres_asyncpg_pool.close())

#task 1
@client_celery_consumer.task(name="function_postgres_object_create_asyncpg")
def celery_task_1(table,object_list):
    try:
        def run_wrapper():
            async def wrapper():
                global client_postgres_asyncpg_pool
                async with client_postgres_asyncpg_pool.acquire() as client_postgres_asyncpg:
                    await function_postgres_object_create_asyncpg(table,object_list,client_postgres_asyncpg)
            loop=asyncio.get_event_loop()
            return loop.run_until_complete(wrapper())
        return run_wrapper()
    except Exception as e:
        print("Exception occurred:",str(e))
        traceback.print_exc()
        return None

#task 2
@client_celery_consumer.task(name="add")
def celery_task_2(x,y):
   print(x+y)
   return None