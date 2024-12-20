### about atom
```
1. atom is an open-source backend that has pre-built modules which are most commonly used
2. atom can reduce develoment time to a large extent
3. primary vision is to help entreprenurs to laucnh their ideas faster
4. atom is non-opionanted as it is written on object level with no affection to type of object
5. core tech stack=python,fastapi,postgres,redis
6. atom doesn't rely on any orm and uses raw sql entirely
```

### coding paradigm
```
Atom follows procedural+functional programming paradigm with focus on solid principles.

Procedural programming is a programming paradigm built around the idea that programs are sequences of instructions to be executed.
They focus heavily on splitting up programs into named sets of instructions called procedures, analogous to functions.
A procedure can store local data that is not accessible from outside the procedure's scope and can also access and modify global data variables.
```

### api docs
```
1. http://localhost:8000/redoc

2. http://127.0.0.1:8000/docs

3. sample hsoted docs = https://atom-tbsk.onrender.com/docs
```

### contact
```
atom36942@gmail.com
```

### how to run
```
1. download atom repo
2. create .env file inside downloaded folder(check env file section)
3. create venv
4. install requirements.txt
5. run python main.py
```

### how to run using docker
```
1. docker build -t atom .
2. docker run -p 8000:8000 atom
```

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

### sentry logs
```
Atom has inbuilt sentry logs logic which provides end-to-end distributed tracing, enabling developers to identify and debug performance issues and errors across their systems and services.

How to enable sentry logs in atom:-

1. add key "sentry_dsn" in .env file
2. check your sentry account for logs
```

### redis caching layer
```
Atom has inbuild redis caching layer for any api including request query params+token.

How to enable redis caching in atom:-

1. add key "redis_server_url" in .env file
2. add decorator @cache(expire=60) in any api you want to cache with expiry time in seconds (example api below)
3. atom has support to upload bulk data in the redis cache

@app.get("/example-api")
@cache(expire=60)
async def example_api(request:Request):
   api logic
   return response
```

### lifespan
```
If you want to execute some logics at app startup/shutdown, you can add them in the lifespan section.

Currently added logics:-

1. postgres connect/disconnect
2. redis client init
3. ratelimiter init
```

### ratelimiter
```
A Rate Limiter limits the number of client requests allowed to be sent over a specified period. If the API request count exceeds the threshold defined by the rate limiter, all the excess calls are blocked.
Atom support ratelimiting for any api with a simple query param.

How to use

1. Pass ratelimit configuration in the api dependencies(example api below)

@app.get("/example-api",dependencies=[Depends(RateLimiter(times=1,seconds=1))])
@cache(expire=60)
async def example_api(request:Request):
   api logic
   return response
```

### cors
```
You can modify cors as per your needs in the cors section.

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

```

### middleware
```
Atom has inbuilt middleware with below logics already built. You can add more logic as per your need.

1. auth check
2. api logs in database with batch insert
3. api errors catch
```

### authorization
```
Atom divides all api starting points as gates.
Atom has 5 gates depending on the type of user and its authorization. 
Gates auth logic is handled in middleware by default. While adding any api, just choose which gate you want your api belong to.
You can add more gates in the middleware if there is a need.

1. root=all api starting with /root will need root user token which is present in the .env file. This gate is for adding apis which has to be accessed by limited users without any need of database.
2. auth=all api stating with /auth are login apis.
3. my=all api starting from /my are logged-in user api.
4. public=all api starting with /public are apis where there is no auth needed. Any user can access it.
5. private - all api starting with /private are apis where there is token is needed.
6. admin - all api starting with /admin are api where user.type="admin" in db. 
```

### routers
```
If you want to make new api files, then just name it with "api_{filename}" and it will be automatically imported.
```

### database schema init
```
1. atom uses postgres as the primary database.
2. just add "postgres_database_url" in .env file
3. atom has a simple api to initialzie the entire database schema with just one click
4. api = {{baseurl}}/root/postgres-schema-init?mode=default
5. above api executes - extension installation + table creation + column creation + not null configuration + unique configuration + bulk delete disable + triggers + functions + procedures + protection on rows delete + misc query
```

### query runner
```
1. atom has given root user privilege to run any sql.
2. api={{baseurl}}/root/postgres-query-runner
3. to run bulk query, use separator "---"
4. bulk query sample=insert into otp (otp,email) values (123,'atom36942@gmail.com')---insert into otp (otp,mobile) values (123,'123456789')
```

### auth module
```
Atom has all the necessary auth apis prebuilt.

1. signup with username/password
2. login with username/password
3. login with google
4. login with email/otp
5. login with mobile/otp
6. login with email/password
7. login with mobile/password

Above apis support admin login also depending on the query param passed.
```

