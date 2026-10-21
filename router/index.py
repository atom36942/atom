# import
from fastapi import APIRouter, Request, WebSocket, responses

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
            "api_list": [route.path for route in app_state.func_app_route_list(app=request.app) if hasattr(route, "path")],
            "config_column_int_mapping": app_state.config_column_int_mapping,
            "dropdown": app_state.config_dropdown,
        }
    }

@router.get("/openapi.json")
async def func_api_openapi_json(*, request:Request):
    app_state = request.app.state
    return app_state.cache_openapi
    
@router.websocket("/websocket-test-create")
async def func_api_websocket_test_create(*, websocket: WebSocket):
    await websocket.app.state.func_websocket_test_create(app_state=websocket.app.state, websocket=websocket)

@router.post("/pgweb")
async def func_api_pgweb(*, request: Request):
    app_state = request.app.state
    app_state.func_pgweb_request_check(request=request, config_is_pgweb_enabled=app_state.config_is_pgweb_enabled)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[])
    return await app_state.func_pgweb_response(app_state=app_state, ob=ob)
