"""Atom storage functions."""

async def func_blob_url_delete(*, app_state: any, service: str, urls: list, user_id: int = None) -> list:
    """Deletes S3 or Azure blobs by their URLs, optionally enforcing user ownership."""
    import urllib.parse
    import asyncio
    if (service == "s3" and not app_state.client_s3) or (service == "azure" and not app_state.client_azure_blob):
        raise Exception("blob client not initialized")
    tasks = []
    deleted_urls = []
    if service == "s3":
        s3_batches = {}
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            host_parts = parsed.netloc.split(".")
            if host_parts[0] != "s3":
                bucket = host_parts[0]
                key = parsed.path.lstrip("/")
            else:
                parts = parsed.path.lstrip("/").split("/", 1)
                if len(parts) != 2: continue
                bucket, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            if user_id is not None and not decoded_key.startswith(f"user_{user_id}/"): continue
            s3_batches.setdefault(bucket, []).append({"Key": decoded_key})
            deleted_urls.append(url)
        for bucket, keys in s3_batches.items():
            for i in range(0, len(keys), 1000):
                tasks.append(app_state.client_s3.delete_objects(Bucket=bucket, Delete={"Objects": keys[i:i+1000], "Quiet": True}))
    elif service == "azure":
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            parts = parsed.path.lstrip("/").split("/", 1)
            if len(parts) != 2: continue
            container, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            if user_id is not None and not decoded_key.startswith(f"user_{user_id}/"): continue
            tasks.append(app_state.client_azure_blob.get_blob_client(container=container, blob=decoded_key).delete_blob())
            deleted_urls.append(url)
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                if type(res).__name__ != "ResourceNotFoundError": raise res
        return deleted_urls

async def func_blob_preview_urls_get(*, client_s3: any, client_azure_blob: any, config_azure_account_name: str, config_azure_account_key: str, config_blob_expire_sec_preview: int, service: str, urls: list) -> dict:
    """Generates presigned preview URLs for S3 or Azure blob URLs using robust parsing and unquoting."""
    import urllib.parse
    from datetime import datetime, timedelta, timezone
    from azure.storage.blob import BlobSasPermissions, generate_blob_sas
    if (service == "s3" and not client_s3) or (service == "azure" and not client_azure_blob):
        raise Exception("blob client not initialized")
    if service == "azure" and (not config_azure_account_name or not config_azure_account_key):
        raise Exception("azure storage credentials not configured")
    output = {}
    if service == "s3":
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            host_parts = parsed.netloc.split(".")
            if host_parts[0] != "s3":
                bucket = host_parts[0]
                key = parsed.path.lstrip("/")
            else:
                parts = parsed.path.lstrip("/").split("/", 1)
                if len(parts) != 2: continue
                bucket, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            presigned_url = client_s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket, 'Key': decoded_key}, ExpiresIn=config_blob_expire_sec_preview)
            output[url] = presigned_url
    elif service == "azure":
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            parts = parsed.path.lstrip("/").split("/", 1)
            if len(parts) != 2: continue
            container, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            sas_token = generate_blob_sas(account_name=config_azure_account_name, account_key=config_azure_account_key, container_name=container, blob_name=decoded_key, permission=BlobSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=config_blob_expire_sec_preview))
            output[url] = f"https://{config_azure_account_name}.blob.core.windows.net/{container}/{decoded_key}?{sas_token}"
    return output

async def func_blob_delete_all(*, app_state: any, user_id: int, limit: int = 500) -> dict:
    """Fetches and deletes a batch of blobs for a user, marking them as deleted in the database."""
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    async with app_state.client_postgres.acquire() as conn:
        records = await conn.fetch("SELECT id, file_url, service FROM blob WHERE created_by_id = $1 AND deleted_at IS NULL LIMIT $2", user_id, limit + 1)
    if not records: return {"deleted_count": 0, "has_more": False, "has_next_page": False}
    has_more = len(records) > limit
    process_records = records[:limit]
    s3_urls = [r["file_url"] for r in process_records if r["service"] == "s3"]
    azure_urls = [r["file_url"] for r in process_records if r["service"] == "azure"]
    if s3_urls: await app_state.func_blob_url_delete(app_state=app_state, service="s3", urls=s3_urls, user_id=user_id)
    if azure_urls: await app_state.func_blob_url_delete(app_state=app_state, service="azure", urls=azure_urls, user_id=user_id)
    ids_to_update = [r["id"] for r in process_records]
    async with app_state.client_postgres.acquire() as conn:
        await conn.execute("UPDATE blob SET deleted_at = NOW(), deleted_by_id = $1 WHERE id = ANY($2::bigint[])", user_id, ids_to_update)
    return {"deleted_count": len(process_records), "has_more": has_more, "has_next_page": has_more}

async def func_blob_upload_file(*, app_state: any, service: str, container: str, files: list, user_id: int = None) -> dict:
    """Uploads a list of UploadFile objects to S3 or Azure and logs them in the database."""
    import uuid
    if not app_state.client_postgres or (service == "s3" and not app_state.client_s3) or (service == "azure" and not app_state.client_azure_blob):
        raise Exception("required postgres/blob client not initialized")
    if len(files) > app_state.config_blob_limit_upload:
        raise Exception(f"maximum {app_state.config_blob_limit_upload} files allowed")
    output = {}
    blob_list = []
    container_client = app_state.client_azure_blob.get_container_client(container) if service == "azure" else None
    for item in files:
        file_data = await item.read()
        if len(file_data) > app_state.config_blob_limit_size_kb * 1024:
            raise Exception(f"file size exceeds {app_state.config_blob_limit_size_kb}kb")
        ext = item.filename.split(".")[-1] if "." in item.filename else "bin"
        file_key = f"user_{user_id}/{uuid.uuid4().hex}.{ext}" if user_id else f"public/{uuid.uuid4().hex}.{ext}"
        if service == "s3":
            await app_state.client_s3.put_object(Bucket=container, Key=file_key, Body=file_data)
            file_url = f"https://{container}.s3.amazonaws.com/{file_key}"
        elif service == "azure":
            blob_client = container_client.get_blob_client(file_key)
            await blob_client.upload_blob(file_data)
            file_url = blob_client.url
        output[item.filename] = file_url
        blob_list.append({"created_by_id": user_id, "type": 1, "service": service, "file_url": file_url})
    if blob_list:
        await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_column_regex=app_state.config_column_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table="blob", obj_list=blob_list)
    return output

