async def func_resend_send_email(*, config_resend_url: str, config_resend_key: str, from_email: str, to_email: str, email_subject: str, email_content: str) -> None:
    """Send an email using the Resend API."""
    import httpx, orjson
    headers = {"Authorization": f"Bearer {config_resend_key}", "Content-Type": "application/json"}
    payload = {"from": from_email, "to": [to_email], "subject": email_subject, "html": email_content}
    async with httpx.AsyncClient() as client:
        response = await client.post(config_resend_url, headers=headers, data=orjson.dumps(payload).decode("utf-8"))
        if response.status_code != 200:
            raise Exception(f"failed to send email: {response.text}")
    return None
