import aio_pika
async def function_rabbitmq_client_read_producer(config_rabbitmq_url):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_producer=await client_rabbitmq.channel()
   return client_rabbitmq,client_rabbitmq_producer

import aio_pika
async def function_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name):
   client_rabbitmq=await aio_pika.connect_robust(config_rabbitmq_url)
   client_rabbitmq_channel=await client_rabbitmq.channel()
   client_rabbitmq_consumer=await client_rabbitmq_channel.declare_queue(config_channel_name,auto_delete=False)
   return client_rabbitmq,client_rabbitmq_consumer

import json,aio_pika
async def function_rabbitmq_producer(client_rabbitmq_producer,channel_name,payload):
    body=json.dumps(payload).encode()
    message=aio_pika.Message(body=body)
    output=await client_rabbitmq_producer.default_exchange.publish(message,routing_key=channel_name)
    return output