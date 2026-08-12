# packages
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, responses

# router
router = APIRouter()

# api
@router.get("/")
async def func_api_index(*, request: Request):
    return responses.FileResponse(request.app.state.config_root_html_path)

@router.get("/health")
async def func_api_index_health(*, request:Request):
    return {"status":1,"message":"ok"}

@router.get("/info")
async def func_api_index_info(*, request:Request):
    app_state = request.app.state
    return {
        "status": 1,
        "message": {
            "api_list": [route.path for route in request.app.routes if hasattr(route, "path")],
            "postgres_schema": app_state.cache_postgres_schema,
            "mapping": app_state.config_column_int_mapping,
            "dropdown": app_state.config_dropdown,
            "config": {
                "config_query_runner_read_limit": app_state.config_query_runner_read_limit,
                "config_query_runner_export_limit": app_state.config_query_runner_export_limit,
            },
        }
    }

@router.get("/openapi.json")
async def func_api_openapi_json(*, request:Request):
    app_state = request.app.state
    return app_state.cache_openapi
    
@router.websocket("/websocket")
async def func_api_websocket(*, websocket:WebSocket):
    await websocket.accept()
    app_state = websocket.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    try:
        while True:
            message = await websocket.receive_text()
            output = await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get("test", {}).get("buffer_limit", app_state.config_buffer_limit_default), mode="buffer", table="test", obj_list=[{"title":message}])
            await websocket.send_text(str(output))
    except WebSocketDisconnect:
        pass

@router.post("/pgweb")
async def func_api_pgweb(*, request: Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[])
    if ob.get("action") == "stream":
        pool = app_state.client_postgres_pgweb.get("pool")
        if not pool: return responses.JSONResponse({"status": 0, "message": "not_connected"}, status_code=400)
        params = {key: value for key, value in ob.items() if key != "action"}
        try: generator = await app_state.func_pgweb_stream(pool=pool, **params)
        except Exception as exc: return responses.JSONResponse({"status": 0, "message": str(exc)}, status_code=400)
        return responses.StreamingResponse(generator, media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": 'attachment; filename="query-result-all.csv"',
            "Cache-Control": "no-store",
        })
    return {"status": 1, "message": await app_state.func_pgweb(app_state=app_state, **ob)}
