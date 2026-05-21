import pytest

@pytest.mark.asyncio
async def test_my_mongodb_create(integration_app, auth_client):
    user = auth_client(user_id=1)
    db, table = "test_db", "test_collection"
    
    # 0. CLEAN the collection to prevent leakage
    mongo_client = integration_app.app.state.client_mongodb
    await mongo_client[db][table].delete_many({})
    
    # 1. Create multiple objects in MongoDB using the correct 'obj_list' envelope
    payload = {
        "obj_list": [
            {"name": "Mongo Item 1", "data": {"key": "val1"}},
            {"name": "Mongo Item 2", "data": {"key": "val2"}}
        ]
    }
    res = await user.post(f"/my/object-create-mongodb?database={db}&table={table}", json=payload)
    
    assert res.json()["status"] == 1
    inserted_ids = res.json()["message"]
    assert len(inserted_ids) == 2
    
    # 2. Verify in real MongoDB
    count = await mongo_client[db][table].count_documents({})
    assert count == 2
    print(f"\n✅ MongoDB: Direct creation in '{db}.{table}' verified.")

@pytest.mark.asyncio
async def test_admin_mongodb_import(integration_app, auth_client):
    admin = auth_client(role=1)
    db, table = "admin_db", "import_collection"
    
    # 0. CLEAN the collection
    mongo_client = integration_app.app.state.client_mongodb
    await mongo_client[db][table].delete_many({})
    
    # 1. Create a CSV for MongoDB
    csv_data = b"name,email,metadata\nImported 1,imported1@example.com,\"{\"\"source\"\": \"\"test\"\"}\"\nImported 2,imported2@example.com,\"{\"\"source\"\": \"\"test\"\"}\"\n"
    files = {"file": ("mongo.csv", csv_data, "text/csv")}
    data = {"mode": "create", "database": db, "table": table}
    
    res = await admin.post("/admin/mongodb-import", data=data, files=files)
    
    assert res.json()["status"] == 1
    assert "2 rows processed" in res.json()["message"]
    
    # 2. Verify the data
    doc = await mongo_client[db][table].find_one({"name": "Imported 1"})
    assert doc["email"] == "imported1@example.com"
    print("✅ MongoDB: Bulk Admin Import verified.")

@pytest.mark.asyncio
async def test_admin_mongodb_import_update_and_delete(integration_app, auth_client):
    admin = auth_client(role=1)
    db, table = "admin_db", "import_collection_modes"

    mongo_client = integration_app.app.state.client_mongodb
    collection = mongo_client[db][table]
    await collection.delete_many({})
    await collection.insert_many([
        {"_id": "mongo_import_1", "name": "Before 1", "email": "before1@example.com"},
        {"_id": "mongo_import_2", "name": "Before 2", "email": "before2@example.com"},
    ])

    update_csv = b"_id,name,email\nmongo_import_1,After 1,after1@example.com\nmongo_import_2,After 2,after2@example.com\n"
    update_res = await admin.post(
        "/admin/mongodb-import",
        data={"mode": "update", "database": db, "table": table},
        files={"file": ("mongo_update.csv", update_csv, "text/csv")},
    )

    assert update_res.status_code == 200
    assert update_res.json() == {"status": 1, "message": "2 rows processed"}
    doc = await collection.find_one({"_id": "mongo_import_1"})
    assert doc["name"] == "After 1"
    assert doc["email"] == "after1@example.com"

    delete_csv = b"id\nmongo_import_2\n"
    delete_res = await admin.post(
        "/admin/mongodb-import",
        data={"mode": "delete", "database": db, "table": table},
        files={"file": ("mongo_delete.csv", delete_csv, "text/csv")},
    )

    assert delete_res.status_code == 200
    assert delete_res.json() == {"status": 1, "message": "1 rows processed"}
    assert await collection.find_one({"_id": "mongo_import_2"}) is None
    assert await collection.find_one({"_id": "mongo_import_1"}) is not None
