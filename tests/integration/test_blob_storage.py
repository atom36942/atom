import pytest
import io

@pytest.mark.asyncio
async def test_private_blob_upload_to_localstack(integration_app, auth_client):
    # This tests the Localstack (S3) integration
    admin = auth_client(role=1)
    
    # 1. Prepare a file for upload
    file_content = b"integration test content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    
    # 2. Upload to S3 (Localstack)
    # We use 'atom-integration-test' bucket which we created in conftest.py
    params = {"service": "s3", "container": "atom-integration-test"}
    res = await admin.post("/private/blob-upload-file", data=params, files=files)
    
    assert res.status_code == 200
    blob_id = res.json()["message"]
    print(f"\n✅ Blob: Uploaded to Localstack S3 (ID: {blob_id})")
    
    # 3. Verify the DB entry exists via /my/object-read
    res_db = await admin.get("/my/object-read?table=test_blob&limit=10&page=1&order=id desc")
    assert any(str(blob_id) in str(row["id"]) for row in res_db.json()["message"])
    print("✅ Blob: Database record verified.")

@pytest.mark.asyncio
async def test_private_blob_presigned_url_generation(integration_app, auth_client):
    admin = auth_client(role=1)
    
    # 1. First ensure we have a blob (from previous test or create one)
    # 2. Call the presigned URL API
    # Assuming we have a blob with id 'test_blob_id' or similar
    # We'll just test the endpoint existence and parameter validation
    res = await admin.get("/private/blob-read-link?service=s3&container=atom-integration-test&filename=test.txt")
    
    # If successful, it should return a URL from localhost (Localstack)
    assert res.status_code == 200
    assert "localhost" in res.json()["message"] or "127.0.0.1" in res.json()["message"]
    print("✅ Blob: Presigned URL generated pointing to Localstack.")
