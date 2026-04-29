async def func_orchestrator_obj_create(*, user_id: any, api_role: str, obj_query: dict, obj_body: dict, config_table_create_my: list, config_table_create_public: list, config_column_blocked: list, config_table: dict, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, func_orchestrator_producer: callable, func_postgres_create: callable, client_postgres_pool: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, cache_postgres_buffer: dict) -> any:
    """Wrapper orchestration for object creation with role-based validation and optional queueing. Uses atomic parameters for all dependencies."""
    limit_batch = 5000
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
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
        func_name = func_postgres_create.__name__
        results = []
        for i in range(0, len(obj_list), limit_batch):
            batch = obj_list[i : i + limit_batch]
            payload = {"mode": mode, "table": table, "obj_list": batch, "is_serialize": is_serialize, "buffer_limit": buffer_limit}
            res = await func_orchestrator_producer(queue=obj_query.get("queue"), func_name=func_name, payload=payload, client_celery_producer=client_celery_producer, client_kafka_producer=client_kafka_producer, client_rabbitmq_producer=client_rabbitmq_producer, client_redis_producer=client_redis_producer)
            results.append(res)
        return results if len(results) > 1 else results[0]
    return await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode=mode, table=table, obj_list=obj_list, is_serialize=is_serialize, buffer_limit=buffer_limit, cache_postgres_buffer=cache_postgres_buffer)

async def func_orchestrator_obj_update(*, user_id: any, api_role: str, obj_query: dict, obj_body: dict, config_is_otp_users_update_admin: int, config_column_blocked: list, config_column_single_update: list, func_otp_verify: callable, client_postgres_pool: any, client_password_hasher: any, config_expiry_sec_otp: int, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, func_orchestrator_producer: callable, func_postgres_update: callable, func_postgres_serialize: callable, cache_postgres_schema: dict) -> any:
    """Wrapper orchestration for object updates with owner validation, OTP checks, and optional queueing. Uses atomic parameters."""
    limit_batch = 5000
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    created_by_id = user_id
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
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
            await func_otp_verify(client_postgres_pool=client_postgres_pool, otp=obj_query.get("otp"), email=item.get("email"), mobile=item.get("mobile"), config_expiry_sec_otp=config_expiry_sec_otp)
        return None
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
            await _func_otp_check(item)
    elif api_role == "admin":
        created_by_id = None
        if obj_query.get("table") == "users" and (config_is_otp_users_update_admin or 0) == 1:
            await _func_otp_check(obj_list[0])
    if user_id:
        for item in obj_list:
            item["updated_by_id"] = user_id
    is_serialize = int(obj_query.get("is_serialize", 1))
    is_return_ids = 0
    if obj_query.get("queue"):
        func_name = func_postgres_update.__name__
        results = []
        for i in range(0, len(obj_list), limit_batch):
            batch = obj_list[i : i + limit_batch]
            payload = {"table": obj_query.get("table"), "obj_list": batch, "is_serialize": is_serialize, "created_by_id": created_by_id, "is_return_ids": is_return_ids}
            res = await func_orchestrator_producer(queue=obj_query.get("queue"), func_name=func_name, payload=payload, client_celery_producer=client_celery_producer, client_kafka_producer=client_kafka_producer, client_rabbitmq_producer=client_rabbitmq_producer, client_redis_producer=client_redis_producer)
            results.append(res)
        return results if len(results) > 1 else results[0]
    return await func_postgres_update(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=obj_query.get("table", ""), obj_list=obj_list, is_serialize=is_serialize, created_by_id=created_by_id, is_return_ids=is_return_ids)
