#router
from fastapi import APIRouter
router=APIRouter()

#import
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#index
@router.get("/")
async def func_api_index(*, request:Request):
   app_state=request.app.state
   return {"status":1,"message":"welcome to atom"} if not app_state.config_index_html_path else responses.FileResponse(app_state.config_index_html_path)

@router.get("/health")
async def func_api_index_health(*, request:Request):
   return {"status":1,"message":"ok"}

@router.get("/openapi.json")
async def func_api_openapi_json(*, request:Request):
   app_state=request.app.state
   return app_state.cache_openapi

@router.get("/info")
async def func_api_index_info(*, request:Request):
   app_state=request.app.state
   output=app_state.func_repo_info(app_routes=request.app.routes, cache_postgres_schema=app_state.cache_postgres_schema, config_postgres=app_state.config_postgres, config_table=app_state.config_table, config_api=app_state.config_api)
   return {"status":1,"message":output}

@router.websocket("/websocket")
async def func_api_websocket(*, websocket:WebSocket):
   await websocket.accept()
   app_state=websocket.app.state
   try:
      while True:
         message=await websocket.receive_text()
         output=await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, mode="buffer", table="test", obj_list=[{"title":message}], is_serialize=0, buffer_limit=3, cache_postgres_buffer=app_state.cache_postgres_buffer)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")
