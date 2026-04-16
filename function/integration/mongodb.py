async def func_mongodb_object_create(*, client_mongodb: any, database: str, table: str, obj_list: list) -> str:
    """Insert multiple records into a MongoDB collection."""
    if not client_mongodb:
        raise Exception("mongo client missing")
    result = await client_mongodb[database][table].insert_many(obj_list)
    return str(result.inserted_ids)

async def func_mongodb_object_delete(*, client_mongodb: any, database: str, table: str, obj_list: list) -> str:
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
