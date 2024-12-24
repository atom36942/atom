### about atom
1. atom is an open-source backend that has pre-built modules which are most commonly used
2. atom can reduce develoment time to a large extent
3. primary vision is to help entreprenurs to laucnh their ideas faster
4. atom is non-opionanted and can be used to build backend for most of the ideas
5. core tech stack=python,fastapi,postgres,redis
6. atom doesn't rely on any orm and uses raw sql entirely
7. atom supports large scale data ingestion using rabbitmq/lavinmq/kafka
8. atom has object-level crud by directly interacting with databaese schema for serialization
9. atom can generate entire business schema with a single json

### contact
If you have an idea and want to use atom to build tech super-fast,email your requirement @:-
atom36942@gmail.com

### coding paradigm
Atom follows procedural+functional programming paradigm with focus on solid principles.  
Procedural programming is a programming paradigm built around the idea that programs are sequences of instructions to be executed.
They focus heavily on splitting up programs into named sets of instructions called procedures, analogous to functions.
A procedure can store local data that is not accessible from outside the procedure's scope and can also access and modify global data variables.

### api docs
1. live = https://www.atom42.org/docs
2. localhost = http://localhost:8000/docs
3. localhost =  http://127.0.0.1:8000/redoc

### how to run
1. download atom repo
2. create .env file inside downloaded folder(check env file section)
3. create venv
4. install requirements.txt
5. run python main.py

### how to run using docker
1. docker build -t atom .
2. docker run -p 8000:8000 atom

### env file
```
postgres_database_url=null
redis_server_url=null
secret_key_jwt=null
secret_key_root=null
token_expiry_second=null
aws_access_key_id=null
aws_secret_access_key=null
secret_key_gemini=null
secret_key_openai=null
sentry_dsn=null
opensearch_url=null
valkey_server_url=null
mongodb_cluster_url=null
lavinmq_server_url=null
rabbitmq_server_url=null
kafka_server_url=null
kafka_path_cafile=null
kafka_path_certfile=null
kafka_path_keyfile=null
ftp_host=null
ftp_username=null
ftp_password=null
ftp_port=null
timescaledb_url=null
meilisearch_url=null
meilisearch_key=null
cassandra_scb_path=null
cassandra_client_id=null
cassandra_secret_key=null
USER_AGENT=null
```

### features
```
1. sentry logs
2. redis caching layer
3. lifespan events
4. postgres client
5. redis client
6. ratelimiter
7. cors
8. middleware
9. authorization
10. routers
11. database schema one click setup
12. query runner
13. logged-in user apis
14. object level crud
15. action module
16. otp module
17. location search
18. s3 apis
19. admin apis
20. gemini integration
21. chromadb integration
22. openai integration
23. langchain apis
24. opensearch apis
25. memcached integration
26. valkey integration
27. mongodb integration
28. kafka producer-consumer
29. redis pubs-ub
30. rabbitmq producer-consumer
31. lavinmq producer-consumer
32. ftp integration
33. timescaledb integration
34. meilisearch integration
35. aws sns integration
36. aws ses integration
37. aws rekognition integration
38. aws dynamodb integration
39. sqlite integration
40. streamlit forms
41. postgres read replicas
41. postgres schema setup usuing one json
42. postgres indexing
```
