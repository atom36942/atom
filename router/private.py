# router
from fastapi import APIRouter
router = APIRouter()

# import
from fastapi import Request
import asyncio
import orjson
import uuid
from datetime import datetime, timedelta, timezone
from azure.storage.blob import generate_blob_sas, generate_container_sas, BlobSasPermissions, ContainerSasPermissions

# api
@router.post("/private/send-email")
async def func_api_private_send_email(request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("service", "str", 1, app_state.config_allowed_email_services, None), ("sender", "str", 1, None, None), ("to", "list", 1, None, None), ("subject", "str", 1, None, None), ("text", "str", 1, None, None), ("cc", "list", 0, None, []), ("bcc", "list", 0, None, []), ("reply_to", "list", 0, None, [])])
    message = None
    if ob["service"] == "ses":
        params = {"Source": ob["sender"], "Destination": {"ToAddresses": ob["to"], "CcAddresses": ob["cc"], "BccAddresses": ob["bcc"]}, "Message": {"Subject": {"Data": ob["subject"]}, "Body": {"Text": {"Data": ob["text"]}}}}
        if ob["reply_to"]: params["ReplyToAddresses"] = ob["reply_to"]
        response = app_state.client_ses.send_email(**params)
        message = {"id": response.get("MessageId")}
    elif ob["service"] == "resend":
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": ob["sender"], "to": ob["to"], "subject": ob["subject"], "text": ob["text"]}
        if ob["cc"]: payload["cc"] = ob["cc"]
        if ob["bcc"]: payload["bcc"] = ob["bcc"]
        if ob["reply_to"]: payload["reply_to"] = ob["reply_to"]
        response = await app_state.client_http.post(app_state.config_resend_url, headers=headers, content=orjson.dumps(payload))
        if response.status_code not in (200, 201): raise Exception(f"failed to send email: {response.text}")
        message = response.json()
    elif ob["service"] == "azure":
        if not app_state.client_azure_email: raise Exception("azure email client not configured")
        azure_message = {"senderAddress": ob["sender"], "recipients": {"to": [{"address": email} for email in ob["to"]]}, "content": {"subject": ob["subject"], "plainText": ob["text"]}}
        if ob["cc"]: azure_message["recipients"]["cc"] = [{"address": email} for email in ob["cc"]]
        if ob["bcc"]: azure_message["recipients"]["bcc"] = [{"address": email} for email in ob["bcc"]]
        if ob["reply_to"]: azure_message["replyTo"] = [{"address": email} for email in ob["reply_to"]]
        result = await asyncio.to_thread(lambda: app_state.client_azure_email.begin_send(azure_message).result())
        message = dict(result) if isinstance(result, dict) else {"id": getattr(result, "id", None), "status": getattr(result, "status", None)}
    return {"status":1,"message":message}

@router.post("/private/blob-upload-file")
async def func_api_private_blob_upload_file(request:Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("service", "str", 1, app_state.config_allowed_blob_services, None), ("file", "file", 1, None, None), ("container", "str", 0, None, app_state.config_blob_container_default)])
    container = of["container"]
    if len(of["file"]) > app_state.config_blob_upload_limit_count: raise Exception(f"maximum {app_state.config_blob_upload_limit_count} files allowed")
    output = {}; blob_list = []
    if of["service"] == "s3":
        for item in of["file"]:
            file_data = await item.read()
            if len(file_data) > app_state.config_blob_limit_kb * 1024: raise Exception(f"file size exceeds {app_state.config_blob_limit_kb}kb")
            ext = item.filename.split(".")[-1] if "." in item.filename else "bin"; file_key = f"{uuid.uuid4().hex}.{ext}"
            await app_state.client_s3.put_object(Bucket=container, Key=file_key, Body=file_data)
            file_url = f"https://{container}.s3.amazonaws.com/{file_key}"
            output[item.filename] = file_url; blob_list.append({"created_by_id": request.state.user["id"], "type": 1, "service": of["service"], "container": container, "blob_key": file_key, "file_url": file_url})
    elif of["service"] == "azure":
        container_client = app_state.client_azure_blob.get_container_client(container)
        for item in of["file"]:
            file_data = await item.read()
            if len(file_data) > app_state.config_blob_limit_kb * 1024: raise Exception(f"file size exceeds {app_state.config_blob_limit_kb}kb")
            ext = item.filename.split(".")[-1] if "." in item.filename else "bin"; file_key = f"{uuid.uuid4().hex}.{ext}"
            blob_client=container_client.get_blob_client(file_key); await blob_client.upload_blob(file_data)
            output[item.filename] = blob_client.url; blob_list.append({"created_by_id": request.state.user["id"], "type": 1, "service": of["service"], "container": container, "blob_key": file_key, "file_url": blob_client.url})
    if blob_list: await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, config_table=app_state.config_table, config_obj_list_limit=app_state.config_obj_list_limit, config_buffer_limit=app_state.config_buffer_limit, mode="now", table="blob", obj_list=blob_list)
    return {"status":1,"message":output}

