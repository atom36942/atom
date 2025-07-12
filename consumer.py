#function
from function import *

#env load
env=function_load_env(".env")

#kafka
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="kafka":
    try:asyncio.run(function_consumer_kafka_postgres_crud(env.get("config_kafka_url"),env.get("config_kafka_path_cafile"),env.get("config_kafka_path_certfile"),env.get("config_kafka_path_keyfile"),env.get("config_channel_name","ch1"),env.get("config_postgres_url"),function_client_read_kafka_consumer,function_client_read_postgres,function_postgres_schema_read,function_postgres_object_create,function_postgres_object_update,function_postgres_object_serialize))
    except KeyboardInterrupt:print("exit")

#redis
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="redis":
    try:asyncio.run(function_consumer_redis_postgres_crud(env.get("config_redis_url"),env.get("config_channel_name","ch1"),env.get("config_postgres_url"),function_client_read_redis,function_client_read_redis_consumer,function_client_read_postgres,function_postgres_schema_read,function_postgres_object_create,function_postgres_object_update,function_postgres_object_serialize))
    except KeyboardInterrupt:print("exit")

#rabbitmq
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="rabbitmq":
    try:asyncio.run(function_consumer_rabbitmq_postgres_crud(env.get("config_rabbitmq_url"),env.get("config_channel_name","ch1"),env.get("config_postgres_url"),function_client_read_rabbitmq,function_client_read_postgres,function_postgres_schema_read,function_postgres_object_create,function_postgres_object_update,function_postgres_object_serialize))
    except KeyboardInterrupt:print("exit")

#lavinmq
import sys,asyncio
if __name__ == "__main__" and len(sys.argv)>1 and sys.argv[1]=="lavinmq":
    try:asyncio.run(function_consumer_lavinmq_postgres_crud(env.get("config_lavinmq_url"),env.get("config_channel_name","ch1"),env.get("config_postgres_url"),function_client_read_lavinmq,function_client_read_postgres,function_postgres_schema_read,function_postgres_object_create,function_postgres_object_update,function_postgres_object_serialize))
    except KeyboardInterrupt:print("exit")
    