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
async def test_public_tag_aggregation(integration_app):
    # Tests the Postgres 'unnest' tagging logic
    pool = integration_app.app.state.client_postgres_pool
    
    # 0. Clean up
    await pool.execute("DELETE FROM test")
    
    # 1. Seed data
    await pool.execute("INSERT INTO test (title, tag) VALUES ('Tag Test', ARRAY['alpha', 'beta'])")
        
    # 2. Call the tag aggregation API
    res = await integration_app.get("/public/table-tag-read?table=test&column=tag")
    assert res.status_code == 200
    tags = res.json()["message"]
    
    # Verify our tags are in the aggregation
    assert any(t["tag"] == "alpha" for t in tags)
    assert any(t["tag"] == "beta" for t in tags)
    print("✅ Public: Tag aggregation (unnest) verified.")

@pytest.mark.asyncio
async def test_public_read_whitelist_security(integration_app):
    # Tests that /public/object-read only allows whitelisted tables
    
    # Flush the rate limiter to prevent it from firing before the whitelist check
    await integration_app.app.state.client_redis_ratelimiter.flushdb()
    
    res = await integration_app.get("/public/object-read?table=users&limit=10&page=1&order=id desc")
    
    assert res.json()["status"] == 0
    assert "not allowed" in res.json()["message"].lower()
    print("✅ Public: Security whitelist blocked public access to 'users' table.")
