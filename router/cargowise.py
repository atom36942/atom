# packages
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.post("/admin/mssql-sql-runner")
async def func_api_cargowise_mssql_sql_runner(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql: raise Exception("MSSQL client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("mode", "str", 0, ["read", "write"], "read"), ("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if ob["mode"] == "read" and not ql.startswith(("select", "with")): raise Exception("read mode restricted")
    async with app_state.client_mssql.acquire() as conn:
        cursor = await conn.cursor()
        await cursor.execute(ob["sql"])
        if ob["mode"] == "read" or ql.startswith(("select", "with")):
            columns = [column[0] for column in cursor.description]
            return {"status": 1, "message": [dict(zip(columns, row)) for row in await cursor.fetchall()]}
        await conn.commit()
        return {"status": 1, "message": "done"}
