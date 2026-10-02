# import
from fastapi import APIRouter, Request

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
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "relation", "type": "list", "default": []}, {"name": "filter", "type": "list", "default": []}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], relation=oq["relation"], scope="private", action="read")
    ol = await app_state.func_postgres_read(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"], page=oq["page"], order=oq["order"], column=oq["column"], relation=oq["relation"], config_column_read_blocked=app_state.config_column_read_blocked)
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/private/users-list")
async def func_api_private_users_list(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "page", "type": "int", "default": 1}])
    role = int(request.state.user["role"])
    ol = await app_state.func_postgres_read(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table="users", filter=[f"role = {role}"], limit=oq["limit"], page=oq["page"], order="username asc", column="id,username", relation=[], config_column_read_blocked=app_state.config_column_read_blocked)
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/private/table-column-groupby")
async def func_api_private_table_column_groupby(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "col", "type": "list", "required": True}, {"name": "agg", "type": "str", "allowed": ["count", "sum", "avg", "min", "max"], "default": "count"}, {"name": "agg_col", "type": "str", "default": "*"}, {"name": "limit", "type": "int", "default": 1000}, {"name": "page", "type": "int", "default": 1}, {"name": "order", "type": "str", "default": "count desc"}, {"name": "filter", "type": "list", "default": []}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="read")
    res = await app_state.func_postgres_table_column_groupby_read(app_state=app_state, client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], agg=oq["agg"], agg_col=oq["agg_col"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}

@router.get("/private/table-column-distinct")
async def func_api_private_table_column_distinct(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "col", "type": "str", "required": True}, {"name": "limit", "type": "int", "default": 1000}, {"name": "page", "type": "int", "default": 1}, {"name": "order", "type": "str", "allowed": ["item asc", "item desc", "asc", "desc"], "default": "item asc"}, {"name": "filter", "type": "list", "default": []}])
    app_state.func_check_table_permission(app_state=app_state, table=oq["table"], scope="private", action="read")
    res = await app_state.func_postgres_table_column_distinct_read(app_state=app_state, client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], page=oq["page"], order=oq["order"], filter=oq["filter"])
    return {"status": 1, "message": res}
