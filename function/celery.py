from celery import Celery
async def function_celery_client_read_producer(config_celery_broker_url,config_celery_backend_url):
   client_celery_producer=Celery("producer",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_producer

from celery import Celery
def function_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url):
   client_celery_consumer=Celery("worker",broker=config_celery_broker_url,backend=config_celery_backend_url)
   return client_celery_consumer

async def function_celery_producer(client_celery_producer,function,param_list):
   output=client_celery_producer.send_task(function,args=param_list)
   return output.id
