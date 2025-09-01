from aiokafka import AIOKafkaProducer
async def function_kafka_client_read_producer(config_kafka_url,config_kafka_username,config_kafka_password):
    client_kafka_producer=AIOKafkaProducer(bootstrap_servers=config_kafka_url,security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,)
    await client_kafka_producer.start()
    return client_kafka_producer
 
from aiokafka import AIOKafkaConsumer
async def function_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,topic_name,group_id,enable_auto_commit):
    client_kafka_consumer=AIOKafkaConsumer(topic_name,bootstrap_servers=config_kafka_url,group_id=group_id, security_protocol="SASL_PLAINTEXT",sasl_mechanism="PLAIN",sasl_plain_username=config_kafka_username,sasl_plain_password=config_kafka_password,auto_offset_reset="earliest",enable_auto_commit=enable_auto_commit)
    await client_kafka_consumer.start()
    return client_kafka_consumer
 
import json
async def function_kafka_producer(client_kafka_producer,channel_name,payload):
   output=await client_kafka_producer.send_and_wait(channel_name,json.dumps(payload,indent=2).encode('utf-8'),partition=0)
   return output
