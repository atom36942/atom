### About atom
```
1. atom is an open-source backend that has pre-built modules which are most commonly used
2. atom can reduce develoment time to a large extent
3. primary vision is to help entreprenurs to laucnh their ideas faster
4. atom is non-opionanted as atom is written on object level with no affection to type of object
5. core tech stack=python,fastapi,postgres,redis
```

### coding pattern
```
Atom follows procedural+functional programming style with focus on solid principles.

Procedural programming is a programming paradigm built around the idea that programs are sequences of instructions to be executed. They focus heavily on splitting up programs into named sets of instructions called procedures, analogous to functions. A procedure can store local data that is not accessible from outside the procedure's scope and can also access and modify global data variables.

```

### api docs
```
https://atom-tbsk.onrender.com/docs
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