# packages
from datetime import datetime, timezone
from fastapi import APIRouter, Request

# router
router = APIRouter()

# config
TABLE = "rates"
RATE_COLUMNS = {
    "carrier", "pol", "pod", "rate_validity",
    "freight_20ft_cntr_usd", "freight_40ft_cntr_usd",
    "manifest_shpt_usd", "seal_cntr_usd",
    "thc_20ft_cntr_inr", "thc_40ft_cntr_inr",
    "bl_fees_shpt_inr", "remarks"
}
RATE_UPDATE_COLUMNS = RATE_COLUMNS | {"deactivated_at"}

def _rate_obj_clean(*, obj: dict, is_update: int = 0) -> dict:
    allowed = RATE_UPDATE_COLUMNS if is_update else RATE_COLUMNS
    obj = dict(obj)
    if "pul" in obj:
        if "pol" not in obj: obj["pol"] = obj["pul"]
        obj.pop("pul")
    output = {key: value for key, value in obj.items() if key in allowed or (is_update and key == "id")}
    unknown = [key for key in obj if key not in output]
    if unknown: raise Exception(f"unknown rate column: {', '.join(unknown)}")
    if is_update:
        if "id" not in output: raise Exception("id required for rate update")
        if len(output) < 2: raise Exception("at least one rate field required for update")
    else:
        for key in ("pol", "pod"):
            if not output.get(key): raise Exception(f"{key} required")
    return output

def _rate_obj_list_clean(*, obj_list: list, is_update: int = 0) -> list:
    if not isinstance(obj_list, list) or not obj_list: raise Exception("obj_list required")
    if len(obj_list) > 1000: raise Exception("maximum 1000 rates allowed")
    return [_rate_obj_clean(obj=obj, is_update=is_update) for obj in obj_list]

# api
@router.get("/rates")
async def func_api_rates_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("filter", "list", 0, None, [])])
    ol = await app_state.func_postgres_read(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=TABLE, filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column="*", relation=[])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.post("/rates/upload")
async def func_api_rates_upload(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = _rate_obj_list_clean(obj_list=ob.get("obj_list", [ob]), is_update=0)
    obj_list = [dict(item, created_by_id=request.state.user["id"]) for item in obj_list]
    result = await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table=TABLE, obj_list=obj_list)
    return {"status": 1, "message": result}

@router.put("/rates/update")
async def func_api_rates_update(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = _rate_obj_list_clean(obj_list=ob.get("obj_list", [ob]), is_update=1)
    obj_list = [dict(item, updated_by_id=request.state.user["id"]) for item in obj_list]
    result = []
    obj_group = {}
    for obj in obj_list:
        obj_group.setdefault(tuple(sorted(obj.keys())), []).append(obj)
    for group_list in obj_group.values():
        group_result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=TABLE, obj_list=group_list, created_by_id=request.state.user["id"])
        result.extend(group_result if isinstance(group_result, list) else [])
    return {"status": 1, "message": result}

@router.post("/rates/delete")
async def func_api_rates_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("ids", "list:int", 1, None, None)])
    result = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=TABLE, ids=ob["ids"], created_by_id=request.state.user["id"])
    return {"status": 1, "message": result}

@router.put("/rates/deactivate")
async def func_api_rates_deactivate(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("ids", "list:int", 1, None, None)])
    obj_list = [{"id": rate_id, "deactivated_at": datetime.now(timezone.utc), "deactivated_by_id": request.state.user["id"], "updated_by_id": request.state.user["id"]} for rate_id in ob["ids"]]
    result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=TABLE, obj_list=obj_list, created_by_id=request.state.user["id"])
    return {"status": 1, "message": result}
