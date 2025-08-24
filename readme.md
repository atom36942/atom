## About
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Built-in support for Postgres, Redis, S3, Kafka, and many other services  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated: full flexibility in defining business schema, API structure, and external libraries
- Tech Stack:Python,FastAPI,PostgreSQL,Redis,S3,Celery,RabbitMQ,Kafka,Sentry







## Installation
```bash
#download repo
git clone https://github.com/atom36942/atom.git
cd atom

#create venv
python3 -m venv venv

#install requirements
./venv/bin/pip install -r requirements.txt

#setup env must
config_postgres_url=postgresql://atom@127.0.0.1/postgres?sslmode=disable
config_redis_url=redis://localhost:6379
config_key_root=UZit5LLGZmqqvScH8E8PAZSsYKSt21LDzYwAyJ6hIrvpRrv4clHM8asr6gATOgPB
config_key_jwt=UZit5LLGZmqqvScH8E8PAZSsYKSt21LDzYwAyJ6hIrvpRrv4clHM8asr6gATOgPB

#setup env optional
config_mongodb_url=mongodb://localhost:27017
config_celery_broker_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_redis_pubsub_url=redis://localhost:6379
config_sentry_dsn=value

#server start direct
./venv/bin/uvicorn main:app --reload

#server start docker
docker build -t atom .
docker run -p 8000:8000 atom
```










## Commands
```python
#package
./venv/bin/pip install fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip freeze > requirements.txt

#test curls
./curl.sh

#stop python
lsof -ti :8000 | xargs kill -9

#reset postgres                    
drop schema if exists public cascade;
create schema if not exists public;

#export postgres
\copy table to 'path'  delimiter ',' csv header;
\copy (query) to 'path'  delimiter ',' csv header;

#import postgres       
\copy table from 'path' delimiter ',' csv header;
\copy table(column) from 'path' delimiter ',' csv header;

#consumer
cd consumer && ./venv/bin/celery -A celery worker --loglevel=info
cd consumer && ./venv/bin/python kafka.py
cd consumer && ./venv/bin/python rabbitmq.py
cd consumer && ./venv/bin/python redis.py

#p95
SELECT api, ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)::numeric, 2) AS p95_response_time FROM log_api WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY api ORDER BY p95_response_time DESC;

#asyncio
from function import function_export_postgres_query
import asyncio
postgres_url = "postgresql://atom@127.0.0.1/postgres?sslmode=disable"
query = "SELECT * FROM users"
x=function_export_postgres_query(postgres_url,query)
asyncio.run(x)
```




















































