### about
- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
- Non-opinionated and full flexible to extend
- Tech Stack: Python, FastAPI, Postgres, Redis, S3, Celery, RabbitMQ, Kafka, Sentry

### setup
<details>
<summary>direct</summary>

```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -V
./venv/bin/uvicorn main:app --reload
```
</details>

<details>
<summary>docker</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```
</details>

### consumer
<details>
<summary>run</summary>

```bash
./venv/bin/python consumer.py celery
./venv/bin/python consumer.py rabbitmq
./venv/bin/python consumer.py redis
./venv/bin/python consumer.py kafka
```
</details>

### develop
- Refer [AGENTS.md](file:///Users/atom/atom/AGENTS.md) for coding rules
- Refer [dev.md](file:///Users/atom/atom/static/dev.md) for personal notes & snippets
