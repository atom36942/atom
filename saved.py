#db runner
@app.post("/root/db-runner")
async def root_db_runner(request:Request):
   #param
   query=(await request.json()).get("query")
   if not query:return error("query must")
   query_list=query.split("---")
   #check
   danger_word=["drop","truncate"]
   for item in danger_word:
       if item in query.lower():return error(f"{item} keyword not allowed in query")
   #logic
   output=[]
   async with postgres_client.transaction():
      for query in query_list:
         result=await postgres_client.fetch_all(query=query,values={})
         output.append(result)
   #final
   output=output[0] if len(query_list)==1 else output
   return {"status":1,"message":output}

@app.post("/root/object-create")
async def root_object_create(request:Request):
   #param
   is_serialize=int(request.query_params.get("is_serialize",1))
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=await request.json()
   #check
   if table in ["spatial_ref_sys"]:return error("table not allowed")
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   for key,value in object.items():
      if key in column_lowercase:object[key]=value.strip().lower()
   if "password" in object:is_serialize=1
   #logic
   response=await postgres_create(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response

@app.put("/root/object-update")
async def root_object_update(request:Request):
   #param
   is_serialize=int(request.query_params.get("is_serialize",1))
   table=request.query_params.get("table")
   if not table:return error("table missing")
   object=await request.json()
   #check
   if table in ["spatial_ref_sys"]:return error("table not allowed")
   if len(object)<=1:return error ("object issue")
   if "id" not in object:return error ("id missing")
   if "password" in object and len(object)!=2:return error("object length should be 2 only")
   if "password" in object:is_serialize=1
   response=await object_check(table_id,column_lowercase,[object])
   if response["status"]==0:return error(response["message"])
   object=response["message"][0]
   #logic
   response=await postgres_update(table,[object],is_serialize,postgres_client,postgres_column_datatype,object_serialize)
   if response["status"]==0:return error(response["message"])
   #final
   return response
