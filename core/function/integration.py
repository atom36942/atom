async def func_s3_bucket_create(*, client_s3: any, config_s3_region_name: str, bucket: str) -> any:
    """Create a new AWS S3 bucket in a specific region."""
    return await client_s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": config_s3_region_name})

async def func_s3_bucket_public(*, client_s3: any, bucket: str) -> any:
    """Expose an AWS S3 bucket for public read access."""
    await client_s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
    return await client_s3.put_bucket_policy(Bucket=bucket, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}""".replace("bucket_name", bucket))

def func_s3_bucket_empty(*, client_s3_resource: any, bucket: str) -> any:
    """Purge all objects from an AWS S3 bucket."""
    return client_s3_resource.Bucket(bucket).objects.all().delete()

async def func_s3_bucket_delete(*, client_s3: any, bucket: str) -> any:
    """Delete an AWS S3 bucket."""
    return await client_s3.delete_bucket(Bucket=bucket)

def func_s3_url_delete(*, client_s3_resource: any, url: list) -> any:
    """Delete multiple objects from AWS S3 in bulk given their public URLs."""
    for file_url in url:
        bucket = file_url.split("//", 1)[1].split(".", 1)[0]
        key = file_url.rsplit("/", 1)[1]
        client_s3_resource.Object(bucket, key).delete()
    return "urls deleted"

async def func_s3_upload_file(*, client_s3: any, bucket: str, file_list: list, config_s3_limit_kb: int, config_s3_upload_limit_count: int) -> dict:
    import uuid
    if len(file_list) > config_s3_upload_limit_count:
        raise Exception(f"maximum {config_s3_upload_limit_count} files allowed")
    output = {}
    for item in file_list:
        file_data = await item.read()
        if len(file_data) > config_s3_limit_kb * 1024:
            raise Exception(f"file size exceeds {config_s3_limit_kb}kb for {item.filename}")
        ext = item.filename.split(".")[-1] if "." in item.filename else "bin"
        file_key = f"{uuid.uuid4().hex}.{ext}"
        await client_s3.put_object(Bucket=bucket, Key=file_key, Body=file_data)
        output[item.filename] = f"https://{bucket}.s3.amazonaws.com/{file_key}"
    return output

def func_s3_upload_url_presigned(*, client_s3: any, config_s3_region_name: str, bucket: str, config_s3_limit_kb: int, config_s3_presigned_expire_sec: int, count: int, config_s3_upload_limit_count: int) -> list:
    import uuid
    if count > config_s3_upload_limit_count:
        raise Exception(f"maximum {config_s3_upload_limit_count} allowed")
    output = []
    for _ in range(count):
        file_key = f"{uuid.uuid4().hex}.bin"
        presigned_post = client_s3.generate_presigned_post(Bucket=bucket, Key=file_key, ExpiresIn=config_s3_presigned_expire_sec, Conditions=[["content-length-range", 1, config_s3_limit_kb * 1024]])
        output.append({**presigned_post["fields"], "url_final": f"https://{bucket}.s3.{config_s3_region_name}.amazonaws.com/{file_key}"})
    return output

def func_sns_send_mobile_message(*, client_sns: any, mobile: str, message: str) -> None:
    """Send a mobile SMS using AWS SNS."""
    client_sns.publish(PhoneNumber=mobile, Message=message)
    return None

def func_sns_send_mobile_message_template(*, client_sns: any, mobile: str, message: str, template_id: str, entity_id: str, sender_id: str) -> None:
    """Send a mobile SMS using AWS SNS with specific template and attributes."""
    client_sns.publish(PhoneNumber=mobile, Message=message, MessageAttributes={"AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": sender_id}, "AWS.MM.SMS.TemplateId": {"DataType": "String", "StringValue": template_id}, "AWS.MM.SMS.EntityId": {"DataType": "String", "StringValue": entity_id}, "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}})
    return None

def func_ses_send_email(*, client_ses: any, from_email: str, to_emails: list, subject: str, body: str) -> None:
    """Send an email via AWS SES."""
    client_ses.send_email(Source=from_email, Destination={"ToAddresses": to_emails}, Message={"Subject": {"Data": subject}, "Body": {"Html": {"Data": body}}})
    return None

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

def func_gsheet_object_create(*, client_gsheet: any, sheet_url: str, obj_list: list) -> any:
    """Append records to a Google Sheet."""
    from urllib.parse import urlparse, parse_qs
    if not obj_list:
        return None
    parsed_url = urlparse(sheet_url)
    spreadsheet_id = parsed_url.path.split("/")[3]
    query_params = parse_qs(parsed_url.query)
    grid_id = int(query_params.get("gid", [""])[0])
    spreadsheet = client_gsheet.open_by_key(spreadsheet_id)
    worksheet = next((ws for ws in spreadsheet.worksheets() if ws.id == grid_id), None)
    if not worksheet:
        raise Exception("worksheet not found")
    column_headers = list(obj_list[0].keys())
    rows_to_insert = [[obj.get(col, "") for col in column_headers] for obj in obj_list]
    return worksheet.append_rows(rows_to_insert, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")

async def func_gsheet_object_read(*, sheet_url: str) -> list:
    """Read records from a public Google Sheet as a list of dictionaries."""
    from urllib.parse import urlparse, parse_qs
    import pandas as pd, aiohttp, io
    parsed_url = urlparse(sheet_url)
    spreadsheet_id = parsed_url.path.split("/d/")[1].split("/")[0]
    grid_id = parse_qs(parsed_url.query).get("gid", ["0"])[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={grid_id}") as response:
            if response.status != 200:
                raise Exception(f"fetch failed: {response.status}")
            csv_content = await response.text()
    data_frame = pd.read_csv(io.StringIO(csv_content))
    return data_frame.where(pd.notnull(data_frame), None).to_dict(orient="records")

def func_jira_worklog_export(*, url: str, email: str, api_token: str, start_date: str, end_date: str, output_path: str) -> str:
    """Export Jira worklogs for a specific period to a CSV file."""
    try:
        from jira import JIRA
        from pathlib import Path
        import pandas as pd
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        jira_client = JIRA(server=url, basic_auth=(email, api_token))
        log_rows = []
        people = set()
        jql = f"worklogDate >= '{start_date}' AND worklogDate <= '{end_date}'"
        all_issues = jira_client.enhanced_search_issues(jql, maxResults=0)
        for issue in all_issues:
            if getattr(issue.fields, "assignee", None):
                people.add(issue.fields.assignee.displayName)
            for worklog in jira_client.worklogs(issue.id):
                started_at = worklog.started[:10]
                if start_date <= started_at <= end_date:
                    author_name = worklog.author.displayName
                    people.add(author_name)
                    log_rows.append((author_name, started_at, worklog.timeSpentSeconds / 3600))
        date_range = pd.date_range(start=start_date, end=end_date).strftime("%Y-%m-%d").tolist()
        if not log_rows:
            if people:
                pd.DataFrame(index=sorted(list(people)), columns=date_range).fillna(0).astype(int).to_csv(output_path)
                return output_path
            pd.DataFrame(columns=date_range).to_csv(output_path)
            return output_path
        df = pd.DataFrame(log_rows, columns=["author", "date", "hours"])
        pivot = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0).reindex(index=sorted(list(people)), columns=date_range, fill_value=0).round(0).astype(int)
        pivot.to_csv(output_path)
        return output_path
    except Exception as e:
        raise Exception(f"jira config exception: {str(e)}")

async def func_mongodb_create(*, upload_file: any, client_mongodb: any, database: str, table: str, func_api_file_to_chunks: any) -> int:
    """Insert multiple records from a CSV file into a MongoDB collection."""
    limit_batch = 5000
    if not client_mongodb: raise Exception("mongo client missing")
    count = 0
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=limit_batch):
        await client_mongodb[database][table].insert_many(ol)
        count += len(ol)
    return count

async def func_mongodb_update(*, upload_file: any, client_mongodb: any, database: str, table: str, func_api_file_to_chunks: any) -> int:
    """Update multiple records from a CSV file in a MongoDB collection using Replacement."""
    limit_batch = 5000
    if not client_mongodb: raise Exception("mongo client missing")
    from pymongo import ReplaceOne
    from bson.objectid import ObjectId
    count, first_chunk = 0, True
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=limit_batch):
        if first_chunk:
            if not any(k in ol[0] for k in ("_id", "id")):
                raise Exception("CSV format error: MongoDB update requires '_id' or 'id' column")
            first_chunk = False
        ops = []
        for obj in ol:
            obj_id = obj.get("_id") or obj.get("id")
            if not obj_id: continue
            filter_id = ObjectId(obj_id) if len(str(obj_id)) == 24 else obj_id
            update_data = {k: v for k, v in obj.items() if k not in ("_id", "id")}
            ops.append(ReplaceOne({"_id": filter_id}, update_data, upsert=False))
        if ops:
            await client_mongodb[database][table].bulk_write(ops)
        count += len(ol)
    return count

async def func_mongodb_delete(*, upload_file: any, client_mongodb: any, database: str, table: str, func_api_file_to_chunks: any) -> int:
    """Delete multiple records from a MongoDB collection using a list of IDs from a CSV file."""
    limit_batch = 5000
    if not client_mongodb: raise Exception("mongo client missing")
    from bson.objectid import ObjectId
    count, first_chunk = 0, True
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=limit_batch):
        if first_chunk:
            if not any(k in ol[0] for k in ("_id", "id")):
                raise Exception("CSV format error: MongoDB delete requires '_id' or 'id' column")
            first_chunk = False
        id_list = []
        for obj in ol:
            obj_id = obj.get("_id") or obj.get("id")
            if not obj_id: continue
            try:
                id_list.append(ObjectId(obj_id)) if len(str(obj_id)) == 24 else id_list.append(obj_id)
            except Exception:
                id_list.append(obj_id)
        if id_list:
            await client_mongodb[database][table].delete_many({"_id": {"$in": id_list}})
        count += len(ol)
    return count

async def func_redis_create(*, upload_file: any, client_redis: any, config_redis_cache_ttl_sec: int, func_api_file_to_chunks: any) -> int:
    """Batch create/update objects in Redis from an uploaded CSV file."""
    limit_batch = 5000
    import orjson
    count, first_chunk = 0, True
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=limit_batch):
        if first_chunk:
            if sorted(list(ol[0].keys())) != sorted(["key", "value"]):
                raise Exception("CSV format error: 'create' mode requires exactly 'key' and 'value' columns")
            first_chunk = False
        async with client_redis.pipeline(transaction=True) as pipe:
            for item in ol:
                val = orjson.dumps(item["value"]).decode("utf-8")
                if config_redis_cache_ttl_sec:
                    pipe.setex(item["key"], config_redis_cache_ttl_sec, val)
                else:
                    pipe.set(item["key"], val)
            await pipe.execute()
        count += len(ol)
    return count

async def func_redis_delete(*, upload_file: any, client_redis: any, func_api_file_to_chunks: any) -> int:
    """Batch delete objects in Redis from an uploaded CSV file."""
    limit_batch = 5000
    count, first_chunk = 0, True
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=limit_batch):
        if first_chunk:
            if list(ol[0].keys()) != ["key"]:
                raise Exception("CSV format error: 'delete' mode requires exactly one 'key' column")
            first_chunk = False
        async with client_redis.pipeline(transaction=True) as pipe:
            for item in ol:
                pipe.delete(item["key"])
            await pipe.execute()
        count += len(ol)
    return count
