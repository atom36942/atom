# import
import asyncio
import re
from typing import Any
import time
from collections import deque
import httpx
import jwt
import orjson
from starlette.datastructures import State
from starlette.websockets import WebSocket
from starlette.websockets import WebSocketDisconnect
from .auth import func_token_check_secret_key
from .middleware import func_api_error

# function
async def func_otp_send_email(*, app_state: State, service: str, sender: str, email: str, otp: int) -> str:
    """Sends OTP code via configured email service (ses, resend, azure)."""
    if service == "ses":
        if not app_state.client_ses: raise func_api_error(message="SES client not initialized", status_code=500)
        await asyncio.to_thread(app_state.client_ses.send_email, Source=sender, Destination={"ToAddresses": [email]}, Message={"Subject": {"Data": "your otp code"}, "Body": {"Html": {"Data": str(otp)}}})
    elif service == "resend":
        if not app_state.config_resend_key: raise func_api_error(message="resend API key not configured", status_code=500)
        if not app_state.config_resend_url: raise func_api_error(message="resend URL not configured", status_code=500)
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": sender, "to": [email], "subject": "your otp code", "html": f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>"}
        async with httpx.AsyncClient() as client:
            response = await client.post(app_state.config_resend_url, headers=headers, data=orjson.dumps(payload).decode("utf-8"))
            if response.status_code not in (200, 201): raise func_api_error(message=f"email delivery service failed (HTTP {response.status_code})", status_code=502)
    elif service == "azure":
        if not app_state.client_azure_email: raise func_api_error(message="azure email client not configured", status_code=500)
        message = {"senderAddress": sender, "recipients": {"to": [{"address": email}]}, "content": {"subject": "your otp code", "plainText": str(otp)}}
        await asyncio.to_thread(lambda: app_state.client_azure_email.begin_send(message).result())
    else:
        raise Exception(f"email service {service} not supported")
    return "done"

async def func_otp_send_mobile(*, app_state: State, service: str, mobile: str, otp: int, sns_template: dict = None, sender: str = None) -> Any:
    """Sends OTP code via configured mobile service (sns, fast2sms, azure)."""
    if service == "sns":
        if not app_state.client_sns: raise func_api_error(message="SNS client not initialized", status_code=500)
        if sns_template:
            await asyncio.to_thread(
                app_state.client_sns.publish,
                PhoneNumber=mobile,
                Message=sns_template["message"].replace("{otp}", str(otp)),
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": sns_template["sender_id"]},
                    "AWS.MM.SMS.TemplateId": {"DataType": "String", "StringValue": sns_template["template_id"]},
                    "AWS.MM.SMS.EntityId": {"DataType": "String", "StringValue": sns_template["entity_id"]},
                    "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
                }
            )
            return "done"
        await asyncio.to_thread(app_state.client_sns.publish, PhoneNumber=mobile, Message=str(otp))
        return "done"
    if service == "fast2sms":
        if not app_state.config_fast2sms_key: raise func_api_error(message="fast2sms API key not configured", status_code=500)
        if not app_state.config_fast2sms_url: raise func_api_error(message="fast2sms URL not configured", status_code=500)
        params = {"authorization": app_state.config_fast2sms_key, "route": "otp", "variables_values": str(otp), "numbers": mobile}
        async with httpx.AsyncClient() as client:
            response = await client.get(app_state.config_fast2sms_url, params=params)
            if not response.is_success: raise func_api_error(message=f"SMS delivery service failed (HTTP {response.status_code})", status_code=502)
            result = response.json()
            if result.get("return") is not True: raise func_api_error(message="SMS delivery service rejected request", status_code=502)
            return result
    elif service == "azure":
        if not app_state.client_azure_sms: raise func_api_error(message="azure sms client not configured", status_code=500)
        from_number = sender or app_state.config_azure_sms_from_number
        if not from_number: raise func_api_error(message="azure sms from_number not configured", status_code=500)
        await asyncio.to_thread(lambda: app_state.client_azure_sms.send(from_=from_number, to=[mobile], message=f"Your OTP code is {otp}"))
        return "done"
    else:
        raise Exception(f"mobile service {service} not supported")

