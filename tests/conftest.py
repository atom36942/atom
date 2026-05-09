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
    from testcontainers.localstack import LocalStackContainer
    
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres, \
         RedisContainer("redis:7-alpine") as redis_cont, \
         MongoDbContainer("mongo:6") as mongo_cont, \
         LocalStackContainer("localstack/localstack:3.0.2").with_services("s3") as localstack:
        
        # Connection URLs
        # testcontainers returns 'postgresql+psycopg2://', we need just 'postgresql://'
        pg_url = postgres.get_connection_url().replace("+psycopg2", "")
        redis_url = f"redis://{redis_cont.get_container_host_ip()}:{redis_cont.get_exposed_port(6379)}"
        mongo_url = mongo_cont.get_connection_url()
        
        yield {
            "postgres": pg_url,
            "redis": redis_url,
            "mongo": mongo_url,
            "s3_url": localstack.get_url()
        }

# This fixture provides an initialized FastAPI app pointing to real containers
@pytest.fixture(scope="session")
async def integration_app(db_containers):
    from core.app import app
    from core.function import func_postgres_schema_init
    from argon2 import PasswordHasher
    
    # 1. Override App State with Real Container URLs
    from argon2 import PasswordHasher
    app.state.client_password_hasher = PasswordHasher()
    app.state.config_postgres_url = db_containers["postgres"]
    app.state.config_redis_url = db_containers["redis"]
    app.state.config_redis_url_ratelimiter = db_containers["redis"] # Added for ratelimiter
    app.state.config_mongodb_url = db_containers["mongo"]
    
    # 1.1 Override Postgres Config for Integration Tests (Add missing tables/columns)
    from core import config
    config_pg_test = config.config_postgres.copy()
    config_pg_test["table"] = config_pg_test["table"].copy()
    
    # Ensure 'users' has 'is_active' — already in core schema (line 203), skip
    # (config_postgres already defines is_active for users)
    
    # Add 'body' column to 'test' table (not in core schema)
    if "test" in config_pg_test["table"]:
        config_pg_test["table"]["test"] = config_pg_test["table"]["test"] + [
            {"name": "body", "datatype": "text"},
        ]
        # Note: is_active and created_by_id already exist in core test schema
        
    # Note: 'message' table already exists in core config_postgres (config.py:L254)
    # with columns: created_by_id (mandatory), user_id (mandatory), description (mandatory), is_read
    # No override needed — use the core schema as-is
        
    # Note: 'otp' table in core schema has: otp (mandatory), email, mobile, created_at
    # No overrides needed — tests use direct DB queries and /auth/ routes

    # Add 'test_blob' table if missing
    if "test_blob" not in config_pg_test["table"]:
        config_pg_test["table"]["test_blob"] = [
            {"name": "file_url", "datatype": "text"},
            {"name": "created_by_id", "datatype": "bigint"},
            {"name": "created_at", "datatype": "timestamptz", "default": "now()"}
        ]
    app.state.config_postgres = config_pg_test
    
    # Enable Caching and Rate Limiting for Integration Tests
    app.state.config_api = config.config_api.copy()
    app.state.config_api["/public/object-read"] = {
        "api_cache_sec": ["redis", 60],
        "api_ratelimiting_times_sec": ["redis", 10, 60]
    }
    
    # Store default state for resetting
    app.state.config_is_enable_signup = 1
    app.state.config_is_enable_log_api = 0
    app.state.config_is_enable_background_workers = 0
    app.state.config_is_enable_traceback = 0
    
    app.state._default_config = {
        "config_is_enable_signup": 1,
        "config_is_enable_log_api": 0, # Disabled for tests to avoid contention
        "config_is_enable_traceback": 0 # Disabled to keep console clean for expected failures
    }
    
    # 2. Initialize Real Clients
    app.state.client_postgres_pool = await asyncpg.create_pool(dsn=app.state.config_postgres_url)
    app.state.client_redis = redis.from_url(app.state.config_redis_url)
    app.state.client_redis_ratelimiter = redis.from_url(app.state.config_redis_url_ratelimiter) # Manually init ratelimiter client
    app.state.client_redis_producer = redis.from_url(app.state.config_redis_url) # Init producer for background worker tests
    app.state.client_mongodb = AsyncIOMotorClient(app.state.config_mongodb_url)
    
    # 3. Run Real Schema Migration
    # Using your actual core config
    from core.config import config_postgres, config_postgres_root_user_password
    await func_postgres_schema_init(
        client_postgres_pool=app.state.client_postgres_pool,
        client_password_hasher=app.state.client_password_hasher,
        config_postgres=app.state.config_postgres,
        config_postgres_root_user_password=config_postgres_root_user_password
    )
    
    # 3.1 Synchronize State Caches
    from core.function import func_postgres_schema_read, func_postgres_map_column
    from core.config import config_sql
    app.state.config_regex = {} # Disable regex checks for integration tests to prevent 400 errors
    app.state.cache_postgres_schema = await func_postgres_schema_read(client_postgres_pool=app.state.client_postgres_pool)
    app.state.cache_postgres_table_list = list(app.state.cache_postgres_schema.keys())
    app.state.cache_postgres_column_list = sorted(list(set(col for table in app.state.cache_postgres_schema.values() for col in table.keys())))
    app.state.cache_users_role = await func_postgres_map_column(client_postgres_pool=app.state.client_postgres_pool, config_sql=config_sql.get("users_role"))
    app.state.cache_users_is_active = await func_postgres_map_column(client_postgres_pool=app.state.client_postgres_pool, config_sql=config_sql.get("users_is_active"))
    app.state.cache_ratelimiter, app.state.cache_api_response, app.state.cache_postgres_buffer_create = {}, {}, {}

    # 4. Map S3 to Localstack
    import aiobotocore.session
    session = aiobotocore.session.get_session()
    # We use a context manager to ensure the client is closed correctly
    app.state.client_s3 = await session.create_client(
        's3', 
        region_name='us-east-1', 
        endpoint_url=db_containers["s3_url"],
        aws_access_key_id='test',
        aws_secret_access_key='test'
    ).__aenter__()
    
    # Create a bucket for the tests
    await app.state.client_s3.create_bucket(Bucket="atom-integration-test")
    
    # 4. Final State Hardening (prevents race conditions before lifespan finishes)
    for _k in ["cache_postgres_table_list", "cache_postgres_column_list", "cache_postgres_schema", "cache_users_role", "cache_users_is_active", "cache_ratelimiter", "cache_api_response", "cache_postgres_buffer_create", "cache_openapi"]:
        if not hasattr(app.state, _k): setattr(app.state, _k, [] if "list" in _k else {})
    for _k in ["client_sns", "client_ses", "client_openai", "client_gemini", "client_posthog", "client_celery_producer", "client_kafka_producer", "client_rabbitmq", "client_rabbitmq_producer", "client_sftp", "client_azure_blob", "pulse_flush_task"]:
        if not hasattr(app.state, _k): setattr(app.state, _k, None)

    # 5. Provide the AsyncClient
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.app = app # Allow access to app state
        yield client
    
    # 5. POST-SESSION CLEANUP: Just close the pools
    await app.state.client_postgres_pool.close()
    await app.state.client_redis.aclose()
    if hasattr(app.state, "client_s3") and app.state.client_s3:
        await app.state.client_s3.__aexit__(None, None, None)