@router.post("/private/blob-upload-url")
async def func_api_private_blob_upload_url(request:Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, app_state.config_allowed_blob_services, None), ("count", "int", 0, None, 1), ("container", "str", 0, None, app_state.config_blob_container_default)])
    container = oq["container"]
    if oq["count"] > app_state.config_blob_upload_limit_count: raise Exception(f"maximum {app_state.config_blob_upload_limit_count} allowed")
    output = []; blob_list = []
    if oq["service"] == "s3":
        for _ in range(oq["count"]):
            file_key = f"{uuid.uuid4().hex}.bin"
            presigned_post = app_state.client_s3.generate_presigned_post(Bucket=container, Key=file_key, ExpiresIn=app_state.config_upload_url_expire_sec, Conditions=[["content-length-range", 1, app_state.config_blob_limit_kb * 1024]])
            file_url = f"https://{container}.s3.{app_state.config_s3_region_name}.amazonaws.com/{file_key}"
            output.append({"upload_url": presigned_post["url"], **presigned_post["fields"], "file_url": file_url}); blob_list.append({"created_by_id": request.state.user["id"], "type": 2, "service": oq["service"], "container": container, "blob_key": file_key, "file_url": file_url})
    elif oq["service"] == "azure":
        for _ in range(oq["count"]):
            file_key = f"{uuid.uuid4().hex}.bin"
            sas_token = generate_blob_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=container, blob_name=file_key, permission=BlobSasPermissions(write=True, create=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_upload_url_expire_sec))
            sas_url = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}?{sas_token}"
            file_url = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}"
            output.append({"upload_url": sas_url, "key": file_key, "file_url": file_url}); blob_list.append({"created_by_id": request.state.user["id"], "type": 2, "service": oq["service"], "container": container, "blob_key": file_key, "file_url": file_url})
    if blob_list: await app_state.func_postgres_create(client_postgres_pool=app_state.client_postgres_pool, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, config_table=app_state.config_table, config_obj_list_limit=app_state.config_obj_list_limit, config_buffer_limit=app_state.config_buffer_limit, mode="now", table="blob", obj_list=blob_list)
    return {"status":1,"message":output}

@router.post("/private/blob-container-sas")
async def func_api_private_blob_container_sas(request:Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, [service for service in app_state.config_allowed_blob_services if service == "azure"], None), ("container", "str", 0, None, app_state.config_blob_container_default)])
    container = oq["container"]
    if oq["service"] == "azure":
        sas_token = generate_container_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=container, permission=ContainerSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_preview_url_expire_sec))
        return {"status":1,"message":{"sas_token": sas_token, "expiry_sec": app_state.config_preview_url_expire_sec}}

@router.post("/private/blob-preview-urls")
async def func_api_private_blob_preview_urls(request:Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("service", "str", 1, app_state.config_allowed_blob_services, None), ("urls", "list", 1, None, None)])
    output = {}
    if of["service"] == "s3":
        for file_url in of["urls"]:
            dynamic_container = file_url.split("://")[1].split(".s3")[0]
            file_key = file_url.split(".amazonaws.com/")[1].split("?")[0]
            url = app_state.client_s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': dynamic_container, 'Key': file_key}, ExpiresIn=app_state.config_preview_url_expire_sec)
            output[file_url] = url
    elif of["service"] == "azure":
        for file_url in of["urls"]:
            dynamic_container, file_key = file_url.split(".net/")[1].split("?")[0].split("/", 1)
            sas_token = generate_blob_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=dynamic_container, blob_name=file_key, permission=BlobSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_preview_url_expire_sec))
            output[file_url] = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{dynamic_container}/{file_key}?{sas_token}"
    return {"status":1,"message":output}
