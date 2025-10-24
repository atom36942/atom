#function
from file.function import function_server_start

#app
from file.app import app

#package
import asyncio

#logic
if __name__=="__main__":
   try:asyncio.run(function_server_start(app))
   except KeyboardInterrupt:print("exit")