import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from tests.conftest import unique_id

# ---------------------------------------------------------------------------
# Deep Security & Role Validation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_my_user_update_single_column_success(client, my_headers, admin_headers, state, db_available):
    """Scenario 1: User can update their own config_column_single_update keys individually."""
    with patch.object(state, "func_otp_verify", new_callable=AsyncMock) as mock_otp:
        mock_otp.return_value = "verified"
        r_profile = await client.get("/my/profile", headers=my_headers)
        assert r_profile.status_code == 200, f"Profile read failed: {r_profile.text}"
        my_id = int(r_profile.json()["message"]["id"])
        new_username = f"newname{unique_id()}"[:15]
        r = await client.put(f"/my/object-update?table=users&is_serialize=1", json={"id": my_id, "username": new_username}, headers=my_headers)
        assert r.status_code == 200, f"Update failed (Expected 200, got {r.status_code}): {r.text}"
        
        # Verify via DB directly to bypass API cache
        r_db = await client.post("/admin/postgres-runner", json={"mode": "read", "query": f"SELECT username FROM users WHERE id={my_id}"}, headers=admin_headers)
        msg = r_db.json()["message"]
        assert isinstance(msg, list) and len(msg) > 0, f"DB verify failed (Expected list, got {type(msg)}): {r_db.text}"
        assert msg[0]["username"] == new_username, f"Username mismatch: expected {new_username}, got {msg[0]['username']}"

@pytest.mark.asyncio
async def test_my_user_update_multiple_sensitive_columns_rejected(client, my_headers, db_available):
    """Scenario 1: User CANNOT update multiple sensitive columns at once."""
    r_profile = await client.get("/my/profile", headers=my_headers)
    my_id = int(r_profile.json()["message"]["id"])
    r = await client.put(f"/my/object-update?table=users", json={"id": my_id, "username": "newname123", "email": "new@email.com"}, headers=my_headers)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "individually" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_my_user_update_ownership_rejected(client, my_headers, admin_headers, db_available):
    """Scenario 1: Ownership check - User cannot update other users."""
    uid = unique_id()
    uname = f"other{uid}"[:15]
    await client.post("/auth/signup-username-password", json={"type": 1, "username": uname, "password": "password123"})
    r_all = await client.post("/admin/postgres-runner", json={"mode": "read", "query": f"select id from users where username='{uname}'"}, headers=admin_headers)
    msg = r_all.json()["message"]
    assert isinstance(msg, list) and len(msg) > 0, f"Could not find other user: {r_all.text}"
    other_id = int(msg[0]["id"])
    r = await client.put(f"/my/object-update?table=users&is_serialize=1", json={"id": other_id, "username": "hackedname"}, headers=my_headers)
    assert r.status_code == 400, f"Expected 400 for ownership breach, got {r.status_code}: {r.text}"
    assert "ownership" in r.json()["message"].lower(), f"Wrong error message: {r.text}"

@pytest.mark.asyncio
async def test_admin_update_blocked_column_success(client, admin_headers, db_available):
    """Scenario 2: Admin can update blocked columns."""
    r_create = await client.post("/admin/object-create?table=test", json={"title": "admin_test"}, headers=admin_headers)
    assert r_create.status_code == 200, f"Admin create failed: {r_create.text}"
    obj_id = int(r_create.json()["message"][0])
    r = await client.put(f"/admin/object-update?table=test", json={"id": obj_id, "is_active": 0}, headers=admin_headers)
    assert r.status_code == 200, f"Admin update failed: {r.text}"
    r_read = await client.get(f"/admin/object-read?table=test&id==,{obj_id}", headers=admin_headers)
    assert r_read.json()["message"][0]["is_active"] == 0

@pytest.mark.asyncio
async def test_admin_bulk_create_update_success(client, admin_headers, db_available):
    """Scenario 3: Bulk operations by admin."""
    uid = unique_id()
    objs = [{"title": f"bulk1_{uid}"}, {"title": f"bulk2_{uid}"}]
    r = await client.post("/admin/object-create?table=test", json={"obj_list": objs}, headers=admin_headers)
    assert r.status_code == 200, f"Bulk create failed: {r.text}"
    ids = [int(i) for i in r.json()["message"]]
    updates = [{"id": ids[0], "title": f"upd1_{uid}"}, {"id": ids[1], "title": f"upd2_{uid}"}]
    r_upd = await client.put("/admin/object-update?table=test&is_serialize=1", json={"obj_list": updates}, headers=admin_headers)
    assert r_upd.status_code == 200, f"Bulk update status error: {r_upd.text}"
    upd_msg = r_upd.json()["message"]
    
    # Wait a tiny bit for DB consistency in case of high load
    import asyncio
    await asyncio.sleep(0.1)

    r_check = await client.get(f"/admin/object-read?table=test&id=in,{ '|'.join(map(str, ids)) }", headers=admin_headers)
    msg = r_check.json()["message"]
    assert isinstance(msg, list), f"Bulk read failed: {r_check.text}"
    titles = [o["title"] for o in msg]
    expected = f"upd1_{uid}"
    assert expected in titles, f"Update mismatch! Server reported: '{upd_msg}'. Found titles: {titles}. IDs: {ids}. Response: {r_upd.text}"

