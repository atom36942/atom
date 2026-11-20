# import
from fastapi import APIRouter
from fastapi import Request

# router
router = APIRouter()

# api
# the middleware checks every /permission/object-* call: the user holds config_permission_table[table][action] for the route's action
@router.post("/permission/object-create")
async def func_api_permission_object_create(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}])
    app_state.func_check_table_write_blocked(app_state=app_state, table=oq["table"])
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="created_by_id", purpose="ownership tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="created_by_id")
    return {"status": 1, "message": await app_state.func_postgres_create(client_postgres=request.state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, buffer_postgres=app_state.buffer_postgres_create, buffer_rows_max=app_state.config_buffer_rows_max, buffer_full_mode="reject", config_column_regex=app_state.config_column_regex, buffer_limit=app_state.func_buffer_limit(app_state=app_state, table=oq["table"]), mode="now", table=oq["table"], obj_list=obj_list)}

@router.get("/permission/object-read")
async def func_api_permission_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "filter", "type": "list", "default": []}, {"name": "group_column", "type": "str"}, {"name": "group_values", "type": "list"}], reject_unknown=True)
    res = await app_state.func_postgres_read(config_page_offset_max=app_state.config_page_offset_max, client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"], order=oq["order"], column=oq["column"], relation=[], config_column_read_blocked=app_state.config_column_read_blocked, after=oq.get("after"), page=oq.get("page"), group_column=oq.get("group_column"), group_values=oq.get("group_values"))
    return {"status": 1, "message": res}

@router.get("/permission/object-read-export")
async def func_api_permission_object_read_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "filter", "type": "list", "default": []}, {"name": "limit", "type": "int"}], strict=True, strict_types=True, reject_unknown=True)
    generator = await app_state.func_postgres_read_export(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_export_limit=app_state.config_export_limit, table=oq["table"], filter=oq["filter"], order=oq["order"], column=oq["column"], config_column_read_blocked=app_state.config_column_read_blocked, limit=oq.get("limit"))
    return app_state.func_csv_response(content=generator, filename=f'{oq["table"]}.csv')

@router.put("/permission/object-update")
async def func_api_permission_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}])
    app_state.func_check_table_write_blocked(app_state=app_state, table=oq["table"])
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="updated_by_id", purpose="update tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="updated_by_id")
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_column_regex=app_state.config_column_regex, table=oq["table"], obj_list=obj_list, created_by_id=None, client_postgres_conn=None)}

@router.post("/permission/object-delete")
async def func_api_permission_object_delete(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}])
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "ids", "type": "list:int", "required": True}])
    app_state.func_check_table_write_blocked(app_state=app_state, table=oq["table"])
    app_state.func_check_batch_limit(app_state=app_state, items=ob["ids"])
    deleted_count = await app_state.func_postgres_delete(client_postgres=request.state.client_postgres, client_postgres_conn=None, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], ids=ob["ids"], created_by_id=None)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.post("/permission/user-create")
async def func_api_permission_user_create(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "username", "type": "str", "required": True}, {"name": "password", "type": "str", "required": True}, {"name": "role", "type": "int", "required": True}], strict_types=True)    # other users columns pass through to func_user_create, which refuses blocked ones
    app_state.func_check_permission_user_role(app_state=app_state, role=ob["role"])
    user_id = await app_state.func_user_create(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_column_regex=app_state.config_column_regex, role=ob["role"], username=ob["username"], password=ob["password"], created_by_id=request.state.user["id"], columns={k: v for k, v in ob.items() if k not in ("role", "username", "password")}, columns_blocked=[*(app_state.config_permission_user_column_blocked or []), *(app_state.config_column_users_blocked or [])])
    return {"status": 1, "message": {"id": user_id}}

@router.put("/permission/user-update")
async def func_api_permission_user_update(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "id", "type": "int", "required": True}], strict_types=True)
    columns = [key for key in ob if key != "id"]
    if not columns: raise app_state.func_api_error(message="send id and the columns to change", status_code=400)
    if refused := [column for column in columns if column in (app_state.config_permission_user_column_blocked or []) or column in (app_state.config_column_users_blocked or [])]: raise app_state.func_api_error(message=f"{', '.join(refused)} cannot be updated here", status_code=400)
    user = await app_state.func_user_read_single(client_postgres=request.state.client_postgres, user_id=ob["id"])
    app_state.func_check_permission_user_role(app_state=app_state, role=user["role"])
    obj = {**ob, **({"deactivated_by_id": request.state.user["id"] if ob["deactivated_at"] is not None else None} if "deactivated_at" in ob else {})}
    await app_state.func_user_update(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_column_regex=app_state.config_column_regex, obj_list=[obj], updated_by_id=request.state.user["id"], is_otp_required=False, config_column_single_update=app_state.config_column_single_update, config_column_users_blocked=app_state.config_column_users_blocked, config_column_users_my_blocked=app_state.config_column_users_my_blocked, config_otp_expiry_sec=app_state.config_otp_expiry_sec, config_otp_static=app_state.config_otp_static, config_otp_max_attempt=app_state.config_otp_max_attempt)
    return {"status": 1, "message": "user updated"}
