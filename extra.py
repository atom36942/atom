#generate fake data
from main import postgres_url
from main import generate_fake_data
import asyncio
if False:asyncio.run(generate_fake_data(postgres_url,10000,1000))