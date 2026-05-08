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
    csv_data = "name,val\nImported 1,100\nImported 2,200"
    files = {"file": ("mongo.csv", csv_data, "text/csv")}
    data = {"mode": "create", "database": db, "table": table}
    
    res = await admin.post("/admin/mongodb-import", data=data, files=files)
    
    assert res.json()["status"] == 1
    assert "2 rows processed" in res.json()["message"]
    
    # 2. Verify the data
    doc = await mongo_client[db][table].find_one({"name": "Imported 1"})
    assert doc["val"] == "100"
    print("✅ MongoDB: Bulk Admin Import verified.")
