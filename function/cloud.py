
async def func_s3_bucket_create(client_s3: any, bucket_name: str, region_name: str) -> str:
    """Create a new S3 bucket."""
    await client_s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region_name} if region_name != "us-east-1" else {})
    return "bucket created"

async def func_s3_bucket_public(client_s3: any, bucket_name: str) -> str:
    """Make an S3 bucket publicly accessible."""
    await client_s3.put_bucket_policy(Bucket=bucket_name, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":["s3:GetObject"],"Resource":["arn:aws:s3:::%s/*"]}]}""" % bucket_name)
    return "bucket public"

async def func_s3_bucket_empty(client_s3: any, bucket_name: str) -> str:
    """Delete all objects within an S3 bucket."""
    paginator = client_s3.get_paginator("list_objects_v2")
    async for result in paginator.paginate(Bucket=bucket_name):
        if "Contents" in result:
            items = [{"Key": x["Key"]} for x in result["Contents"]]
            await client_s3.delete_objects(Bucket=bucket_name, Delete={"Objects": items})
    return "bucket emptied"

async def func_s3_bucket_delete(client_s3: any, bucket_name: str) -> str:
    """Delete an S3 bucket after emptying its contents."""
    await func_s3_bucket_empty(client_s3, bucket_name)
    await client_s3.delete_bucket(Bucket=bucket_name)
    return "bucket deleted"

async def func_s3_url_delete(client_s3: any, bucket_name: str, file_url: str) -> str:
    """Delete an object from S3 using its URL."""
    file_key = file_url.split(".com/")[1]
    await client_s3.delete_object(Bucket=bucket_name, Key=file_key)
    return "url deleted"

async def func_s3_upload(client_s3: any, bucket_name: str, file_obj: any, file_name: str, sub_folder: str = None) -> str:
    """Upload a file to S3 and return the public URL."""
    import os
    file_key = f"{sub_folder}/{file_name}" if sub_folder else file_name
    await client_s3.put_object(Bucket=bucket_name, Key=file_key, Body=await file_obj.read())
    return f"https://{bucket_name}.s3.amazonaws.com/{file_key}"

async def func_s3_upload_presigned(client_s3: any, bucket_name: str, file_name: str, sub_folder: str = None, expiry_sec: int = 3600) -> str:
    """Generate a presigned URL for S3 object upload."""
    file_key = f"{sub_folder}/{file_name}" if sub_folder else file_name
    return await client_s3.generate_presigned_url("put_object", Params={"Bucket": bucket_name, "Key": file_key}, ExpiresIn=expiry_sec)


def func_sns_send_mobile_message(client_sns: any, mobile: str, message: str) -> str:
    """Send an SMS via AWS SNS."""
    client_sns.publish(PhoneNumber=mobile, Message=message)
    return "sms sent"

def func_sns_send_mobile_message_template(client_sns: any, mobile: str, template_type: str, data: dict) -> str:
    """Send a templated SMS via AWS SNS."""
    if template_type == "otp":
        message = f"Your OTP is {data['otp']}"
    else:
        message = data.get("message", "")
    return func_sns_send_mobile_message(client_sns, mobile, message)


def func_ses_send_email(client_ses: any, email_from: str, email_to: str, subject: str, body_html: str) -> str:
    """Send an email via AWS SES."""
    client_ses.send_email(Source=email_from, Destination={"ToAddresses": [email_to]}, Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": body_html}}})
    return "email sent"

def func_resend_send_email(url: str, key: str, email_from: str, email_to: str, subject: str, body_html: str) -> str:
    """Send an email via Resend API."""
    import httpx
    httpx.post(url, headers={"Authorization": f"Bearer {key}"}, json={"from": email_from, "to": [email_to], "subject": subject, "html": body_html})
    return "email sent resend"

def func_fast2sms_send_otp_mobile(url: str, key: str, mobile: str, otp: int) -> str:
    """Send an OTP via Fast2SMS API."""
    import httpx
    httpx.get(url, params={"authorization": key, "route": "otp", "variables_values": str(otp), "numbers": mobile})
    return "sms sent fast2sms"

