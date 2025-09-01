import motor.motor_asyncio
async def function_mongodb_client_read(config_mongodb_url):
   client_mongodb=motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
   return client_mongodb