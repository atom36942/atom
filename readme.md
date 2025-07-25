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
### Setup repo on your local(mac)
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
### Setup Environment Variables
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

### Docker Start
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

## RabbitMQ
### Installation
To run RabbitMQ locally:  
1. Install RabbitMQ using Homebrew or Docker  
2. Start RabbitMQ using `brew services` or Docker  
3. Access the UI at [http://localhost:15672](http://localhost:15672) (default: guest/guest) and use `amqp://guest:guest@localhost:5672/` as the connection URL.
### Configuration
- Add the following key to your `.env` file
- You can use remote connection also
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

## Kafka
### Installation
To run Kafka with SASL/PLAIN locally:
1. Install Zookeeper and Kafka using Homebrew  
2. Start Zookeeper using `brew services`  
3. Create a JAAS config file in your home directory with user credentials  
4. Update Kafka's `server.properties` to enable SASL/PLAIN authentication  
5. Export the JAAS config path using the `KAFKA_OPTS` environment variable  
6. Start the Kafka broker manually using the updated config file  
### Configuration
- Add the following key to your `.env` file
- You can use remote connection also
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


