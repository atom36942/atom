#function
from function import *

#env load
import os
from dotenv import load_dotenv
load_dotenv()

#redis
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="redis":
    try:asyncio.run(function_redis_consumer(os.getenv("redis_url"),os.getenv("channel_name","ch1"),os.getenv("postgres_url"),function_redis_client_read,function_redis_consumer_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")

#kafka
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="kafka":
    try:asyncio.run(function_kafka_consumer(os.getenv("kafka_url"),os.getenv("kafka_path_cafile"),os.getenv("kafka_path_certfile"),os.getenv("kafka_path_keyfile"),os.getenv("channel_name","ch1"),os.getenv("postgres_url"),function_kafka_consumer_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")

#rabbitmq
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="rabbitmq":
    try:asyncio.run(function_rabbitmq_consumer(os.getenv("rabbitmq_url"),os.getenv("channel_name","ch1"),os.getenv("postgres_url"),function_rabbitmq_channel_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")

#lavinmq
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="lavinmq":
    try:asyncio.run(function_lavinmq_consumer(os.getenv("lavinmq_url"),os.getenv("channel_name","ch1"),os.getenv("postgres_url"),function_lavinmq_channel_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")
