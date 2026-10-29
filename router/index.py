# import
from fastapi import APIRouter
from fastapi import Request
from fastapi import responses

# router
router = APIRouter()

# api
@router.get("/")
async def func_api_index(*, request: Request):
    return responses.FileResponse(request.app.state.config_root_html_path)

@router.get("/static-pages")
async def func_api_index_static_pages(*, request: Request):
    app_state = request.app.state
    directories = ("static", "static_extend") if app_state.config_is_home_atom_listed else ("static_extend",)
    return {"status": 1, "message": app_state.func_app_static_page_list(directories=directories)}

@router.get("/page/{name}")
async def func_api_index_page(*, request: Request):
    app_state = request.app.state
    path = app_state.func_app_static_page_path(name=request.path_params["name"])
    if not path: raise app_state.func_api_error(message="page not found", status_code=404)
    return responses.FileResponse(path, headers={"Cache-Control": "no-cache"})    # revalidate every load, so a deployed change shows at once

@router.get("/health")
async def func_api_index_health(*, request:Request):
    return {"status":1,"message":"ok"}

@router.get("/info")
async def func_api_index_info(*, request:Request):
    app_state = request.app.state
    return {
        "status": 1,
        "message": {
            "atom_version": app_state.cache_atom_version,
            "api_list": [route.path for route in app_state.func_app_route_list(app=request.app) if hasattr(route, "path")],
            "config_column_int_mapping": app_state.config_column_int_mapping,
            "options": app_state.config_options,
        }
    }

@router.get("/openapi.json")
async def func_api_openapi_json(*, request:Request):
    app_state = request.app.state
    return app_state.cache_openapi
    
@router.post("/pgweb")
async def func_api_pgweb(*, request: Request):
    app_state = request.app.state
    app_state.func_pgweb_request_check(request=request, config_is_pgweb_enabled=app_state.config_is_pgweb_enabled)
    ob = await app_state.func_request_param_read(request=request, mode="body", param_specs=[])
    return await app_state.func_pgweb_response(app_state=app_state, ob=ob)
