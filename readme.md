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

## Installation
To run atom, follow these three sections in order:
### Setup repo (mac)
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
### Setup env variables
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
### Server Start
```bash
python main.py                        # Run directly
uvicorn main:app --reload             # Run with auto-reload (dev)
```

## Docker Start
```bash
docker build -t atom .
docker run -p 8000:8000 atom
```

## Installation Without Activating Virtualenv
```bash
git clone https://github.com/atom36942/atom.git            # Clone the repository
cd atom                                                    # Navigate into project directory
python3 -m venv venv                                       # Create a virtual environment
./venv/bin/pip install -r requirements.txt                 # Install requirements
touch .env                                                 # Create .env file for environment variables
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

## Kafka
### Installation
To run Kafka with SASL/PLAIN (locally or remotely):
1. Install Zookeeper and Kafka using Homebrew, or use a remote Kafka provider like Confluent Cloud, Aiven, or Redpanda  
2. Start Zookeeper locally using `brew services`, or skip this step if using a remote provider  
3. For local Kafka, create a JAAS config file in your home directory with user credentials  
4. Update Kafka's `server.properties` to enable SASL/PLAIN authentication (only for local setup)  
5. Export the JAAS config path using the `KAFKA_OPTS` environment variable (only for local setup)  
6. Start the Kafka broker manually using the updated config file (only for local setup)  
7. For remote Kafka, obtain the bootstrap servers and SASL credentials (username, password, mechanism) from the provider  
8. Use the following connection config in your app:
### Configuration
- Add the following key to your `.env` file
```bash
config_kafka_url=value
config_kafka_username=value
config_kafka_password=value
```
### Publisher
- check `/kafka-publish` in `router.py` file for sample useage
- Hit the `/kafka-publish` route to produce messages  
- Sends JSON payloads to `channel_1` using `function_publisher_kafka`  
- Payload must contain a `"function"` key (e.g., `"function": "function_object_create_postgres"`)  
- Consumer dispatches functions dynamically based on the `function` key  
- You can use any other queue/channel by extending the producer logic  
- You can directly call `function_publisher_kafka` in your own routes  
### Consumer
- Check `consumer_kafka.py` file
- How to run `consumer_kafka.py` file
```bash
python consumer_kafka.py                    # Run with activated virtualenv
./venv/bin/python consumer_kafka.py         # Run without activating virtualenv
```
- The consumer listens on `channel_1` and dispatches tasks based on the `"function"` key using `if-elif` logic
- To extend, add more cases:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```

## RabbitMQ
### Installation
To run RabbitMQ (locally or remotely):
1. Install RabbitMQ using Homebrew (`brew install rabbitmq`) or Docker, or use a managed provider like CloudAMQP or AWS MQ  
2. Start RabbitMQ locally using `brew services start rabbitmq` or Docker with:  
   `docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management`  
3. Access the management UI at [http://localhost:15672](http://localhost:15672) (default login: guest/guest)  
4. Use the local connection URL: `amqp://guest:guest@localhost:5672/`  
5. For remote RabbitMQ, get the connection URL from your provider, typically in this format:  
   `amqp://<username>:<password>@<host>:<port>/`  
6. Use this URL in your app config or `.env` file for secure access
### Configuration
- Add the following key to your `.env` file
```bash
config_rabbitmq_url=amqp://guest:guest@localhost:5672
```
### Publisher
- check `/rabbitmq-publish` in `router.py` file for sample useage
- Hit the `/rabbitmq-publish` route to produce messages  
- Sends JSON payloads to `channel_1` using `function_publisher_rabbitmq`  
- Payload must contain a `"function"` key (e.g., `"function": "function_object_create_postgres"`)  
- Consumer dispatches functions dynamically based on the `function` key  
- You can use any other queue/channel by extending the producer logic  
- You can directly call `function_publisher_rabbitmq` in your own routes. 
### Consumer
- Check `consumer_rabbitmq.py` file
- How to run `consumer_rabbitmq.py` file
```bash
python consumer_rabbitmq.py                    # Run with activated virtualenv
./venv/bin/python consumer_rabbitmq.py         # Run without activating virtualenv
```
- The consumer listens on `channel_1` and dispatches tasks based on the `"function"` key using `if-elif` logic.
- To extend, add more cases:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```

## Redis Pub/Sub
### Installation
To run Redis (locally or remotely):
1. Install Redis using Homebrew (`brew install redis`) or Docker, or use a managed provider like Redis Cloud, Upstash, or AWS ElastiCache  
2. Start Redis locally using `brew services start redis` or Docker:  
   `docker run -p 6379:6379 redis`  
3. Local Redis runs at `redis://localhost:6379` with no authentication by default  
4. For remote Redis, obtain the connection URL from the provider, typically in the format:  
   `redis://:<password>@<host>:<port>`  
5. Use the URL in your app config or `.env` file to connect securely
### Configuration
- Add the following key to your `.env` file
```bash
config_redis_url=redis://:<password>@<host>:<port>
```
### Publisher
- check `/redis-publish` in `router.py` file for sample useage
- Hit the `/redis-publish` route to produce messages  
- Sends JSON payloads to `channel_1` using `function_publisher_rabbitmq`  
- Payload must contain a `"function"` key (e.g., `"function": "function_object_create_postgres"`)  
- Consumer dispatches functions dynamically based on the `function` key  
- You can use any other queue/channel by extending the producer logic  
- You can directly call `function_publisher_redis` in your own routes. 
### Consumer
- Check `consumer_redis.py` file
- How to run `consumer_redis.py` file
```bash
python consumer_redis.py                    # Run with activated virtualenv
./venv/bin/python consumer_redis.py      # Run without activating virtualenv
```
- The consumer listens on `channel_1` and dispatches tasks based on the `"function"` key using `if-elif` logic.
- To extend, add more cases:
```python
if data["function"] == "your_custom_function":
    await your_custom_function(...)
```
