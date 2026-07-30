# Development Guidelines

## How to add a new API

Keep the router small: accept and validate the request, call a reusable
`func_*` helper, and return the standard response format.

### 1. Create a router file

Create a Python file inside `router/`, for example:

```text
router/product.py
```

Router files are discovered automatically. Every router file must define a
module-level `router = APIRouter()`.

### 2. Import the required packages

Only import packages used by the router:

```python
# router/product.py
from fastapi import APIRouter, Request

router = APIRouter()
```

Put imports needed only by the core logic in `function_extend.py`, not in the
router.

### 3. Add the route and follow existing naming

Check the existing files in `router/` before choosing the path, HTTP method,
and function name.

- Route path: `/<tier>/<action-kebab-case>`
- Function name: `func_api_<tier>_<action_snake_case>`
- Function signature: `async def func_api_...(*, request: Request)`
- Use `GET` for reads and `POST` for operations that create or change data.

Example:

```python
# router/product.py
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/my/product-create")
async def func_api_my_product_create(*, request: Request):
    app_state = request.app.state
```

The common route tiers are `index`, `auth`, `my`, `public`, `private`, and
`admin`. Use the tier that matches the endpoint's access level.

### 4. Accept parameters with `func_request_param_read`

Do not read `request.query_params`, `request.json()`, or `request.form()`
directly. Use `func_request_param_read` so parameters are extracted,
type-cast, validated, and given defaults consistently.

```python
oq = await app_state.func_request_param_read(
    request=request,
    mode="query",
    strict=0,
    param_specs=[
        {"name": "category", "type": "str", "required": 1},
        {"name": "active", "type": "bool", "default": 1},
    ],
)

ob = await app_state.func_request_param_read(
    request=request,
    mode="body",
    strict=1,
    param_specs=[
        {"name": "name", "type": "str", "required": 1},
        {"name": "quantity", "type": "int", "default": 1},
        {"name": "tags", "type": "list:str", "default": []},
    ],
)
```

Use:

- `mode="query"` for URL query parameters
- `mode="body"` for a JSON object
- `mode="form"` for multipart form data and file uploads
- `mode="header"` for headers
- `strict=1` to return only declared parameters
- `strict=0` to preserve undeclared parameters too

Each parameter specification requires `name` and `type`. It can also use
`required`, `default`, and `allowed`. By convention, name the results `oq`
for query, `ob` for body, and `of` for form parameters.

### 5. Move core logic to `function_extend.py`

Business logic, database work, and reusable transformations belong in a
`func_*` helper in `function_extend.py`. Use keyword-only arguments and pass
dependencies explicitly.

```python
# function_extend.py
async def func_product_create(
    *,
    client_postgres,
    name: str,
    quantity: int,
    category: str,
    active: int,
    tags: list,
    user_id: int,
):
    if not client_postgres:
        raise Exception("postgres client not initialized")

    async with client_postgres.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO product
                (name, quantity, category, active, tags, created_by_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            name,
            quantity,
            category,
            active,
            tags,
            user_id,
        )
    return dict(row)
```

Functions from `function_extend.py` are loaded onto the application state.
Access them in a route by first assigning:

```python
app_state = request.app.state
```

Then call the helper through `app_state`:

```python
product = await app_state.func_product_create(
    client_postgres=app_state.client_postgres,
    name=ob["name"],
    quantity=ob["quantity"],
    category=oq["category"],
    active=oq["active"],
    tags=ob["tags"],
    user_id=request.state.user["id"],
)
```

### 6. Return the standard response format

Every JSON response must contain `status` and `message`:

```python
return {"status": 1, "message": product}
```

- `status: 1` means success.
- `message` contains the response payload.
- On failure, raise an exception with a clear message. The middleware converts
  it to `{"status": 0, "message": "..."}`.

Do not manually return a success status for an error:

```python
if not app_state.client_postgres:
    raise Exception("postgres client not initialized")
```

### Complete example

```python
# router/product.py
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/my/product-create")
async def func_api_my_product_create(*, request: Request):
    app_state = request.app.state

    oq = await app_state.func_request_param_read(
        request=request,
        mode="query",
        strict=1,
        param_specs=[
            {"name": "category", "type": "str", "required": 1},
            {"name": "active", "type": "bool", "default": 1},
        ],
    )
    ob = await app_state.func_request_param_read(
        request=request,
        mode="body",
        strict=1,
        param_specs=[
            {"name": "name", "type": "str", "required": 1},
            {"name": "quantity", "type": "int", "default": 1},
            {"name": "tags", "type": "list:str", "default": []},
        ],
    )

    product = await app_state.func_product_create(
        client_postgres=app_state.client_postgres,
        name=ob["name"],
        quantity=ob["quantity"],
        category=oq["category"],
        active=oq["active"],
        tags=ob["tags"],
        user_id=request.state.user["id"],
    )
    return {"status": 1, "message": product}
```

If the API needs authentication, roles, rate limiting, or caching, also add
its path to `config_api` in `config_extend.py`. See [router.md](router.md) and
[config.md](config.md) for the available options.
