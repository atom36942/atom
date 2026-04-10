
async def func_redis_producer(channel: str, client_redis: any, task_obj: dict) -> str:
    """Dispatch a task to Redis PubSub."""
    import orjson
    await client_redis.publish(channel, orjson.dumps(task_obj))
    return "queued redis"

async def func_redis_object_create(client_redis: any, obj_list: list, expiration_sec: int = None) -> str:
    """Batch create/update objects in Redis with optional expiration in a pipeline transaction."""
    async with client_redis.pipeline(transaction=True) as pipe:
        for obj in obj_list:
            key = obj.get("id")
            if not key:
                continue
            pipe.set(str(key), str(obj))
            if expiration_sec:
                pipe.expire(str(key), expiration_sec)
        await pipe.execute()
    return "redis object created"

async def func_redis_object_delete(client_redis: any, obj_list: list) -> str:
    """Batch delete objects in Redis using a pipeline transaction."""
    async with client_redis.pipeline(transaction=True) as pipe:
        for obj in obj_list:
            key = obj.get("id")
            if not key:
                continue
            pipe.delete(str(key))
        await pipe.execute()
    return "redis object deleted"

async def func_gsheet_object_create(client_gsheet: any, spreadsheet_id: str, obj_list: list) -> str:
    """Batch append records to a Google Sheet."""
    sheet = client_gsheet.open_by_key(spreadsheet_id).get_worksheet(0)
    sheet.append_rows([list(obj.values()) for obj in obj_list])
    return "gsheet object created"

async def func_gsheet_object_read(client_gsheet: any, spreadsheet_id: str) -> list:
    """Read all records from a Google Sheet."""
    sheet = client_gsheet.open_by_key(spreadsheet_id).get_worksheet(0)
    return sheet.get_all_records()


async def func_mongodb_object_create(client_mongodb: any, db_name: str, collection_name: str, obj_list: list) -> str:
    """Batch insert documents into a MongoDB collection."""
    db = client_mongodb[db_name]
    collection = db[collection_name]
    await collection.insert_many(obj_list)
    return "mongodb object created"

async def func_mongodb_object_delete(client_mongodb: any, db_name: str, collection_name: str, query: dict) -> str:
    """Delete documents from a MongoDB collection based on a query."""
    db = client_mongodb[db_name]
    collection = db[collection_name]
    await collection.delete_many(query)
    return "mongodb object deleted"

async def func_jira_worklog_export(jira_url: str, jira_email: str, jira_token: str, jql_query: str) -> list:
    """Export Jira worklogs for issues matching a JQL query, with automatic pagination and user mapping."""
    from jira import JIRA
    jira = JIRA(server=jira_url, basic_auth=(jira_email, jira_token))
    issues = jira.search_issues(jql_query, maxResults=False)
    worklogs = []
    for issue in issues:
        issue_worklogs = jira.worklogs(issue.id)
        for wl in issue_worklogs:
            worklogs.append({"issue": issue.key, "author": wl.author.displayName, "time_spent": wl.timeSpent, "date": wl.started})
    return worklogs

