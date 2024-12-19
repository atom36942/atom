# about atom
```
- atom is an open-source backend that has pre-built modules which are most commonly used
- atom can reduce develoment time to a large extent
- primary vision is to help entreprenurs to laucnh their ideas faster
- atom is non-opionanted as atom is written on object level with no affection to type of object
- atom follows procedural+functional programming style with focus on solid principles
- core tech stack=python,fastapi,postgres,redis
```

# contact/links
```
- api docs=https://atom-tbsk.onrender.com/docs
- contact=atom36942@gmail.com
```

# how to run
```
- download atom repo
- create .env file inside downloaded folder(check env file section)
- create venv
- install requirements.txt
- run python main.py
```

# env file
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

# How to add sentry
```
Sentry provides end-to-end distributed tracing, enabling developers to identify and debug performance issues and errors across their systems and services.
Just add key "sentry_dsn" in .file
```

# fundamentals - api gates and authorization
```
atom has 5 api gates to divide all the apis from the access pov.
all apis auto
- {baseurl}/root = this gate needs root user
```

# database schema init
