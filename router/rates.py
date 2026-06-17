from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.post("/rates/my-create")
async def func_api_rates_create(*, request: Request):
    app_state = request.app.state
    table = "rates"
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if not isinstance(obj_list, list) or not obj_list: raise Exception("obj_list required")
    if len(obj_list) > 5000: raise Exception("maximum 5000 rates allowed")
    if any(not isinstance(obj, dict) for obj in obj_list): raise Exception("object data invalid")
    obj_list = [dict(obj) for obj in obj_list]
    for obj in obj_list:
        obj.pop("id", None)
        obj.pop("created_by_id", None)
        obj.pop("updated_by_id", None)
        obj.pop("deactivated_by_id", None)
        obj["created_by_id"] = request.state.user["id"]
    result = await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table=table, obj_list=obj_list)
    return {"status": 1, "message": result}

@router.put("/rates/my-update")
async def func_api_rates_update(*, request: Request):
    app_state = request.app.state
    table = "rates"
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if not isinstance(obj_list, list) or not obj_list: raise Exception("obj_list required")
    if len(obj_list) > 5000: raise Exception("maximum 5000 rates allowed")
    if any(not isinstance(obj, dict) for obj in obj_list): raise Exception("object data invalid")
    obj_list = [dict(obj) for obj in obj_list]
    for obj in obj_list:
        if "id" not in obj: raise Exception("id required for rate update")
        if len(obj) < 2: raise Exception("at least one rate field required for update")
        obj.pop("created_by_id", None)
        obj.pop("deactivated_by_id", None)
        if "deactivated_at" in obj and obj.get("deactivated_at") is not None: obj["deactivated_by_id"] = request.state.user["id"]
        obj["updated_by_id"] = request.state.user["id"]
    result = []
    obj_group = {}
    for obj in obj_list:
        obj_group.setdefault(tuple(sorted(obj.keys())), []).append(obj)
    for group_list in obj_group.values():
        group_result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=table, obj_list=group_list, created_by_id=request.state.user["id"])
        result.extend(group_result if isinstance(group_result, list) else [])
    return {"status": 1, "message": result}
    
@router.post("/rates/my-delete")
async def func_api_rates_delete(*, request: Request):
    app_state = request.app.state
    table = "rates"
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("ids", "list:int", 1, None, None)])
    result = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=table, ids=ob["ids"], created_by_id=request.state.user["id"])
    return {"status": 1, "message": result}
    
@router.get("/rates")
async def func_api_rates_read(*, request: Request):
    app_state = request.app.state
    table = "rates"
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("filter", "list", 0, None, [])])
    ol = await app_state.func_postgres_read(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=table, filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column="*", relation=[])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}
