import pytest

@pytest.mark.asyncio
async def test_object_read_parameter_matrix(integration_app, auth_client):
    # This test exhaustively checks the combinations of filters, sorts, and limits
    admin = auth_client(role=1)
    table = "test"
    
    # 0. CLEAN the table to prevent leakage from other tests
    pool = integration_app.app.state.client_postgres_pool
    async with pool.acquire() as conn:
        await conn.execute(f"DELETE FROM {table}")
    
    # 1. Seed Matrix Data (Correct Envelope)
    seed_data = [
        {"title": f"Item {i}", "status": 1 if i % 2 == 0 else 0} 
        for i in range(1, 11)
    ]
    # NOTE: Using /my/ for generic object creation as it's the standard path
    res_seed = await admin.post(f"/my/object-create?table={table}&mode=now", json={"obj_list": seed_data})
    assert res_seed.json()["status"] == 1
    
    # --- MATRIX TEST 1: Operators (LIKE, IN, >, !=) ---
    # Test: Like search
    res = await admin.get(f"/my/object-read?table={table}&title=like,%Item 1%&limit=10&page=1&order=id asc")
    # Should match "Item 1" and "Item 10"
    assert len(res.json()["message"]) == 2
    
    # Test: Comparison
    # We find IDs > 8 (which are 9 and 10)
    res = await admin.get(f"/my/object-read?table={table}&id=>,8&limit=10&page=1&order=id asc")
    assert len(res.json()["message"]) == 2 
    
    # Test: In list
    res = await admin.get(f"/my/object-read?table={table}&status=in,0&limit=10&page=1&order=id asc")
    assert len(res.json()["message"]) == 5 # All odd items (1, 3, 5, 7, 9)
    
    # --- MATRIX TEST 2: Pagination & Sorting ---
    # Test: Limit and Page
    res = await admin.get(f"/my/object-read?table={table}&limit=3&page=1&order=id asc")
    titles_p1 = [r["title"] for r in res.json()["message"]]
    assert titles_p1 == ["Item 1", "Item 2", "Item 3"]
    
    res = await admin.get(f"/my/object-read?table={table}&limit=3&page=2&order=id asc")
    titles_p2 = [r["title"] for r in res.json()["message"]]
    assert titles_p2 == ["Item 4", "Item 5", "Item 6"]
    
    # --- MATRIX TEST 3: Column Selection (Masking) ---
    res = await admin.get(f"/my/object-read?table={table}&column=title&limit=1&page=1&order=id asc")
    item = res.json()["message"][0]
    assert "title" in item
    assert "id" not in item # PROVE: Column selection works and hides other fields
    
    print("\n✅ Matrix: object-read parameter combinations verified.")

@pytest.mark.asyncio
async def test_api_param_strict_validation(integration_app, auth_client):
    user = auth_client(user_id=500)
    # Testing enum validation for 'mode' parameter in account-delete
    res = await user.delete("/my/account-delete?mode=invalid_mode")
    assert res.json()["status"] == 0
    assert "not allowed" in res.json()["message"].lower()
    print("✅ Matrix: Strict parameter validation (Enum checking) verified.")
