import pytest

# ---------------------------------------------------------------------------
# All /private/ endpoints require S3 + auth — skip if not configured
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_private_no_token_rejected(client):
    r = await client.post("/private/s3-upload-file")
    assert r.status_code == 400
    assert "token" in r.json()["message"].lower() or "authorization" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_private_s3_upload_presigned_no_token(client):
    r = await client.post("/private/s3-upload-presigned?bucket=test&count=1")
    assert r.status_code == 400
