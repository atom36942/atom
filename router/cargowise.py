# packages
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.post("/admin/mssql-sql-runner")
async def func_api_cargowise_mssql_sql_runner(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql: raise Exception("MSSQL client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    for attempt in range(3):
        try:
            async with app_state.client_mssql.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(ob["sql"])
                if ql.startswith(("select", "with")):
                    columns = [column[0] for column in cursor.description]
                    result = [dict(zip(columns, row)) for row in await cursor.fetchall()]
                else:
                    await conn.commit()
                    result = "done"
                return {"status": 1, "message": result}
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(0.5)
                continue
            raise e

@router.post("/admin/mssql-sql-runner-read")
async def func_api_cargowise_mssql_sql_runner_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_mssql_read: raise Exception("MSSQL read client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    ql = ob["sql"].lower().strip().lstrip("(").strip()
    if not ql.startswith(("select", "with")): raise Exception("read mode restricted")
    for attempt in range(3):
        try:
            async with app_state.client_mssql_read.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(ob["sql"])
                columns = [column[0] for column in cursor.description]
                return {"status": 1, "message": [dict(zip(columns, row)) for row in await cursor.fetchall()]}
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                import asyncio
                await asyncio.sleep(0.5)
                continue
            raise e
