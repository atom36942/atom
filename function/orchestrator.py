async def func_orchestrator_obj_create(*, api_role: str, obj_query: dict[str, any], obj_body: dict[str, any], user_id: any, config_table_create_my: list, config_table_create_public: list, config_column_blocked: list, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, config_table: dict, func_orchestrator_producer: callable, producer_obj: dict, func_postgres_create: callable, config_limit_obj_list: int, cache_postgres_buffer: dict) -> any:
    """Wrapper orchestration for object creation with role-based validation and optional queueing."""
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    if len(obj_list) > config_limit_obj_list:
        raise Exception("batch size exceeded")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
    if api_role not in ("my", "public", "admin"):
        raise Exception(f"role not allowed for creation: {api_role}")
    if api_role == "my" and obj_query.get("table") not in config_table_create_my:
        raise Exception(f"""table not allowed for role 'my': {obj_query.get("table")}, allowed: {config_table_create_my}""")
    if api_role == "public" and obj_query.get("table") not in config_table_create_public:
        raise Exception(f"""table not allowed for role 'public': {obj_query.get("table")}, allowed: {config_table_create_public}""")
    if api_role != "admin":
        for key in obj_list[0]:
            if key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    if user_id:
        for item in obj_list:
            item["created_by_id"] = user_id
    mode = obj_query.get("mode", "now")
    is_serialize = int(obj_query.get("is_serialize", 1))
    table = obj_query.get("table", "")
    buffer_limit = config_table.get(table, {}).get("buffer", 100)
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_create", "params": {"mode": mode, "table": table, "obj_list": obj_list, "is_serialize": is_serialize, "buffer_limit": buffer_limit}}
        return await func_orchestrator_producer(queue=obj_query.get("queue"), task_obj=task_obj, producer_obj=producer_obj)
    return await func_postgres_create(
        client_postgres_pool=client_postgres_pool,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=cache_postgres_schema,
        mode=mode,
        table=table,
        obj_list=obj_list,
        is_serialize=is_serialize,
        buffer_limit=buffer_limit,
        cache_postgres_buffer=cache_postgres_buffer
    )

async def func_orchestrator_obj_update(*, api_role: str, obj_query: dict, obj_body: dict, user_id: any, config_column_blocked: list, config_column_single_update: list, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, func_orchestrator_producer: callable, producer_obj: dict, func_postgres_update: callable, func_otp_verify: callable, config_expiry_sec_otp: int, config_is_otp_users_update_admin: int, config_limit_obj_list: int) -> any:
    """Wrapper orchestration for object updates with owner validation, OTP checks, and optional queueing."""
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    created_by_id = user_id
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    if len(obj_list) > config_limit_obj_list:
        raise Exception("batch size exceeded")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
        created_by_id = None
    if api_role not in ("my", "admin"):
        raise Exception(f"role not allowed for update: {api_role}")
    if api_role != "admin":
        for key in obj_list[0]:
            if key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    async def func_orchestrator_user_otp_check(item: dict) -> None:
        """Internal helper to enforce OTP verification and single-field update constraints for sensitive user data."""
        if any(key in item for key in ("email", "mobile")):
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            if len(item) != 2:
                raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await func_otp_verify(client_postgres_pool=client_postgres_pool, otp=obj_query.get("otp"), email=item.get("email"), mobile=item.get("mobile"), config_expiry_sec_otp=config_expiry_sec_otp)
    if api_role == "my":
        if obj_query.get("table") == "users":
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            item = obj_list[0]
            if str(item.get("id")) != str(user_id):
                raise Exception("ownership issue: cannot update other users")
            for key in item:
                if key in config_column_single_update:
                    if len(item) != 2:
                         raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await func_orchestrator_user_otp_check(item)
    elif api_role == "admin":
        created_by_id = None
        if obj_query.get("table") == "users" and (config_is_otp_users_update_admin or 0) == 1:
            await func_orchestrator_user_otp_check(obj_list[0])
    if user_id:
        for item in obj_list:
            item["updated_by_id"] = user_id
    is_serialize = int(obj_query.get("is_serialize", 1))
    is_return_ids = 0 # Explicitly set to 0 to fulfill mandatory parameter requirement
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_update", "params": {"table": obj_query.get("table"), "obj_list": obj_list, "is_serialize": is_serialize, "created_by_id": created_by_id, "is_return_ids": is_return_ids}}
        return await func_orchestrator_producer(queue=obj_query.get("queue"), task_obj=task_obj, producer_obj=producer_obj)
    return await func_postgres_update(
        client_postgres_pool=client_postgres_pool,
        func_postgres_serialize=func_postgres_serialize,
        cache_postgres_schema=cache_postgres_schema,
        table=obj_query.get("table", ""),
        obj_list=obj_list,
        is_serialize=is_serialize,
        created_by_id=created_by_id,
        is_return_ids=is_return_ids
    )

async def func_orchestrator_producer(*, queue: str, task_obj: dict, producer_obj: dict) -> any:
    """Ultra-standardized producer orchestration. Handles queue splitting, validation, and multi-tech dispatch in exactly 3-7 parameters."""
    import orjson
    if not queue:
        raise Exception("invalid queue format: queue name missing")
    if "_" not in queue:
        raise Exception(f"invalid queue format: '{queue}', expected tech_channel (e.g. redis_default)")
    tech, channel = queue.split("_", 1)
    if tech not in ["redis", "rabbitmq", "kafka", "celery"]:
        raise Exception(f"invalid queue technology: {tech}")
    config_channel_allowed = producer_obj.get("config_channel_allowed")
    client_celery_producer = producer_obj.get("client_celery_producer")
    client_kafka_producer = producer_obj.get("client_kafka_producer")
    client_rabbitmq_producer = producer_obj.get("client_rabbitmq_producer")
    client_redis_producer = producer_obj.get("client_redis_producer")
    if tech == "celery":
        if not client_celery_producer:
            raise Exception("celery producer not initialized")
        return client_celery_producer.send_task(task_obj["task_name"], kwargs=task_obj["params"], queue=channel).id
    elif tech == "rabbitmq":
        import aio_pika
        if not client_rabbitmq_producer:
            raise Exception("rabbitmq producer not initialized")
        return await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(task_obj), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel)
    elif tech == "kafka":
        if not client_kafka_producer:
            raise Exception("kafka producer not initialized")
        return await client_kafka_producer.send_and_wait(channel, orjson.dumps(task_obj))
    elif tech == "redis":
        if not client_redis_producer:
            raise Exception("redis producer not initialized")
        return await client_redis_producer.publish(channel, orjson.dumps(task_obj).decode("utf-8"))
    return None
