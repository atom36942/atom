async def func_orchestrator_obj_create(*, user_id: any, api_role: str, table: str, mode: str, is_serialize: int, queue: any, obj_list: list, config_table_create_my: list, config_table_create_public: list, config_column_blocked: list, config_table: dict, config_regex: dict, func_regex_check: callable, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, func_orchestrator_producer: callable, func_postgres_create: callable, client_postgres_pool: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, cache_postgres_buffer: dict, client_postgres_conn: any) -> any:
    """Wrapper orchestration for object creation with role-based validation and optional queueing. Uses explicit mandatory parameters."""
    limit_batch = 5000
    if not obj_list:
        raise Exception("object list required")
    if table == "users":
        await func_regex_check(config_regex=config_regex, obj_list=obj_list)
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    if table == "users":
        is_serialize = 1
    if api_role not in ("my", "public", "admin"):
        raise Exception(f"role not allowed for creation: {api_role}")
    if api_role == "my" and table not in config_table_create_my:
        raise Exception(f"table not allowed for role 'my': {table}, allowed: {config_table_create_my}")
    if api_role == "public" and table not in config_table_create_public:
        raise Exception(f"table not allowed for role 'public': {table}, allowed: {config_table_create_public}")
    if api_role != "admin":
        for key in obj_list[0]:
            if key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    if user_id:
        for item in obj_list:
            item["created_by_id"] = user_id
    buffer_limit = config_table.get(table, {}).get("buffer", 100)
    if queue:
        func_name = func_postgres_create.__name__
        results = []
        for i in range(0, len(obj_list), limit_batch):
            batch = obj_list[i : i + limit_batch]
            payload = {"mode": mode, "table": table, "obj_list": batch, "is_serialize": is_serialize, "buffer_limit": buffer_limit}
            res = await func_orchestrator_producer(queue=queue, func_name=func_name, payload=payload, client_celery_producer=client_celery_producer, client_kafka_producer=client_kafka_producer, client_rabbitmq_producer=client_rabbitmq_producer, client_redis_producer=client_redis_producer)
            results.append(res)
        return results if len(results) > 1 else results[0]
    return await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode=mode, table=table, obj_list=obj_list, is_serialize=is_serialize, buffer_limit=buffer_limit, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=client_postgres_conn)

async def func_orchestrator_obj_update(*, user_id: any, api_role: str, table: str, is_serialize: int, queue: any, otp: any, obj_list: list, config_is_otp_users_update_admin: int, config_column_blocked: list, config_column_single_update: list, config_regex: dict, func_regex_check: callable, func_otp_verify: callable, client_postgres_pool: any, client_password_hasher: any, config_expiry_sec_otp: int, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, func_orchestrator_producer: callable, func_postgres_update: callable, func_postgres_serialize: callable, cache_postgres_schema: dict, client_postgres_conn: any) -> any:
    """Wrapper orchestration for object updates with owner validation, OTP checks, and optional queueing. Uses explicit mandatory parameters."""
    limit_batch = 5000
    if not obj_list:
        raise Exception("object list required")
    if table == "users":
        await func_regex_check(config_regex=config_regex, obj_list=obj_list)
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    created_by_id = user_id
    if table == "users":
        is_serialize = 1
        created_by_id = None
    if api_role not in ("my", "admin"):
        raise Exception(f"role not allowed for update: {api_role}")
    if api_role != "admin":
        for key in obj_list[0]:
            if key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    async def _func_otp_check(item: dict) -> None:
        if any(key in item for key in ("email", "mobile")):
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            if len(item) != 2:
                raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await func_otp_verify(client_postgres_pool=client_postgres_pool, otp=otp, email=item.get("email"), mobile=item.get("mobile"), config_expiry_sec_otp=config_expiry_sec_otp)
        return None
    if api_role == "my":
        if table == "users":
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            item = obj_list[0]
            if str(item.get("id")) != str(user_id):
                raise Exception("ownership issue: cannot update other users")
            for key in item:
                if key in config_column_single_update:
                    if len(item) != 2:
                         raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await _func_otp_check(item)
    elif api_role == "admin":
        created_by_id = None
        if table == "users" and (config_is_otp_users_update_admin or 0) == 1:
            await _func_otp_check(obj_list[0])
    if user_id:
        for item in obj_list:
            item["updated_by_id"] = user_id
    is_return_ids = 0
    if queue:
        func_name = func_postgres_update.__name__
        results = []
        for i in range(0, len(obj_list), limit_batch):
            batch = obj_list[i : i + limit_batch]
            payload = {"table": table, "obj_list": batch, "is_serialize": is_serialize, "created_by_id": created_by_id, "is_return_ids": is_return_ids}
            res = await func_orchestrator_producer(queue=queue, func_name=func_name, payload=payload, client_celery_producer=client_celery_producer, client_kafka_producer=client_kafka_producer, client_rabbitmq_producer=client_rabbitmq_producer, client_redis_producer=client_redis_producer)
            results.append(res)
        return results if len(results) > 1 else results[0]
    return await func_postgres_update(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_serialize=is_serialize, created_by_id=created_by_id, is_return_ids=is_return_ids, client_postgres_conn=client_postgres_conn)

