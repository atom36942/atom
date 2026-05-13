import pytest

@pytest.mark.asyncio
async def test_public_converter_roundtrip(integration_app):
    # Tests the ID encoder/decoder logic
    num = "123456"
    # 1. Encode
    res_enc = await integration_app.get(f"/public/converter-number?x={num}&mode=encode&datatype=bigint")
    assert res_enc.status_code == 200
    encoded = res_enc.json()["message"]
    
    # 2. Decode
    res_dec = await integration_app.get(f"/public/converter-number?x={encoded}&mode=decode&datatype=bigint")
    assert res_dec.status_code == 200
    decoded = res_dec.json()["message"]
    
    assert str(decoded) == str(num)
    print(f"\n✅ Public: Number {num} ➔ {encoded} ➔ {decoded} roundtrip successful.")

@pytest.mark.asyncio
async def test_public_table_groupby(integration_app):
    # Tests the generic groupby logic with new dynamic operations
    pool = integration_app.app.state.client_postgres_pool
    
    # 0. Clean up and Seed data
    await pool.execute("DELETE FROM test")
    await pool.execute("INSERT INTO test (type, title, tag, rating, price) VALUES (1, 'Obj 1', ARRAY['a'], 4.0, 10.0)")
    await pool.execute("INSERT INTO test (type, title, tag, rating, price) VALUES (1, 'Obj 2', ARRAY['a', 'b'], 5.0, 20.0)")
    await pool.execute("INSERT INTO test (type, title, tag, rating, price) VALUES (2, 'Obj 3', ARRAY['b'], 3.0, 30.0)")
        
    # 1. Test Default (count, array unnest, count desc)
    res = await integration_app.get("/public/table-groupby?table=test&col=tag")
    assert res.status_code == 200
    items = res.json()["message"]
    # 'a' appears twice, 'b' appears twice
    assert any(t["item"] == "a" and t["value"] == 2 for t in items)
    assert any(t["item"] == "b" and t["value"] == 2 for t in items)
    
    # 2. Test Sum operation (sum(price) grouped by type, item asc)
    res = await integration_app.get("/public/table-groupby?table=test&col=type&agg_func=sum&agg_col=price&order=item asc")
    assert res.status_code == 200
    items = res.json()["message"]
    # type 1: 10 + 20 = 30
    # type 2: 30
    assert items[0]["item"] == 1 and float(items[0]["value"]) == 30.0
    assert items[1]["item"] == 2 and float(items[1]["value"]) == 30.0
    
    # 3. Test Avg operation (avg(rating) grouped by type, count asc)
    res = await integration_app.get("/public/table-groupby?table=test&col=type&agg_func=avg&agg_col=rating&order=count asc")
    assert res.status_code == 200
    items = res.json()["message"]
    # type 1: (4+5)/2 = 4.5
    # type 2: 3.0
    # ordered by count asc: type 2 (1 row) then type 1 (2 rows)
    assert items[0]["item"] == 2 and float(items[0]["value"]) == 3.0
    assert items[1]["item"] == 1 and float(items[1]["value"]) == 4.5
    
    # 4. Test filtering logic (only where price > 15)
    res = await integration_app.get("/public/table-groupby?table=test&col=type&price=>,15")
    assert res.status_code == 200
    items = res.json()["message"]
    # price > 15: Obj 2 (type 1), Obj 3 (type 2)
    assert len(items) == 2
    assert all(t["value"] == 1 for t in items)
    
    print("✅ Public: Table GroupBy (dynamic ops, ordering, filtering) verified.")

@pytest.mark.asyncio
async def test_public_read_whitelist_security(integration_app):
    # Tests that /public/object-read only allows whitelisted tables
    # We explicitly set a whitelist for this test to verify the logic
    integration_app.app.state.config_table_read_enable_public = ["test"]
    
    # Flush the rate limiter to prevent it from firing before the whitelist check
    await integration_app.app.state.client_redis.flushdb()
    
    res = await integration_app.get("/public/object-read?table=users&limit=10&page=1&order=id desc")
    
    assert res.json()["status"] == 0
    assert "read disabled for table: users" in res.json()["message"].lower()
    print("✅ Public: Security whitelist blocked public access to 'users' table (when restricted).")
