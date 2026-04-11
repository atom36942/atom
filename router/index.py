#router
from fastapi import APIRouter
router=APIRouter()

#import
from function import *
from core.config import *
import asyncio
from datetime import datetime
from fastapi import Request, responses, WebSocket, WebSocketDisconnect

#index
@router.get("/")
async def func_api_index(request:Request):
   return {"status":1,"message":"welcome to atom"} if not config_index_html_path else responses.FileResponse(config_index_html_path)

@router.get("/health")
async def func_api_index(request:Request):
   return {"status":1,"message":"ok"}

@router.get("/openapi.json")
async def func_api_openapi_json(request:Request):
   return request.app.state.cache_openapi

@router.get("/info")
async def func_api_index(request:Request):
   st=request.app.state
   output=st.func_repo_info(request.app.routes,st.cache_postgres_schema,st.config_postgres,st.config_table,st.config_api)
   return {"status":1,"message":output}

@router.websocket("/websocket")
async def func_api_websocket(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         message=await websocket.receive_text()
         output=await func_postgres_object_create(websocket.app.state.client_postgres_pool,func_postgres_serialize,"buffer","test",[{"title":message}],func_validate_identifier,0,3)
         await websocket.send_text(str(output))
   except WebSocketDisconnect:
      print("client disconnected")
