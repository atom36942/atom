# Direct Deployment
```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
venv/bin/python main.py
venv/bin/uvicorn main:app --reload
```

# Docker Deployment
```bash
git clone https://github.com/atom36942/atom.git
cd atom
docker build -t atom .
docker run --rm -p 8000:8000 atom
```

# Sample Local Env
```bash
config_postgres_url=postgresql://atom:123456@127.0.0.1:5432/postgres?sslmode=disable
config_postgres_url_read=postgresql://user_read:123456@127.0.0.1:5432/postgres?sslmode=disable
config_redis_url=redis://localhost:6379
config_mongodb_url=mongodb://localhost:27017
config_redis_url_queue=redis://localhost:6379
config_rabbitmq_url=amqp://guest:guest@localhost:5672
config_celery_url=redis://localhost:6379
```