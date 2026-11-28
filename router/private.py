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
    blocked = app_state.func_object_access(app_state=app_state, connection=request.state.connection, table=oq["table"], relation=oq["relation"], group="private", action="read")
    res = await app_state.func_postgres_read(config_page_offset_max=app_state.config_page_offset_max, client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=oq["table"], filter=oq["filter"], limit=oq["limit"], order=oq["order"], column=oq["column"], relation=oq["relation"], read_blocked=blocked, after=oq.get("after"), page=oq.get("page"), group_column=oq.get("group_column"), group_values=oq.get("group_values"))
    return {"status": 1, "message": res}

@router.get("/private/object-read-export")
async def func_api_private_object_read_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "column", "type": "str", "default": "*"}, {"name": "filter", "type": "list", "default": []}, {"name": "connection", "type": "str"}, {"name": "limit", "type": "int"}], strict=True, strict_types=True, reject_unknown=True)
    blocked = app_state.func_object_access(app_state=app_state, connection=request.state.connection, table=oq["table"], group="private", action="read")
    generator = await app_state.func_postgres_read_export(client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_export_limit=app_state.config_export_limit, table=oq["table"], filter=oq["filter"], order=oq["order"], column=oq["column"], read_blocked=blocked, limit=oq.get("limit"))
    return app_state.func_csv_response(content=generator, filename=f'{oq["table"]}.csv')

@router.get("/private/user-read")
async def func_api_private_user_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "limit", "type": "int", "default": app_state.config_sql_read_limit_default}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "default": "id desc"}, {"name": "filter", "type": "list", "default": []}], reject_unknown=True)
    allowed = [column for column in app_state.cache_users_access["private_read"] if column not in app_state.func_object_read_blocked(app_state=app_state, table="users", group="private")]
    blocked = [column for column in request.state.cache_postgres_schema.get("users", {}) if column not in allowed]
    res = await app_state.func_postgres_read(config_page_offset_max=app_state.config_page_offset_max, client_postgres=request.state.client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=request.state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table="users", filter=oq["filter"], limit=oq["limit"], after=oq.get("after"), page=oq.get("page"), order=oq["order"], column=",".join(allowed), relation=[], read_blocked=[*blocked, "password"])
    return {"status": 1, "message": res}

@router.get("/private/table-column-groupby")
async def func_api_private_table_column_groupby(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "col", "type": "list", "required": True}, {"name": "agg", "type": "str", "allowed": ["count", "sum", "avg", "min", "max"], "default": "count"}, {"name": "agg_col", "type": "str", "default": "*"}, {"name": "limit", "type": "int", "default": 1000}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "default": "count desc"}, {"name": "filter", "type": "list", "default": []}])
    blocked = app_state.func_object_access(app_state=app_state, connection=request.state.connection, table=oq["table"], group="private", action="read")
    res = await app_state.func_postgres_table_column_groupby_read(app_state=app_state, client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], after=oq.get("after"), page=oq.get("page"), agg=oq["agg"], agg_col=oq["agg_col"], order=oq["order"], filter=oq["filter"], read_blocked=blocked)
    return {"status": 1, "message": res}

@router.get("/private/table-column-distinct")
async def func_api_private_table_column_distinct(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", param_specs=[{"name": "table", "type": "str", "required": True}, {"name": "col", "type": "str", "required": True}, {"name": "limit", "type": "int", "default": 1000}, {"name": "after", "type": "str"}, {"name": "page", "type": "int", "minimum": 1}, {"name": "order", "type": "str", "allowed": ["item asc", "item desc", "asc", "desc"], "default": "item asc"}, {"name": "filter", "type": "list", "default": []}])
    blocked = app_state.func_object_access(app_state=app_state, connection=request.state.connection, table=oq["table"], group="private", action="read")
    res = await app_state.func_postgres_table_column_distinct_read(app_state=app_state, client_postgres=request.state.client_postgres, cache_postgres_schema=request.state.cache_postgres_schema, table=oq["table"], col=oq["col"], limit=oq["limit"], after=oq.get("after"), page=oq.get("page"), order=oq["order"], filter=oq["filter"], read_blocked=blocked)
    return {"status": 1, "message": res}
