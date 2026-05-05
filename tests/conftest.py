import pytest
import asyncio
import sys
import os
import time
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from fastapi import responses

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.app import app

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def unique_id():
    """Return a unique integer suffix for test isolation."""
    return int(time.time() * 1000)

# ---------------------------------------------------------------------------
# App Lifespan & Client Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def lifespan_manager():
    """Boot the full app lifecycle once for the entire test session."""
    try:
        async with asyncio.timeout(30):
            async with LifespanManager(app) as manager:
                yield manager
    except asyncio.TimeoutError:
        pytest.exit("❌ Test setup failed: App lifespan timed out. Check your .env connections.")
    except Exception as e:
        pytest.exit(f"❌ Test setup failed: {str(e)}")

@pytest.fixture(scope="session")
async def client(lifespan_manager):
    """Session-scoped async HTTP client connected to the running app."""
    transport = ASGITransport(app=lifespan_manager.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="session")
def state(lifespan_manager):
    """Shortcut to app.state for direct function testing."""
    return app.state

# ---------------------------------------------------------------------------
# Hybrid Mocking Logic (Mock only if missing in .env)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_hybrid_clients(state):
    """
    Inspects app.state and injects mocks only for services 
    that are not configured in the environment.
    """
    # 1. Base Clients
    if not getattr(state, "client_s3", None):
        state.client_s3 = MagicMock()
        state.client_s3.list_buckets = MagicMock(return_value={"Buckets": []})
        state.client_s3_resource = MagicMock()
        
    if not getattr(state, "client_azure_blob", None):
        state.client_azure_blob = MagicMock()
        state.client_azure_blob.list_containers = MagicMock(return_value=[])
        
    if not getattr(state, "client_redis", None):
        state.client_redis = AsyncMock()
        
    if not getattr(state, "client_mongodb", None):
        state.client_mongodb = MagicMock()

    # 2. Postgres Mocking (Only if pool initialization failed/skipped)
    if not getattr(state, "client_postgres_pool", None):
        # Robust Postgres Mock for fallback
        class AsyncContextManagerMock:
            def __init__(self, return_val): self.return_val = return_val
            async def __aenter__(self): return self.return_val
            async def __aexit__(self, *args): pass
        
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [{"id": 1, "role": 1, "is_active": 1, "username": "testuser"}]
        mock_conn.fetchval.return_value = 1
        mock_conn.execute.return_value = "UPDATE 1"
        
        state.client_postgres_pool = MagicMock()
        state.client_postgres_pool.acquire.return_value = AsyncContextManagerMock(mock_conn)
        state.client_postgres_pool.fetch = AsyncMock(return_value=[])
        state.client_postgres_pool.execute = AsyncMock(return_value="UPDATE 1")

    # 3. Cloud Functions (Mock if missing)
    if not getattr(state, "func_ses_send_email", None) or isinstance(state.func_ses_send_email, MagicMock):
        state.func_ses_send_email = MagicMock(return_value="sent")
    
    if not getattr(state, "func_resend_send_email", None) or isinstance(state.func_resend_send_email, MagicMock):
        state.func_resend_send_email = AsyncMock(return_value="sent")
        
    if not getattr(state, "func_sns_send_mobile_message", None) or isinstance(state.func_sns_send_mobile_message, MagicMock):
        state.func_sns_send_mobile_message = MagicMock(return_value="sent")
        
    if not getattr(state, "func_fast2sms_send_otp_mobile", None) or isinstance(state.func_fast2sms_send_otp_mobile, MagicMock):
        state.func_fast2sms_send_otp_mobile = MagicMock(return_value="sent")

    if not getattr(state, "func_jira_worklog_export", None) or isinstance(state.func_jira_worklog_export, MagicMock):
        state.func_jira_worklog_export = MagicMock()

    if not getattr(state, "func_client_download_file", None) or isinstance(state.func_client_download_file, MagicMock):
        state.func_client_download_file = AsyncMock(return_value=responses.StreamingResponse(asyncio.sleep(0), media_type="text/csv"))

# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def admin_headers(state):
    """JWT Authorization header for the root admin user (id=1, role=1)."""
    from core.function.user import func_token_encode
    user = {"id": 1, "type": 1, "role": 1, "is_active": 1}
    token = await func_token_encode(
        user=user,
        config_token_secret_key=state.config_token_secret_key,
        config_token_expiry_sec=state.config_token_expiry_sec,
        config_token_refresh_expiry_sec=state.config_token_refresh_expiry_sec,
        config_token_key=state.config_token_key
    )
    return {"Authorization": f"Bearer {token['token']}"}

# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------
def pytest_configure(config):
    config.option.no_header = True
    config.addinivalue_line("filterwarnings", "ignore")

@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Replace default terminal reporter with TableReporter."""
    config = session.config
    standard_reporter = config.pluginmanager.getplugin("terminalreporter")
    if standard_reporter:
        from tests.reporter import TableReporter
        custom_reporter = TableReporter(config, sys.stdout)
        custom_reporter._session = session
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(custom_reporter, "terminalreporter")

def pytest_collection_finish(session):
    sys.stdout.write(f"\n  🧪 Test Suite — {len(session.items)} tests\n")
    sys.stdout.flush()
