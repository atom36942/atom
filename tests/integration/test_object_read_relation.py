import pytest
import json

@pytest.mark.asyncio
async def test_object_read_relation_full_flow(integration_app):
    pool = integration_app.app.state.client_postgres_pool
    redis = integration_app.app.state.client_redis
    
    # 0. Clean up and Seed data
    await redis.flushdb()
    await pool.execute("DELETE FROM test_action")
    await pool.execute("DELETE FROM test")
    await pool.execute("DELETE FROM users WHERE username IN ('cre_1', 'cre_2')")
    
    # Seed users
    u1_id = await pool.fetchval("INSERT INTO users (username, name, is_active, type) VALUES ('cre_1', 'Creator One', 1, 1) RETURNING id")
    u2_id = await pool.fetchval("INSERT INTO users (username, name, is_active, type) VALUES ('cre_2', 'Creator Two', 1, 1) RETURNING id")
    
    # Seed main table
    t1_id = await pool.fetchval("INSERT INTO test (title, created_by_id) VALUES ('Main Item 1', $1) RETURNING id", u1_id)
    t2_id = await pool.fetchval("INSERT INTO test (title, created_by_id) VALUES ('Main Item 2', $1) RETURNING id", u2_id)
    
    # Seed child table (actions)
    await pool.execute("INSERT INTO test_action (test_id, title) VALUES ($1, 'Action 1.1')", t1_id)
    await pool.execute("INSERT INTO test_action (test_id, title) VALUES ($1, 'Action 1.2')", t1_id)
    await pool.execute("INSERT INTO test_action (test_id, title) VALUES ($1, 'Action 1.3')", t1_id)
    await pool.execute("INSERT INTO test_action (test_id, title) VALUES ($1, 'Action 2.1')", t2_id)

    # 1. Test One-to-One (Fetch Creator)
    # Syntax: source_col,target_table,target_col,fetch|limit,cols
    relation_1 = "created_by_id,users,id,fetch|1,username,name"
    res = await integration_app.get(
        "/public/object-read",
        params={"table": "test", "relation": json.dumps([relation_1]), "order": "id asc"},
    )
    assert res.status_code == 200
    items = res.json()["message"]
    assert items[0]["users"]["username"] == "cre_1"
    assert items[1]["users"]["username"] == "cre_2"
    
    # 2. Test One-to-Many with Limit (Fetch Actions)
    # Syntax: source_col,target_table,target_col,fetch|limit,cols
    relation_2 = "id,test_action,test_id,fetch|2,id,title"
    res = await integration_app.get(
        "/public/object-read",
        params={"table": "test", "relation": json.dumps([relation_2]), "filter": json.dumps([f"id = {t1_id}"])},
    )
    assert res.status_code == 200
    item = res.json()["message"][0]
    # Should have exactly 2 actions even though 3 exist
    assert len(item["test_action"]) == 2
    
    # 3. Test Aggregate (Count Actions)
    # Syntax: source_col,target_table,target_col,count,cols
    relation_3 = "id,test_action,test_id,count,id"
    res = await integration_app.get(
        "/public/object-read",
        params={"table": "test", "relation": json.dumps([relation_3]), "order": "id asc"},
    )
    assert res.status_code == 200
    items = res.json()["message"]
    assert items[0]["test_action_count"] == 3 # T1 has 3 actions
    assert items[1]["test_action_count"] == 1 # T2 has 1 action
    
    # 4. Test Multiple Relations Combined
    res = await integration_app.get(
        "/public/object-read",
        params={"table": "test", "relation": json.dumps([relation_1, relation_3]), "order": "id asc"},
    )
    assert res.status_code == 200
    items = res.json()["message"]
    assert "users" in items[0]
    assert "test_action_count" in items[0]
    
    # 5. Error Case: Missing Limit
    bad_relation = "created_by_id,users,id,fetch,username"
    res = await integration_app.get(
        "/public/object-read",
        params={"table": "test", "relation": json.dumps([bad_relation])},
    )
    assert res.status_code == 400
    assert "explicit limit required" in res.json()["message"]
    
    # 6. Error Case: Exceeding Max Limit
    # Assuming config_relation_fetch_limit_max=100
    too_much = "created_by_id,users,id,fetch|500,username"
    res = await integration_app.get(
        "/public/object-read",
        params={"table": "test", "relation": json.dumps([too_much])},
    )
    assert res.status_code == 400
    assert "exceeds maximum allowed" in res.json()["message"]

    print("✅ Integration: Object Relation Engine (fetch|limit, count, security) verified.")
