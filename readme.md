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
<summary>Setup: GitHub SSH</summary>
<div style="padding-top: 10px;">

```bash
ssh-keygen -t ed25519 -C "email"
cat ~/.ssh/id_ed25519.pub
ssh -T git@github.com
git clone git@github.com:atom36942/atom.git
cd atom
git remote set-url origin git@github.com:atom36942/atom.git
git pull origin main
git add .
git commit -m "sync"
git push origin main
```

</div>
</details>

<details>
<summary>Setup: Brew</summary>
<div style="padding-top: 10px;">

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew install python@3.11
brew install postgis
brew install postgresql && brew install redis && brew install rabbitmq && echo 'export PATH="/opt/homebrew/sbin:$PATH"' >> ~/.zshrc && source ~/.zshrc
brew services start postgresql && brew services start redis && brew services start rabbitmq
brew services restart postgresql && brew services restart redis && brew services start rabbitmq
brew services stop postgresql && brew services stop redis && brew services stop rabbitmq
brew update && brew upgrade postgresql && brew upgrade redis && brew upgrade rabbitmq && brew services restart --all
brew services stop --all && brew uninstall --force postgresql && brew uninstall --force redis && brew uninstall --force rabbitmq && rm -rf /opt/homebrew/var/postgres /opt/homebrew/var/db/redis /opt/homebrew/var/lib/rabbitmq && brew cleanup
psql --version && redis-cli --version && rabbitmqctl version
brew services list
```

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

| Environment Variable | Sample Value |
| :--- | :--- |
| `config_postgres` | `postgresql://user:pass@host/db` |
| `config_redis_url` | `redis://localhost:6379` |
| `config_rabbitmq_url` | `amqp://guest:guest@localhost:5672` |
| `config_mongodb_uri` | `mongodb://localhost:27017` |

</div>
</details>



<details>
<summary>Consumers</summary>
<div style="padding-top: 10px;">

| Protocol | Backend | Driver | Run Consumer |
| :--- | :--- | :--- | :--- |
| **Celery** | Redis | `func_celery_producer` | `python consumer.py celery` |
| **Kafka** | Event Stream | `func_kafka_producer` | `python consumer.py kafka` |
| **RabbitMQ** | AMQP | `func_rabbitmq_producer` | `python consumer.py rabbitmq` |
| **Redis** | Pub/Sub | `func_redis_producer` | `python consumer.py redis` |


</div>
</details>


<details>
<summary>Middleware</summary>
<div style="padding-top: 10px;">

Every incoming request passes through a strictly ordered validation and processing sequence.

| Order | Pipeline Stage | Behavior |
| :--- | :--- | :--- |
| **1** | **Authentication** | JWT decoding and identity verification. |
| **2** | **Admin Check** | Enforces admin role for `/admin/` paths. |
| **3** | **Active Check** | Checks `is_active=1` status from cache. |
| **4** | **Rate Limiting** | Enforces IP/User sliding window constraints. |
| **5** | **Response Cache** | Returns Gzip/B64 cache if TTL is valid. |
| **6** | **API Execution** | Processes main functional logic. |
| **7** | **API Logging** | Logs non-GET requests in background. |


</div>
</details>

<details>
<summary>API Roles</summary>
<div style="padding-top: 10px;">

Path-based security is enforced automatically by the unified middleware pipeline.

| Prefix Path | Requirement | Behavior |
| :--- | :--- | :--- |
| `/auth/` | Public | Auth flows (login, signup, OTP). |
| `/public/` | Public | Data access for non-registered users. |
| `/my/` | **Protected** | Requires valid Bearer token. |
| `/private/` | **Protected** | Requires valid Bearer token. |
| `/admin/` | **Role-Based** | Requires token and admin role. |


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
