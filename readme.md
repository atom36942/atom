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

### Test
```bash
./file/test.sh
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

#export postgres
\copy table to 'path'  delimiter ',' csv header;
\copy (query) to 'path'  delimiter ',' csv header;

#import postgres       
\copy table from 'path' delimiter ',' csv header;
\copy table(column) from 'path' delimiter ',' csv header;

#p95
SELECT api, ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)::numeric, 2) AS p95_response_time FROM log_api WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY api ORDER BY p95_response_time DESC;

#sample csv
title	type	rating	updated_at	dob	tags	location	metadata
test 1	1	2.24	2023-01-02 12:00:00	2000-01-01	{1,2,3,4,5}	POINT(67.138848 -16.578165)	1
test 2	2	3.34234	2023-01-03 12:00:00	2000-01-02	{a,b,c}	POINT(69.138848 -16.578165)	"test"
test 3	3	1.06	2023-01-04 12:00:00	2000-01-03	{{1,2},{3,4}}	POINT(76.317336 52.088573)	{"type":1,"title":"list"}
test 4	4	1.7	2023-01-05 12:00:00	2000-01-04	{true,false,true}	POINT(-6.616613 -88.085726)	[{"type":1,"title":"list"},{"type":2,"title":"admin"},{"type":3,"title":"admin"}]
test 5	5	1.67	2023-01-06 12:00:00	2000-01-05	{python,java,sql}	POINT(-47.936117 3.251615)	{"object_list":[{"type":1,"title":"list"},{"type":2,"title":"admin"},{"type":3,"title":"admin"}]}
```