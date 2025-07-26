<details>
<summary>About</summary>

- Open-source backend framework to speed up large-scale application development  
- Modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Built-in support for Postgres, Redis, S3, Kafka, and many other services  
- Production-ready to build APIs, background jobs, and integrations quickly  
- Minimal boilerplate so you don’t have to reinvent the wheel each time  
</details>




<details>
<summary>Tech Stack</summary>

Atom uses a fixed set of proven core technologies, so you can focus on building your idea quickly without getting stuck in stack decisions.
- Language: Python  
- Framework: FastAPI (for building async APIs)  
- Database: PostgreSQL (primary relational database)  
- Caching: Redis or Valkey (used for cache, rate limiting, task queues, etc.)  
- Queue: RabbitMQ or Kafka (for background jobs and async processing)  
- Task Worker: Celery (for background processing)  
- Monitoring: Sentry/Prometheus (for error tracking and performance monitoring)  
</details>




<details>
<summary>Repository Structure</summary>

Explanation of key files in the repo:  
- `main.py` – FastAPI Server + APIs  
- `router.py` – Sample router+function definitions for extending the APIs  
- `function.py` – Core business logic or utility functions  
- `config.py` – Loads config/env variables used across the app  
- `requirements.txt` – Python dependencies  
- `readme.md` – Project documentation  
- `Dockerfile` – Build and run the project inside Docker  
- `curl.txt` – List of curl requests used for testing  
- `test.sh` – Shell script to execute curl.txt tests  
- `consumer_redis.py` – Redis consumer for pub/sub or queue  
- `consumer_rabbitmq.py` – RabbitMQ consumer  
- `consumer_kafka.py` – Kafka consumer  
- `consumer_celery.py` – Celery worker  
- `.gitignore` – Files/directories to ignore in git
</details>



<details>
<summary>Installation</summary>

# Setup repo
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
# Setup env
- Create a `.env` file in the root directory with min 4 keys 
- You can use local or remote URLs for Postgres and Redis
- `config_postgres_url`: primary database (PostgreSQL) connection URL  
- `config_redis_url`: used for caching, rate limiting, background tasks, etc.  
- `config_key_root`: secret key to authenticate root-user APIs - /root/{api}  
- `config_key_jwt`: secret key used for signing and verifying JWT tokens
```env
config_postgres_url=postgresql://username:password@localhost:5432/dbname
config_redis_url=redis://:password@your_host:6379
config_key_root=any random secret key (2n91nIEaJpsqjFUz)
config_key_jwt=any random secret key (2n91nIEaJpsqjFUz)
```
# Server Start
```bash
python main.py                  # Run directly
uvicorn main:app --reload       # Run with auto-reload (dev)
```
</details>



<details>
<summary>Installation Docker</summary>

```bash
git clone https://github.com/atom36942/atom.git
cd atom
docker build -t atom .
docker run -p 8000:8000 atom
```
</details>



<details>
<summary>Installation Without Activating Virtualenv</summary>

```bash
git clone https://github.com/atom36942/atom.git       # Clone the repository
cd atom                                               # Navigate into project directory
python3 -m venv venv                                  # Create a virtual environment
./venv/bin/pip install -r requirements.txt            # Install requirements
touch .env                                            # Create .env file for environment variables
./venv/bin/python main.py                             # Run directly
./venv/bin/uvicorn main:app --reload                  # Start the server with reload
./venv/bin/pip install fastapi                        # Install package (ex FastAPI)
./venv/bin/pip install --upgrade fastapi              # Upgrade package (ex FastAPI)
./venv/bin/pip freeze > requirements.txt              # Freeze updated dependencies
```
</details>



<details>
<summary>API collection</summary>

- All API endpoints are listed in `curl.txt` as ready-to-run `curl` commands  
- You can copy-paste any of these directly into Postman (use "Raw Text" option)  
- `test.sh` executes all active curl commands automatically  
- Any line starting with `0 curl` is skipped during automated testing with `test.sh`
</details>



<details>
<summary>API Testing</summary>

- You can use the `test.sh` script to run a batch of API tests.
- It reads all curl commands from `curl.txt`
- Executes them one by one as a quick integration test
- To disable a specific curl command, prefix the curl command with `0` in `curl.txt`
- Testing Summary (URL, status code, execution time) will be saved to `curl.csv`
```bash
./test.sh
```
</details>



<details>
<summary>Extend Routes</summary>

- You can easily add new API routes in Atom
- Add any file starting with `router_` in the root folder  
- Or create a `router/` folder and add any `.py` file inside it  
- All router files are auto-loaded at startup  
- You can load env and write any logic in your own routers  
- All routes pass through Atom middleware automatically  
- Check other sections for ready-to-use logic like auth, ratelimiting, user active checks, caching, admin APIs, background APIs, etc.  
- See `router.py` for basic usage  
```python
from function import *
from fastapi import Request
from fastapi import APIRouter
router=APIRouter()
@router.get("/test")
async def route_test():
    return {"status": 1, "message": "welcome to test routes"}
```
</details>



<details>
<summary>Extend Config</summary>

- Add secret keys in `.env` and load with load_dotenv package
- Add static keys directly in `config.py` and import and use as needed
</details>



