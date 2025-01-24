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










