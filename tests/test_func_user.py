import pytest
import time
from tests.conftest import unique_id
from core.function.user import (
    func_auth_signup_username_password,
    func_auth_login_username_password,
    func_token_encode,
    func_otp_generate,
    func_otp_verify,
    func_user_single_read,
    func_user_profile_read,
    func_user_account_delete,
)

# ===========================================================================
# Signup
# ===========================================================================
@pytest.mark.asyncio
async def test_signup_returns_user_dict(state, db_available):
    uid = unique_id()
    user = await func_auth_signup_username_password(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        type=1, username=f"fu_signup_{uid}", password="password123",
        config_is_signup=1, config_auth_type=state.config_auth_type
    )
    assert isinstance(user, dict)
    assert "id" in user
    assert user["username"] == f"fu_signup_{uid}"

@pytest.mark.asyncio
async def test_signup_disabled_flag(state, db_available):
    with pytest.raises(Exception, match="signup disabled"):
        await func_auth_signup_username_password(
            client_postgres_pool=state.client_postgres_pool,
            client_password_hasher=state.client_password_hasher,
            type=1, username="neverexists", password="password123",
            config_is_signup=0, config_auth_type=state.config_auth_type
        )

@pytest.mark.asyncio
async def test_signup_invalid_type(state, db_available):
    with pytest.raises(Exception, match="not allowed"):
        await func_auth_signup_username_password(
            client_postgres_pool=state.client_postgres_pool,
            client_password_hasher=state.client_password_hasher,
            type=999, username="neverexists", password="password123",
            config_is_signup=1, config_auth_type=state.config_auth_type
        )

# ===========================================================================
# Login
# ===========================================================================
@pytest.mark.asyncio
async def test_login_success(state, db_available):
    uid = unique_id()
    username = f"fu_login_{uid}"
    await func_auth_signup_username_password(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        type=1, username=username, password="password123",
        config_is_signup=1, config_auth_type=state.config_auth_type
    )
    user = await func_auth_login_username_password(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        type=1, username=username, password="password123"
    )
    assert user["username"] == username

@pytest.mark.asyncio
async def test_login_username_not_found(state, db_available):
    with pytest.raises(Exception, match="username not found"):
        await func_auth_login_username_password(
            client_postgres_pool=state.client_postgres_pool,
            client_password_hasher=state.client_password_hasher,
            type=1, username="nonexistent_xyz_999", password="pass"
        )

@pytest.mark.asyncio
async def test_login_wrong_password(state, db_available):
    uid = unique_id()
    username = f"fu_wrongpw_{uid}"
    await func_auth_signup_username_password(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        type=1, username=username, password="password123",
        config_is_signup=1, config_auth_type=state.config_auth_type
    )
    with pytest.raises(Exception, match="incorrect password"):
        await func_auth_login_username_password(
            client_postgres_pool=state.client_postgres_pool,
            client_password_hasher=state.client_password_hasher,
            type=1, username=username, password="wrongpassword"
        )

# ===========================================================================
# Token
# ===========================================================================
@pytest.mark.asyncio
async def test_token_encode_contains_keys(state):
    user = {"id": 1, "type": 1, "role": 1, "is_active": 1, "username": "atom"}
    token = await func_token_encode(
        user=user,
        config_token_secret_key=state.config_token_secret_key,
        config_token_expiry_sec=state.config_token_expiry_sec,
        config_token_refresh_expiry_sec=state.config_token_refresh_expiry_sec,
        config_token_key=state.config_token_key
    )
    assert "token" in token
    assert "token_refresh" in token
    assert "token_expiry_sec" in token

@pytest.mark.asyncio
async def test_token_encode_none_user(state):
    token = await func_token_encode(
        user=None,
        config_token_secret_key=state.config_token_secret_key,
        config_token_expiry_sec=state.config_token_expiry_sec,
        config_token_refresh_expiry_sec=state.config_token_refresh_expiry_sec,
        config_token_key=state.config_token_key
    )
    assert token is None

# ===========================================================================
# OTP
# ===========================================================================
@pytest.mark.asyncio
async def test_otp_generate_and_verify(state, db_available):
    uid = unique_id()
    email = f"otp_{uid}@test.com"
    otp = await func_otp_generate(
        client_postgres_pool=state.client_postgres_pool,
        email=email, mobile=None
    )
    assert 100000 <= otp <= 999999
    # Verify succeeds
    await func_otp_verify(
        client_postgres_pool=state.client_postgres_pool,
        otp=otp, email=email, mobile=None,
        config_expiry_sec_otp=state.config_expiry_sec_otp
    )

@pytest.mark.asyncio
async def test_otp_verify_wrong_code(state, db_available):
    uid = unique_id()
    email = f"otpwrong_{uid}@test.com"
    await func_otp_generate(client_postgres_pool=state.client_postgres_pool, email=email, mobile=None)
    with pytest.raises(Exception, match="invalid otp"):
        await func_otp_verify(
            client_postgres_pool=state.client_postgres_pool,
            otp=999999, email=email, mobile=None,
            config_expiry_sec_otp=state.config_expiry_sec_otp
        )

@pytest.mark.asyncio
async def test_otp_verify_missing_identifier(state):
    with pytest.raises(Exception, match="missing"):
        await func_otp_verify(
            client_postgres_pool=None,
            otp=123456, email=None, mobile=None,
            config_expiry_sec_otp=600
        )

@pytest.mark.asyncio
async def test_otp_verify_missing_code(state):
    with pytest.raises(Exception, match="otp code missing"):
        await func_otp_verify(
            client_postgres_pool=None,
            otp=None, email="test@test.com", mobile=None,
            config_expiry_sec_otp=600
        )

# ===========================================================================
# User profile and account
# ===========================================================================
@pytest.mark.asyncio
async def test_user_single_read(state, db_available):
    user = await func_user_single_read(client_postgres_pool=state.client_postgres_pool, user_id=1)
    assert user["id"] == 1
    assert "username" in user

@pytest.mark.asyncio
async def test_user_single_read_not_found(state, db_available):
    with pytest.raises(Exception, match="user not found"):
        await func_user_single_read(client_postgres_pool=state.client_postgres_pool, user_id=999999999)

@pytest.mark.asyncio
async def test_user_profile_read(state, db_available):
    profile = await func_user_profile_read(
        client_postgres_pool=state.client_postgres_pool,
        user_id=1,
        config_sql=state.config_sql,
        func_user_single_read=state.func_user_single_read
    )
    assert profile["id"] == 1

@pytest.mark.asyncio
async def test_user_account_delete_with_role(state, db_available):
    """User with role should not be deletable."""
    with pytest.raises(Exception, match="role cannot be deleted"):
        await func_user_account_delete(
            mode="soft",
            client_postgres_pool=state.client_postgres_pool,
            user_id=1
        )
