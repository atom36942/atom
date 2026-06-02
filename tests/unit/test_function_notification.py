import pytest
from unittest.mock import AsyncMock, MagicMock
from core.function import func_notification_create


@pytest.fixture
def mock_app_state():
    state = MagicMock()
    state.func_postgres_create = AsyncMock()
    state.client_postgres_pool = "mock_pool"
    state.client_password_hasher = "mock_hasher"
    state.func_postgres_serialize = "mock_serialize"
    state.func_regex_check = "mock_regex"
    state.cache_postgres_schema = {}
    state.cache_postgres_buffer_create = {}
    state.config_regex = {}
    state.config_table = {}
    state.config_buffer_limit = 10
    return state


@pytest.mark.asyncio
async def test_notification_type_1_job_status_change_approved(mock_app_state):
    # Job approved (status 3) by an admin (actor 99) for owner (user 10)
    payload = {
        "table": "job",
        "obj_list": [{"id": 100, "status": 3, "created_by_id": 10, "updated_by_id": 99}]
    }

    await func_notification_create(type=1, app_state=mock_app_state, payload=payload)

    # Should have called func_postgres_create with the correct notification object
    mock_app_state.func_postgres_create.assert_called_once()
    kwargs = mock_app_state.func_postgres_create.call_args.kwargs
    assert kwargs["table"] == "notification"
    assert kwargs["mode"] == "buffer"
    assert len(kwargs["obj_list"]) == 1
    
    notif = kwargs["obj_list"][0]
    assert notif["type"] == 1
    assert notif["created_by_id"] == 99
    assert notif["user_id"] == 10
    assert notif["title"] == "Your Job has been Approved"
    assert notif["reference_table"] == "job"
    assert notif["reference_id"] == 100


@pytest.mark.asyncio
async def test_notification_type_1_ignores_owner_self_action(mock_app_state):
    # Job approved by the owner themselves (actor 10 == owner 10)
    payload = {
        "table": "job",
        "obj_list": [{"id": 100, "status": 3, "created_by_id": 10, "updated_by_id": 10}]
    }

    await func_notification_create(type=1, app_state=mock_app_state, payload=payload)
    mock_app_state.func_postgres_create.assert_not_called()


@pytest.mark.asyncio
async def test_notification_type_1_ignores_pending_status(mock_app_state):
    # Job status is 1 (Draft) or 2 (Pending), not 3 or 4
    payload = {
        "table": "job",
        "obj_list": [{"id": 100, "status": 2, "created_by_id": 10, "updated_by_id": 99}]
    }

    await func_notification_create(type=1, app_state=mock_app_state, payload=payload)
    mock_app_state.func_postgres_create.assert_not_called()


@pytest.mark.asyncio
async def test_notification_type_2_password_change_by_admin(mock_app_state):
    # Password updated for user 10 by admin 99
    payload = {
        "table": "users",
        "obj_list": [{"id": 10, "password": "new_hashed_password", "updated_by_id": 99}]
    }

    await func_notification_create(type=2, app_state=mock_app_state, payload=payload)

    mock_app_state.func_postgres_create.assert_called_once()
    kwargs = mock_app_state.func_postgres_create.call_args.kwargs
    
    notif = kwargs["obj_list"][0]
    assert notif["type"] == 2
    assert notif["created_by_id"] == 99
    assert notif["user_id"] == 10
    assert notif["title"] == "Your password has been changed by Admin."
    assert notif["reference_table"] == "users"
    assert notif["reference_id"] == 10


@pytest.mark.asyncio
async def test_notification_type_2_ignores_self_password_change(mock_app_state):
    # User 10 changes their own password
    payload = {
        "table": "users",
        "obj_list": [{"id": 10, "password": "new_hashed_password", "updated_by_id": 10}]
    }

    await func_notification_create(type=2, app_state=mock_app_state, payload=payload)
    mock_app_state.func_postgres_create.assert_not_called()


@pytest.mark.asyncio
async def test_notification_type_2_ignores_non_password_update(mock_app_state):
    # Admin updates user 10's email, but NOT password
    payload = {
        "table": "users",
        "obj_list": [{"id": 10, "email": "new@email.com", "updated_by_id": 99}]
    }

    await func_notification_create(type=2, app_state=mock_app_state, payload=payload)
    mock_app_state.func_postgres_create.assert_not_called()
