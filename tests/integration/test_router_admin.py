import pytest
import io

@pytest.mark.asyncio
async def test_admin_postgres_runner_and_security(integration_app, auth_client):
    admin = auth_client(role=1) # Admin role
    
    # 1. Valid Read Operation
    res = admin.post("/admin/postgres-runner", json={"mode": "read", "sql": "SELECT 1 as val"})
    assert res.json()["message"][0]["val"] == 1
    
    # 2. Security: Block forbidden keywords
    res = admin.post("/admin/postgres-runner", json={"mode": "write", "sql": "DROP TABLE users"})
    assert "forbidden" in res.json()["message"].lower()
    print("\n✅ Admin: Postgres Runner security (DROP blocking) verified.")

@pytest.mark.asyncio
async def test_admin_import_export_loop(integration_app, auth_client):
    admin = auth_client(role=1)
    table = "test"
    
    # 1. Seed data
    seed_payload = {"obj_list": [{"title": f"Row {i}"} for i in range(5)]}
    admin.post(f"/admin/object-create?table={table}", json=seed_payload)
    
    # 2. EXPORT data to CSV
    # postgres-export returns a StreamingResponse (CSV)
    export_res = admin.post(f"/admin/postgres-export?sql=SELECT title FROM {table}")
    assert export_res.status_code == 200
    csv_content = export_res.content
    assert b"Row 0" in csv_content
    print("✅ Admin: Postgres Export successful.")

    # 3. WIPE the table
    admin.post("/admin/postgres-runner", json={"mode": "write", "sql": f"DELETE FROM {table}"})
    
    # 4. IMPORT the CSV back
    # We simulate a file upload using the exported content
    files = {"file": ("test.csv", csv_content, "text/csv")}
    data = {"table": table, "mode": "create", "is_serialize": 0}
    import_res = admin.post("/admin/postgres-import", data=data, files=files)
    
    assert import_res.status_code == 200
    assert "5 rows processed" in import_res.json()["message"]
    print("✅ Admin: Postgres Import successful.")

    # 5. Verify the results
    read_res = admin.get(f"/admin/object-read?table={table}")
    assert len(read_res.json()["message"]) == 5
    print("✅ Admin: Data integrity verified after Export/Import cycle.")

@pytest.mark.asyncio
async def test_admin_redis_import(integration_app, auth_client):
    admin = auth_client(role=1)
    
    # Create a simple CSV for Redis: key,value
    csv_data = "key,value\nredis_int_1,val_1\nredis_int_2,val_2"
    files = {"file": ("redis.csv", csv_data, "text/csv")}
    data = {"mode": "create"}
    
    res = admin.post("/admin/redis-import", data=data, files=files)
    assert res.status_code == 200
    
    # Verify in real Redis
    redis_client = integration_app.app.state.client_redis
    val = await redis_client.get("redis_int_1")
    # Your logic orjson.dumps the value, so it will be "val_1"
    assert b"val_1" in val
    print("✅ Admin: Redis Bulk Import verified.")
