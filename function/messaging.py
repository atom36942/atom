"""Atom messaging functions."""

async def func_email_send(*, app_state: any, service: str, sender: str, to: list, subject: str, text: str, cc: list = None, bcc: list = None, reply_to: list = None) -> dict:
    """Sends a custom email via the specified service (ses, resend, azure)."""
    import asyncio
    import orjson
    if (service == "ses" and not app_state.client_ses) or (service == "resend" and not app_state.client_http) or (service == "azure" and not app_state.client_azure_email):
        raise Exception("email client not initialized")
    cc = cc or []
    bcc = bcc or []
    reply_to = reply_to or []
    message = None
    if service == "ses":
        params = {"Source": sender, "Destination": {"ToAddresses": to, "CcAddresses": cc, "BccAddresses": bcc}, "Message": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": text}}}}
        if reply_to: params["ReplyToAddresses"] = reply_to
        response = app_state.client_ses.send_email(**params)
        message = {"id": response.get("MessageId")}
    elif service == "resend":
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": sender, "to": to, "subject": subject, "text": text}
        if cc: payload["cc"] = cc
        if bcc: payload["bcc"] = bcc
        if reply_to: payload["reply_to"] = reply_to
        response = await app_state.client_http.post(app_state.config_resend_url, headers=headers, content=orjson.dumps(payload))
        if response.status_code not in (200, 201): raise Exception(f"failed to send email: {response.text}")
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
    import re
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

def func_postgres_mark_read(*, client_postgres: any, table: str, ownership_column: str, user_id: int, ids: list) -> None:
    """Schedule a non-blocking read_at update for fetched objects owned by a user."""
    import asyncio, re
    if not ids: return
    for identifier in (table, ownership_column):
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(identifier)): raise Exception(f"invalid identifier {identifier}")
    read_ids = list(dict.fromkeys(int(obj_id) for obj_id in ids if obj_id is not None))
    if not read_ids: return
    async def update_read_at():
        async with client_postgres.acquire() as conn:
            await conn.execute(f'UPDATE "{table}" SET read_at=now() WHERE "{ownership_column}"=$1 AND "id"=ANY($2::bigint[]) AND read_at IS NULL', user_id, read_ids)
    task = asyncio.create_task(update_read_at())
    task.add_done_callback(lambda t: (t.exception() if not t.cancelled() else None))
    return None

async def func_otp_send_email(*, app_state: any, service: str, sender: str, email: str, otp: int) -> str:
    """Sends OTP code via configured email service (ses, resend, azure)."""
    import httpx
    import orjson
    import asyncio
    if service == "ses":
        if not app_state.client_ses: raise Exception("SES client not initialized")
        app_state.client_ses.send_email(Source=sender, Destination={"ToAddresses": [email]}, Message={"Subject": {"Data": "your otp code"}, "Body": {"Html": {"Data": str(otp)}}})
    elif service == "resend":
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": sender, "to": [email], "subject": "your otp code", "html": f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>"}
        async with httpx.AsyncClient() as client:
            response = await client.post(app_state.config_resend_url, headers=headers, data=orjson.dumps(payload).decode("utf-8"))
            if response.status_code != 200: raise Exception(f"failed to send email: {response.text}")
    elif service == "azure":
        if not app_state.client_azure_email: raise Exception("azure email client not configured")
        message = {"senderAddress": sender, "recipients": {"to": [{"address": email}]}, "content": {"subject": "your otp code", "plainText": str(otp)}}
        await asyncio.to_thread(lambda: app_state.client_azure_email.begin_send(message).result())
    else:
        raise Exception(f"email service {service} not supported")
    return "done"

async def func_otp_send_mobile(*, app_state: any, service: str, mobile: str, otp: int, sns_template: dict = None, sender: str = None) -> any:
    """Sends OTP code via configured mobile service (sns, fast2sms, azure)."""
    import httpx
    if service == "sns":
        if not app_state.client_sns: raise Exception("SNS client not initialized")
        if sns_template:
            app_state.client_sns.publish(
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
        else:
            app_state.client_sns.publish(PhoneNumber=mobile, Message=str(otp))
            return "done"
    elif service == "fast2sms":
        params = {"authorization": app_state.config_fast2sms_key, "route": "otp", "variables_values": str(otp), "numbers": mobile}
        async with httpx.AsyncClient() as client:
            response = await client.get(app_state.config_fast2sms_url, params=params)
            return response.json()
    elif service == "azure":
        if not app_state.client_azure_sms: raise Exception("azure sms client not configured")
        from_number = sender or app_state.config_azure_sms_from_number
        if not from_number: raise Exception("azure sms from_number not configured")
        import asyncio
        await asyncio.to_thread(lambda: app_state.client_azure_sms.send(from_=from_number, to=[mobile], message=f"Your OTP code is {otp}"))
        return "done"
    else:
        raise Exception(f"mobile service {service} not supported")