@pytest.fixture
def auth_client(integration_app):
    """Returns a function to get a FRESH authenticated client for a specific user."""
    import jwt
    from core.config import config_token_secret_key
    from fastapi.testclient import TestClient
    from core.app import app
    
    def _get_client(user_id=1, role=1, is_active=1):
        import orjson
        from httpx import AsyncClient, ASGITransport
        user_data = {"id": user_id, "role": role, "is_active": is_active, "type": 1}
        payload = {"data": orjson.dumps(user_data).decode("utf-8")}
        token = jwt.encode(payload, config_token_secret_key, algorithm="HS256")
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        client.headers.update({"Authorization": f"Bearer {token}"})
        client.app = app
        return client
        
    return _get_client

@pytest.fixture(autouse=True)
async def reset_state(integration_app):
    """Resets the app state and ensures background tasks are settled."""
    from core.app import app
    import asyncio
    
    # 1. Reset configuration
    if hasattr(app.state, "_default_config"):
        for key, value in app.state._default_config.items():
            setattr(app.state, key, value)
    
    yield
    
    # 2. POST-TEST CLEANUP: Cancel all tasks except the current one
    # This specifically kills pulse_flush and any func_background tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    
    # Give tasks a moment to settle
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Reset any buffers
    if hasattr(app.state, "cache_postgres_buffer_create"):
        app.state.cache_postgres_buffer_create.clear()
