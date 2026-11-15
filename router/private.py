# import
from fastapi import APIRouter
from fastapi import Request

# router
router = APIRouter()

# api
@router.post("/private/send-email")
async def func_api_private_send_email(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_email_services}, {"name": "sender", "type": "str", "required": True}, {"name": "to", "type": "list", "required": True}, {"name": "subject", "type": "str", "required": True}, {"name": "text", "type": "str", "required": True}, {"name": "cc", "type": "list", "default": []}, {"name": "bcc", "type": "list", "default": []}, {"name": "reply_to", "type": "list", "default": []}])
    res = await app_state.func_email_send(app_state=app_state, service=ob["service"], sender=ob["sender"], to=ob["to"], subject=ob["subject"], text=ob["text"], cc=ob["cc"], bcc=ob["bcc"], reply_to=ob["reply_to"])
    return {"status": 1, "message": res}

@router.post("/private/blob-upload-file")
async def func_api_private_blob_upload_file(*, request: Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services}, {"name": "container", "type": "str", "required": True}, {"name": "file", "type": "file", "required": True}])
    res = await app_state.func_blob_upload_file(app_state=app_state, service=of["service"], container=of["container"], files=of["file"], user_id=request.state.user["id"])
    return {"status": 1, "message": res}

@router.post("/private/blob-upload-presigned")
async def func_api_private_blob_upload_presigned(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "service", "type": "str", "required": True, "allowed": app_state.config_blob_services}, {"name": "container", "type": "str", "required": True}, {"name": "count", "type": "int", "default": 1}])
    res = await app_state.func_blob_upload_url(app_state=app_state, service=oq["service"], container=oq["container"], count=oq["count"], user_id=request.state.user["id"])
    return {"status": 1, "message": res}

@router.get("/private/object-read")
async def func_api_private_object_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "relation", "type": "list", "default": []}, {"name": "filter", "type": "list", "default": []}, {"name": "group_column", "type": "str"}, {"name": "group_values", "type": "list"}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], relation=oq["relation"], scope="private", action="read")
    res = await app_state.func_postgres_read(config_page_offset_max=app_state.config_page_offset_max, client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"], order=oq["order"], column=oq["column"], relation=oq["relation"], config_column_read_blocked=app_state.config_column_read_blocked, after=oq.get("after"), page=oq.get("page"), group_column=oq.get("group_column"), group_values=oq.get("group_values"))
    return {"status": 1, "message": res}

@router.get("/private/object-read-export")
async def func_api_private_object_read_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "filter", "type": "list", "default": []}, {"name": "connection", "type": "str"}, {"name": "limit", "type": "int"}], strict=True, strict_types=True, reject_unknown=True)
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], relation=[], scope="private", action="read")
    generator = await app_state.func_postgres_read_export(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_export_limit=app_state.config_export_limit, table=oq["table"], filter=oq["filter"], order=oq["order"], column=oq["column"], config_column_read_blocked=app_state.config_column_read_blocked, limit=oq.get("limit"))
    return app_state.func_csv_response(content=generator, filename=f'{oq["table"]}.csv')

@router.put("/private/object-update")
async def func_api_private_object_update(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="write")
    app_state.func_check_table_not_users(table=oq["table"], api="/admin/user-update")
    app_state.func_check_table_write_blocked(app_state=app_state, table=oq["table"])
    obj_list = await app_state.func_extract_request_object_list(request=request)
    app_state.func_check_batch_limit(app_state=app_state, items=obj_list)
    app_state.func_validate_restricted_columns(app_state=app_state, obj_list=obj_list)
    app_state.func_check_table_column_exists(app_state=app_state, table=oq["table"], column="updated_by_id", purpose="update tracking")
    obj_list = app_state.func_attach_user_audit_fields(request=request, obj_list=obj_list, field="updated_by_id")
    return {"status": 1, "message": await app_state.func_postgres_update(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_column_regex=app_state.config_column_regex, table=oq["table"], obj_list=obj_list, created_by_id=None, client_postgres_conn=None)}

@router.post("/private/object-delete")
async def func_api_private_object_delete(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "ids", "type": "list:int", "required": True}])
    table, ids = ob["table"], ob["ids"]
    app_state.func_check_table_permission(app_state=app_state, table=table, scope="private", action="write")
    app_state.func_check_table_not_users(table=table, api="/admin/user-delete")
    app_state.func_check_table_write_blocked(app_state=app_state, table=table)
    app_state.func_check_batch_limit(app_state=app_state, items=ids)
    deleted_count = await app_state.func_postgres_delete(client_postgres=request.state.client_postgres, client_postgres_conn=None, cache_postgres_schema=request.state.cache_postgres_schema, table=table, ids=ids, created_by_id=None)
    return {"status": 1, "message": f"{deleted_count} ids deleted"}

@router.get("/private/user-read")
async def func_api_private_user_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "filter", "type": "list", "default": []}], reject_unknown=True)
    allowed = app_state.config_column_users_private_read
    blocked = [column for column in request.state.cache_postgres_schema.get("users", {}) if column not in allowed]
    res = await app_state.func_postgres_read(config_page_offset_max=app_state.config_page_offset_max, client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table="users", filter=oq["filter"], limit=oq["limit"], after=oq.get("after"), page=oq.get("page"), order=oq["order"], column=",".join(allowed), relation=[], config_column_read_blocked=[*blocked, "password"])
    return {"status": 1, "message": res}

@router.get("/private/table-column-groupby")
async def func_api_private_table_column_groupby(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "col", "type": "list", "required": True}, {"name": "agg", "type": "str", "allowed": ["count", "sum", "avg", "min", "max"], "default": "count"}, {"name": "agg_col", "type": "str", "default": "*"}, {"name": "limit", "type": "int", "default": 1000}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "default": "count desc"}, {"name": "filter", "type": "list", "default": []}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="read")
    res = await app_state.func_postgres_table_column_groupby_read(app_state=app_state, client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], after=oq.get("after"), page=oq.get("page"), agg=oq["agg"], agg_col=oq["agg_col"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}

@router.get("/private/table-column-distinct")
async def func_api_private_table_column_distinct(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "col", "type": "str", "required": True}, {"name": "limit", "type": "int", "default": 1000}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "allowed": ["item asc", "item desc", "asc", "desc"], "default": "item asc"}, {"name": "filter", "type": "list", "default": []}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="read")
    res = await app_state.func_postgres_table_column_distinct_read(app_state=app_state, client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], after=oq.get("after"), page=oq.get("page"), order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}
