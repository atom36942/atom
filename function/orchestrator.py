async def func_orchestrator_obj_create(api_role: str, obj_query: dict[str, any], obj_body: dict[str, any], user_id: any, config_table_create_my: list, config_table_create_public: list, config_column_blocked: list, client_postgres_pool: any, func_postgres_serialize: callable, config_table: dict, func_orchestrator_producer: callable, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, config_channel_allowed: list, func_postgres_object_create: callable, config_postgres_batch_limit: int = None) -> any:
    """Wrapper orchestration for object creation with role-based validation and optional queueing."""
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    config_postgres_batch_limit = config_postgres_batch_limit or 1000
    if len(obj_list) > config_postgres_batch_limit:
        raise Exception("batch size exceeded")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
    if api_role not in ("my", "public", "admin"):
        raise Exception(f"role not allowed for creation: {api_role}")
    if api_role == "my" and obj_query.get("table") not in config_table_create_my:
        raise Exception(f"""table not allowed for role 'my': {obj_query.get("table")}, allowed: {config_table_create_my}""")
    if api_role == "public" and obj_query.get("table") not in config_table_create_public:
        raise Exception(f"""table not allowed for role 'public': {obj_query.get("table")}, allowed: {config_table_create_public}""")
    for item in obj_list:
        if not isinstance(item, dict):
            continue
        for key in item:
            if key == "created_at":
                raise Exception(f"restricted update to immutable field: {key}")
            if api_role != "admin" and key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    if user_id:
        for item in obj_list:
            item["created_by_id"] = user_id
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_object_create", "params": {"execution_mode": obj_query.get("mode"), "table_name": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "config_table": config_table.get(obj_query.get("table"), {}).get("buffer")}}
        return await func_orchestrator_producer(obj_query.get("queue"), task_obj, config_channel_allowed, client_celery_producer, client_kafka_producer, client_rabbitmq_producer, client_redis_producer)
    return await func_postgres_object_create(client_postgres_pool, func_postgres_serialize, obj_query.get("mode"), obj_query.get("table"), obj_list, obj_query.get("is_serialize"), config_table.get(obj_query.get("table"), {}).get("buffer"))

async def func_orchestrator_obj_update(api_role: str, obj_query: dict, obj_body: dict, user_id: any, config_column_blocked: list, config_column_single_update: list, client_postgres_pool: any, func_postgres_serialize: callable, func_orchestrator_producer: callable, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, config_channel_allowed: list, func_postgres_object_update: callable, func_otp_verify: callable, config_expiry_sec_otp: int, config_is_otp_users_update_admin: int = None, config_postgres_batch_limit: int = None) -> any:
    """Wrapper orchestration for object updates with owner validation, OTP checks, and optional queueing."""
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    created_by_id = user_id
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    config_postgres_batch_limit = config_postgres_batch_limit or 1000
    if len(obj_list) > config_postgres_batch_limit:
        raise Exception("batch size exceeded")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
        created_by_id = None
    if api_role not in ("my", "admin"):
        raise Exception(f"role not allowed for update: {api_role}")
    for item in obj_list:
        if not isinstance(item, dict):
            continue
        for key in item:
            if key == "created_at":
                raise Exception(f"restricted update to immutable field: {key}")
            if api_role != "admin" and key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    async def func_orchestrator_user_otp_check(item: dict) -> None:
        """Internal helper to enforce OTP verification and single-field update constraints for sensitive user data."""
        if any(key in item for key in ("email", "mobile")):
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            if len(item) != 2:
                raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await func_otp_verify(client_postgres_pool, obj_query.get("otp"), item.get("email"), item.get("mobile"), config_expiry_sec_otp)
    if api_role == "my":
        item = obj_list[0]
        if obj_query.get("table") == "users":
            if str(item.get("id")) != str(user_id):
                raise Exception("ownership issue: cannot update other users")
            await func_orchestrator_user_otp_check(item)
    elif api_role == "admin":
        created_by_id = None
        if obj_query.get("table") == "users" and (config_is_otp_users_update_admin or 0) == 1:
            await func_orchestrator_user_otp_check(obj_list[0])
    if user_id:
        for item in obj_list:
            item["updated_by_id"] = user_id
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_object_update", "params": {"table_name": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "created_by_id": created_by_id}}
        return await func_orchestrator_producer(obj_query.get("queue"), task_obj, config_channel_allowed, client_celery_producer, client_kafka_producer, client_rabbitmq_producer, client_redis_producer)
    return await func_postgres_object_update(client_postgres_pool, func_postgres_serialize, obj_query.get("table"), obj_list, obj_query.get("is_serialize"), created_by_id)

async def func_orchestrator_producer(queue: str, task_obj: dict, config_channel_allowed: list, client_celery_producer: any = None, client_kafka_producer: any = None, client_rabbitmq_producer: any = None, client_redis_producer: any = None) -> any:
    """Ultra-standardized producer orchestration. Handles queue splitting, validation, and multi-tech dispatch in exactly 3-7 parameters."""
    import orjson
    if not queue:
        raise Exception("invalid queue format: queue name missing")
    if "_" not in queue:
        raise Exception(f"invalid queue format: '{queue}', expected tech_channel (e.g. redis_default)")
    tech, channel = queue.split("_", 1)
    if tech not in ["redis", "rabbitmq", "kafka", "celery"]:
        raise Exception(f"invalid queue technology: {tech}")
    if channel not in (config_channel_allowed or []):
        raise Exception(f"unauthorized channel: {channel}, allowed: {config_channel_allowed}")
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
