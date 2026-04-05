#import
from function import *
from config import *
import asyncio,sys,orjson as json

#celery
client_postgres_pool=None
worker_loop=None
async def _init_pool():
    global client_postgres_pool
    if client_postgres_pool is None:
        client_postgres_pool=await func_postgres_client_read({"dsn":config_postgres_url,"min_size":config_postgres_min_connection,"max_size":config_postgres_max_connection})
        print("postgres pool initialized", flush=True)
def logic_celery():
    from celery import signals
    from itertools import count
    app=func_celery_client_read_consumer(config_celery_broker_url,config_celery_backend_url)
    app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
    _run_counter=count(1)
    @signals.worker_process_init.connect
    def init_worker(**kwargs):
        global worker_loop
        worker_loop=asyncio.new_event_loop()
        asyncio.set_event_loop(worker_loop)
        if config_postgres_url:
            worker_loop.run_until_complete(_init_pool())
        print("celery worker initialized", flush=True)
    def run_async(coro_func, *args):
        n=next(_run_counter)
        global worker_loop, client_postgres_pool
        if not worker_loop:
            worker_loop=asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
        if client_postgres_pool is None and config_postgres_url:
            worker_loop.run_until_complete(_init_pool())
        try:
            worker_loop.run_until_complete(coro_func(client_postgres_pool, func_postgres_obj_serialize, *args))
            print(f"task completed #{n}", flush=True)
            return None
        except Exception as e:
            print(f"task failed #{n}: {str(e)}", flush=True)
            raise
    @app.task(name="func_postgres_create")
    def celery_task_1(mode,table,obj_list,is_serialize,buffer):
        return run_async(func_postgres_create, table, obj_list, mode, is_serialize, buffer)
    @app.task(name="func_postgres_update")
    def celery_task_2(table,obj_list,is_serialize,created_by_id):
        return run_async(func_postgres_update, table, obj_list, is_serialize, created_by_id)
    return app

#redis
async def logic_redis():
    import asyncio
    while True:
        try:
            try:
                global client_postgres_pool
                client_redis=await func_redis_client_read(config_redis_url_pubsub)
                client_redis_consumer=await func_redis_client_read_consumer(client_redis,config_channel_name)
                if config_postgres_url:await _init_pool()
                print("redis consumer started", flush=True)
                local_queue = asyncio.Queue()
                async def redis_listener():
                    async for message in client_redis_consumer.listen():
                        if message["type"]=="message" and message["channel"]==config_channel_name.encode():
                            await local_queue.put(message["data"])
                async def redis_processor():
                    while True:
                        payloads = []
                        for _ in range(config_redis_batch_limit):
                            try:
                                data = await asyncio.wait_for(local_queue.get(), timeout=config_redis_batch_timeout_ms/1000.0 if not payloads else 0.1)
                                payloads.append(json.loads(data))
                            except asyncio.TimeoutError: break
                        if payloads:
                            await func_consumer_batch_logic(payloads,func_postgres_create,func_postgres_update,func_postgres_obj_serialize,client_postgres_pool)
                            print(f"redis batch processed: {len(payloads)} msgs", flush=True)
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(redis_listener())
                    tg.create_task(redis_processor())
            except* Exception as e:print(f"redis error: {str(e)}", flush=True); await asyncio.sleep(5)
        except asyncio.CancelledError:break
        finally:
            if "client_redis" in locals():await client_redis.aclose()
            if client_postgres_pool:await client_postgres_pool.close();client_postgres_pool=None

#rabbitmq
async def logic_rabbitmq():
    import aio_pika, asyncio
    try:
        global client_postgres_pool
        client_rabbitmq,client_rabbitmq_consumer=await func_rabbitmq_client_read_consumer(config_rabbitmq_url,config_channel_name)
        if config_postgres_url:await _init_pool()
        print("rabbitmq consumer started", flush=True)
        local_queue = asyncio.Queue()
        async def aqmp_callback(message:aio_pika.IncomingMessage): await local_queue.put(message)
        await client_rabbitmq_consumer.consume(aqmp_callback)
        while True:
            payloads, messages = [], []
            for _ in range(config_rabbitmq_batch_limit):
                try:
                    msg = await asyncio.wait_for(local_queue.get(), timeout=config_rabbitmq_batch_timeout_ms/1000.0 if not payloads else 0.1)
                    messages.append(msg); payloads.append(json.loads(msg.body))
                except asyncio.TimeoutError: break
            if payloads:
                try:
                    await func_consumer_batch_logic(payloads,func_postgres_create,func_postgres_update,func_postgres_obj_serialize,client_postgres_pool)
                    for m in messages: await m.ack()
                    print(f"rabbitmq batch processed: {len(payloads)} msgs", flush=True)
                except Exception as e:
                    for m in messages: await m.nack(requeue=True)
                    raise e
    except asyncio.CancelledError:pass
    except Exception as e:print(f"rabbitmq error: {str(e)}", flush=True); await asyncio.sleep(5)
    finally:
        if "client_rabbitmq_consumer" in locals():await client_rabbitmq_consumer.channel.close()
        if "client_rabbitmq" in locals() and not client_rabbitmq.is_closed:await client_rabbitmq.close()
        if client_postgres_pool:await client_postgres_pool.close();client_postgres_pool=None

#kafka
async def logic_kafka():
    try:
        global client_postgres_pool
        client_kafka_consumer=await func_kafka_client_read_consumer(config_kafka_url,config_kafka_username,config_kafka_password,config_channel_name,config_kafka_group_id,config_kafka_is_auto_commit)
        if config_postgres_url:await _init_pool()
        print("kafka consumer started", flush=True)
        while True:
            batch=await client_kafka_consumer.getmany(timeout_ms=config_kafka_batch_timeout_ms, max_records=config_kafka_batch_limit)
            if not batch:continue
            payloads = []
            for tp, messages in batch.items():
                for message in messages: payloads.append(json.loads(message.value))
                if not config_kafka_is_auto_commit:await client_kafka_consumer.commit(tp)
            await func_consumer_batch_logic(payloads,func_postgres_create,func_postgres_update,func_postgres_obj_serialize,client_postgres_pool)
            print(f"kafka batch processed: {len(payloads)} msgs", flush=True)
    except asyncio.CancelledError:pass
    except Exception as e:print(f"kafka error: {str(e)}", flush=True)
    finally:
        if "client_kafka_consumer" in locals():await client_kafka_consumer.stop()
        if client_postgres_pool:await client_postgres_pool.close();client_postgres_pool=None

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
        elif mode=="celery":(celery.worker_main(argv=["worker","--loglevel=info"]) if celery else None)
        else:print(f"unknown mode: {mode}")
    except KeyboardInterrupt:sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)