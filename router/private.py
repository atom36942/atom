# packages
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
import orjson
from azure.storage.blob import BlobSasPermissions, ContainerSasPermissions, generate_blob_sas, generate_container_sas
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.post("/private/send-email")
async def func_api_private_send_email(request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_email_services}, {"name": "sender", "type": "str", "required": 1}, {"name": "to", "type": "list", "required": 1}, {"name": "subject", "type": "str", "required": 1}, {"name": "text", "type": "str", "required": 1}, {"name": "cc", "type": "list", "default": []}, {"name": "bcc", "type": "list", "default": []}, {"name": "reply_to", "type": "list", "default": []}])
    res = await app_state.func_email_send(app_state=app_state, service=ob["service"], sender=ob["sender"], to=ob["to"], subject=ob["subject"], text=ob["text"], cc=ob["cc"], bcc=ob["bcc"], reply_to=ob["reply_to"])
    return {"status":1,"message":res}

@router.post("/private/blob-upload-file")
async def func_api_private_blob_upload_file(request:Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="form", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_blob_services}, {"name": "container", "type": "str", "required": 1}, {"name": "file", "type": "file", "required": 1}])
    res = await app_state.func_blob_upload_file(app_state=app_state, service=of["service"], container=of["container"], files=of["file"], user_id=request.state.user["id"])
    return {"status":1,"message":res}

@router.post("/private/blob-upload-url")
async def func_api_private_blob_upload_url(request:Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_blob_services}, {"name": "container", "type": "str", "required": 1}, {"name": "count", "type": "int", "default": 1}])
    res = await app_state.func_blob_upload_url(app_state=app_state, service=oq["service"], container=oq["container"], count=oq["count"], user_id=request.state.user["id"])
    return {"status":1,"message":res}

@router.post("/private/blob-container-sas")
async def func_api_private_blob_container_sas(request:Request):
    app_state = request.app.state
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_blob_services}, {"name": "container", "type": "str", "required": 1}])
    if oq["service"] == "s3":
        raise Exception("s3 is not allowed for this api")
    container = oq["container"]
    if oq["service"] == "azure":
        sas_token = generate_container_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=container, permission=ContainerSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_blob_expire_sec_preview))
        return {"status":1,"message":{"sas_token": sas_token, "expiry_sec": app_state.config_blob_expire_sec_preview}}

@router.post("/private/blob-preview-urls")
async def func_api_private_blob_preview_urls(request:Request):
    app_state = request.app.state
    of = await app_state.func_request_param_read(request=request, mode="body", strict=0, param_specs=[{"name": "service", "type": "str", "required": 1, "allowed": app_state.config_blob_services}, {"name": "urls", "type": "list", "required": 1}])
    res = await app_state.func_blob_preview_urls_get(client_s3=app_state.client_s3, client_azure_blob=app_state.client_azure_blob, config_azure_account_name=app_state.config_azure_account_name, config_azure_account_key=app_state.config_azure_account_key, config_blob_expire_sec_preview=app_state.config_blob_expire_sec_preview, service=of["service"], urls=of["urls"])
    return {"status":1,"message":res}
