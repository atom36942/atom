import pytest
import json

@pytest.mark.asyncio
async def test_flat_list_filtering(integration_app):
    """Test the new flat list SQL-like filtering syntax via the API."""
    pool = integration_app.app.state.client_postgres_pool
    
    # 1. Seed data
    await pool.execute("DELETE FROM test")
    await pool.execute("INSERT INTO test (title, type, is_active, rating) VALUES ('Apple iPhone', 1, 1, 4.5)")
    await pool.execute("INSERT INTO test (title, type, is_active, rating) VALUES ('Samsung Galaxy', 1, 1, 4.8)")
    await pool.execute("INSERT INTO test (title, type, is_active, rating) VALUES ('Nokia 3310', 2, 0, 3.0)")
    await pool.execute("INSERT INTO test (title, type, is_active, rating) VALUES ('Google Pixel', 1, 1, 4.2)")

    # 2. Test simple equality in list
    payload = {
        "table": "test",
        "filter": ["type = 1", "is_active = 1"]
    }
    res = await integration_app.get("/public/object-read", params={"table": "test", "filter": json.dumps(["type = 1", "is_active = 1"])})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == 1
    assert len(data["message"]) == 3
    
    # 3. Test ILIKE pattern
    res = await integration_app.get("/public/object-read", params={"table": "test", "filter": json.dumps(["title ILIKE '%apple%'"])})
    assert res.status_code == 200
    assert len(res.json()["message"]) == 1
    assert res.json()["message"][0]["title"] == "Apple iPhone"

    # 4. Test OR logic in flat string
    res = await integration_app.get("/public/object-read", params={"table": "test", "filter": json.dumps(["type = 2 OR title ILIKE '%Samsung%'"])})
    assert res.status_code == 200
    assert len(res.json()["message"]) == 2 # Nokia and Samsung
    
    # 5. Test IN operator
    res = await integration_app.get("/public/object-read", params={"table": "test", "filter": json.dumps(["type IN (1, 2)", "rating > 4.0"])})
    assert res.status_code == 200
    assert len(res.json()["message"]) == 3 # iPhone, Galaxy, Pixel

    # 6. Test Mixed format (Legacy Dict + Flat String)
    payload_filter = [
        "is_active = 1",
        {"_or": [{"title": "ilike,%apple%"}, {"title": "ilike,%samsung%"}]}
    ]
    res = await integration_app.get("/public/object-read", params={"table": "test", "filter": json.dumps(payload_filter)})
    assert res.status_code == 200
    assert len(res.json()["message"]) == 2
    
    # 7. Test Between
    res = await integration_app.get("/public/object-read", params={"table": "test", "filter": json.dumps(["rating BETWEEN 4.0 AND 4.6"])})
    assert res.status_code == 200
    assert len(res.json()["message"]) == 2 # iPhone (4.5), Pixel (4.2)

    print("\n✅ Integration: Flat List SQL Filtering verified successfully.")
