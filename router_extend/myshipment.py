# import
from fastapi import APIRouter, HTTPException, Request

# router
router = APIRouter()

# api
@router.get("/myshipment/landed-cost-options")
async def func_api_myshipment_landed_cost_options(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict_types=True, header_fallback=False, reject_unknown=True, param_specs=[{"name": "kind", "type": "str", "required": True, "allowed": ["countries", "destinations", "currencies", "incoterms", "charges"]}, {"name": "effectiveDate", "type": "str"}])
    result = await app_state.func_myshipment_landed_cost_options(app_state=app_state, kind=oq['kind'], effective_date=oq.get('effectiveDate'))
    return {"status": 1, "message": result}

@router.get("/myshipment/landed-cost-units")
async def func_api_myshipment_landed_cost_units(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict_types=True, header_fallback=False, reject_unknown=True, param_specs=[{"name": "destination", "type": "str", "required": True}, {"name": "hsCode", "type": "str", "required": True}, {"name": "effectiveDate", "type": "str", "required": True}])
    result = await app_state.func_myshipment_landed_cost_units(app_state=app_state, destination=oq['destination'], hs_code=oq['hsCode'], effective_date=oq['effectiveDate'])
    return {"status": 1, "message": result}

@router.post("/myshipment/landed-cost-compare")
async def func_api_myshipment_landed_cost_compare(*, request: Request):
    app_state = request.app.state
    if len(await request.body()) > 64000: raise HTTPException(413, "Comparison request is too large.")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict_types=True, header_fallback=False, param_specs=None)
    result = await app_state.func_myshipment_landed_cost_compare(app_state=app_state, body=ob)
    return {"status": 1, "message": result}
