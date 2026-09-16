# 🔐 Environment Variables (`.env`)

Atom automatically loads environment variables from `.env` and system environment via `python-dotenv` at startup.

Any variable starting with `CONFIG_` or `config_` is loaded, type-cast, and bound to `app.state`, making it directly accessible across route handlers and lifespan tasks.

---

## ⚡ Dynamic `CONFIG_*` Discovery

Developers can add **any** custom variable to `.env` without modifying `config.py`. As long as the variable follows the `CONFIG_` (or `config_`) prefix pattern, Atom will:

1. Detect the variable at startup.
2. Normalize the key to lowercase snake_case (`config_<name>`).
3. Automatically infer and cast the value to the appropriate Python type.
4. Mount it onto `app.state` as `app.state.config_<name>`.

### Example `.env`

```dotenv
# String values
CONFIG_PAYMENT_GATEWAY_API_KEY="sk_live_123456789"
CONFIG_EXTERNAL_WEBHOOK_URL="https://hooks.example.com/events"

# Booleans (case-insensitive true/false, yes/no, on/off)
CONFIG_ENABLE_BETA_CHECKOUT=true
CONFIG_MAINTENANCE_BANNER_ENABLED=false

# Numbers (integers)
CONFIG_MAX_RETRY_ATTEMPTS=5
CONFIG_SYNC_INTERVAL_SEC=300

# JSON Arrays & Objects
CONFIG_WHITELISTED_IPS=["192.168.1.1", "10.0.0.1"]
CONFIG_TIER_LIMITS={"free": 100, "pro": 1000}
```

---

## 🚦 Accessing in Routes

In your route handlers, access custom configuration directly via `request.app.state`:

```python
# router/my_feature.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/checkout/status")
async def get_checkout_status(request: Request):
    app_state = request.app.state

    api_key = app_state.config_payment_gateway_api_key   # "sk_live_123456789" (str)
    is_beta = app_state.config_enable_beta_checkout      # True (bool)
    retries = app_state.config_max_retry_attempts        # 5 (int)
    ips = app_state.config_whitelisted_ips               # ("192.168.1.1", "10.0.0.1") (tuple)
    limits = app_state.config_tier_limits                # {"free": 100, "pro": 1000} (dict)

    return {
        "beta_active": is_beta,
        "max_retries": retries,
        "allowed_ips": ips,
    }
```

---

## 🔄 Overriding Core Configurations

If an environment variable matches a pre-existing configuration defined in `config.py`, it overrides the shipped default:

```dotenv
# Override shipped defaults in config.py
CONFIG_IS_DEBUG=true
CONFIG_IS_SIGNUP=false
CONFIG_POSTGRES_URL="postgresql://user:pass@localhost:5432/my_db"
CONFIG_REDIS_URL="redis://localhost:6379/0"
```

The loader respects the existing type definition in `config.py`:
- Booleans are validated strictly (`true`/`false`, `1`/`0`, `yes`/`no`, `on`/`off`).
- JSON strings are parsed into lists (converted to tuples) or dictionaries.
- Digits are converted to integers.

---

## 🗄️ Dynamic PostgreSQL Pools

Atom supports provisioning multiple named PostgreSQL pools dynamically using the `CONFIG_POSTGRES_URL_<NAME>` pattern:

```dotenv
CONFIG_POSTGRES_URL_READ="postgresql://user:pass@read-replica:5432/db"
CONFIG_POSTGRES_URL_ANALYTICS="postgresql://user:pass@analytics-db:5432/db"
```

These are automatically parsed into `app.state.config_postgres_url_dict`:

```python
{
    "read": "postgresql://user:pass@read-replica:5432/db",
    "analytics": "postgresql://user:pass@analytics-db:5432/db",
}
```

During startup, Atom provisions dedicated async connection pools for each, accessible as:

```python
app_state.client_postgres_dict["read"]
app_state.client_postgres_dict["analytics"]
```

See [postgres.md](postgres.md) for full details on multi-database routing.

---

## 🛠️ Type Casting Rules for Custom Variables

When adding a new `CONFIG_*` variable that is not in `config.py`, Atom applies the following type resolution rules:

| Value in `.env` | Parsed Python Type | Example |
|---|---|---|
| `true`, `false`, `yes`, `no`, `on`, `off` | `bool` | `CONFIG_FLAG=true` → `True` |
| Whole digits / negative digits | `int` | `CONFIG_PORT=8080` → `8080` |
| Valid JSON array `[...]` | `tuple` | `CONFIG_TAGS=["a", "b"]` → `('a', 'b')` |
| Valid JSON object `{...}` | `dict` | `CONFIG_META={"k": 1}` → `{'k': 1}` |
| Anything else | `str` | `CONFIG_API_KEY=xyz` → `"xyz"` |
