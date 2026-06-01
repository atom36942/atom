# API Development & Configuration

Atom uses FastAPI for routing, but heavily augments it with a robust, centralized configuration layer (`config_api`) and a global middleware that automatically handles security, caching, and rate-limiting.

## 1. Creating New API Endpoints

All endpoints are organized inside the `core/router/` directory. 

Atom's `app.py` automatically scans this directory and mounts any `APIRouter` instances it finds based on a pre-defined order.

To add a new set of endpoints, simply create a new Python file in `core/router/` (or use an existing one) and define your FastAPI routes:

```python
# core/router/public.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/public/items")
async def func_api_public_items(*, request: Request):
    app_state = request.app.state
    # Your logic here, accessing centralized clients via app_state
    return {"status": 1, "data": []}
```

> **Note:** Thin routers are preferred. Heavy business logic should be placed in `core/function.py` and called from the router.

## 2. Configuring API Behaviors (`config_api`)

Instead of cluttering your API endpoint functions with repetitive authentication checks, caching decorators, and rate limiters, Atom abstracts all of this into `config_api` located in `core/config.py`.

The global middleware intercepts all requests, looks up the path in `config_api`, and enforces the rules *before* the request ever hits your router function.

### Example Configuration

```python
# core/config.py
config_api = {
    # 1. Role-Based Access Control (RBAC)
    "/admin/object-delete": {
        "id": 5, 
        "user_role_check": ["realtime", [1]],  # Only role ID 1 (Admin) allowed. Checked live against the DB.
        "user_active_check": ["realtime"],     # Ensure user is not deactivated
        "user_deleted_check": ["realtime"]     # Ensure user is not deleted
    },
    
    # 2. Response Caching
    "/public/object-read": {
        "id": 14, 
        "api_cache_sec": ["inmemory", 100]     # Cache the response for 100 seconds in memory
    },
    
    # 3. Rate Limiting
    "/public/data-export": {
        "id": 19, 
        "api_ratelimiting_times_sec": ["inmemory", 10, 60] # Max 10 requests per 60 seconds
    },
}
```

### Supported Configuration Capabilities

When mapping a route path in `config_api`, you can define any combination of the following constraints. Atom's middleware evaluates these automatically.

#### 1. Role-Based Access Control (`user_role_check`)
Restricts endpoint access to specific user roles (defined by integers, e.g., Admin = 1).
- **Syntax:** `[backend, [allowed_roles]]`
- **Example:** `"user_role_check": ["realtime", [1, 2]]` (Allows roles 1 and 2, checked live against the database).

#### 2. Account Status Checks (`user_active_check` & `user_deleted_check`)
Prevents users from accessing an endpoint if their account has been deactivated (banned/suspended) or softly deleted.
- **Syntax:** `[backend]`
- **Example:** `"user_active_check": ["realtime"]` (Verifies the user is currently active in the database before proceeding).

#### 3. Response Caching (`api_cache_sec`)
Caches the successful JSON response based on the endpoint path, the user ID (if authenticated), and the exact query parameters provided. Subsequent identical requests bypass the database and application logic entirely.
- **Syntax:** `[backend, seconds]`
- **Example:** `"api_cache_sec": ["redis", 300]` (Caches the output globally in Redis for 5 minutes).

#### 4. Rate Limiting (`api_ratelimiting_times_sec`)
Enforces strict traffic limits. It limits requests per user ID (for authenticated endpoints) or per IP address (for public endpoints). If a user exceeds the threshold, the middleware immediately rejects the request with an HTTP 429 Too Many Requests.
- **Syntax:** `[backend, requests, seconds]`
- **Example:** `"api_ratelimiting_times_sec": ["inmemory", 10, 60]` (Allows a maximum of 10 requests per 60-second sliding window).

### Storage Backend Modes

When configuring rules like `user_role_check`, `api_cache_sec`, or `api_ratelimiting_times_sec`, you must specify a backend mode. Atom supports several backends depending on the level of speed versus persistence required:

- **`token`**: The fastest user-check method. It relies entirely on the cryptographically signed JWT token payload. It doesn't query a database, making it extremely fast, but it means role changes or deactivations won't reflect until the token expires or is refreshed.
- **`inmemory`**: Uses the local Python server's memory. It is blazingly fast but ephemeral. Best used for localized rate-limiting or caching short-lived data where sharing state across multiple server instances (workers) is not necessary.
- **`redis`**: Uses a centralized Redis instance. Perfect for distributed caching and rate-limiting across multiple FastAPI workers/containers.
- **`realtime`**: Performs a live database lookup against PostgreSQL. This ensures absolute consistency (e.g., if an admin is demoted, their access drops instantly), but it adds a database hit to the request. Best reserved for highly sensitive operations (e.g., `/admin/object-delete`).

### Background Task Execution

Atom has built-in support for detaching long-running requests into background tasks. 
If an endpoint supports it, a client can simply append `?is_background=1` to the URL. The middleware will immediately return a `status: 1` accepted response and push the actual execution of the API function to a background worker queue, completely bypassing the synchronous wait time.
