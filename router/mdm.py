# import
from fastapi import APIRouter, Request, HTTPException

# router
router = APIRouter()

# api
@router.get("/mdm/read")
async def func_api_mdm_read(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, strict_types=True, header_fallback=False, reject_unknown=True, param_specs=[
        {"name": "kind", "type": "str", "required": True, "allowed": ["overview", "groups", "detail", "candidates", "cw-search", "approved", "audit", "matches"]},
        {"name": "source", "type": "str", "allowed": ["CW", "SAP"], "default": "CW"},
        {"name": "page", "type": "int", "default": 1, "minimum": 1, "maximum": 100000},
        {"name": "q", "type": "str", "default": ""},
        {"name": "mode", "type": "str", "allowed": ["duplicates", "all", "exceptions"], "default": "duplicates"},
        {"name": "pending", "type": "bool", "default": True},
        {"name": "ids", "type": "str", "default": ""},
        {"name": "id", "type": "int", "minimum": 1, "maximum": 9223372036854775807},
    ])
    client_postgres, _, _ = app_state.func_postgres_db_select(app_state=app_state, db="mdm")
    res = await app_state.func_mdm_read(app_state=app_state, pool=client_postgres, kind=oq["kind"], params=oq)
    return {"status": 1, "message": res}

@router.post("/mdm/review")
async def func_api_mdm_review(*, request: Request):
    app_state = request.app.state
    if len(await request.body()) > 2_000_000:
        raise HTTPException(status_code=413, detail="Review request is too large.")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, strict_types=True, header_fallback=False, reject_unknown=True, param_specs=[
        {"name": "request_id", "type": "str", "required": True},
        {"name": "source", "type": "str", "required": True, "allowed": ["CW", "SAP"]},
        {"name": "run_id", "type": "str", "required": True},
        {"name": "action", "type": "str", "required": True, "allowed": ["approve", "split", "keep_separate", "reject_suggestion", "confirm_existing", "approve_new", "reject_match", "correct", "record_success", "record_failure"]},
        {"name": "reason", "type": "str", "required": True, "min_length": 3, "max_length": 4000},
        {"name": "master_ids", "type": "list", "default": [], "max_length": 100},
        {"name": "parts", "type": "list", "default": [], "max_length": 2000},
        {"name": "approved_id", "type": "int", "minimum": 1, "maximum": 9223372036854775807},
        {"name": "version", "type": "int", "minimum": 1, "maximum": 9223372036854775807},
        {"name": "cw_code", "type": "str"},
        {"name": "comparison_id", "type": "str"},
        {"name": "confirmed", "type": "bool", "default": False},
        {"name": "organization_name", "type": "str"},
        {"name": "addresses", "type": "list"},
    ])
    client_postgres, _, _ = app_state.func_postgres_db_select(app_state=app_state, db="mdm")
    res = await app_state.func_mdm_write(app_state=app_state, pool=client_postgres, actor=request.state.user, body=ob)
    return {"status": 1, "message": res}

@router.get("/mdm/export")
async def func_api_mdm_export(*, request: Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=False, strict_types=True, header_fallback=False, reject_unknown=True, param_specs=[{"name": "source", "type": "str", "required": False, "allowed": ["CW", "SAP"], "default": "CW"}])
    client_postgres, _, _ = app_state.func_postgres_db_select(app_state=app_state, db="mdm")
    return await app_state.func_mdm_export(app_state=app_state, pool=client_postgres, source=oq["source"])