async def func_email_send(*, app_state: State, service: str, sender: str, to: list, subject: str, text: str, cc: list = None, bcc: list = None, reply_to: list = None) -> dict:
    """Sends a custom email via the specified service (ses, resend, azure)."""
    if (service == "ses" and not app_state.client_ses) or (service == "resend" and not app_state.client_http) or (service == "azure" and not app_state.client_azure_email):
        raise func_api_error(message="email client not initialized", status_code=500)
    cc = cc or []
    bcc = bcc or []
    reply_to = reply_to or []
    message = None
    if service == "ses":
        params = {"Source": sender, "Destination": {"ToAddresses": to, "CcAddresses": cc, "BccAddresses": bcc}, "Message": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": text}}}}
        if reply_to: params["ReplyToAddresses"] = reply_to
        response = await asyncio.to_thread(app_state.client_ses.send_email, **params)
        message = {"id": response.get("MessageId")}
    elif service == "resend":
        if not app_state.config_resend_key: raise func_api_error(message="resend API key not configured", status_code=500)
        if not app_state.config_resend_url: raise func_api_error(message="resend URL not configured", status_code=500)
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": sender, "to": to, "subject": subject, "text": text}
        if cc: payload["cc"] = cc
        if bcc: payload["bcc"] = bcc
        if reply_to: payload["reply_to"] = reply_to
        response = await app_state.client_http.post(app_state.config_resend_url, headers=headers, content=orjson.dumps(payload))
        if response.status_code not in (200, 201): raise func_api_error(message=f"email delivery service failed (HTTP {response.status_code})", status_code=502)
        message = response.json()
    elif service == "azure":
        azure_message = {"senderAddress": sender, "recipients": {"to": [{"address": email} for email in to]}, "content": {"subject": subject, "plainText": text}}
        if cc: azure_message["recipients"]["cc"] = [{"address": email} for email in cc]
        if bcc: azure_message["recipients"]["bcc"] = [{"address": email} for email in bcc]
        if reply_to: azure_message["replyTo"] = [{"address": email} for email in reply_to]
        result = await asyncio.to_thread(lambda: app_state.client_azure_email.begin_send(azure_message).result())
        message = dict(result) if isinstance(result, dict) else {"id": getattr(result, "id", None), "status": getattr(result, "status", None)}
    else:
        raise Exception(f"email service {service} not supported")
    return message

def func_message_pagination(*, limit: int, page: int, max_limit: int) -> tuple[int, int]:
    if limit < 1: raise Exception("query limit must be greater than 0")
    if page < 1: raise Exception("query page must be greater than 0")
    if max_limit and limit > max_limit: raise Exception(f"query limit {limit} exceeds maximum allowed: {max_limit}")
    return limit + 1, (page - 1) * limit

def func_message_order(*, order: str, cache_postgres_schema: dict) -> str:
    schema = cache_postgres_schema.get("message", {})
    if not schema: raise Exception("table 'message' not found")
    order_list, ordered_columns = [], set()
    for item in str(order or "id desc").split(","):
        parts = item.strip().split()
        if not parts or len(parts) > 2 or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", parts[0]) or parts[0] not in schema:
            raise Exception(f"invalid message order: {item.strip()}")
        if len(parts) == 2 and parts[1].lower() not in ("asc", "desc"): raise Exception(f"invalid message order: {item.strip()}")
        direction = parts[1].upper() if len(parts) == 2 else "ASC"
        order_list.append(f'"{parts[0]}" {direction}')
        ordered_columns.add(parts[0])
    if "id" not in ordered_columns: order_list.append('"id" DESC')
    return ", ".join(order_list)

async def func_message_socket_auth(*, websocket: WebSocket, config_token_secret_key: str, auth_timeout_sec: int) -> tuple:
    """Read the first websocket message {"token": "<access token>"}; return (user_id, token_expires_at) or raise ValueError with the close reason."""
    try: first = orjson.loads(await asyncio.wait_for(websocket.receive_text(), timeout=auth_timeout_sec))
    except TimeoutError: raise ValueError("token not sent") from None
    except orjson.JSONDecodeError: raise ValueError("first message must be {\"token\": \"...\"}") from None
    token = first.get("token") if isinstance(first, dict) else None
    if not isinstance(token, str) or not token: raise ValueError("first message must be {\"token\": \"...\"}")
    func_token_check_secret_key(config_token_secret_key=config_token_secret_key)
    try: payload = jwt.decode(token, str(config_token_secret_key), algorithms="HS256")
    except jwt.ExpiredSignatureError: raise ValueError("token expired") from None
    except jwt.PyJWTError: raise ValueError("invalid token") from None
    if payload.get("type") != "access": raise ValueError("access token required")
    user = orjson.loads(payload.get("data") or "{}")
    if not isinstance(user, dict) or not isinstance(user.get("id"), int): raise ValueError("invalid token")
    return user["id"], payload["exp"]

async def func_message_socket_send(*, sockets: dict, user_ids: tuple, payload: dict) -> None:
    """Push a payload to every open socket of the given users in this worker; a socket that fails is dropped."""
    text = orjson.dumps(payload).decode()
    for user_id in set(user_ids):
        for socket in list(sockets.get(user_id, ())):
            try: await socket.send_text(text)
            except Exception: sockets.get(user_id, set()).discard(socket)
    return

async def func_message_socket(*, app_state: State, websocket: WebSocket, auth_timeout_sec: int = 5, description_length_max: int = 4000, rate_limit_per_minute: int = 60, connection_per_user_max: int = 5) -> None:
    """Live chat over the message table: authenticate with a first {"token"} message, then each {"received_by_id", "description"} is saved and pushed to both users' open sockets.

    Limits: auth_timeout_sec to send the token, description_length_max characters per message, rate_limit_per_minute messages per connection, connection_per_user_max open sockets per user.
    """
    # accept before any close, so browsers receive the code and reason instead of a bare 1006 handshake failure
    await websocket.accept()
    if not app_state.config_api.get(websocket.url.path, {}).get("is_active", True): return await websocket.close(code=1008, reason="endpoint disabled")
    client_postgres = app_state.client_postgres_dict.get("master")
    if not client_postgres: return await websocket.close(code=1011, reason="postgres client not initialized")
    try: user_id, token_expires_at = await func_message_socket_auth(websocket=websocket, config_token_secret_key=app_state.config_token_secret_key, auth_timeout_sec=auth_timeout_sec)
    except ValueError as e: return await websocket.close(code=1008, reason=str(e))
    sockets = app_state.runtime_message_socket
    if len(sockets.get(user_id, ())) >= connection_per_user_max: return await websocket.close(code=1008, reason="too many connections")
    sockets.setdefault(user_id, set()).add(websocket)
    sent_at = deque()
    try:
        await websocket.send_text(orjson.dumps({"type": "connected", "message": {"user_id": user_id}}).decode())
        while True:
            try: text = await asyncio.wait_for(websocket.receive_text(), timeout=max(token_expires_at - time.time(), 0))
            except TimeoutError: return await websocket.close(code=1008, reason="token expired")
            now = time.monotonic()
            while sent_at and now - sent_at[0] > 60: sent_at.popleft()
            try:
                if len(sent_at) >= rate_limit_per_minute: raise ValueError("rate limit exceeded")
                ob = orjson.loads(text) if text else None
                if not isinstance(ob, dict): raise ValueError("message must be {\"received_by_id\": int, \"description\": str}")
                received_by_id, description = ob.get("received_by_id"), ob.get("description")
                if not isinstance(received_by_id, int) or isinstance(received_by_id, bool) or received_by_id == user_id: raise ValueError("received_by_id must be another user's id")
                if not isinstance(description, str) or not description.strip(): raise ValueError("description is required")
                if len(description) > description_length_max: raise ValueError(f"description is longer than {description_length_max} characters")
                async with client_postgres.acquire() as conn:
                    if not await conn.fetchval("SELECT 1 FROM users WHERE id=$1", received_by_id): raise ValueError("received_by_id not found")
                    row = dict(await conn.fetchrow("INSERT INTO message (created_by_id, received_by_id, description) VALUES ($1, $2, $3) RETURNING *", user_id, received_by_id, description))
            except (ValueError, orjson.JSONDecodeError) as e:
                await websocket.send_text(orjson.dumps({"type": "error", "message": str(e) if isinstance(e, ValueError) else "invalid JSON"}).decode())
                continue
            sent_at.append(now)
            await func_message_socket_send(sockets=sockets, user_ids=(user_id, received_by_id), payload={"type": "message", "message": row})
    except WebSocketDisconnect:
        return None
    finally:
        sockets.get(user_id, set()).discard(websocket)
        if not sockets.get(user_id): sockets.pop(user_id, None)
