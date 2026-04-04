### AGENTS Rules

### Core Development Principles
| Section | Standard | Execution Logic |
| :--- | :--- | :--- |
| **Style** | Senior, Compact | 1 blank line before headers; no breaks between comments/logic inside functions. |
| **Logic** | Pure Functional | `function.py` for stateless logic; no external dependencies; SOLID compliant. |
| **Safety** | Error Isolation | No `or` logic in checks; individual `if` blocks for specific exceptions. |
| **IO** | Path Security | `tmp/` for temporary files only. No exceptions. |
| **Defaults** | INTERNAL HANDLING| No parameter defaults in signatures; use `None` and handle at function start. |
| **Frontend** | Single-File | `static/` HTML files must contain all JS/CSS/HTML logic. No external local assets. |

### Naming Conventions
| Category | Variable Prefix | Behavior |
| :--- | :--- | :--- |
| **Boolean** | `is_[name]` | Strictly `int` (1/0). NEVER use Python `True`/`False`. |
| **Config** | `config_` | Reserved for variables in `config.py`. Single line assignment. |
| **Functions** | `func_` | Standard prefix for all functional logic. |
| **Clients** | `client_` | Persistent singletons (HTTP, DB, Redis, etc.). |
| **Cache** | `cache_` | Dictionary-based local or distributed state maps. |

### Repository Map
| Path | Service | Responsibility |
| :--- | :--- | :--- |
| `main.py` | **Entry** | Lifespan, Middleware, App Initialization. |
| `router.py` | **API** | Definition of all endpoints and role assignments. |
| `function.py` | **Core** | Primary functional logic and database drivers. |
| `config.py` | **Settings** | Global configuration and schema definitions. |
| `consumer.py` | **Workers** | Background task processing (Celery, Kafka, etc.). |
| `static/` | **Assets** | Frontend files and documentation pages. |
| `tmp/` | **Runtime** | Workspace for temporary runtime operations. |

### Standardized Routing Logic
| Rule | Pattern | Behavior |
| :--- | :--- | :--- |
| **Structure** | `/{cat}/{name}` | Strictly 2 levels deep. `{name}` maps to a pure function. |
| **Consolidation**| Identical Params | Combine `create/update/delete` if all parameters match. |
| **Isolation** | Divergent Params | Use unique endpoints if action-specific parameters (e.g. `expiry`) exist. |
| **Audit** | Sync Check | Update all related files (configs, docs, HTML) after any API change. |

### Development Workflow
| Stage | File | Action |
| :--- | :--- | :--- |
| **1. Define** | `router.py` | Add route with path-based prefix code. |
| **2. Logic** | `function.py` | Create pure logic (use local imports). |
| **3. Config** | `config.py` | Add `config_` variables and table schemas. |
| **4. Init** | `main.py` | Initialize new `client_` singletons if required. |
| **5. Entry** | `static/api.html` | Sync OpenAPI and Test Runner entries. |
| **6. Audit** | - | Verify system-wide alignment and update documentation. |

### Protected Resources
| Resource | Constraint | Rationale |
| :--- | :--- | :--- |