import pytest
import asyncio
import sys
import os
import time
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager

# Standalone Portability: Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.app import app

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def unique_id():
    """Return a unique integer suffix for test isolation."""
    return int(time.time() * 1000)

# ---------------------------------------------------------------------------
# Session-scoped lifespan manager
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def lifespan_manager():
    """Boot the full app lifecycle once for the entire test session."""
    try:
        async with asyncio.timeout(15):
            async with LifespanManager(app) as manager:
                yield manager
    except asyncio.TimeoutError:
        pytest.exit("❌ Test setup failed: App lifespan timed out. Check your DB/Redis connections.")
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

@pytest.fixture(scope="session")
async def my_user(state):
    """Create a regular test user and return its full record."""
    if state.client_postgres_pool is None:
        pytest.skip("Postgres not available")
    from core.function.user import func_auth_signup_username_password
    uid = unique_id()
    user = await func_auth_signup_username_password(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        type=1,
        username=f"testmyuser_{uid}",
        password="password123",
        config_is_signup=1,
        config_auth_type=state.config_auth_type
    )
    return user

@pytest.fixture(scope="session")
async def my_headers(state, my_user):
    """JWT Authorization header for a regular (non-admin) user."""
    from core.function.user import func_token_encode
    token = await func_token_encode(
        user=my_user,
        config_token_secret_key=state.config_token_secret_key,
        config_token_expiry_sec=state.config_token_expiry_sec,
        config_token_refresh_expiry_sec=state.config_token_refresh_expiry_sec,
        config_token_key=state.config_token_key
    )
    return {"Authorization": f"Bearer {token['token']}"}

# ---------------------------------------------------------------------------
# DB availability marker — auto-skip tests needing Postgres
# ---------------------------------------------------------------------------
requires_db = pytest.mark.skipif(
    "not config.getoption('--db', default=False)",
    reason="Postgres not available (checked at collection time)"
)

def _has_db():
    """Check if Postgres pool is live — resolved at test time."""
    return getattr(app.state, "client_postgres_pool", None) is not None

@pytest.fixture(scope="session")
def db_available(state):
    """Skip test if Postgres is not connected."""
    if state.client_postgres_pool is None:
        pytest.skip("Postgres not available")

# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------
def pytest_addoption(parser):
    parser.addoption("--db", action="store_true", default=False, help="run tests that require postgres")

def pytest_configure(config):
    config.option.no_header = True
    config.addinivalue_line("markers", "requires_db: skip if Postgres is not connected")
    config.addinivalue_line("filterwarnings", "ignore")

@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Replace default terminal reporter with AtomReporter."""
    config = session.config
    standard_reporter = config.pluginmanager.getplugin("terminalreporter")
    if standard_reporter:
        from tests.atom_reporter import AtomReporter
        custom_reporter = AtomReporter(config, sys.stdout)
        custom_reporter._session = session
        config.pluginmanager.unregister(standard_reporter)
        config.pluginmanager.register(custom_reporter, "terminalreporter")

def pytest_collection_finish(session):
    sys.stdout.write(f"\n  🧪 Atom Test Suite — {len(session.items)} tests\n")
    sys.stdout.flush()
