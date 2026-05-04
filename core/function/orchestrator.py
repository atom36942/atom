#import
import orjson

async def func_orchestrator_mongodb_import(*, service: str, mode: str, database: str, table: str, upload_file: any, client_mongodb: any, func_mongodb_create: callable, func_mongodb_update: callable, func_mongodb_delete: callable, func_api_file_to_chunks: callable) -> any:
    """Orchestrates MongoDB import operations."""
    if service == "mongodb":
        if mode == "create":
            return await func_mongodb_create(upload_file=upload_file, client_mongodb=client_mongodb, database=database, table=table, func_api_file_to_chunks=func_api_file_to_chunks)
        elif mode == "update":
            return await func_mongodb_update(upload_file=upload_file, client_mongodb=client_mongodb, database=database, table=table, func_api_file_to_chunks=func_api_file_to_chunks)
        elif mode == "delete":
            return await func_mongodb_delete(upload_file=upload_file, client_mongodb=client_mongodb, database=database, table=table, func_api_file_to_chunks=func_api_file_to_chunks)
    raise Exception(f"service {service} or mode {mode} not supported")

async def func_orchestrator_redis_import(*, service: str, mode: str, upload_file: any, client_redis: any, config_redis_cache_ttl_sec: int, func_redis_create: callable, func_redis_delete: callable, func_api_file_to_chunks: callable) -> any:
    """Orchestrates Redis import operations."""
    if service == "redis":
        if mode == "create":
            return await func_redis_create(upload_file=upload_file, client_redis=client_redis, config_redis_cache_ttl_sec=config_redis_cache_ttl_sec, func_api_file_to_chunks=func_api_file_to_chunks)
        elif mode == "delete":
            return await func_redis_delete(upload_file=upload_file, client_redis=client_redis, func_api_file_to_chunks=func_api_file_to_chunks)
    raise Exception(f"service {service} or mode {mode} not supported")

async def func_orchestrator_postgres_runner(*, query: str, client_postgres: any, func_postgres_runner: callable) -> any:
    """Orchestrates Postgres query execution."""
    return await func_postgres_runner(client_postgres=client_postgres, query=query)

async def func_orchestrator_postgres_export(*, table: str, client_postgres: any, func_postgres_export: callable) -> any:
    """Orchestrates Postgres table export."""
    return await func_postgres_export(client_postgres=client_postgres, table=table)

async def func_orchestrator_postgres_import(*, table: str, upload_file: any, client_postgres: any, func_postgres_import: callable, func_api_file_to_chunks: callable) -> any:
    """Orchestrates Postgres table import."""
    return await func_postgres_import(table=table, upload_file=upload_file, client_postgres=client_postgres, func_api_file_to_chunks=func_api_file_to_chunks)

async def func_orchestrator_jira_worklog_export(*, url: str, email: str, api_token: str, start_date: str, end_date: str, output_path: str, func_jira_worklog_export: callable) -> any:
    """Orchestrates Jira worklog export."""
    return func_jira_worklog_export(url=url, email=email, api_token=api_token, start_date=start_date, end_date=end_date, output_path=output_path)

async def func_orchestrator_gsheet_object_create(*, sheet_url: str, obj_list: list, client_gsheet: any, func_gsheet_object_create: callable) -> any:
    """Orchestrates Google Sheet record creation."""
    return func_gsheet_object_create(client_gsheet=client_gsheet, sheet_url=sheet_url, obj_list=obj_list)

async def func_orchestrator_gsheet_object_read(*, sheet_url: str, func_gsheet_object_read: callable) -> any:
    """Orchestrates Google Sheet record reading."""
    return await func_gsheet_object_read(sheet_url=sheet_url)

async def func_orchestrator_resend_send_email(*, config_resend_url: str, config_resend_key: str, from_email: str, to_email: str, email_subject: str, email_content: str, func_resend_send_email: callable) -> any:
    """Orchestrates sending an email via Resend."""
    return await func_resend_send_email(config_resend_url=config_resend_url, config_resend_key=config_resend_key, from_email=from_email, to_email=to_email, email_subject=email_subject, email_content=email_content)

async def func_orchestrator_sns_send_mobile_message(*, mobile: str, message: str, client_sns: any, func_sns_send_mobile_message: callable) -> any:
    """Orchestrates sending an SMS via SNS."""
    return func_sns_send_mobile_message(client_sns=client_sns, mobile=mobile, message=message)

async def func_orchestrator_sns_send_mobile_message_template(*, mobile: str, message: str, template_id: str, entity_id: str, sender_id: str, client_sns: any, func_sns_send_mobile_message_template: callable) -> any:
    """Orchestrates sending a templated SMS via SNS."""
    return func_sns_send_mobile_message_template(client_sns=client_sns, mobile=mobile, message=message, template_id=template_id, entity_id=entity_id, sender_id=sender_id)

async def func_orchestrator_ses_send_email(*, from_email: str, to_emails: list, subject: str, body: str, client_ses: any, func_ses_send_email: callable) -> any:
    """Orchestrates sending an email via SES."""
    return func_ses_send_email(client_ses=client_ses, from_email=from_email, to_emails=to_emails, subject=subject, body=body)

async def func_orchestrator_redis_publish(*, channel: str, payload: dict, client_redis_producer: any) -> any:
    """Orchestrates publishing a message to a Redis channel."""
    if client_redis_producer:
        return await client_redis_producer.publish(channel, orjson.dumps(payload).decode("utf-8"))
    return None

async def func_orchestrator_blob_container_ops(*, service: str, mode: str, container: str, client_s3: any, config_s3_region_name: str, client_s3_resource: any, client_azure_blob: any, func_s3_container_create: callable, func_s3_container_public: callable, func_s3_container_empty: callable, func_s3_container_delete: callable, func_azure_container_create: callable, func_azure_container_delete: callable) -> any:
    """Orchestrates blob container operations (S3 and Azure) with unified branching logic."""
    if service == "s3":
        if mode == "create":
            return await func_s3_container_create(client_s3=client_s3, config_s3_region_name=config_s3_region_name, bucket=container)
        elif mode == "public":
            return await func_s3_container_public(client_s3=client_s3, bucket=container)
        elif mode == "empty":
            return func_s3_container_empty(client_s3_resource=client_s3_resource, bucket=container)
        elif mode == "delete":
            return await func_s3_container_delete(client_s3=client_s3, bucket=container)
    elif service == "azure":
        if mode == "create":
            return await func_azure_container_create(client_azure_blob=client_azure_blob, container=container)
        elif mode == "delete":
            return await func_azure_container_delete(client_azure_blob=client_azure_blob, container=container)
        else:
            raise Exception(f"mode {mode} not supported for azure")
    raise Exception(f"service {service} or mode {mode} not supported")

async def func_orchestrator_blob_url_delete(*, url: list, client_s3: any, client_azure_blob: any, func_s3_url_delete: callable, func_azure_url_delete: callable) -> any:
    """Detects service provider from URL and routes to deletion functions with parallel execution."""
    import asyncio
    s3_urls = [u for u in url if "amazonaws.com" in u]
    azure_urls = [u for u in url if "windows.net" in u]
    
    tasks = []
    if s3_urls:
        tasks.append(func_s3_url_delete(client_s3=client_s3, url=s3_urls))
    if azure_urls:
        tasks.append(func_azure_url_delete(client_azure_blob=client_azure_blob, url=azure_urls))
    
    if tasks: await asyncio.gather(*tasks)
    return f"{len(s3_urls)} S3 and {len(azure_urls)} Azure URLs processed"