async def func_blob_upload_url(*, app_state: any, service: str, container: str, count: int, user_id: int = None) -> list:
    """Generates presigned upload URLs (S3 post fields or Azure SAS URLs) for client-side uploads and logs them in the database."""
    import uuid
    from datetime import datetime, timedelta, timezone
    from azure.storage.blob import BlobSasPermissions, generate_blob_sas
    if not app_state.client_postgres or (service == "s3" and not app_state.client_s3):
        raise Exception("required postgres/blob client not initialized")
    if service == "azure" and (not app_state.config_azure_account_name or not app_state.config_azure_account_key):
        raise Exception("azure storage credentials not configured")
    if count > app_state.config_blob_limit_upload:
        raise Exception(f"maximum {app_state.config_blob_limit_upload} allowed")
    output = []
    blob_list = []
    for _ in range(count):
        file_key = f"user_{user_id}/{uuid.uuid4().hex}.bin" if user_id else f"public/{uuid.uuid4().hex}.bin"
        if service == "s3":
            presigned_post = app_state.client_s3.generate_presigned_post(Bucket=container, Key=file_key, ExpiresIn=app_state.config_blob_expire_sec_upload, Conditions=[["content-length-range", 1, app_state.config_blob_limit_size_kb * 1024]])
            file_url = f"https://{container}.s3.{app_state.config_aws_s3_region_name}.amazonaws.com/{file_key}"
            output.append({"upload_url": presigned_post["url"], **presigned_post["fields"], "file_url": file_url})
        elif service == "azure":
            sas_token = generate_blob_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=container, blob_name=file_key, permission=BlobSasPermissions(write=True, create=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_blob_expire_sec_upload))
            sas_url = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}?{sas_token}"
            file_url = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}"
            output.append({"upload_url": sas_url, "key": file_key, "file_url": file_url})
        blob_list.append({"created_by_id": user_id, "type": 2, "service": service, "file_url": file_url})
    if blob_list:
        await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_column_regex=app_state.config_column_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table="blob", obj_list=blob_list)
    return output

async def func_blob_containers_read(*, client_s3: any, client_azure_blob: any, service: str) -> list:
    """Lists names of all S3 buckets or Azure containers for the initialized client."""
    if (service == "s3" and not client_s3) or (service == "azure" and not client_azure_blob):
        raise Exception("blob client not initialized")
    if service == "s3":
        res = await client_s3.list_buckets()
        return [b["Name"] for b in res.get("Buckets", [])]
    elif service == "azure":
        output = []
        async for c in client_azure_blob.list_containers():
            output.append(c.name)
        return output
    raise Exception(f"service {service} not supported")

async def func_blob_container_ops(*, client_s3: any, client_s3_resource: any, client_azure_blob: any, config_aws_s3_region_name: str, service: str, container: str, mode: str) -> any:
    """Creates, makes public, empties, or deletes S3 buckets or Azure Blob containers."""
    if (service == "s3" and ((mode == "empty" and not client_s3_resource) or (mode != "empty" and not client_s3))) or (service == "azure" and not client_azure_blob):
        raise Exception("blob client not initialized")
    res = None
    if service == "s3":
        if mode == "create":
            res = await client_s3.create_bucket(Bucket=container, CreateBucketConfiguration={"LocationConstraint": config_aws_s3_region_name})
        elif mode == "public":
            await client_s3.put_public_access_block(Bucket=container, PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
            res = await client_s3.put_bucket_policy(Bucket=container, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}""".replace("bucket_name", container))
        elif mode == "empty":
            res = client_s3_resource.Bucket(container).objects.all().delete()
        elif mode == "delete":
            res = await client_s3.delete_bucket(Bucket=container)
    elif service == "azure":
        from azure.storage.blob import PublicAccess
        if mode == "create":
            await client_azure_blob.create_container(container)
            res = {"service": service, "mode": mode, "container": container}
        elif mode == "public":
            container_client = client_azure_blob.get_container_client(container)
            await container_client.set_container_access_policy(signed_identifiers={}, public_access=PublicAccess.Blob)
            res = {"service": service, "mode": mode, "container": container}
        elif mode == "empty":
            container_client = client_azure_blob.get_container_client(container)
            deleted_count, batch = 0, []
            async for blob in container_client.list_blobs():
                batch.append(blob.name)
                if len(batch) >= 256:
                    delete_responses = await container_client.delete_blobs(*batch, delete_snapshots="include")
                    if hasattr(delete_responses, "__aiter__"):
                        async for _ in delete_responses: pass
                    deleted_count += len(batch)
                    batch = []
            if batch:
                delete_responses = await container_client.delete_blobs(*batch, delete_snapshots="include")
                if hasattr(delete_responses, "__aiter__"):
                    async for _ in delete_responses: pass
                deleted_count += len(batch)
            res = {"service": service, "mode": mode, "container": container, "deleted": deleted_count}
        elif mode == "delete":
            await client_azure_blob.delete_container(container)
            res = {"service": service, "mode": mode, "container": container}
        else:
            raise Exception(f"mode {mode} not supported for azure")
    return res
