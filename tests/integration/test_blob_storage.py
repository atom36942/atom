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
    assert res.status_code == 200, f"Upload failed: {res.text}"
    
    # The route returns {"status": 1, "message": {"test.txt": "https://..."}}
    data = res.json()
    assert data["status"] == 1
    assert "test.txt" in data["message"], f"Expected filename key in response: {data['message']}"
    file_url = data["message"]["test.txt"]
    assert "s3.amazonaws.com" in file_url or "atom-integration-test" in file_url
    print(f"\n✅ Blob: Uploaded to Localstack S3 (URL: {file_url})")
    
    # 3. Verify file exists in S3 via direct client call
    s3 = integration_app.app.state.client_s3
    # Extract the key from the URL (last part after the bucket)
    file_key = file_url.split("/")[-1]
    obj = await s3.get_object(Bucket="atom-integration-test", Key=file_key)
    body = await obj["Body"].read()
    assert body == file_content
    print("✅ Blob: File content verified in S3.")
