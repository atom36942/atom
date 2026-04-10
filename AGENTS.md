### AGENTS Rules

### Repository Map
| Path | Service | Responsibility |
| :--- | :--- | :--- |
| `static/` | **Assets** | Frontend files and documentation pages. |
| `tmp/` | **Runtime** | Workspace for temporary runtime operations. |
| `function.py` | **Core** | Primary functional logic and database drivers. |
| `config.py` | **Settings** | Global configuration and schema definitions. |
| `app.py` | **Initialization** | Lifespan, Middleware, App Setup. |
| `main.py` | **Entry** | Server execution and runtime orchestration. |
| `router/` | **API** | Definition of all endpoints and role assignments. |
| `consumer.py` | **Workers** | Background task processing (Celery, Kafka, etc.). |
| `script/` | **Isolated** | Independent scripts with standalone Docker/Main logic. |


### Core Development Principles
| Section | Standard | Execution Logic |
| :--- | :--- | :--- |
| **Logic** | Pure Functional | `function.py` for stateless logic; no external dependencies; SOLID compliant. |
| **Safety** | Error Isolation | No `or` logic in checks; individual `if` blocks for specific exceptions. No clubbed error messages (e.g., "A or B missing"). |
| **IO** | Path Security | `tmp/` for temporary files only. No exceptions. |
| **Defaults** | INTERNAL HANDLING| No parameter defaults in signatures; use `None` and handle at function start. |
| **Philosophy** | **Explicitness** | Explicitness > Implicitness. 1:1 mapping between parameters and global state. |

### Naming Conventions
| Category | Variable Prefix | Behavior |
| :--- | :--- | :--- |
| **Boolean** | `is_[name]` | Strictly `int` (1/0). NEVER use Python `True`/`False`. |
| **Config** | `config_` | Global settings in `config.py` and matching function parameters. |
| **Functions** | `func_` | Standard prefix for all functional logic. |
| **Clients** | `client_` | Persistent singletons and matching function parameters (e.g. `client_postgres_pool`). |
| **Cache** | `cache_` | Dictionary-based local or distributed state maps. |
| **Explicit** | N/A | Variable names MUST include the service/feature name (e.g., `config_postgres_batch_limit`). |


### Development Workflow
| Stage | File | Action |
| :--- | :--- | :--- |
| **1. Define** | `router/` | Add route with path-based prefix code. |
| **2. Logic** | `function.py` | Create pure logic (use local imports). |
| **3. Config** | `config.py` | Add `config_` variables and table schemas. |
| **4. Setup** | `app.py` | Define Lifespan, Middleware, and app instance. |
| **5. Run** | `main.py` | Start uvicorn server. |
| **6. Audit** | - | Verify system-wide alignment and update documentation. |

