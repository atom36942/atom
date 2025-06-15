#function
from function import *

#env
env=function_load_env(".env")

#redis
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="redis":
    try:asyncio.run(function_redis_consumer(env.get("redis_url"),env.get("channel_name","ch1"),env.get("postgres_url"),function_redis_client_read,function_redis_consumer_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")

#kafka
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="kafka":
    try:asyncio.run(function_kafka_consumer(env.get("kafka_url"),env.get("kafka_path_cafile"),env.get("kafka_path_certfile"),env.get("kafka_path_keyfile"),env.get("channel_name","ch1"),env.get("postgres_url"),function_kafka_consumer_client_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")

#rabbitmq
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="rabbitmq":
    try:asyncio.run(function_rabbitmq_consumer(env.get("rabbitmq_url"),env.get("channel_name","ch1"),env.get("postgres_url"),function_rabbitmq_channel_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")

#lavinmq
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="lavinmq":
    try:asyncio.run(function_lavinmq_consumer(env.get("lavinmq_url"),env.get("channel_name","ch1"),env.get("postgres_url"),function_lavinmq_channel_read,function_postgres_client_read,function_postgres_schema_read,function_postgres_create,function_postgres_update,function_object_serialize))
    except KeyboardInterrupt:print("exit")
