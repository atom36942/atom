import pytest
import asyncio
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from testcontainers.mongodb import MongoDbContainer

@pytest.mark.asyncio
async def test_full_stack_client_integration():
    # 1. Initialize Containers
    print("\n🚀 Starting Full Stack Containers (Postgres, Redis, Mongo)...")
    
    with PostgresContainer("postgres:16-alpine") as postgres, \
         RedisContainer("redis:7-alpine") as redis_cont, \
         MongoDbContainer("mongo:6") as mongo_cont:
        
        # --- POSTGRES SETUP ---
        pg_url = postgres.get_connection_url().replace("psycopg2", "postgresql")
        pg_pool = await asyncpg.create_pool(dsn=pg_url)
        
        # --- REDIS SETUP ---
        # RedisContainer returns host and port
        redis_host = redis_cont.get_container_host_ip()
        redis_port = redis_cont.get_exposed_port(6379)
        redis_url = f"redis://{redis_host}:{redis_port}"
        redis_client = redis.from_url(redis_url)
        
        # --- MONGODB SETUP ---
        mongo_url = mongo_cont.get_connection_url()
        mongo_client = AsyncIOMotorClient(mongo_url)
        
        try:
            # --- TEST 1: POSTGRES ALIVE? ---
            pg_version = await pg_pool.fetchval("SELECT version()")
            assert "PostgreSQL" in pg_version
            print("✅ Postgres: Connected and responding.")

            # --- TEST 2: REDIS ALIVE? ---
            await redis_client.set("integration_test_key", "atom_success")
            val = await redis_client.get("integration_test_key")
            assert val.decode("utf-8") == "atom_success"
            print("✅ Redis: Set/Get successful.")

            # --- TEST 3: MONGODB ALIVE? ---
            db = mongo_client["test_db"]
            res = await db["test_collection"].insert_one({"test": "data"})
            doc = await db["test_collection"].find_one({"_id": res.inserted_id})
            assert doc["test"] == "data"
            print("✅ MongoDB: Insert/Find successful.")

            print("\n🏆 ALL CORE CLIENTS INTEGRATED SUCCESSFULLY!")

        finally:
            await pg_pool.close()
            await redis_client.aclose()
            # Motor client closes automatically on exit

if __name__ == "__main__":
    asyncio.run(test_full_stack_client_integration())
