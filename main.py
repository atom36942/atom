#function
from function import function_server_start

#app
from app import app

#package
import asyncio

#logic
import asyncio
if __name__=="__main__":
   try:asyncio.run(function_server_start(app))
   except KeyboardInterrupt:print("exit")