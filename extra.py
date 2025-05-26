#env
import os
from dotenv import load_dotenv
load_dotenv()

#generate fake data
from main import generate_fake_data
import asyncio
if True:asyncio.run(generate_fake_data(os.getenv("postgres_url"),10000,1000))

