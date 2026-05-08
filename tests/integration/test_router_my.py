import pytest

@pytest.mark.asyncio
async def test_my_bulk_creation_and_ownership(integration_app, auth_client):
    # 1. We create two different users
    user_1 = auth_client(user_id=101)
    user_2 = auth_client(user_id=102)
    
    table = "test" 
    
    # 2. User 1 creates a BULK list of objects using the correct 'obj_list' envelope
    payload = {
        "obj_list": [
            {"title": "User 1 - Item A"},
            {"title": "User 1 - Item B"}
        ]
    }
    create_res = await user_1.post(f"/my/object-create?table={table}&mode=now", json=payload)
    assert create_res.json()["status"] == 1
    u1_ids = create_res.json()["message"]
    assert len(u1_ids) == 2
    print("\n✅ User 1: Bulk creation successful.")

    # 3. User 2 tries to UPDATE User 1's object (Security Violation)
    update_payload = {"id": u1_ids[0], "title": "Hacked Title"}
    update_res = await user_2.put(f"/my/object-update?table={table}&mode=now", json=update_payload)
    
    # Verify no records were actually updated (message should be empty list or 0)
    assert str(u1_ids[0]) not in str(update_res.json()["message"])
    print("✅ Security: User 2 blocked from updating User 1's data.")

    # 4. User 2 tries to DELETE User 1's object (Security Violation)
    delete_payload = {"table": table, "ids": str(u1_ids[1])}
    delete_res = await user_2.post("/my/ids-delete", json=delete_payload)
    
    # Verify by reading as User 1 with mandatory paging
    read_res = await user_1.get(f"/my/object-read?table={table}&limit=10&page=1&order=id desc")
    titles = [item["title"] for item in read_res.json()["message"]]
    assert "User 1 - Item B" in titles
    print("✅ Security: User 2 blocked from deleting User 1's data.")
