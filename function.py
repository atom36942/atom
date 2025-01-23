async def queue_pull(data,postgres_cud,postgres_client,object_serialize,postgres_column_datatype):
   try:
      mode,table,object,is_serialize=data["mode"],data["table"],data["object"],data["is_serialize"]
      if is_serialize:
         response=await object_serialize(postgres_column_datatype,[object])
         if response["status"]==0:print(response)
         object=response["message"][0]
      response=await postgres_cud(postgres_client,mode,table,[object])
      if response["status"]==0:print(response)
      print(mode,table,response)
   except Exception:pass
   return None



async def create_where_string(postgres_column_datatype,object):
   object={k:v for k,v in object.items() if k in postgres_column_datatype}
   object={k:v for k,v in object.items() if k not in ["location","metadata"]}
   object={k:v for k,v in object.items() if k not in ["table","order","limit","page"]}
   object_operator={k:v.split(',',1)[0] for k,v in object.items()}
   object_value={k:v.split(',',1)[1] for k,v in object.items()}
   column_read_list=[*object]
   where_column_single_list=[f"({column} {object_operator[column]} :{column} or :{column} is null)" for column in column_read_list]
   where_column_joined=' and '.join(where_column_single_list)
   where_string=f"where {where_column_joined}" if where_column_joined else ""
   where_value=object_value
   return {"status":1,"message":[where_string,where_value]}







async def add_action_count(postgres_client,action,object_table,object_list):
   if not object_list:return {"status":1,"message":object_list}
   key_name=f"{action}_count"
   object_list=[dict(item)|{key_name:0} for item in object_list]
   parent_ids_list=[str(item["id"]) for item in object_list if item["id"]]
   parent_ids_string=",".join(parent_ids_list)
   if parent_ids_string:
      query=f"select parent_id,count(*) from {action} where parent_table=:parent_table and parent_id in ({parent_ids_string}) group by parent_id;"
      query_param={"parent_table":object_table}
      object_list_action=await postgres_client.fetch_all(query=query,values=query_param)
      for x in object_list:
         for y in object_list_action:
               if x["id"]==y["parent_id"]:
                  x[key_name]=y["count"]
                  break
   return {"status":1,"message":object_list}

async def add_creator_data(postgres_client,object_list):
   if not object_list:return {"status":1,"message":object_list}
   object_list=[dict(item)|{"created_by_username":None} for item in object_list]
   created_by_ids_list=[str(item["created_by_id"]) for item in object_list if item["created_by_id"]]
   created_by_ids_string=",".join(created_by_ids_list)
   if created_by_ids_string:
      query=f"select * from users where id in ({created_by_ids_string});"
      object_list_user=await postgres_client.fetch_all(query=query,values={})
      for x in object_list:
         for y in object_list_user:
            if x["created_by_id"]==y["id"]:
               x["created_by_username"]=y["username"]
               break
   return {"status":1,"message":object_list}



