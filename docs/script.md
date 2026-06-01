# Scripts and Background Workers

The `core/script/` directory is dedicated to standalone, long-running processes, CRON jobs, and message queue consumers. These scripts are designed to run independently from the main FastAPI server, typically deployed as separate background containers or daemon processes.

## Types of Scripts

### 1. Consumers (`consumer_*.py`)
These are message queue listeners designed to process events asynchronously off a queue (e.g., RabbitMQ, Celery, Redis, Kafka).
- **Use Case:** When an API endpoint publishes a message to a queue (like a request to generate a large PDF), a consumer script listens to that specific queue, picks up the message, and processes it.
- **Example:** `consumer_postgres_create.py` listens for events demanding a database insertion and handles them sequentially to prevent database locking or overload.

### 2. Cron Jobs (`cron_*.py`)
These are scheduled scripts designed to run periodically (e.g., hourly, daily) or loop indefinitely with large sleep intervals.
- **Use Case:** Routine maintenance tasks like pruning old data, generating nightly analytical reports, or syncing external API data.
- **Example:** `cron_postgres_cleaner.py` connects to the database, queries the `config_table` for `retention_day` settings, and automatically drops old logs and OTPs to keep the database lean.

### 3. Dedicated Workers (`worker_*.py`)
These are continuous, infinite-looping daemon workers that process stateful items directly from the database using a locking mechanism (`SELECT ... FOR UPDATE SKIP LOCKED`).
- **Use Case:** Complex AI processing, bulk email sending, or heavy data processing where you have a specific queue table or column in your database representing "jobs".
- **Example:** `worker_resume_parser.py` constantly polls the `candidate` table for newly uploaded resumes. When it finds one, it locks the row, downloads the file, calls the Gemini AI API to parse the candidate's skills and experience, and updates the row back into PostgreSQL.

## How to Expand (Creating a new script)

1. **Create the file**: Add a new Python file to `core/script/` following the naming conventions above (e.g., `worker_invoice_generator.py`).
2. **Structure**: 
   - Define your imports at the top (usually pulling `config_*` variables from `core.config`).
   - Wrap your logic inside an `async def execute():` block.
   - Setup your own connection pools (e.g., `asyncpg.create_pool`) since these scripts run entirely isolated from the FastAPI lifespan.
   - Create a `while True:` loop if it's a daemon, or a single procedural run if it's a cron.
   - Initialize execution at the bottom using `asyncio.run(execute())`.

```python
# core/script/worker_example.py
import asyncio
from core.config import config_postgres_url

async def execute():
    # Setup your connections
    print("Starting Worker...")
    while True:
        # Perform your logic
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(execute())
```

## How to Execute

To run any script locally, execute it as a Python module from the project root:

```bash
# Run a background worker
python -m core.script.worker_resume_parser

# Run a cron job once
python -m core.script.cron_postgres_cleaner
```

If you are using Docker, you would typically run the main web app in one container, and launch your workers in separate, dedicated containers using the same image but overriding the startup command.