<details>
<summary>Client Initialization</summary>

- All service clients are initialized once during app startup using the FastAPI lifespan event in `main.py`
- You can access these clients in your custom routes via `request.app.state.{client_name}`
- You can check `router.py` for sample usage of the clients
- Available clients (see latest list in `main.py`):
```python
request.app.state.client_postgres  
request.app.state.client_postgres_asyncpg  
request.app.state.client_postgres_asyncpg_pool  
request.app.state.client_postgres_read  
request.app.state.client_redis  
request.app.state.client_mongodb  
request.app.state.client_s3  
request.app.state.client_s3_resource  
request.app.state.client_sns  
request.app.state.client_ses  
request.app.state.client_openai  
request.app.state.client_kafka_producer  
request.app.state.client_rabbitmq  
request.app.state.client_rabbitmq_channel  
request.app.state.client_celery_producer  
request.app.state.client_posthog  
```
</details>



<details>
<summary>JWT Token Keys Encoding</summary>

- Set `config_token_key_list` in `config.py` to define which user fields go into the JWT token. 
- Always include: `id`, `is_active`, and `api_access`
- Add any other fields as needed, like `mobile`, `username`, etc.
- You can access encoded user keys in your FastAPI routes like:
```python
config_token_key_list=id,is_active,api_access,mobile,username
``` 
```python
request.state.user.get("id")
request.state.user.get("is_active")
request.state.user.get("mobile")
```
</details>



<details>
<summary>Admin APIs</summary>

- Add `/admin` in the route path to mark it as an admin API  
- Check the `curl.txt` file for examples under the admin section  
- Assign a unique API ID in the `config_api` variable in `config.py` (check existing samples there)  
- Only users whose `api_access` column in the database contains that API ID will be allowed to access it  
- Example to give user_id=1 access to admin APIs with IDs 1,2,3
```sql
update users set api_access='1,2,3' where id=1
```  
</details>




<details>
<summary>PostHog Events</summary>

- You can send events to PostHog for analytics or tracking user behavior.
- Refer sample api `/posthog` in `router.py` for sample usage.
- Add the following keys to your `.env` file:
```bash
config_posthog_project_host=value
config_posthog_project_key=value
```
</details>



<details>
<summary>Kafka</summary>

- Start Kafka server locally or remotely with SASL/PLAIN 
- Add the following key to your `.env` file
```bash
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value
```
- check `/kafka-producer` in `router.py` file for sample useage
- You can use any other function/channel by extending the producer logic 
- You can directly call `function_producer_kafka` in your own routes 
- Check `consumer_kafka.py` file for consumer logic
- How to run `consumer_kafka.py` file
```bash
python consumer_kafka.py                # Run with activated virtualenv
./venv/bin/python consumer_kafka.py     # Run without activating virtualenv
```
- The consumer dispatches tasks based on the `"function"` key using `if-elif` logic
- To extend, add more cases:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```
</details>



<details>
<summary>RabbitMQ</summary>

- Start RabbitMQ server locally or remotely
- Add the following key to your `.env` file
```bash
config_rabbitmq_url=amqp://guest:guest@localhost:5672
```
- check `/rabbitmq-producer` in `router.py` file for sample useage
- You can use any other function/channel by extending the producer logic 
- You can directly call `function_producer_rabbitmq` in your own routes 
- Check `consumer_rabbitmq.py` file for consumer logic
- How to run `consumer_rabbitmq.py` file
```bash
python consumer_rabbitmq.py                # Run with activated virtualenv
./venv/bin/python consumer_rabbitmq.py     # Run without activating virtualenv
```
- The consumer dispatches tasks based on the `"function"` key using `if-elif` logic
- To extend, add more cases:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```
</details>



<details>
<summary>Redis Pub/Sub</summary>

- Start Redis server locally or remotely
- Add the following key to your `.env` file
```bash
config_redis_url=redis://:<password>@<host>:<port>
```
- check `/redis-producer` in `router.py` file for sample useage
- You can use any other function/channel by extending the producer logic 
- You can directly call `function_producer_redis` in your own routes 
- Check `consumer_redis.py` file for consumer logic
- How to run `consumer_redis.py` file
```bash
python consumer_redis.py                # Run with activated virtualenv
./venv/bin/python consumer_redis.py     # Run without activating virtualenv
```
- The consumer dispatches tasks based on the `"function"` key using `if-elif` logic
- To extend, add more cases:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```
</details>



<details>
<summary>Celery</summary>

- Start Redis server locally or remotely
- Add the following key to your `.env` file
```bash
config_redis_url=redis://:<password>@<host>:<port>
```
- check `/celery-producer` in `router.py` file for sample useage
- You can use any other function by extending the producer logic 
- You can directly call `function_producer_celery` in your own routes 
- Check `consumer_celery.py` file for consumer logic
- How to run `consumer_celery.py` file
```bash
celery -A consumer_celery worker --loglevel=info                # Run with activated virtualenv
 ./venv/bin/celery -A consumer_celery worker --loglevel=info    # Run without activating virtualenv
```
- The consumer dispatches tasks based on the function name passed in the producer
- To extend, add more cases, you can write more function task logic.
</details>


