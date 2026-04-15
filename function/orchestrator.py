async def func_orchestrator_obj_create(*, request: any, api_role: str, obj_query: dict, obj_body: dict) -> any:
    """Wrapper orchestration for object creation with role-based validation and optional queueing."""
    st = request.app.state
    user_id = request.state.user.get("id") if getattr(request.state, "user", None) else None
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
    if api_role == "my" and obj_query.get("table") not in st.config_table_create_my:
        raise Exception(f"""table not allowed for role 'my': {obj_query.get("table")}, allowed: {st.config_table_create_my}""")
    if api_role == "public" and obj_query.get("table") not in st.config_table_create_public:
        raise Exception(f"""table not allowed for role 'public': {obj_query.get("table")}, allowed: {st.config_table_create_public}""")
    if api_role != "admin":
        for key in obj_list[0]:
            if key in st.config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    if user_id:
        for item in obj_list:
            item["created_by_id"] = user_id
    mode = obj_query.get("mode", "now")
    is_serialize = int(obj_query.get("is_serialize", 1))
    table = obj_query.get("table", "")
    buffer_limit = st.config_table.get(table, {}).get("buffer", 100)
    if obj_query.get("queue"):
        task_obj = {"task_name": "func_postgres_create", "params": {"mode": mode, "table": table, "obj_list": obj_list, "is_serialize": is_serialize, "buffer_limit": buffer_limit}}
        producer_obj = {"config_channel_allowed": st.config_channel_allowed, "client_celery_producer": st.client_celery_producer, "client_kafka_producer": st.client_kafka_producer, "client_rabbitmq_producer": st.client_rabbitmq_producer, "client_redis_producer": st.client_redis_producer}
        return await st.func_orchestrator_producer(queue=obj_query.get("queue"), task_obj=task_obj, producer_obj=producer_obj)
    return await st.func_postgres_create(
        client_postgres_pool=st.client_postgres_pool,
        func_postgres_serialize=st.func_postgres_serialize,
        cache_postgres_schema=st.cache_postgres_schema,
        mode=mode,
        table=table,
        obj_list=obj_list,
        is_serialize=is_serialize,
        buffer_limit=buffer_limit,
        cache_postgres_buffer=st.cache_postgres_buffer
    )

async def func_orchestrator_obj_update(*, request: any, api_role: str, obj_query: dict, obj_body: dict) -> any:
    """Wrapper orchestration for object updates with owner validation, OTP checks, and optional queueing."""
    st = request.app.state
    user_id = request.state.user.get("id")
    config_is_otp_users_update_admin = st.config_is_otp_users_update_admin if api_role == "admin" else 0
    if not obj_body:
        raise Exception("body required")
    obj_list = obj_body.get("obj_list", [obj_body])
    created_by_id = user_id
    if not obj_list:
        raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]:
        raise Exception("object data required")
    if len(obj_list) > st.config_limit_obj_list:
        raise Exception("batch size exceeded")
    if obj_query.get("table") == "users":
        obj_query["is_serialize"] = 1
        created_by_id = None
    if api_role not in ("my", "admin"):
        raise Exception(f"role not allowed for update: {api_role}")
    if api_role != "admin":
        for key in obj_list[0]:
            if key in st.config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")
    async def func_orchestrator_user_otp_check(item: dict) -> None:
        """Internal helper to enforce OTP verification and single-field update constraints for sensitive user data."""
        if any(key in item for key in ("email", "mobile")):
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            if len(item) != 2:
                raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await st.func_otp_verify(client_postgres_pool=st.client_postgres_pool, otp=obj_query.get("otp"), email=item.get("email"), mobile=item.get("mobile"), config_expiry_sec_otp=st.config_expiry_sec_otp)
        return None
    if api_role == "my":
        if obj_query.get("table") == "users":
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            item = obj_list[0]
            if str(item.get("id")) != str(user_id):
                raise Exception("ownership issue: cannot update other users")
            for key in item:
                if key in st.config_column_single_update:
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
        producer_obj = {"config_channel_allowed": st.config_channel_allowed, "client_celery_producer": st.client_celery_producer, "client_kafka_producer": st.client_kafka_producer, "client_rabbitmq_producer": st.client_rabbitmq_producer, "client_redis_producer": st.client_redis_producer}
        return await st.func_orchestrator_producer(queue=obj_query.get("queue"), task_obj=task_obj, producer_obj=producer_obj)
    return await st.func_postgres_update(
        client_postgres_pool=st.client_postgres_pool,
        func_postgres_serialize=st.func_postgres_serialize,
        cache_postgres_schema=st.cache_postgres_schema,
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

async def func_orchestrator_admin_sync(*, request: any) -> None:
    """Orchestrates the full system synchronization for administration by passing the state object directly."""
    st, app_routes = request.app.state, request.app.routes
    await st.func_postgres_schema_init(client_postgres_pool=st.client_postgres_pool, config_postgres=st.config_postgres)
    await st.func_postgres_create(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, mode="flush", table="", obj_list=[], is_serialize=0, buffer_limit=0, cache_postgres_buffer=st.cache_postgres_buffer)
    st.cache_postgres_schema = await st.func_postgres_schema_read(client_postgres_pool=st.client_postgres_pool) if st.client_postgres_pool else {}
    st.cache_postgres_schema_tables = list(st.cache_postgres_schema.keys())
    st.cache_postgres_schema_columns = sorted(list(set(col for table in st.cache_postgres_schema.values() for col in table.keys())))
    st.cache_users_role = await st.func_postgres_map_column(client_postgres_pool=st.client_postgres_pool, config_sql=st.config_sql.get("cache_users_role")) if st.client_postgres_pool else {}
    st.cache_users_is_active = await st.func_postgres_map_column(client_postgres_pool=st.client_postgres_pool, config_sql=st.config_sql.get("cache_users_is_active")) if st.client_postgres_pool else {}
    await st.func_postgres_clean(client_postgres_pool=st.client_postgres_pool, config_table=st.config_table)
    st.cache_openapi = st.func_openapi_spec_generate(app_routes=app_routes, config_api_roles_auth=st.config_api_roles_auth, app_state=st)
    return None


