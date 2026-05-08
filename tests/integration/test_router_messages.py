import pytest

@pytest.mark.asyncio
async def test_my_messages_inbox_and_thread(integration_app, auth_client):
    # 1. Setup two users
    user_a = auth_client(user_id=1, role=None)
    user_b = auth_client(user_id=2, role=None)
    pool = integration_app.app.state.client_postgres_pool
    
    # 0. Clean up previous test data
    await pool.execute("DELETE FROM message")
    
    # 2. User A sends a message to User B
    # Using the correct 'obj_list' envelope and mode=now
    payload_1 = {"obj_list": [{"user_id": 2, "message": "Hello from A"}]}
    res1 = await user_a.post("/my/object-create?table=message&mode=now", json=payload_1)
    assert res1.json()["status"] == 1
    
    # 3. User B sends a reply
    payload_2 = {"obj_list": [{"user_id": 1, "message": "Hi A, this is B"}]}
    res2 = await user_b.post("/my/object-create?table=message&mode=now", json=payload_2)
    assert res2.json()["status"] == 1
    
    # 4. Verify Inbox for User A
    res_inbox = await user_a.get("/my/message-inbox?mode=all")
    inbox = res_inbox.json()["message"]
    # Should only see the latest message from B
    assert len(inbox) == 1
    assert inbox[0]["message"] == "Hi A, this is B"
    print("\n✅ Messages: Inbox logic (Conversation grouping) verified.")
    
    # 5. Verify Thread between A and B
    res_thread = await user_a.get("/my/message-thread?user_id=2")
    thread = res_thread.json()["message"]
    assert len(thread) == 2
    print("✅ Messages: Thread logic (Bi-directional) verified.")
    
    # 6. Bulk Delete: User A deletes all SENT messages
    # Note: Ensure your router supports this or use object-delete
    await user_a.delete("/my/message-delete-bulk?mode=sent")
    res_thread_after = await user_a.get("/my/message-thread?user_id=2")
    # Only B's message should remain in the thread for A
    assert len(res_thread_after.json()["message"]) == 1
    print("✅ Messages: Bulk Delete (mode=sent) verified.")
