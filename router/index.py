# packages
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, responses

# router
router = APIRouter()

# api
@router.get("/")
async def func_api_index():
    return responses.FileResponse("static/api.html")

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
            "mapping": app_state.config_column_int_mapping
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
    try:
        while True:
            message = await websocket.receive_text()
            output = await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_table.get("test", {}).get("buffer_limit", app_state.config_buffer_limit_default), mode="buffer", table="test", obj_list=[{"title":message}])
            await websocket.send_text(str(output))
    except WebSocketDisconnect:
        pass