@pytest.mark.asyncio
async def test_my_role_bulk_user_update_rejected(client, my_headers, db_available):
    """Scenario 4: Bulk user update restricted for 'my' role."""
    r_profile = await client.get("/my/profile", headers=my_headers)
    my_id = int(r_profile.json()["message"]["id"])
    r = await client.put("/my/object-update?table=users", json={"obj_list": [{"id": my_id, "username": "name123"}, {"id": my_id, "username": "name456"}]}, headers=my_headers)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "multi-object" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_public_create_restricted_table_rejected(client, db_available):
    """Scenario 4: Public role table restriction."""
    r = await client.post("/public/object-create?table=users", json={"username": "publicuser123", "password": "password123"})
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "not allowed" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_my_create_blocked_column_rejected(client, my_headers, db_available):
    """Scenario 4: My role blocked column restriction on create."""
    r = await client.post("/my/object-create?table=test", json={"title": "hacker", "role": 1}, headers=my_headers)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    msg = r.json()["message"].lower()
    assert "restricted" in msg or "unauthorized" in msg

@pytest.mark.asyncio
async def test_my_update_email_otp_flow(client, my_headers, admin_headers, db_available):
    """Scenario: OTP email update flow."""
    r_profile = await client.get("/my/profile", headers=my_headers)
    my_id = int(r_profile.json()["message"]["id"])
    new_email = f"new_{unique_id()}@test.com"
    otp_code = 123456
    r_fail = await client.put(f"/my/object-update?table=users", json={"id": my_id, "email": new_email}, headers=my_headers)
    assert r_fail.status_code == 400, f"Should fail without OTP: {r_fail.text}"
    await client.post("/admin/postgres-runner", json={"mode": "write", "query": f"INSERT INTO otp (otp, email) VALUES ({otp_code}, '{new_email}')"}, headers=admin_headers)
    r_ok = await client.put(f"/my/object-update?table=users&otp={otp_code}", json={"id": my_id, "email": new_email}, headers=my_headers)
    assert r_ok.status_code == 200, f"OTP update failed: {r_ok.text}"

@pytest.mark.asyncio
async def test_my_update_mobile_otp_flow(client, my_headers, admin_headers, db_available):
    """Scenario: OTP mobile update flow."""
    r_profile = await client.get("/my/profile", headers=my_headers)
    my_id = int(r_profile.json()["message"]["id"])
    new_mobile = f"9{unique_id()}"[:10]
    otp_code = 654321
    await client.post("/admin/postgres-runner", json={"mode": "write", "query": f"INSERT INTO otp (otp, mobile) VALUES ({otp_code}, '{new_mobile}')"}, headers=admin_headers)
    r_ok = await client.put(f"/my/object-update?table=users&otp={otp_code}", json={"id": my_id, "mobile": new_mobile}, headers=my_headers)
    assert r_ok.status_code == 200, f"OTP update failed: {r_ok.text}"

@pytest.mark.asyncio
async def test_my_update_email_otp_expired(client, my_headers, admin_headers, db_available):
    """Scenario: Expired OTP check."""
    r_profile = await client.get("/my/profile", headers=my_headers)
    my_id = int(r_profile.json()["message"]["id"])
    new_email = f"exp_{unique_id()}@test.com"
    otp_code = 111222
    await client.post("/admin/postgres-runner", json={"mode": "write", "query": f"INSERT INTO otp (otp, email, created_at) VALUES ({otp_code}, '{new_email}', CURRENT_TIMESTAMP - INTERVAL '20 minutes')"}, headers=admin_headers)
    r = await client.put(f"/my/object-update?table=users&otp={otp_code}", json={"id": my_id, "email": new_email}, headers=my_headers)
    assert r.status_code == 400, f"Should fail for expired OTP, got {r.status_code}: {r.text}"
    assert "expired" in r.json()["message"].lower()