### logged-in user apis
```
Atom has many pre-built apis for logged-in user.

1. my profile
2. token refres
3. update password
4. update email with otp verification
5. update mobile with otp verification
6. delete any table primary keys in single/bulk mode
7. message module
8. object crud
9. action module

```

### object crud
```
1. atom has a object level crud approach where any object can be passed in crud apis
2. atom will handle serialization by interacting with the db schema itself
3. atom support all primary datatypes + array+jsonb crud
```

### action module
```
Atom supports unique/multiple action on any table with parent table concept.
Ex- likes,bookmark,comment,report,follow,block,etc
```

### otp module
```
Atom has pre-built to send/verify otp on email/mobile via aws sns/ses/etc

```


### location search
```
Atom has location search apis using postgis extension. PostGIS is a PostgreSQL extension that adds geospatial data capabilities to the database. You can seach store lat/long with search based on any filters.

```

### s3 apis
```
Atom has all the neccessary s3 apis to handle the blob storage use-cases.

1. upload binary
2. presigned url
3. empty/delete bucket
4. delete key
```

### admin apis
```
Atom has rback control to the deepest level to control rbac.
You can create further logics to build your own access control.
Atom inlcludes all the basics admin apis to control the business operations.
```

### gemini integration
```
Atom has all the basics gemini apis to start with for AI use-cases.

1. promot text generation
2. image analysis
3. audio analysis
4. embeddings
```

### chromadb integration
```
Atom has integrated chromadb for vector search use-cases like Embeddings, vector search, document storage, full-text search, metadata filtering, and multi-modal. 
```

### openai integration
```
Atom has baisc openai intregration for chat completion,create embedding etc.
```

### langchain
```
atom has basics langchain apis to do operations on data for ai use-cases.
1. chunk splitting
2. webpage loader
3. csv loader
4. pdf/txt loader
```

### opensearch apis
```
OpenSearch is an open-source, enterprise-grade search and observability suite that brings order to unstructured data at scale.
Atom has all the basics apis to start with OpenSearch. You can extend your search use-cases on top of that.
```

### memcached integration
```
Atom has integration for memcached where you can build high-performance, distributed memory object caching system, generic in nature, but intended for use in speeding up dynamic web applications by alleviating database load.
```

### valkey integration
```
Valkey is an open source (BSD) high-performance key/value datastore that supports a variety of workloads such as caching, message queues, and can act as a primary database. Valkey can run as either a standalone daemon or in a cluster, with options for replication and high availability.
Atom supports valkey integration
```

### mongodb integration
```
The document data model maps to how you think and code. Break out of rigid, tabular data structures with flexible documents that map directly to objects in your code. Embed related data into a single document to increase performance and minimize computational cost.
Atom supports mongodb integrations for all crud needs.
```

### pub-sub module
```
Atom has integrations with all major pub-sub vendors. Atom has both producer+consumer apis for below stacks.

1. kafka
2. redis
3. rabbitmq
4. lavinmq
```

### ftp
```
Atom has connection apis with ftp server with below aps.

1. create,rename,delete file,dir
2. upload file
```

### timescaledb
```
For ingesting and querying vast amounts of live data, atom has apis for timescaledb integration.
```

### meilisearch
```
Meilisearch is a flexible and powerful user-focused search engine that can be added to any website or application.

Atom has basic integration with meilisearch which  can be easily extended.
```

### sns integration
```
Amazon Simple Notification Service (Amazon SNS) is a web service that makes it easy to set up, operate, and send notifications from the cloud.

Atom has pre-built api to use aws sns.
```

### ses integration
```
Amazon Simple Email Service (SES) is a cost-effective email service built on the reliable and scalable infrastructure that Amazon.com developed to serve its own customer base. With Amazon SES, you can send transactional email, marketing messages, or any other type of high-quality content to your customers

Atom has pre-built api to use aws ses.
```

### ses integration
```
Rekognition Image is an image recognition service that detects objects, scenes, activities, landmarks, faces, dominant colors, and image quality. Rekognition Image also extracts text, recognizes celebrities, and identifies inappropriate content in images.

Atom has pre-built api to use aws Rekognition.
```

### dynamodb integration
```
Rekognition Image is an image recognition service that detects objects, scenes, activities, landmarks, faces, dominant colors, and image quality. Rekognition Image also extracts text, recognizes celebrities, and identifies inappropriate content in images.

Atom has pre-built api to use aws dynamodb.
```

### sqlite integration
```
SQLite is a C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine. SQLite is the most used database engine in the world. SQLite is built into all mobile phones and most computers and comes bundled inside countless other applications that people use every day.

Atom has pre-built api to use aws sqlite.
```
