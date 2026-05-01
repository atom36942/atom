import pytest
import asyncio
import os
from unittest.mock import MagicMock, AsyncMock, patch

# ---------------------------------------------------------------------------
# S3 Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_func_s3_bucket_create():
    from core.function.integration import func_s3_bucket_create
    mock_s3 = AsyncMock()
    await func_s3_bucket_create(client_s3=mock_s3, config_s3_region_name="us-east-1", bucket="test-bucket")
    mock_s3.create_bucket.assert_called_once_with(
        Bucket="test-bucket", 
        CreateBucketConfiguration={"LocationConstraint": "us-east-1"}
    )

@pytest.mark.asyncio
async def test_func_s3_bucket_public():
    from core.function.integration import func_s3_bucket_public
    mock_s3 = AsyncMock()
    await func_s3_bucket_public(client_s3=mock_s3, bucket="test-bucket")
    mock_s3.put_public_access_block.assert_called_once()
    mock_s3.put_bucket_policy.assert_called_once()

def test_func_s3_bucket_empty():
    from core.function.integration import func_s3_bucket_empty
    mock_resource = MagicMock()
    func_s3_bucket_empty(client_s3_resource=mock_resource, bucket="test-bucket")
    mock_resource.Bucket.assert_called_once_with("test-bucket")

def test_func_s3_url_delete():
    from core.function.integration import func_s3_url_delete
    mock_resource = MagicMock()
    urls = ["https://bucket1.s3.amazonaws.com/file1.txt"]
    res = func_s3_url_delete(client_s3_resource=mock_resource, url=urls)
    assert res == "urls deleted"
    mock_resource.Object.assert_called_once_with("bucket1", "file1.txt")

@pytest.mark.asyncio
async def test_func_s3_upload_file():
    from core.function.integration import func_s3_upload_file
    mock_s3 = AsyncMock()
    mock_file = AsyncMock()
    mock_file.filename = "test.txt"
    mock_file.read.return_value = b"content"
    
    res = await func_s3_upload_file(
        client_s3=mock_s3, 
        bucket="test-bucket", 
        file_list=[mock_file], 
        config_s3_limit_kb=10, 
        config_s3_upload_limit_count=5
    )
    assert "test.txt" in res
    mock_s3.put_object.assert_called_once()

@pytest.mark.asyncio
async def test_func_s3_upload_file_limit_exceeded():
    from core.function.integration import func_s3_upload_file
    with pytest.raises(Exception, match="maximum 1 files allowed"):
        await func_s3_upload_file(
            client_s3=AsyncMock(), 
            bucket="test", 
            file_list=[AsyncMock(), AsyncMock()], 
            config_s3_limit_kb=10, 
            config_s3_upload_limit_count=1
        )

def test_func_s3_upload_url_presigned():
    from core.function.integration import func_s3_upload_url_presigned
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_post.return_value = {"fields": {"key": "val"}}
    res = func_s3_upload_url_presigned(
        client_s3=mock_s3,
        config_s3_region_name="us-east-1",
        bucket="test",
        config_s3_limit_kb=100,
        config_s3_presigned_expire_sec=3600,
        count=1,
        config_s3_upload_limit_count=5
    )
    assert len(res) == 1
    assert "url_final" in res[0]

# ---------------------------------------------------------------------------
# SNS / SES Tests
# ---------------------------------------------------------------------------

def test_func_sns_send_mobile_message():
    from core.function.integration import func_sns_send_mobile_message
    mock_sns = MagicMock()
    func_sns_send_mobile_message(client_sns=mock_sns, mobile="123456", message="hi")
    mock_sns.publish.assert_called_once_with(PhoneNumber="123456", Message="hi")

def test_func_sns_send_mobile_message_template():
    from core.function.integration import func_sns_send_mobile_message_template
    mock_sns = MagicMock()
    func_sns_send_mobile_message_template(
        client_sns=mock_sns, mobile="123456", message="hi", 
        template_id="t1", entity_id="e1", sender_id="s1"
    )
    mock_sns.publish.assert_called_once()

