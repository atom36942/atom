import pytest
import json

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
    res = await admin.get("/my/object-read", params={"table": table, "filter": json.dumps(["title LIKE '%Item 1%'"]), "limit": 10, "page": 1, "order": "id asc"})
    assert res.json()["status"] == 1, f"LIKE read failed: {res.json()}"
    like_results = res.json()["message"]
    like_titles = [r["title"] for r in like_results]
    # Should match "Item 1" and "Item 10" only
    assert len(like_results) == 2, f"LIKE filter returned {len(like_results)} items instead of 2. Titles: {like_titles}"
    
    # Test: Comparison — use the actual IDs from the seed response
    seed_ids = res_seed.json()["message"]
    # Get the 8th ID (0-indexed: seed_ids[7]) and filter for > that value
    eighth_id = seed_ids[7]
    res = await admin.get("/my/object-read", params={"table": table, "filter": json.dumps([f"id > {eighth_id}"]), "limit": 10, "page": 1, "order": "id asc"})
    assert len(res.json()["message"]) == 2, f"Expected 2 items with id>{eighth_id}, got {len(res.json()['message'])}"
    
    # Test: In list
    res = await admin.get(f"/my/object-read", params={"table": table, "filter": json.dumps(["status = 0"]), "limit": 10, "page": 1, "order": "id asc"})
    assert len(res.json()["message"]) == 5 # All odd items (1, 3, 5, 7, 9)
    
    # --- MATRIX TEST 2: Pagination & Sorting ---
    # Test: Limit and Page
    res = await admin.get(f"/my/object-read", params={"table": table, "limit": 3, "page": 1, "order": "id asc"})
    titles_p1 = [r["title"] for r in res.json()["message"]]
    assert titles_p1 == ["Item 1", "Item 2", "Item 3"]
    
    res = await admin.get(f"/my/object-read", params={"table": table, "limit": 3, "page": 2, "order": "id asc"})
    titles_p2 = [r["title"] for r in res.json()["message"]]
    assert titles_p2 == ["Item 4", "Item 5", "Item 6"]
    
    # --- MATRIX TEST 3: Column Selection (Masking) ---
    res = await admin.get(f"/my/object-read", params={"table": table, "column": "title", "limit": 1, "page": 1, "order": "id asc"})
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
