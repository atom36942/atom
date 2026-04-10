def func_logic_data_validate(obj_list: list, api_role: str, config_column_blocked: list, immutable_fields: list = None) -> None:
    """Centralized validation for platform constraints, blocked columns, and immutable fields across one pass."""
    immutable_fields = immutable_fields or ["created_at"]
    for item in obj_list:
        if not isinstance(item, dict):
            continue
        for key in item:
            if key in immutable_fields:
                raise Exception(f"restricted update to immutable field: {key}")
            if api_role != "admin" and key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")

async def func_logic_obj_create(api_role: str, obj_query: dict[str, any], obj_body: dict[str, any], user_id: any, config_table_create_my: list, config_table_create_public: list, config_column_blocked: list, client_postgres_pool: any, func_postgres_obj_serialize: callable, config_table: dict, func_producer_logic: callable, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, config_channel_allowed: list, func_celery_producer: callable, func_kafka_producer: callable, func_rabbitmq_producer: callable, func_redis_producer: callable, func_postgres_create: callable, config_postgres_batch_limit: int = None) -> any:
    """Wrapper logic for object creation with role-based validation and optional queueing."""
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
    func_logic_data_validate(obj_list, api_role, config_column_blocked)
    if user_id:
        for item in obj_list:
            item["created_by_id"] = user_id
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_create", "params": {"execution_mode": obj_query.get("mode"), "table_name": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "config_table": config_table.get(obj_query.get("table"), {}).get("buffer")}}
        producer_obj = {"celery": {"client": client_celery_producer, "func": func_celery_producer}, "kafka": {"client": client_kafka_producer, "func": func_kafka_producer}, "rabbitmq": {"client": client_rabbitmq_producer, "func": func_rabbitmq_producer}, "redis": {"client": client_redis_producer, "func": func_redis_producer}, "config_channel_allowed": config_channel_allowed}
        return await func_producer_logic(obj_query.get("queue"), task_obj, producer_obj)
    return await func_postgres_create(client_postgres_pool, func_postgres_obj_serialize, obj_query.get("mode"), obj_query.get("table"), obj_list, obj_query.get("is_serialize"), config_table.get(obj_query.get("table"), {}).get("buffer"))

async def func_logic_obj_update(api_role: str, obj_query: dict, obj_body: dict, user_id: any, config_column_blocked: list, config_column_single_update: list, client_postgres_pool: any, func_postgres_obj_serialize: callable, func_producer_logic: callable, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, config_channel_allowed: list, func_celery_producer: callable, func_kafka_producer: callable, func_rabbitmq_producer: callable, func_redis_producer: callable, func_postgres_update: callable, func_otp_verify: callable, config_expiry_sec_otp: int, config_is_otp_users_update_admin: int = None, config_postgres_batch_limit: int = None) -> any:
    """Wrapper logic for object updates with owner validation, OTP checks, and optional queueing."""
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
    func_logic_data_validate(obj_list, api_role, config_column_blocked)
    async def func_logic_user_otp_check(item: dict) -> None:
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
            await func_logic_user_otp_check(item)
    elif api_role == "admin":
        created_by_id = None
        if obj_query.get("table") == "users" and (config_is_otp_users_update_admin or 0) == 1:
            await func_logic_user_otp_check(obj_list[0])
    if user_id:
        for item in obj_list:
            item["updated_by_id"] = user_id
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_update", "params": {"table_name": obj_query.get("table"), "obj_list": obj_list, "is_serialize": obj_query.get("is_serialize"), "created_by_id": created_by_id}}
        producer_obj = {"celery": {"client": client_celery_producer, "func": func_celery_producer}, "kafka": {"client": client_kafka_producer, "func": func_kafka_producer}, "rabbitmq": {"client": client_rabbitmq_producer, "func": func_rabbitmq_producer}, "redis": {"client": client_redis_producer, "func": func_redis_producer}, "config_channel_allowed": config_channel_allowed}
        return await func_producer_logic(obj_query.get("queue"), task_obj, producer_obj)
    return await func_postgres_update(client_postgres_pool, func_postgres_obj_serialize, obj_query.get("table"), obj_list, obj_query.get("is_serialize"), created_by_id)

async def func_producer_logic(queue: str, task_obj: dict, producer_obj: dict) -> any:
    """Ultra-standardized producer logic. Handles queue splitting, validation, and multi-tech dispatch in exactly 3 parameters."""
    if not queue:
        raise Exception("invalid queue format: queue name missing")
    if "_" not in queue:
        raise Exception(f"invalid queue format: '{queue}', expected tech_channel (e.g. redis_default)")
    tech, channel = queue.split("_", 1)
    if tech not in ["redis", "rabbitmq", "kafka", "celery"]:
        raise Exception(f"invalid queue technology: {tech}")
    if channel not in producer_obj.get("config_channel_allowed", []):
        raise Exception(f"unauthorized channel: {channel}, allowed: {producer_obj.get('config_channel_allowed')}")
    p = producer_obj.get(tech)
    if not p:
        raise Exception(f"producer not found for tech: {tech}")
    if tech == "celery":
        return p["func"](channel, task_obj["task_name"], p["client"], task_obj["params"])
    return await p["func"](channel, p["client"], task_obj)
