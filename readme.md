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
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -V
./venv/bin/uvicorn main:app --reload

#docker
docker build -t atom .
docker run --rm -p 8000:8000 atom
```

### Commands
```bash
#test curls
./test.sh

#consumer
venv/bin/python consumer.py celery
venv/bin/python consumer.py rabbitmq
venv/bin/python consumer.py redis
venv/bin/python consumer.py kafka
```

### zzz
```bash
#env
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_mongodb_url=mongodb://localhost:27017

#package
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
\copy test to 'tmp/file.csv' csv header;
\copy (select * from test limit 1000) to 'file.csv' csv header;
\copy test(title,type,rating) from 'file.csv' delimiter ',' csv header;

#p95
SELECT api, ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)) AS p95_response_time FROM log_api WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' GROUP BY api ORDER BY p95_response_time DESC;

#func/trigger
SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE p.proname LIKE 'func_%' ORDER BY p.proname;
SELECT trigger_name FROM information_schema.triggers WHERE trigger_name LIKE 'trigger_%' UNION ALL SELECT evtname FROM pg_event_trigger WHERE evtname LIKE 'trigger_%' ORDER BY 1;

#uuid without dash
uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-'

#github setup repo as dev
ssh-keygen -t ed25519 -C "atom36942@gmail.com"
cat ~/.ssh/id_ed25519.pub
ssh -T git@github.com
git clone git@github.com:atom36942/atom.git
cd atom
git remote set-url origin git@github.com:atom36942/atom.git
git pull origin main
git add .
git commit -m "sync"
git push origin main

#brew setup
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install python@3.11
brew install postgis
brew install postgresql && brew install redis && brew install rabbitmq && brew tap mongodb/brew && brew install mongodb-community && echo 'export PATH="/opt/homebrew/sbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
brew services start postgresql && brew services start redis && brew services start rabbitmq && brew services start mongodb-community
brew services restart postgresql && brew services restart redis && brew services restart rabbitmq && brew services restart mongodb-community
brew services stop postgresql && brew services stop redis && brew services stop rabbitmq && brew services stop mongodb-community
brew update && brew upgrade postgresql && brew upgrade redis && brew upgrade rabbitmq && brew upgrade mongodb-community && brew services restart --all
brew services stop --all && brew uninstall --force postgresql && brew uninstall --force redis && brew uninstall --force rabbitmq && brew uninstall --force mongodb-community && rm -rf /opt/homebrew/var/postgres /opt/homebrew/var/db/redis /opt/homebrew/var/lib/rabbitmq /opt/homebrew/var/mongodb && brew cleanup
psql --version && redis-cli --version && rabbitmqctl version && mongosh --version && mongod --version
brew services list && nc -zv 127.0.0.1 5432 6379 5672 27017
brew services list

#psql
psql --version
psql -U atom -d postgres
psql postgres
\x off
psql postgres -c "\du"
psql postgres -c "\l"

#psql
psql postgres -c "CREATE USER user_1;"
psql postgres -c "ALTER USER user_1 WITH PASSWORD '123';"
psql postgres -c "ALTER USER user_1 NOSUPERUSER NOCREATEDB NOCREATEROLE;"
psql postgres -c "CREATE DATABASE db_1 OWNER user_1;"
psql -U user_1 -d db_1
postgresql://user_1:123@127.0.0.1/db_1
```