### About
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Built-in support for Postgres, Redis, S3, Kafka, and many other services  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated: full flexibility in defining business schema, API structure, and external libraries
- Tech Stack:Python,FastAPI,PostgreSQL,Redis,S3,Celery,RabbitMQ,Kafka,Sentry

### Modules
- one click postgres database setup
- postgres csv uploader
- postgres query runner
- auth apis
- logged in user apis
- admin apis
- api cache using redis
- api ratelimiter setup
- celery/kafka/rabbitmq/redis pub-sub queue setup
- sentry/mongodb/posthog integration
- otp client integration - fast2sms/resend
- aws s3,sns,ses integration
- html pages serve
- user crud apis as per rbac
- bulk insert/update with buffer
- gsheet integration
- easy extension
- supports multi-tenant design

### Installation
```bash
git clone https://github.com/atom36942/atom.git
cd atom
touch .env
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn main:app --reload
```

### Docker
```bash
docker build -t atom .
docker run -it --rm -p 8000:8000 atom
```

### Consumer
```bash
venv/bin/celery -A consumer.celery worker --loglevel=info
venv/bin/python -m consumer.kafka
venv/bin/python -m consumer.rabbitmq
venv/bin/python -m consumer.redis
```

### Commands
```bash
#test curls
./file/test.sh

#update packages
./venv/bin/python ./file/package.py
```

### Env Sample
```bash
config_postgres_url=postgresql://postgres@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_key_root=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
config_key_jwt=YwAyJ6hIrvpRrv4clHM8asr6gATOg
config_celery_broker_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_redis_url_pubsub=redis://localhost:6379
config_mongodb_url=mongodb://localhost:27017
```

### zzz
```bash
#package
./venv/bin/pip install fastapi
./venv/bin/pip freeze > requirements.txt
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip uninstall fastapi

#stop python
lsof -ti :8000 | xargs kill -9

#reset postgres                    
drop schema if exists public cascade;
create schema if not exists public;

#exim postgres
\copy test to 'export/zzz/psql_export_all.csv' csv header;
\copy (select * from test limit 1000) to 'export/zzz/psql_export_limit.csv' csv header;
\copy test(title,type,rating,updated_at,dob,tags,location,metadata) from 'sample/postgres.csv' delimiter ',' csv header;

#p95
SELECT api, ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)::numeric, 2) AS p95_response_time FROM log_api WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY api ORDER BY p95_response_time DESC;
```
