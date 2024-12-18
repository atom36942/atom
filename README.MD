# about atom
1. atom is a open-source repo that be used to deployed backend of most applications in minimal time
2. atom has pre-built modules that is common accross most of the applications
3. primary vision is to help entreprenurs to laucnh their ideas faster
4. atom follows procedural+functional programming style with focus on solid principles
5. core tech stack=python,fastapi,postgres,redis
6. [api docs](https://atom-tbsk.onrender.com/docs)
7. contact=atom36942@gmail.com

# how to run
1. download atom repo
2. create .env file inside downloaded folder (check below for env file keys)
3. create venv
4. install requirements.txt
5. python main.py

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
