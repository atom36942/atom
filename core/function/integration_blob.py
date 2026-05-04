async def func_s3_container_create(*, client_s3: any, config_s3_region_name: str, bucket: str) -> any:
    """Create a new AWS S3 bucket in a specific region."""
    if not bucket: raise Exception("bucket name required")
    return await client_s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": config_s3_region_name})

async def func_s3_container_public(*, client_s3: any, bucket: str) -> any:
    """Expose an AWS S3 bucket for public read access."""
    if not bucket: raise Exception("bucket name required")
    await client_s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
    return await client_s3.put_bucket_policy(Bucket=bucket, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}""".replace("bucket_name", bucket))

def func_s3_container_empty(*, client_s3_resource: any, bucket: str) -> any:
    """Purge all objects from an AWS S3 bucket."""
    if not bucket: raise Exception("bucket name required")
    return client_s3_resource.Bucket(bucket).objects.all().delete()

async def func_s3_container_delete(*, client_s3: any, bucket: str) -> any:
    """Delete an AWS S3 bucket."""
    if not bucket: raise Exception("bucket name required")
    return await client_s3.delete_bucket(Bucket=bucket)

async def func_s3_container_read(*, client_s3: any) -> list:
    """List all AWS S3 bucket names."""
    response = await client_s3.list_buckets()
    return [bucket["Name"] for bucket in response.get("Buckets", [])]

async def func_s3_url_delete(*, client_s3: any, url: list) -> any:
    """Delete multiple objects from AWS S3 in high-performance bulk batches (up to 1000)."""
    # Group URLs by bucket to use bulk delete_objects API
    batches = {}
    for file_url in url:
        # URL: https://{bucket}.s3.amazonaws.com/{key}
        bucket = file_url.split("//", 1)[1].split(".", 1)[0]
        key = file_url.split(".com/", 1)[1]
        if bucket not in batches: batches[bucket] = []
        batches[bucket].append({"Key": key})
    
    import asyncio
    tasks = []
    for bucket, keys in batches.items():
        # S3 delete_objects supports up to 1000 keys per call
        for i in range(0, len(keys), 1000):
            tasks.append(client_s3.delete_objects(Bucket=bucket, Delete={"Objects": keys[i:i+1000]}))
    
    if tasks: await asyncio.gather(*tasks)
    return "urls deleted"

async def func_s3_upload_file(*, client_s3: any, bucket: str, file_list: list, config_blob_limit_kb: int, config_blob_upload_limit_count: int) -> dict:
    import uuid
    if not bucket: raise Exception("bucket name required")
    if len(file_list) > config_blob_upload_limit_count:
        raise Exception(f"maximum {config_blob_upload_limit_count} files allowed")
    output = {}
    for item in file_list:
        file_data = await item.read()
        if len(file_data) > config_blob_limit_kb * 1024:
            raise Exception(f"file size exceeds {config_blob_limit_kb}kb for {item.filename}")
        ext = item.filename.split(".")[-1] if "." in item.filename else "bin"
        file_key = f"{uuid.uuid4().hex}.{ext}"
        await client_s3.put_object(Bucket=bucket, Key=file_key, Body=file_data)
        output[item.filename] = f"https://{bucket}.s3.amazonaws.com/{file_key}"
    return output

def func_s3_upload_url(*, client_s3: any, config_s3_region_name: str, bucket: str, config_blob_limit_kb: int, config_blob_expire_sec: int, count: int, config_blob_upload_limit_count: int) -> list:
    import uuid
    if not bucket: raise Exception("bucket name required")
    if count > config_blob_upload_limit_count:
        raise Exception(f"maximum {config_blob_upload_limit_count} allowed")
    output = []
    for _ in range(count):
        file_key = f"{uuid.uuid4().hex}.bin"
        presigned_post = client_s3.generate_presigned_post(Bucket=bucket, Key=file_key, ExpiresIn=config_blob_expire_sec, Conditions=[["content-length-range", 1, config_blob_limit_kb * 1024]])
        output.append({**presigned_post["fields"], "url_final": f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{file_key}"})
    return output

async def func_azure_upload_file(*, client_azure_blob: any, container: str, file_list: list, config_blob_limit_kb: int, config_blob_upload_limit_count: int) -> dict:
    """Upload multiple files to Azure Blob Storage."""
    import uuid
    if not container: raise Exception("container name required")
    if len(file_list) > config_blob_upload_limit_count:
        raise Exception(f"maximum {config_blob_upload_limit_count} files allowed")
    output = {}
    container_client = client_azure_blob.get_container_client(container)
    for item in file_list:
        file_data = await item.read()
        if len(file_data) > config_blob_limit_kb * 1024:
            raise Exception(f"file size exceeds {config_blob_limit_kb}kb for {item.filename}")
        ext = item.filename.split(".")[-1] if "." in item.filename else "bin"
        file_key = f"{uuid.uuid4().hex}.{ext}"
        blob_client = container_client.get_blob_client(file_key)
        await blob_client.upload_blob(file_data)
        output[item.filename] = blob_client.url
    return output

def func_azure_upload_url(*, client_azure_blob: any, config_azure_account_name: str, config_azure_account_key: str, container: str, config_blob_limit_kb: int, config_blob_expire_sec: int, count: int, config_blob_upload_limit_count: int) -> list:
    """Generate multiple URLs for uploading files to Azure Blob Storage using SAS tokens."""
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions
    from datetime import datetime, timedelta, timezone
    import uuid
    if not container: raise Exception("container name required")
    if count > config_blob_upload_limit_count:
        raise Exception(f"maximum {config_blob_upload_limit_count} allowed")
    output = []
    for _ in range(count):
        file_key = f"{uuid.uuid4().hex}.bin"
        sas_token = generate_blob_sas(
            account_name=config_azure_account_name,
            account_key=config_azure_account_key,
            container_name=container,
            blob_name=file_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=datetime.now(timezone.utc) + timedelta(seconds=config_blob_expire_sec)
        )
        sas_url = f"https://{config_azure_account_name}.blob.core.windows.net/{container}/{file_key}?{sas_token}"
        output.append({"url": sas_url, "file_key": file_key, "url_final": f"https://{config_azure_account_name}.blob.core.windows.net/{container}/{file_key}"})
    return output

async def func_azure_container_create(*, client_azure_blob: any, container: str) -> any:
    """Create a new Azure Blob container."""
    if not container: raise Exception("container name required")
    return await client_azure_blob.create_container(container)

async def func_azure_container_delete(*, client_azure_blob: any, container: str) -> any:
    """Delete an Azure Blob container."""
    if not container: raise Exception("container name required")
    return await client_azure_blob.delete_container(container)

async def func_azure_container_read(*, client_azure_blob: any) -> list:
    """List all Azure Blob container names."""
    containers = []
    async for container in client_azure_blob.list_containers():
        containers.append(container.name)
    return containers

async def func_azure_url_delete(*, client_azure_blob: any, url: list) -> any:
    """Delete multiple blobs from Azure in parallel given their public URLs."""
    import asyncio
    tasks = []
    for file_url in url:
        # URL: https://account.blob.core.windows.net/container/blob_name
        parts = file_url.split(".net/", 1)[1].split("/", 1)
        container = parts[0]
        blob_name = parts[1]
        blob_client = client_azure_blob.get_blob_client(container=container, blob=blob_name)
        tasks.append(blob_client.delete_blob())
    
    if tasks: await asyncio.gather(*tasks)
    return "urls deleted"
