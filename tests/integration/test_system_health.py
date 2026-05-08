import pytest

@pytest.mark.asyncio
async def test_system_health_and_sync(integration_app, auth_client):
    # 1. Check /info API
    res_info = await integration_app.get("/info")
    if res_info.status_code != 200:
        print(f"❌ /info failed with {res_info.status_code}: {res_info.text}")
    assert res_info.status_code == 200
    assert "status" in res_info.json()
    print("\n✅ System: /info status check successful.")
    
    # 2. Check /admin/sync (Cache Reloading)
    admin = auth_client(role=1)
    res_sync = await admin.get("/admin/sync")
    if res_sync.status_code != 200:
        print(f"❌ /admin/sync failed with {res_sync.status_code}: {res_sync.text}")
    assert res_sync.status_code == 200
    assert res_sync.json()["message"] == "done"
    print("✅ System: /admin/sync (Cache reload) successful.")
