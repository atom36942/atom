#import
from function import *
from config import *
import asyncio,sys,orjson as json

#celery
client_postgres_pool=None
cache_postgres_schema=None
cache_postgres_column_datatype=None
worker_loop=None
def logic_celery():
    from celery import signals
    from itertools import count
    app=func_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url)
    app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
    _run_counter=count(1)
    async def _init_pool():
        global client_postgres_pool,cache_postgres_schema,cache_postgres_column_datatype
        if client_postgres_pool is None:
            client_postgres_pool=await func_postgres_client_read(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection)
            cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool)
            print("postgres pool initialized")
    @signals.worker_process_init.connect
    def init_worker(**kwargs):
        global worker_loop
        worker_loop=asyncio.new_event_loop()
        asyncio.set_event_loop(worker_loop)
        if config_postgres_url:
            worker_loop.run_until_complete(_init_pool())
        print("celery worker initialized")
    def run_async(coro_func, *args):
        n=next(_run_counter)
        global worker_loop, client_postgres_pool, cache_postgres_column_datatype
        if not worker_loop:
            worker_loop=asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
        try:
            worker_loop.run_until_complete(_init_pool())
            worker_loop.run_until_complete(coro_func(client_postgres_pool, func_postgres_obj_serialize, cache_postgres_column_datatype, *args))
            print(f"task completed #{n}")
            return None
        except Exception as e:
            print(f"task failed #{n}: {str(e)}")
            raise
    @app.task(name="func_postgres_obj_create")
    def celery_task_1(mode,table,obj_list,is_serialize,buffer):
        return run_async(func_postgres_obj_create, mode, table, obj_list, is_serialize, buffer)
    @app.task(name="func_postgres_obj_update")
    def celery_task_2(table,obj_list,is_serialize,created_by_id):
        return run_async(func_postgres_obj_update, table, obj_list, is_serialize, created_by_id)
    return app

#redis
async def logic_redis():
    try:
        client_redis=await func_redis_client_read(config_redis_url_pubsub)
        client_redis_consumer=await func_redis_client_read_consumer(client_redis,config_channel_name)
        client_postgres_pool=await func_postgres_client_read(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
        cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None,None)
        print("redis consumer started")
        async for message in client_redis_consumer.listen():
            if message["type"]=="message" and message["channel"]==config_channel_name.encode():
                payload=json.loads(message['data'])
                await func_consumer_logic(payload,func_postgres_obj_create,func_postgres_obj_update,func_postgres_obj_serialize,client_postgres_pool,cache_postgres_column_datatype)
                print("redis message processed")
    except asyncio.CancelledError:pass
    except Exception as e:print(f"redis error: {str(e)}")
    finally:
        if 'client_redis' in locals():await client_redis.aclose()
        if 'client_postgres_pool' in locals() and client_postgres_pool:await client_postgres_pool.close()

#rabbitmq
async def logic_rabbitmq():
    import aio_pika
    try:
        client_rabbitmq,client_rabbitmq_consumer=await func_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name)
        client_postgres_pool=await func_postgres_client_read(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
        cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None,None)
        async def aqmp_callback(message:aio_pika.IncomingMessage):
            async with message.process():
                payload=json.loads(message.body)
                await func_consumer_logic(payload,func_postgres_obj_create,func_postgres_obj_update,func_postgres_obj_serialize,client_postgres_pool,cache_postgres_column_datatype)
                print("rabbitmq message processed")
        print("rabbitmq consumer started")
        await client_rabbitmq_consumer.consume(aqmp_callback)
        await asyncio.Future()
    except asyncio.CancelledError:pass
    except Exception as e:print(f"rabbitmq error: {str(e)}")
    finally:
        if 'client_rabbitmq_consumer' in locals():await client_rabbitmq_consumer.channel.close()
        if 'client_rabbitmq' in locals() and not client_rabbitmq.is_closed:await client_rabbitmq.close()
        if 'client_postgres_pool' in locals() and client_postgres_pool:await client_postgres_pool.close()

#kafka
async def logic_kafka():
    try:
        client_kafka_consumer=await func_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_kafka_group_id,config_kafka_enable_auto_commit)
        client_postgres_pool=await func_postgres_client_read(config_postgres_url,config_postgres_min_connection,config_postgres_max_connection) if config_postgres_url else None
        cache_postgres_schema,cache_postgres_column_datatype=await func_postgres_schema_read(client_postgres_pool) if client_postgres_pool else (None,None)
        print("kafka consumer started")
        while True:
            batch=await client_kafka_consumer.getmany(timeout_ms=1000, max_records=100)
            if not batch:continue
            for tp, messages in batch.items():
                for message in messages:
                    payload=json.loads(message.value.decode('utf-8'))
                    await func_consumer_logic(payload,func_postgres_obj_create,func_postgres_obj_update,func_postgres_obj_serialize,client_postgres_pool,cache_postgres_column_datatype)
                if not config_kafka_enable_auto_commit:await client_kafka_consumer.commit(tp)
                print(f"kafka batch processed: {len(messages)} msgs")
    except asyncio.CancelledError:pass
    except Exception as e:print(f"kafka error: {str(e)}")
    finally:
        if 'client_kafka_consumer' in locals():await client_kafka_consumer.stop()
        if 'client_postgres_pool' in locals() and client_postgres_pool:await client_postgres_pool.close()

#celery init
celery=None
if "celery" in sys.argv[0] or (len(sys.argv) > 1 and sys.argv[1] == "celery"):celery=logic_celery()

#main
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: venv/bin/python consumer.py [redis|rabbitmq|kafka|celery]")
        sys.exit(1)
    mode=sys.argv[1]
    try:
        if mode=="redis":asyncio.run(logic_redis())
        elif mode=="rabbitmq":asyncio.run(logic_rabbitmq())
        elif mode=="kafka":asyncio.run(logic_kafka())
        elif mode=="celery":(celery.worker_main(argv=['worker','--loglevel=info']) if celery else None)
        else:print(f"unknown mode: {mode}")
    except KeyboardInterrupt:sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)