### About
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated and full flexible to extend
- Tech Stack:Python,FastAPI,PostgreSQL,Redis,S3,Celery,RabbitMQ,Kafka,Sentry

### Modules
- PostgreSQL: one-click setup, CSV upload, query runner
- Auth & RBAC: auth APIs, user/admin APIs
- Performance: Redis cache, rate limiting
- Async & Queues: Celery, Kafka, RabbitMQ, Redis pub/sub
- Integrations: Sentry, MongoDB, PostHog
- Messaging: OTP (Fast2SMS, Resend), AWS S3/SNS/SES
- Data Ops: bulk insert/update, Google Sheets, SFTP
- Platform: HTML serving, multi-tenant support, extensible architecture

### Installation
```bash
#direct
git clone https://github.com/atom36942/atom.git
cd atom
touch .env
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn main:app --reload

#docker
docker build -t atom .
docker run -it --rm -p 8000:8000 atom
```

### Commands
```bash
#test curls
./core/test.sh

#consumer
venv/bin/celery -A consumer.celery worker
venv/bin/python -m consumer.kafka
venv/bin/python -m consumer.rabbitmq
venv/bin/python -m consumer.redis
```




### zzz
```bash
#env sample
config_postgres_url=postgresql://postgres@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_key_jwt=YwAyJ6hIrvpRrv4clHM8asr6gATOg
config_key_root=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
config_celery_broker_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_redis_url_pubsub=redis://localhost:6379
config_mongodb_url=mongodb://localhost:27017

#package ops
./venv/bin/pip install fastapi
./venv/bin/pip uninstall fastapi
./venv/bin/pip install --upgrade fastapi
./venv/bin/pip install -r requirements.txt
./venv/bin/pip freeze > requirements.txt

#stop python
lsof -ti :8000 | xargs kill -9

#reset postgres                    
drop schema if exists public cascade;
create schema if not exists public;

#exim postgres
\copy test to 'export/zzz/psql_export_all.csv' csv header;
\copy (select * from test limit 1000) to 'export/zzz/psql_export_limit.csv' csv header;
\copy test(title,type,rating,updated_at,dob,tag,tag_int,tag_bigint,location,metadata) from 'sample/postgres_create.csv' delimiter ',' csv header;

#p95
SELECT api, ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)) AS p95_response_time FROM log_api WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY api ORDER BY p95_response_time DESC;

#sample config table sql
INSERT INTO config (title, metadata) VALUES ('config_api', '{"\/protected\/test":{"password":"123"}}'::jsonb);
```
