async def func_mongodb_create(*, upload_file: any, client_mongodb: any, database: str, table: str, chunk_size: int, func_api_file_to_chunks: any) -> int:
    """Insert multiple records from a CSV file into a MongoDB collection."""
    if not client_mongodb: raise Exception("mongo client missing")
    count = 0
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=chunk_size):
        await client_mongodb[database][table].insert_many(ol)
        count += len(ol)
    return count

async def func_mongodb_update(*, upload_file: any, client_mongodb: any, database: str, table: str, chunk_size: int, func_api_file_to_chunks: any) -> int:
    """Update multiple records from a CSV file in a MongoDB collection using Replacement."""
    if not client_mongodb: raise Exception("mongo client missing")
    from pymongo import ReplaceOne
    from bson.objectid import ObjectId
    count = 0
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=chunk_size):
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

async def func_mongodb_delete(*, upload_file: any, client_mongodb: any, database: str, table: str, chunk_size: int, func_api_file_to_chunks: any) -> int:
    """Delete multiple records from a MongoDB collection using a list of IDs from a CSV file."""
    if not client_mongodb: raise Exception("mongo client missing")
    from bson.objectid import ObjectId
    count = 0
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=chunk_size):
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
