# router
from fastapi import APIRouter
router = APIRouter()

# import
from fastapi import Request
import uuid
from datetime import datetime, timedelta, timezone

# api
@router.post("/private/blob-upload-file")
async def func_api_private_blob_upload_file(request:Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, config=[("service", "str", 1, ["s3", "azure"], None), ("file", "file", 1, None, None), ("container", "str", 0, None, app_state.config_blob_container_default)])
    container = of["container"]
    if len(of["file"]) > app_state.config_blob_upload_limit_count: raise Exception(f"maximum {app_state.config_blob_upload_limit_count} files allowed")
    output = {}
    if of["service"] == "s3":
        for item in of["file"]:
            file_data = await item.read()
            if len(file_data) > app_state.config_blob_limit_kb * 1024: raise Exception(f"file size exceeds {app_state.config_blob_limit_kb}kb")
            ext = item.filename.split(".")[-1] if "." in item.filename else "bin"; file_key = f"{uuid.uuid4().hex}.{ext}"
            await app_state.client_s3.put_object(Bucket=container, Key=file_key, Body=file_data)
            output[item.filename] = f"https://{container}.s3.amazonaws.com/{file_key}"
    elif of["service"] == "azure":
        container_client = app_state.client_azure_blob.get_container_client(container)
        for item in of["file"]:
            file_data = await item.read()
            if len(file_data) > app_state.config_blob_limit_kb * 1024: raise Exception(f"file size exceeds {app_state.config_blob_limit_kb}kb")
            ext = item.filename.split(".")[-1] if "." in item.filename else "bin"; file_key = f"{uuid.uuid4().hex}.{ext}"
            blob_client=container_client.get_blob_client(file_key); await blob_client.upload_blob(file_data)
            output[item.filename] = blob_client.url
    return {"status":1,"message":output}

@router.post("/private/blob-upload-url")
async def func_api_private_blob_upload_url(request:Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("service", "str", 1, ["s3", "azure"], None), ("count", "int", 0, None, 1), ("container", "str", 0, None, app_state.config_blob_container_default)])
    container = oq["container"]
    if oq["count"] > app_state.config_blob_upload_limit_count: raise Exception(f"maximum {app_state.config_blob_upload_limit_count} allowed")
    output = []
    if oq["service"] == "s3":
        for _ in range(oq["count"]):
            file_key = f"{uuid.uuid4().hex}.bin"
            presigned_post = app_state.client_s3.generate_presigned_post(Bucket=container, Key=file_key, ExpiresIn=app_state.config_upload_url_expire_sec, Conditions=[["content-length-range", 1, app_state.config_blob_limit_kb * 1024]])
            output.append({"upload_url": presigned_post["url"], **presigned_post["fields"], "file_url": f"https://{container}.s3.{app_state.config_s3_region_name}.amazonaws.com/{file_key}"})
    elif oq["service"] == "azure":
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        for _ in range(oq["count"]):
            file_key = f"{uuid.uuid4().hex}.bin"
            sas_token = generate_blob_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=container, blob_name=file_key, permission=BlobSasPermissions(write=True, create=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_upload_url_expire_sec))
            sas_url = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}?{sas_token}"
            output.append({"upload_url": sas_url, "key": file_key, "file_url": f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}"})
    return {"status":1,"message":output}
