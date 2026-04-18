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
