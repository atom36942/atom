async def func_redis_object_create(client_redis: any, keys: list, objects: list, config_redis_cache_ttl_sec: int) -> None:
    """Batch create/update objects in Redis with optional expiration in a pipeline transaction."""
    import orjson
    async with client_redis.pipeline(transaction=True) as pipe:
        for key, obj in zip(keys, objects):
            val = orjson.dumps(obj).decode("utf-8")
            if config_redis_cache_ttl_sec:
                pipe.setex(key, config_redis_cache_ttl_sec, val)
            else:
                pipe.set(key, val)
        await pipe.execute()
    return None


async def func_redis_object_delete(client_redis: any, keys: list) -> None:
    """Batch delete objects in Redis using a pipeline transaction."""
    async with client_redis.pipeline(transaction=True) as pipe:
        for key in keys:
            pipe.delete(key)
        await pipe.execute()
    return None


async def func_resend_send_email(config_resend_url: str, config_resend_key: str, from_email: str, to_email: str, email_subject: str, email_content: str) -> None:
    """Send an email using the Resend API."""
    import httpx, orjson
    headers = {"Authorization": f"Bearer {config_resend_key}", "Content-Type": "application/json"}
    payload = {"from": from_email, "to": [to_email], "subject": email_subject, "html": email_content}
    async with httpx.AsyncClient() as client:
        response = await client.post(config_resend_url, headers=headers, data=orjson.dumps(payload).decode("utf-8"))
        if response.status_code != 200:
            raise Exception(f"failed to send email: {response.text}")
    return None


def func_fast2sms_send_otp_mobile(config_fast2sms_url: str, config_fast2sms_key: str, mobile_number: str, otp_code: str) -> dict:
    """Send an OTP via Fast2SMS API."""
    import requests
    response = requests.get(config_fast2sms_url, params={"authorization": config_fast2sms_key, "numbers": mobile_number, "variables_values": otp_code, "route": "otp"}).json()
    if not response.get("return"):
        raise Exception(response.get("message"))
    return response


def func_gsheet_object_create(client_gsheet: any, sheet_url: str, obj_list: list) -> any:
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


async def func_gsheet_object_read(sheet_url: str) -> list:
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


async def func_mongodb_object_create(client_mongodb: any, database: str, table: str, obj_list: list) -> str:
    """Insert multiple records into a MongoDB collection."""
    if not client_mongodb:
        raise Exception("mongo client missing")
    result = await client_mongodb[database][table].insert_many(obj_list)
    return str(result.inserted_ids)


async def func_mongodb_object_delete(client_mongodb: any, database: str, table: str, obj_list: list) -> str:
    """Delete multiple records from a MongoDB collection using ID matching from a list of objects."""
    if not client_mongodb:
        raise Exception("mongo client missing")
    from bson.objectid import ObjectId
    id_list = []
    for obj in obj_list:
        obj_id = obj.get("_id") or obj.get("id")
        if not obj_id:
            continue
        try:
            id_list.append(ObjectId(obj_id)) if len(str(obj_id)) == 24 else id_list.append(obj_id)
        except Exception:
            id_list.append(obj_id)
    if not id_list:
        return "0 rows deleted"
    result = await client_mongodb[database][table].delete_many({"_id": {"$in": id_list}})
    return f"{result.deleted_count} rows deleted"


def func_jira_worklog_export(*, url: str, email_address: str, api_token: str, start_date: str, end_date: str, output_path: str) -> str:
    """Export Jira worklogs for a specific period to a CSV file."""
    try:
        from jira import JIRA
        from pathlib import Path
        import pandas as pd, uuid
        output_path = output_path or f"tmp/{uuid.uuid4().hex}.csv"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        jira_client = JIRA(server=url, basic_auth=(email_address, api_token))
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
