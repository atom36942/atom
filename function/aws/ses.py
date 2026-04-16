def func_ses_send_email(*, client_ses: any, from_email: str, to_emails: list, subject: str, body: str) -> None:
    """Send an email via AWS SES."""
    client_ses.send_email(Source=from_email, Destination={"ToAddresses": to_emails}, Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}})
    return None
