#function
from core.function import function_server_start

#app
from core.app import app

#package
import asyncio

#logic
if __name__=="__main__":
   try:asyncio.run(function_server_start(app))
   except KeyboardInterrupt:print("exit")