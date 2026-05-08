import pytest
import asyncio
import os
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from testcontainers.mongodb import MongoDbContainer
import asyncpg
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient

# This fixture starts the databases once for the entire test session
@pytest.fixture(scope="session")
def db_containers():
    print("\n🏗️  Spinning up Shared Integration Environment...")
    with PostgresContainer("postgres:16-alpine") as postgres, \
         RedisContainer("redis:7-alpine") as redis_cont, \
         MongoDbContainer("mongo:6") as mongo_cont:
        
        # Connection URLs
        pg_url = postgres.get_connection_url().replace("psycopg2", "postgresql")
        redis_url = f"redis://{redis_cont.get_container_host_ip()}:{redis_cont.get_exposed_port(6379)}"
        mongo_url = mongo_cont.get_connection_url()
        
        yield {
            "postgres": pg_url,
            "redis": redis_url,
            "mongo": mongo_url
        }

# This fixture provides an initialized FastAPI app pointing to real containers
@pytest.fixture(scope="session")
async def integration_app(db_containers):
    from core.app import app
    from core.function import func_postgres_schema_init
    
    # 1. Override App State with Real Container URLs
    app.state.config_postgres_url = db_containers["postgres"]
    app.state.config_redis_url = db_containers["redis"]
    app.state.config_mongodb_url = db_containers["mongo"]
    
    # 2. Initialize Real Clients
    app.state.client_postgres_pool = await asyncpg.create_pool(dsn=app.state.config_postgres_url)
    app.state.client_redis = redis.from_url(app.state.config_redis_url)
    app.state.client_mongodb = AsyncIOMotorClient(app.state.config_mongodb_url)
    
    # 3. Run Real Schema Migration
    # Using your actual core config
    from core.config import config_postgres, config_postgres_root_user_password
    await func_postgres_schema_init(
        client_postgres_pool=app.state.client_postgres_pool,
        client_password_hasher=None,
        config_postgres=config_postgres,
        config_postgres_root_user_password=config_postgres_root_user_password
    )
    
    # 4. Provide the TestClient
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    await app.state.client_postgres_pool.close()
    await app.state.client_redis.aclose()

@pytest.fixture
def auth_client(integration_app):
    """Returns a function to get an authenticated client for a specific user."""
    import jwt
    from core.config import config_token_secret_key
    
    def _get_client(user_id=1, role=1, is_active=1):
        payload = {
            "id": user_id,
            "role": role,
            "is_active": is_active,
            "type": 1
        }
        token = jwt.encode(payload, config_token_secret_key, algorithm="HS256")
        integration_app.headers.update({"Authorization": f"Bearer {token}"})
        return integration_app
        
    return _get_client
