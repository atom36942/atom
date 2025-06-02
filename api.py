#router
from fastapi import APIRouter
router=APIRouter()

#env
import os
from dotenv import load_dotenv
load_dotenv()

#function
from function import *

#ratelimiter
from fastapi import Depends
from fastapi_limiter.depends import RateLimiter

#test
@router.get("/api",dependencies=[Depends(RateLimiter(times=1,seconds=1))])
async def test(request:Request):
   table="test"
   object={"title":"test_api"}
   await postgres_create(table,[object],1,request.state.postgres_client,request.state.postgres_column_datatype,object_serialize)
   return {"status":1,"message":"welcome to test"}

