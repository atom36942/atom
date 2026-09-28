# import
from fastapi import APIRouter, HTTPException, Request

# router
router = APIRouter()

# api
@router.get("/wisetech/countries")
async def func_api_wisetech_countries(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict_types=True, header_fallback=False, reject_unknown=True, param_specs=[
        {"name": "moduleType", "type": "str", "allowed": ["ImportHS", "ExportHS"], "default": "ImportHS"},
        {"name": "effectiveDate", "type": "str", "default": None},
    ])
    result = await app_state.func_wisetech_countries(app_state=app_state, module_type=oq['moduleType'], effective_date=oq.get('effectiveDate'))
    return {"status": 1, "message": result}

@router.get("/wisetech/reference")
async def func_api_wisetech_reference(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict_types=True, header_fallback=False, reject_unknown=True, param_specs=[
        {"name": "kind", "type": "str", "required": True, "allowed": ["countries", "destinations", "currencies", "incoterms", "charges"]},
        {"name": "effectiveDate", "type": "str", "default": None},
    ])
    result = await app_state.func_wisetech_reference(app_state=app_state, kind=oq['kind'], effective_date=oq.get('effectiveDate'))
    return {"status": 1, "message": result}

@router.post("/wisetech/search")
async def func_api_wisetech_search(*, request: Request):
    app_state = request.app.state
    if len(await request.body()) > 64000: raise HTTPException(413, "Search request is too large.")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict_types=True, header_fallback=False, param_specs=None)
    result = await app_state.func_wisetech_search(app_state=app_state, body=ob)
    return {"status": 1, "message": result}
