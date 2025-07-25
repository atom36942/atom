## About
- Open-source backend framework to speed up large-scale application development  
- Clean, modular architecture combining functional and procedural styles  
- Pure functions used to minimize side effects and improve testability  
- Built-in support for Postgres, Redis, S3, Kafka, and many other services  
- Quickly build production-ready APIs, background jobs, and integrations  
- Reduces boilerplate, so you don’t have to reinvent the wheel each time

## Tech Stack
atom uses a fixed set of proven core technologies, so you can focus on building your idea quickly without getting stuck in stack decisions.
- **Language**: Python
- **Framework**: FastAPI (for building async APIs)
- **Database**: PostgreSQL (primary relational database)
- **Caching**: Redis or Valkey (used for cache, rate limiting, task queues, etc.)
- **Queue**: RabbitMQ or Kafka (for background jobs and async processing)
- **Task Worker**: Celery (for background processing)
- **Monitoring**: Sentry/Prometheus (for error tracking and performance monitoring)

## Getting Started
To run atom, follow these three sections in order:
1. [Installation](#installation)
2. [Environment Variables](#environment-variables)
3. [Server Start](#server-start) or [Docker Start](#docker-start)

## Installation
Mac
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Windows
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables
Create a `.env` file in the root directory with at least the following keys.  
You can use local or remote URLs for Postgres and Redis.
- `config_postgres_url`: primary database (PostgreSQL) connection URL  
- `config_redis_url`: used for caching, rate limiting, background tasks, etc.  
- `config_key_root`: secret key to authenticate root-user APIs - /root/{api}  
- `config_key_jwt`: secret key used for signing and verifying JWT tokens
```env
config_postgres_url=postgresql://atom@127.0.0.1/postgres
config_redis_url=redis://localhost:6379
config_key_root=0bVJ9Jpb7s
config_key_jwt=2n91nIEaJpsqjFUz
```

## Server Start
```bash
python main.py                        # Run directly
uvicorn main:app --reload             # Run with auto-reload (dev)
```

## Docker Start
```bash
docker build -t atom .
docker run -p 8000:8000 atom
```

## Run Without Activating Virtualenv
```bash
git clone https://github.com/atom36942/atom.git            # Clone the repository
cd atom                                                    # Navigate into project directory
python3 -m venv venv                                       # Create a virtual environment
./venv/bin/pip install -r requirements.txt                 # Install requirements
./venv/bin/python main.py                                  # Run directly
./venv/bin/uvicorn main:app --reload                       # Start the server with reload
./venv/bin/pip install fastapi                             # Install package (ex FastAPI)
./venv/bin/pip install --upgrade fastapi                   # Upgrade package (ex FastAPI)
./venv/bin/pip freeze > requirements.txt                   # Freeze updated dependencies
```

## Testing
You can use the `test.sh` script to run a batch of API tests.
- It reads all curl commands from `curl.txt`
- Executes them one by one as a quick integration test
- To disable a specific curl command, prefix the curl command with `0` in `curl.txt`
```bash
./test.sh
```

## Repository Structure
Explanation of key files in the repo:
- `main.py` – FastAPI Server + APIs
- `router.py` – Sample router definitions for extending the APIs
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

## JWT Token Keys Encoding
To control which user fields are encoded in the JWT token, set `config_token_key_list` in `config.py`.  
Add `id`, `is_active`, and `api_access` always. Then add any other keys as needed.
```python
config_token_key_list=id,is_active,api_access,mobile,username
```
These keys will be included in the JWT and available in your FastAPI routes like:
```python
request.state.user.get("id")
request.state.user.get("is_active")
request.state.user.get("mobile")
```

## RabbitMQ

**Installation:**  
To run RabbitMQ locally:  
1. Install RabbitMQ using Homebrew or Docker  
2. Start RabbitMQ using `brew services` or Docker  
3. Access the UI at [http://localhost:15672](http://localhost:15672) (default: guest/guest) and use `amqp://guest:guest@localhost:5672/` as the connection URL 
 
**Configuration:**  
Add the following key to your `.env` file:  
```bash
config_rabbitmq_url=amqp://guest:guest@localhost:5672
```
**Publisher** (from `router.py`):  
- Hit the `/rabbitmq-publish` route to produce messages  
- Sends JSON payloads to `channel_1` using `function_publisher_rabbitmq`  
- Payload must contain a `"function"` key (e.g., `"function": "function_object_create_postgres"`)  
- Consumer dispatches functions dynamically based on the `function` key  
- You can use any other queue/channel by extending the producer logic  
- You can directly call `function_publisher_rabbitmq` in your own routes  

**Consumer** (from `consumer_rabbitmq.py`):  

**Run Rabbitmq Consumer:**
```bash
python consumer_rabbitmq.py                    # Run with activated virtualenv
./venv/bin/python consumer_rabbitmq.py         # Run without activating virtualenv
```
The consumer listens on `channel_1` and dispatches tasks based on the `"function"` key using `if-elif` logic.  
To extend, add more cases:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```

## Kafka
To run Kafka with SASL/PLAIN locally:
1. Install Zookeeper and Kafka using Homebrew  
2. Start Zookeeper using `brew services`  
3. Create a JAAS config file in your home directory with user credentials  
4. Update Kafka's `server.properties` to enable SASL/PLAIN authentication  
5. Export the JAAS config path using the `KAFKA_OPTS` environment variable  
6. Start the Kafka broker manually using the updated config file  

---

**Kafka Publish Example** (from `router.py`):

To **produce** messages to Kafka, hit the route `/kafka-publish`.  
It demonstrates publishing JSON data to `channel_1` using the internal `function_publisher_kafka`.

You can send **any payload** with a `function` key (e.g., `"function": "function_object_create_postgres"`),  
and the Kafka consumer will dynamically dispatch the corresponding function.

You can use **any channel/topic** while publishing. Extend the producer logic to route data accordingly.

---

**Kafka Consumer Example** (from `consumer_kafka.py`):

The Kafka consumer listens on `channel_1`, parses incoming messages, and dispatches them using `if-elif` logic based on the `function` key.

To add more functionality:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```

Extend this logic to handle new function calls as needed.

You can also use **Kafka Consumer Groups** to scale consumers horizontally.  
Each consumer in the same group gets a subset of the topic partitions, enabling parallel processing.

---

**Run Kafka Consumer:**
```bash
python consumer_kafka.py                    # Run with activated virtualenv
./venv/bin/python consumer_kafka.py         # Run without activating virtualenv
```