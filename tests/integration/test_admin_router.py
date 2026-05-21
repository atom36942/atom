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
    
    # 2. Security: Read mode blocks modifying commands
    res = await admin.post("/admin/postgres-sql-runner", json={"mode": "read", "sql": "DROP TABLE users"})
    assert "restricted" in res.json()["message"].lower()
    
    # 3. Robustness: Parentheses in read mode
    res = await admin.post("/admin/postgres-sql-runner", json={"mode": "read", "sql": " ( SELECT 1 as val ) "})
    assert res.json()["status"] == 1
    assert res.json()["message"][0]["val"] == 1

    # 4. Security: Write mode
    app_state = integration_app.app.state
    res = await admin.post("/admin/postgres-sql-runner", json={"mode": "write", "sql": "DELETE FROM test WHERE 1=0"})
    if app_state.config_is_enable_postgres_sql_runner_write != 1:
        assert "disabled" in res.json()["message"].lower()
    else:
        assert res.json()["status"] == 1
    
    print("\n✅ Admin: Postgres Runner security and robustness verified.")

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
async def test_admin_postgres_import_constructed_csv(integration_app, auth_client):
    admin = auth_client(role=1)
    table = "test"

    pool = integration_app.app.state.client_postgres_pool
    await pool.execute(f"DELETE FROM {table}")

    csv_content = b"title,type,is_active,rating\nCSV Import 1,1,1,4.5\nCSV Import 2,2,0,3.5\n"
    expected_rows = len(csv_content.decode("utf-8").splitlines()) - 1
    files = {"file": ("postgres_create.csv", csv_content, "text/csv")}
    data = {"table": table, "mode": "create"}

    res = await admin.post("/admin/postgres-import", data=data, files=files)

    assert res.status_code == 200
    assert res.json()["status"] == 1
    assert res.json()["message"] == f"{expected_rows} rows processed"

    count = await pool.fetchval(f"SELECT count(*) FROM {table}")
    assert count == expected_rows

@pytest.mark.asyncio
async def test_admin_postgres_import_update_and_delete_constructed_csv(integration_app, auth_client):
    admin = auth_client(role=1)
    table = "test"

    pool = integration_app.app.state.client_postgres_pool
    await pool.execute(f"DELETE FROM {table}")
    rows = await pool.fetch(
        f"""
        INSERT INTO {table} (title, type, is_active, rating, created_by_id)
        VALUES
            ('Before Import Update 1', 1, 1, 1.0, 1),
            ('Before Import Update 2', 1, 1, 1.0, 1)
        RETURNING id
        """
    )
    ids = [row["id"] for row in rows]

    update_csv = f"id,title,rating\n{ids[0]},After Import Update 1,4.5\n{ids[1]},After Import Update 2,4.8\n".encode()
    update_res = await admin.post(
        "/admin/postgres-import",
        data={"table": table, "mode": "update"},
        files={"file": ("postgres_update.csv", update_csv, "text/csv")},
    )

    assert update_res.status_code == 200
    assert update_res.json() == {"status": 1, "message": "2 rows processed"}
    updated_title = await pool.fetchval(f"SELECT title FROM {table} WHERE id=$1", ids[0])
    assert updated_title == "After Import Update 1"

    delete_csv = f"id\n{ids[0]}\n{ids[1]}\n".encode()
    delete_res = await admin.post(
        "/admin/postgres-import",
        data={"table": table, "mode": "delete"},
        files={"file": ("postgres_delete.csv", delete_csv, "text/csv")},
    )

    assert delete_res.status_code == 200
    assert delete_res.json() == {"status": 1, "message": "2 rows processed"}
    remaining = await pool.fetchval(f"SELECT count(*) FROM {table} WHERE id = ANY($1::bigint[])", ids)
    assert remaining == 0

@pytest.mark.asyncio
async def test_admin_redis_import(integration_app, auth_client):
    admin = auth_client(role=1)
    
    csv_data = b'key,value\nredis_int_1,"{""name"": ""Alice"", ""role"": ""admin""}"\nredis_int_2,plain-value\n'
    files = {"file": ("redis.csv", csv_data, "text/csv")}
    data = {"mode": "create"}
    
    res = await admin.post("/admin/redis-import", data=data, files=files)
    assert res.status_code == 200
    assert res.json()["status"] == 1
    assert res.json()["message"] == "2 rows processed"
    
    # Verify in real Redis
    redis_client = integration_app.app.state.client_redis
    val = await redis_client.get("redis_int_1")
    assert b"Alice" in val

    delete_res = await admin.post(
        "/admin/redis-import",
        data={"mode": "delete"},
        files={"file": ("redis_delete.csv", b"key\nredis_int_1\n", "text/csv")},
    )
    assert delete_res.status_code == 200
    assert delete_res.json() == {"status": 1, "message": "1 rows processed"}
    assert await redis_client.get("redis_int_1") is None
    assert await redis_client.get("redis_int_2") is not None
    print("✅ Admin: Redis Bulk Import verified.")