async def func_orchestrator_postgres_import(*, upload_file: any, mode: str, table: str, is_serialize: int, config_regex: dict, func_regex_check: callable, client_postgres_pool: any, client_password_hasher: any, cache_postgres_schema: dict, cache_postgres_buffer: dict, func_postgres_serialize: callable, func_postgres_create: callable, func_postgres_update: callable, func_postgres_delete: callable, func_api_file_to_chunks: callable) -> int:
    """Orchestrates atomic bulk PostgreSQL operations using a single transaction to ensure data integrity."""
    limit_chunk = 5000
    if mode == "update" and is_serialize == 0:
        raise Exception("is_serialize=1 is mandatory for update mode")
    count = 0
    first_chunk = True
    async with client_postgres_pool.acquire() as conn:
        async with conn.transaction():
            async for obj_list in func_api_file_to_chunks(upload_file=upload_file, chunk_size=limit_chunk):
                if first_chunk:
                    if mode in ("update", "delete") and "id" not in obj_list[0]:
                        raise Exception(f"CSV format error: Postgres {mode} requires 'id' column")
                    first_chunk = False
                if table == "users":
                    await func_regex_check(config_regex=config_regex, obj_list=obj_list)
                if mode == "create":
                    await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="now", table=table, obj_list=obj_list, is_serialize=is_serialize, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=conn)
                elif mode == "update":
                    await func_postgres_update(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_serialize=is_serialize, created_by_id=None, is_return_ids=0, client_postgres_conn=conn)
                elif mode == "delete":
                    await func_postgres_delete(client_postgres_pool=client_postgres_pool, table=table, ids=",".join(str(obj["id"]) for obj in obj_list), created_by_id=None, client_postgres_conn=conn)
                count += len(obj_list)
    return count

async def func_orchestrator_producer(*, queue: str, func_name: str, payload: dict, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any) -> any:
    """Ultra-standardized producer orchestration. Handles multi-tech dispatch with explicit clients."""
    import orjson
    if not queue: raise Exception("invalid queue format: queue missing")
    channel = func_name
    allowed_queue = ["redis", "rabbitmq", "kafka", "celery"]
    if queue not in allowed_queue: raise Exception(f"invalid queue: {queue}. allowed: {allowed_queue}")
    if queue == "celery":
        if not client_celery_producer: raise Exception("celery producer not initialized")
        return client_celery_producer.send_task(func_name, kwargs=payload, queue=channel).id
    elif queue == "rabbitmq":
        import aio_pika
        if not client_rabbitmq_producer: raise Exception("rabbitmq producer not initialized")
        return await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(payload), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel)
    elif queue == "kafka":
        if not client_kafka_producer: raise Exception("kafka producer not initialized")
        return await client_kafka_producer.send_and_wait(channel, orjson.dumps(payload))
    elif queue == "redis":
        if not client_redis_producer: raise Exception("redis producer not initialized")
        return await client_redis_producer.publish(channel, orjson.dumps(payload).decode("utf-8"))
    return None
