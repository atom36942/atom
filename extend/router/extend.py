#import
from core.route import *
from extend.core.function import *
from extend.core.config import *

#api
@router.get("/extend")
async def func_api_4998ba01493d40a9a088750006435c0c(request:Request):
   return {"status":1,"message":"welcome to extend api"}
