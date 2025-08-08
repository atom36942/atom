#import
from extend import *

#test
@router.get("/test")
async def route_test():
   value=config.get("your_config_key")
   return {"status":1,"message":f"welcome to test"}


#postgres create
@router.get("/postgres-create")
async def route_postgres_create(request:Request):
   table="test"
   object={"created_by_id":request.state.user.get("id"),"title":"router"}
   await function_object_create_postgres(request.app.state.client_postgres,table,[object],0,None,None)
   return {"status":1,"message":"done"}

#postgres update
@router.get("/postgres-update")
async def route_postgres_update(request:Request):
   table="users"
   object={"id":1,"email":"atom1","mobile":"atom2"}
   await function_object_update_postgres(request.app.state.client_postgres,table,[object],0,None,None)
   return {"status":1,"message":"done"}

#websocket
from fastapi import WebSocket,WebSocketDisconnect
@router.websocket("/ws")
async def websocket_endpoint(websocket:WebSocket):
   await websocket.accept()
   try:
      while True:
         data=await websocket.receive_text()
         table="test"
         object={"title":data}
         await function_object_create_postgres(websocket.app.state.client_postgres,table,[object],0,None,None)
         await websocket.send_text(f"echo: {data}")
   except WebSocketDisconnect:
      print("client disconnected")

