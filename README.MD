### about atom
```
- atom is an open-source backend that has pre-built modules which are most commonly used
- atom can reduce develoment time to a large extent
- primary vision is to help entreprenurs to laucnh their ideas faster
- atom is non-opionanted as atom is written on object level with no affection to type of object
- atom follows procedural+functional programming style with focus on solid principles
- core tech stack=python,fastapi,postgres,redis
```

### contact/links
```
- api docs=https://atom-tbsk.onrender.com/docs
- contact=atom36942@gmail.com
```

### how to run
```
- download atom repo
- create .env file inside downloaded folder(check env file section)
- create venv
- install requirements.txt
- run python main.py
```

### env file
```
postgres_database_url=credential
redis_server_url=credential
secret_key_jwt=credential
secret_key_root=credential
secret_key_pinecone=credential
secret_key_gemini=credential
secret_key_openai=credential
aws_access_key_id=credential
aws_secret_access_key=credential
cassandra_scb_path=credential
cassandra_client_id=credential
cassandra_secret_key=credential
valkey_server_url=credential
lavinmq_server_url=credential
rabbitmq_server_url=credential
mongodb_cluster_url=credential
ftp_host=credential
ftp_username=credential
ftp_password=credential
ftp_port=credential
USER_AGENT=credential
```

### how to add sentry
```
Sentry provides end-to-end distributed tracing, enabling developers to identify and debug performance issues and errors across their systems and services.
How:-
-add key "sentry_dsn" in .env file
-check your sentry account for logs
```

### redis caching layer
```
Redis offers several key benefits, including: extremely fast performance due to its in-memory storage, support for a wide variety of data structures, high scalability, flexible persistence options, and ease of use, making it ideal for caching frequently accessed data and improving application responsiveness.
Atom has inbuild redis caching layer for any api.
How:-
- add key "redis_server_url" in .env file
- add decorator @cache(expire=60) in any api you want to cache with expiry time in seconds
- for ex:

@app.get("/public/project-meta")
@cache(expire=60)
async def public_project_meta(request:Request):
   #logic
   query_dict={"user_count":"select count(*) from users;"}
   temp={k:await postgres_client.fetch_all(query=v,values={}) for k,v in query_dict.items()}
   response={"status":1,"message":temp}
   #final
   return response
```




