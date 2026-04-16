async def func_s3_bucket_create(*, client_s3: any, config_s3_region_name: str, bucket: str) -> any:
    """Create a new AWS S3 bucket in a specific region."""
    return await client_s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": config_s3_region_name})

async def func_s3_bucket_public(*, client_s3: any, bucket: str) -> any:
    """Expose an AWS S3 bucket for public read access."""
    await client_s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
    return await client_s3.put_bucket_policy(Bucket=bucket, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}""".replace("bucket_name", bucket))

def func_s3_bucket_empty(*, client_s3_resource: any, bucket: str) -> any:
    """Purge all objects from an AWS S3 bucket."""
    return client_s3_resource.Bucket(bucket).objects.all().delete()

async def func_s3_bucket_delete(*, client_s3: any, bucket: str) -> any:
    """Delete an AWS S3 bucket."""
    return await client_s3.delete_bucket(Bucket=bucket)

def func_s3_url_delete(*, client_s3_resource: any, url: list) -> any:
    """Delete multiple objects from AWS S3 in bulk given their public URLs."""
    for file_url in url:
        bucket = file_url.split("//", 1)[1].split(".", 1)[0]
        key = file_url.rsplit("/", 1)[1]
        client_s3_resource.Object(bucket, key).delete()
    return "urls deleted"

async def func_s3_upload(*, client_s3: any, bucket: str, file_obj: any, config_s3_limit_kb: int) -> str:
    """Upload a file to AWS S3 bucket with unique key generation and size limit check."""
    import uuid
    file_data = await file_obj.read()
    if len(file_data) > config_s3_limit_kb * 1024:
        raise Exception(f"file size exceeds {config_s3_limit_kb}kb")
    ext = file_obj.filename.split(".")[-1] if "." in file_obj.filename else "bin"
    file_key = f"{uuid.uuid4().hex}.{ext}"
    await client_s3.put_object(Bucket=bucket, Key=file_key, Body=file_data)
    return f"https://{bucket}.s3.amazonaws.com/{file_key}"

def func_s3_upload_presigned(*, client_s3: any, config_s3_region_name: str, bucket: str, config_s3_limit_kb: int, config_s3_presigned_expire_sec: int) -> dict:
    """Generate a presigned POST URL for secure client-side binary uploads to S3 with unique key generation."""
    import uuid
    file_key = f"{uuid.uuid4().hex}.bin"
    presigned_post = client_s3.generate_presigned_post(Bucket=bucket, Key=file_key, ExpiresIn=config_s3_presigned_expire_sec, Conditions=[["content-length-range", 1, config_s3_limit_kb * 1024]])
    return {**presigned_post["fields"], "url_final": f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{file_key}"}
