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
git clone https://github.com/atom36942/atom.git                  # Clone the repository
cd atom                                                          # Navigate into project directory
python3 -m venv venv                                             # Create a virtual environment
./venv/bin/pip install -r requirements.txt                       # Install requirements
./venv/bin/python main.py                                        # Run directly
./venv/bin/uvicorn main:app --reload                             # Start the server with reload
./venv/bin/pip install fastapi                                   # Install package (ex FastAPI)
./venv/bin/pip install --upgrade fastapi                         # Upgrade package (ex FastAPI)
./venv/bin/pip freeze > requirements.txt                         # Freeze updated dependencies
```

## Testing
You can use the `test.sh` script to run a batch of API tests.
- It reads all curl commands from `curl.txt`
- Executes them one by one as a quick integration test
- To disable a specific curl command, prefix the curl command with `0` in `curl.txt`
```bash
./test.sh
```

## JWT Token Encoding
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

## Kafka Setup
To run Kafka with SASL/PLAIN locally:
1. Install Zookeeper and Kafka using Homebrew.
2. Start Zookeeper using `brew services`.
3. Create a JAAS config file in your home directory with user credentials.
4. Update Kafka's `server.properties` to enable SASL/PLAIN authentication.
5. Export the JAAS config path using the `KAFKA_OPTS` environment variable.
6. Start the Kafka broker manually using the updated config file.
