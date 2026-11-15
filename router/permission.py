# import
from fastapi import APIRouter
from fastapi import Request

# router
router = APIRouter()

# api
@router.put("/permission/object-update")
async def func_api_permission_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="permission", action="write")
    app_state.func_check_table_not_users(table=oq["table"], api="/admin/user-update")
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
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ids", "type": "list:int", "required": True}])
    table, ids = ob["table"], ob["ids"]
    app_state.func_check_table_permission(app_state=app_state, table=table, scope="permission", action="write")
    app_state.func_check_table_not_users(table=table, api="/admin/user-delete")
    app_state.func_check_table_write_blocked(app_state=app_state, table=table)
    app_state.func_check_batch_limit(app_state=app_state, items=ids)
    deleted_count = await app_state.func_postgres_delete(client_postgres=request.state.client_postgres, client_postgres_conn=None, cache_postgres_schema=request.state.cache_postgres_schema, table=table, ids=ids, created_by_id=None)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}
