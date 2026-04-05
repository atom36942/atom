<details>
<summary>About</summary>
<div style="padding-top: 10px;">

| Core Principle | Description |
| :--- | :--- |
| **Speed** | Open-source backend for rapid large-scale development. |
| **Architecture** | Modular setup combining functional and procedural styles. |
| **Reliability** | Pure functions to minimize side effects and improve testing. |
| **Production** | Rapidly build APIs, background jobs, and integrations. |
| **Efficiency** | Minimal boilerplate to avoid reinventing the wheel. |
| **Flexibility** | Non-opinionated and fully extensible framework. |
| **Tech Stack** | FastAPI, Postgres, Redis, RabbitMQ, Kafka, Celery, S3. |

</div>
</details>

<details>
<summary>Setup: Local Deployment</summary>
<div style="padding-top: 10px;">

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

</div>
</details>

<details>
<summary>Setup: Docker Deployment</summary>
<div style="padding-top: 10px;">

```bash
docker build -t atom .
docker run --rm -p 8000:8000 atom
```

</div>
</details>

<details>
<summary>Setup: Environment Variables</summary>
<div style="padding-top: 10px;">

```bash
export config_postgres="postgresql://atom@127.0.0.1/postgres"
export config_redis_url="redis://localhost:6379"
export config_rabbitmq_url="amqp://guest:guest@localhost:5672"
export config_mongodb_uri="mongodb://localhost:27017"
```

</div>
</details>



<details>
<summary>Consumers</summary>
<div style="padding-top: 10px;">

| Protocol | Backend | Run Consumer |
| :--- | :--- | :--- |
| **Celery** | Redis | `python consumer.py celery` |
| **Kafka** | Event Stream | `python consumer.py kafka` |
| **RabbitMQ** | AMQP | `python consumer.py rabbitmq` |
| **Redis** | Pub/Sub | `python consumer.py redis` |


</div>
</details>


<details>
<summary>FAQ</summary>
<div style="padding-top: 10px;">

| What | Description/Remark |
| :--- | :--- |
| **API Master** | Interactive tester at `static/api.html` or `/page-api`. |
| **Serve static content** | Served via the `static/` directory prefix. |
| **Serve html pages** | Served via `/page-{name}` (e.g. `/page-login`). |
| **Database Lifecycle Init** | Runs `func_postgres_init` on startup. |
| **Database Manual Init** | Full system refresh via `/admin/sync` API. |
| **Access App State** | Global clients and config singletons via `request.app.state`. |
| **Access Request User State** | Authorized user context (id, role, etc.) via `request.state.user`. |

</div>
</details>
