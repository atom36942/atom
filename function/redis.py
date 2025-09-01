import redis.asyncio as redis
async def function_redis_client_read(config_redis_url):
   client_redis=redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))
   return client_redis

async def function_redis_client_read_consumer(client_redis,channel_name):
   client_redis_consumer=client_redis.pubsub()
   await client_redis_consumer.subscribe(channel_name)
   return client_redis_consumer

import json
async def function_redis_producer(client_redis,channel_name,payload):
   output=await client_redis.publish(channel_name,json.dumps(payload))
   return output

import json
async def function_redis_object_read(client_redis,key):
   output=await client_redis.get(key)
   if output:output=json.loads(output)
   return output