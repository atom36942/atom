## About Us

| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend for rapid large-scale development. |
| **Architecture** | Modular setup combining functional and procedural styles. |
| **Reliability** | Pure functions to minimize side effects and improve testing. |
| **Production** | Rapidly build APIs, background jobs, and integrations. |
| **Efficiency** | Minimal boilerplate to avoid reinventing the wheel. |
| **Flexibility** | Non-opinionated and fully extensible framework. |
| **Tech Stack** | FastAPI, Postgres, Redis, RabbitMQ, Kafka, Celery, S3. |

## Setup

<div>
<details>
<summary>Local Deployment</summary>

```bash
git clone https://github.com/atom36942/atom.git
cd atom
rm -rf venv
/opt/homebrew/bin/python3.11 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -V
./venv/bin/python main.py
./venv/bin/uvicorn main:app --reload
```
</details>
</div>

<div>
<details>
<summary>Docker Deployment</summary>

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom```
</details>
</div>

<div>
<details>
<summary>Sample .env</summary>

```bash
cat <<EOF > .env
config_postgres="postgresql://atom@127.0.0.1/postgres"
config_redis_url="redis://localhost:6379"
config_rabbitmq_url="amqp://guest:guest@localhost:5672"
config_mongodb_uri="mongodb://localhost:27017"
EOF
```
</details>
</div>

## Consumers

| Protocol | Backend | Run Consumer |
| :--- | :--- | :--- |
| **Celery** | Redis | `./venv/bin/python consumer.py celery` |
| **Kafka** | Event Stream | `./venv/bin/python consumer.py kafka` |
| **RabbitMQ** | AMQP | `./venv/bin/python consumer.py rabbitmq` |
| **Redis** | Pub/Sub | `./venv/bin/python consumer.py redis` |

## FAQ

| Scenario | Description |
| :--- | :--- |
| **API Master** | Interactive tester at `static/api.html` or `/page-api`. |
| **Serve static content** | Served via the `static/` directory prefix. |
| **Serve html pages** | Served via `/page-{name}` (e.g. `/page-login`). |
| **Database Lifecycle Init** | Runs `func_postgres_init` on startup. |
| **Database Manual Init** | Full system refresh via `/admin/sync` API. |
| **Access App State** | Global clients and config singletons via `request.app.state`. |
| **Access Request User State** | Authorized user context (id, role, etc.) via `request.state.user`. |
