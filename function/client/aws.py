def func_client_read_ses(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_ses_region_name: str) -> any:
    """Initialize AWS SES client."""
    import boto3
    return boto3.client("ses", region_name=config_ses_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)

def func_client_read_sns(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_sns_region_name: str) -> any:
    """Initialize AWS SNS client."""
    import boto3
    return boto3.client("sns", region_name=config_sns_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)

async def func_client_read_s3(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_s3_region_name: str) -> any:
    """Initialize AWS S3 client and resource."""
    import aiobotocore.session
    import boto3
    client = aiobotocore.session.get_session().create_client("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
    resource = boto3.resource("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
    return client, resource
