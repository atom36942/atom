import pytest
import asyncio
import sys
import os
import time
import orjson
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

class _FakePostgresAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *args):
        return None

class _FakeAuthPostgresConn:
    def __init__(self):
        self.users = []
        self.otps = []
        self.user_id = 1
        self.otp_id = 1

    def _user(self, **values):
        user = {
            "id": self.user_id,
            "type": values.get("type"),
            "role": values.get("role", 1),
            "is_active": values.get("is_active", 1),
            "username": values.get("username"),
            "email": values.get("email"),
            "mobile": values.get("mobile"),
            "password": values.get("password"),
            "google_login_id": values.get("google_login_id"),
            "name": values.get("name"),
            "google_login_metadata": values.get("google_login_metadata"),
        }
        self.user_id += 1
        self.users.append(user)
        return user

    def _latest_user(self, predicate):
        matches = [user for user in self.users if predicate(user)]
        return [max(matches, key=lambda user: user["id"])] if matches else []

    async def fetch(self, query, *args):
        sql = " ".join(query.lower().split())
        if sql.startswith("insert into users"):
            if "(type, username, password)" in sql:
                type_, username, password = args
                if any(user["type"] == type_ and user.get("username") == username for user in self.users):
                    raise Exception("duplicate key value violates unique constraint")
                return [self._user(type=type_, username=username, password=password)]
            if "(type, email, password)" in sql:
                return [self._user(type=args[0], email=args[1], password=args[2])]
            if "(type, mobile, password)" in sql:
                return [self._user(type=args[0], mobile=args[1], password=args[2])]
            if "(type, email)" in sql:
                return [self._user(type=args[0], email=args[1])]
            if "(type, mobile)" in sql:
                return [self._user(type=args[0], mobile=args[1])]
            if "(type, google_login_id, email, name, google_login_metadata)" in sql:
                return [self._user(type=args[0], google_login_id=args[1], email=args[2], name=args[3], google_login_metadata=args[4])]
        if sql.startswith("select * from users where type=$1 and username=$2"):
            type_, username = args
            return self._latest_user(lambda user: user["type"] == type_ and user.get("username") == username)
        if sql.startswith("select * from users where type=$1 and email=$2"):
            type_, email = args
            return self._latest_user(lambda user: user["type"] == type_ and user.get("email") == email)
        if sql.startswith("select * from users where type=$1 and mobile=$2"):
            type_, mobile = args
            return self._latest_user(lambda user: user["type"] == type_ and user.get("mobile") == mobile)
        if sql.startswith("select * from users where google_login_id=$1 and type=$2"):
            google_login_id, type_ = args
            return self._latest_user(lambda user: user["type"] == type_ and user.get("google_login_id") == google_login_id)
        if sql.startswith("select otp,") and "where email=$1" in sql:
            email = args[0]
            matches = [otp for otp in self.otps if otp.get("email") == email]
            return [max(matches, key=lambda otp: otp["id"])] if matches else []
        if sql.startswith("select otp,") and "where mobile=$1" in sql:
            mobile = args[0]
            matches = [otp for otp in self.otps if otp.get("mobile") == mobile]
            return [max(matches, key=lambda otp: otp["id"])] if matches else []
        return []

    async def fetchval(self, query, *args):
        return 1

    async def execute(self, query, *args):
        sql = " ".join(query.lower().split())
        if sql.startswith("insert into otp"):
            otp = {"id": self.otp_id, "otp": args[0], "email": None, "mobile": None, "is_active": True}
            self.otp_id += 1
            if "(otp, email)" in sql:
                otp["email"] = args[1]
            elif "(otp, mobile)" in sql:
                otp["mobile"] = args[1]
            elif "(otp, email, mobile)" in sql:
                otp["email"], otp["mobile"] = args[1], args[2]
            self.otps.append(otp)
            return "INSERT 0 1"
        if sql.startswith("delete from users where id=$1"):
            self.users = [user for user in self.users if user["id"] != args[0]]
            return "DELETE 1"
        if sql.startswith("delete from otp where email=$1"):
            self.otps = [otp for otp in self.otps if otp.get("email") != args[0]]
            return "DELETE 1"
        if sql.startswith("delete from otp where mobile=$1"):
            self.otps = [otp for otp in self.otps if otp.get("mobile") != args[0]]
            return "DELETE 1"
        return "UPDATE 1"

class _FakeAuthPostgresPool:
    def __init__(self):
        self.conn = _FakeAuthPostgresConn()

    def acquire(self):
        return _FakePostgresAcquire(self.conn)

    async def fetch(self, query, *args):
        return await self.conn.fetch(query, *args)

    async def execute(self, query, *args):
        return await self.conn.execute(query, *args)

    async def close(self):
        return None

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
        state.client_postgres_pool = _FakeAuthPostgresPool()

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

    if not getattr(state, "func_serialize", None):
        state.func_serialize = lambda obj: orjson.dumps(obj, default=str)

# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def admin_headers(state):
    """JWT Authorization header for the root admin user (id=1, role=1)."""
    from core.function.utility import func_token_encode
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
