# Third-Party Integrations

Atom establishes persistent async connections to various external third-party services and databases globally. These clients are initialized during the FastAPI lifespan (`func_lifespan` in `core/app.py`) and are injected into the application state (`app.state`).

This design prevents connection overhead on every API request and allows you to access these clients natively inside your routing logic.

## 1. Available Clients

Depending on the environment variables provided in `core/config.py` (e.g., keys, URLs, connections strings), the following clients become available on `request.app.state`:

### Databases & Caching
- **`client_postgres_pool` / `client_postgres_pool_read`**: `asyncpg` pools for raw, highly concurrent PostgreSQL querying.
- **`client_redis`**: For fast, in-memory distributed caching, rate-limiting, and state storage.
- **`client_mongodb`**: Using `motor` for asynchronous MongoDB document storage.
- **`client_mssql`**: Using `aioodbc` for legacy SQL Server data retrieval (e.g., CargoWise).

### Cloud Storage & Email (AWS / Azure)
- **`client_s3` / `client_s3_resource`**: Asynchronous `aiobotocore` clients for interacting with AWS S3 buckets.
- **`client_ses`**: Boto3 client for sending transactional emails via AWS Simple Email Service.
- **`client_sns`**: Boto3 client for sending SMS via AWS Simple Notification Service.
- **`client_azure_blob`**: `BlobServiceClient` for Microsoft Azure object storage.

### Artificial Intelligence
- **`client_openai`**: Standard OpenAI Python client for LLM completions.
- **`client_gemini`**: Google GenAI client for fast multimodal analysis (e.g., parsing resumes).

### Telemetry & Analytics
- **`client_posthog`**: PostHog client for backend event capturing and product analytics.
- **Sentry**: Initialized natively in `app.py` for error and performance tracking.

### File Systems & Queues
- **`client_sftp`**: `asyncssh` client for secure FTP operations.
- **`client_celery_producer`, `client_kafka_producer`, `client_rabbitmq_producer`**: Used for publishing to respective event streaming layers.

---

## 2. Using Integrations in Routers

To use an integration inside a FastAPI route, pull it out of `request.app.state`. **Do not** initialize new AWS/AI clients directly within the endpoint.

### Example: Uploading a File to AWS S3

```python
# core/router/private.py
from fastapi import APIRouter, Request, UploadFile

router = APIRouter()

@router.post("/private/upload")
async def upload_document(*, request: Request, file: UploadFile):
    app_state = request.app.state
    
    # Access the global async S3 client
    s3_client = app_state.client_s3
    
    if s3_client:
        # Read file contents and stream to S3
        file_bytes = await file.read()
        await s3_client.put_object(
            Bucket=app_state.config_aws_s3_bucket,
            Key=f"uploads/{file.filename}",
            Body=file_bytes
        )
        return {"status": 1, "message": "Uploaded successfully"}
    
    return {"status": 0, "error": "S3 Client not configured"}
```

### Example: Calling the OpenAI API

```python
@router.post("/private/summarize")
async def ai_summarize(*, request: Request, payload: dict):
    app_state = request.app.state
    openai_client = app_state.client_openai
    
    if openai_client:
        # Depending on configuration, this might be a synchronous call running in a threadpool
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Summarize this: {payload['text']}"}]
        )
        return {"status": 1, "summary": response.choices[0].message.content}
```

---

## 3. Disconnection

During application shutdown (FastAPI lifespan tear down), Atom automatically ensures all initialized async clients (e.g., `.aclose()`, `.wait_closed()`) are safely disconnected to prevent memory leaks and zombie connections on the server.
