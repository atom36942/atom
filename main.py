#import
from core.function import func_server_start
from core.app import app
import asyncio

#logic
if __name__=="__main__":
   try:asyncio.run(func_server_start(app))
   except KeyboardInterrupt:print("exit")
   