def test_func_ses_send_email():
    from core.function.integration import func_ses_send_email
    mock_ses = MagicMock()
    func_ses_send_email(client_ses=mock_ses, from_email="a@b.com", to_emails=["c@d.com"], subject="s", body="b")
    mock_ses.send_email.assert_called_once()

# ---------------------------------------------------------------------------
# Resend / GSheet Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_func_resend_send_email():
    from core.function.integration import func_resend_send_email
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        await func_resend_send_email(
            config_resend_url="http://resend", config_resend_key="k", 
            from_email="a@b.com", to_email="c@d.com", 
            email_subject="s", email_content="c"
        )
        mock_post.assert_called_once()

def test_func_gsheet_object_create():
    from core.function.integration import func_gsheet_object_create
    mock_gsheet = MagicMock()
    mock_ws = MagicMock()
    mock_ws.id = 123
    mock_gsheet.open_by_key.return_value.worksheets.return_value = [mock_ws]
    
    func_gsheet_object_create(
        client_gsheet=mock_gsheet, 
        sheet_url="https://docs.google.com/spreadsheets/d/SID/edit?gid=123", 
        obj_list=[{"col1": "val1"}]
    )
    mock_ws.append_rows.assert_called_once()

@pytest.mark.asyncio
async def test_func_gsheet_object_read():
    from core.function.integration import func_gsheet_object_read
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text.return_value = "col1,col2\nval1,val2"
        mock_get.return_value.__aenter__.return_value = mock_resp
        
        with patch("pandas.read_csv") as mock_pd:
            mock_df = MagicMock()
            mock_df.where.return_value.to_dict.return_value = [{"col1": "val1"}]
            mock_pd.return_value = mock_df
            
            res = await func_gsheet_object_read(sheet_url="https://docs.google.com/spreadsheets/d/SID/edit?gid=0")
            assert len(res) == 1

# ---------------------------------------------------------------------------
# MongoDB / Redis / Jira Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_func_mongodb_create():
    from core.function.integration import func_mongodb_create
    mock_mongo = MagicMock()
    mock_db = MagicMock()
    mock_coll = AsyncMock()
    mock_mongo.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_coll
    
    async def mock_chunks(**kwargs):
        yield [{"k": "v"}]
        
    res = await func_mongodb_create(
        upload_file=None, client_mongodb=mock_mongo, 
        database="db", table="table", 
        func_api_file_to_chunks=mock_chunks
    )
    assert res == 1
    mock_coll.insert_many.assert_called_once()

@pytest.mark.asyncio
async def test_func_redis_create():
    from core.function.integration import func_redis_create
    mock_redis = MagicMock()
    mock_pipe = AsyncMock()
    mock_redis.pipeline.return_value.__aenter__.return_value = mock_pipe
    
    async def mock_chunks(**kwargs):
        yield [{"key": "k1", "value": "v1"}]
        
    res = await func_redis_create(
        upload_file=None, client_redis=mock_redis, 
        config_redis_cache_ttl_sec=60, 
        func_api_file_to_chunks=mock_chunks
    )
    assert res == 1
    mock_pipe.setex.assert_called_once()

def test_func_jira_worklog_export():
    from core.function.integration import func_jira_worklog_export
    # Mock JIRA client to avoid network calls
    with patch("jira.JIRA") as mock_jira:
        mock_client = mock_jira.return_value
        mock_client.enhanced_search_issues.return_value = []
        
        res = func_jira_worklog_export(
            url="http://jira", email="e", api_token="t", 
            start_date="2024-01-01", end_date="2024-01-02", 
            output_path="tmp/test_jira.csv"
        )
        assert res == "tmp/test_jira.csv"
        assert os.path.exists(res)
        if os.path.exists(res): os.remove(res)
