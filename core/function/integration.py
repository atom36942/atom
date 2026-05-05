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
            await client_mongodb[database][table].delete_many({"_id": {"": id_list}})
        count += len(ol)
    return count
