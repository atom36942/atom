import pytest
import io

@pytest.mark.asyncio
async def test_admin_postgres_runner_and_security(integration_app, auth_client):
    admin = auth_client(role=1) # Admin role
    
    # 1. Valid Read Operation
    res = await admin.post("/admin/postgres-sql-runner", json={"mode": "read", "sql": "SELECT 1 as val"})
    data = res.json()
    if data["status"] != 1:
        print(f"❌ Admin Runner failed: {data['message']}")
    assert data["status"] == 1
    assert data["message"][0]["val"] == 1
    
    # 2. Security: Block forbidden keywords
    res = await admin.post("/admin/postgres-sql-runner", json={"mode": "write", "sql": "DROP TABLE users"})
    assert "forbidden" in res.json()["message"].lower()
    print("\n✅ Admin: Postgres Runner security (DROP blocking) verified.")

@pytest.mark.asyncio
async def test_admin_import_export_loop(integration_app, auth_client):
    admin = auth_client(role=1)
    table = "test"
    
    # 0. Clean up
    pool = integration_app.app.state.client_postgres_pool
    await pool.execute(f"DELETE FROM {table}")
    
    # 1. Seed data
    seed_payload = {"obj_list": [{"title": f"Row {i}"} for i in range(5)]}
    res_seed = await admin.post(f"/my/object-create?table={table}&mode=now", json=seed_payload)
    assert res_seed.json()["status"] == 1
    
    # 2. EXPORT data to CSV
    export_res = await admin.post("/admin/postgres-export", json={"sql": f"SELECT title FROM {table}"})
    assert export_res.status_code == 200
    csv_content = export_res.content
    assert b"Row 0" in csv_content
    print("✅ Admin: Postgres Export successful.")

    # 3. WIPE the table
    await admin.post("/admin/postgres-sql-runner", json={"mode": "write", "sql": f"DELETE FROM {table}"})
    
    # 4. IMPORT the CSV back
    files = {"file": ("test.csv", csv_content, "text/csv")}
    data = {"table": table, "mode": "create"}
    import_res = await admin.post("/admin/postgres-import", data=data, files=files)
    
    if import_res.json()["status"] != 1:
        print(f"❌ Admin Import failed: {import_res.json()['message']}")
        
    assert import_res.status_code == 200
    assert "rows processed" in import_res.json()["message"].lower()
    print("✅ Admin: Postgres Import successful.")

    # 5. Verify the results
    read_res = await admin.get(f"/my/object-read?table={table}&limit=10&page=1&order=id desc")
    assert len(read_res.json()["message"]) == 5
    print("✅ Admin: Data integrity verified after Export/Import cycle.")

@pytest.mark.asyncio
async def test_admin_redis_import(integration_app, auth_client):
    admin = auth_client(role=1)
    
    # Create a simple CSV for Redis: key,value
    csv_data = "key,value\nredis_int_1,val_1\nredis_int_2,val_2"
    files = {"file": ("redis.csv", csv_data, "text/csv")}
    data = {"mode": "create"}
    
    res = await admin.post("/admin/redis-import", data=data, files=files)
    assert res.status_code == 200
    
    # Verify in real Redis
    redis_client = integration_app.app.state.client_redis
    val = await redis_client.get("redis_int_1")
    assert b"val_1" in val
    print("✅ Admin: Redis Bulk Import verified.")
