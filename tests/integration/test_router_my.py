import pytest

@pytest.mark.asyncio
async def test_my_bulk_creation_and_ownership(integration_app, auth_client):
    # 1. We create two different users
    user_1 = auth_client(user_id=101)
    user_2 = auth_client(user_id=102)
    
    table = "test" # Standard table from your config
    
    # 2. User 1 creates a BULK list of objects
    payload = {
        "obj_list": [
            {"title": "User 1 - Item A"},
            {"title": "User 1 - Item B"}
        ]
    }
    create_res = user_1.post(f"/my/object-create?table={table}", json=payload)
    assert create_res.status_code == 200
    u1_ids = create_res.json()["message"]
    assert len(u1_ids) == 2
    print("\n✅ User 1: Bulk creation successful.")

    # 3. User 2 tries to UPDATE User 1's object (Security Violation)
    # The API should not return an error, but it should return 0 updated records 
    # or an empty list because the WHERE clause includes created_by_id=102
    update_payload = {"id": u1_ids[0], "title": "Hacked Title"}
    update_res = user_2.put(f"/my/object-update?table={table}", json=update_payload)
    
    # In your logic, func_postgres_update returns the list of actually updated IDs.
    # Since the ownership doesn't match, it should return an empty list or 'updated' with no effect.
    assert u1_ids[0] not in str(update_res.json()["message"])
    print("✅ Security: User 2 blocked from updating User 1's data.")

    # 4. User 2 tries to DELETE User 1's object (Security Violation)
    delete_payload = {"table": table, "ids": str(u1_ids[1])}
    delete_res = user_2.post("/my/ids-delete", json=delete_payload)
    
    # Your func_postgres_delete returns "deleted" but the WHERE clause prevents actual deletion
    # We verify by reading the record as User 1 again
    read_res = user_1.get(f"/my/object-read?table={table}")
    titles = [item["title"] for item in read_res.json()["message"]]
    assert "User 1 - Item B" in titles
    print("✅ Security: User 2 blocked from deleting User 1's data.")

@pytest.mark.asyncio
async def test_my_restricted_fields_protection(integration_app, auth_client):
    # SCENARIO: User tries to elevate their own role via /my/ router
    user_1 = auth_client(user_id=101)
    
    # 1. Attempt to update 'role' (which is in config_column_disable_non_admin)
    payload = {"id": 101, "role": 1}
    response = user_1.put("/my/object-update?table=users", json=payload)
    
    assert response.status_code == 200 # App handles it via try/except or returns error in message
    assert "unauthorized" in str(response.json()["message"]).lower()
    print("✅ Security: User blocked from updating restricted fields (role).")

@pytest.mark.asyncio
async def test_my_object_create_disable_list(integration_app, auth_client):
    # SCENARIO: User tries to create a record in a restricted table (e.g. 'users' or 'log_api')
    user_1 = auth_client(user_id=101)
    
    payload = {"username": "new_user", "password": "123"}
    response = user_1.post("/my/object-create?table=users", json=payload)
    
    assert "not allowed" in str(response.json()["message"]).lower()
    print("✅ Security: User blocked from creating records in restricted tables.")
