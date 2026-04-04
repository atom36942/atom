### AGENTS Rules

### Core Development Principles
<div style="overflow-x: auto;">
| Section | Standard | Execution&nbsp;Logic |
| :--- | :--- | :--- |
| **Style** | Senior,&nbsp;Compact | 1 blank line before headers; no breaks between<br>comments/logic inside functions. |
| **Logic** | Pure&nbsp;Functional | `function.py` for stateless logic; no external<br>dependencies; SOLID compliant. |
| **Safety** | Error&nbsp;Isolation | No `or` logic in checks; individual `if`<br>blocks for specific exceptions. |
| **IO** | Path&nbsp;Security | `tmp/` for temporary files only. No exceptions. |
| **Defaults** | INTERNAL HANDLING| No parameter defaults in signatures; use `None`<br>and handle at function start. |
| **Frontend** | Single-File | `static/` HTML files must contain all JS/CSS/HTML<br>logic. No external local assets. |
</div>


### Naming Conventions
<div style="overflow-x: auto;">
| Category | Variable&nbsp;Prefix | Behavior |
| :--- | :--- | :--- |
| **Boolean** | `is_[name]` | Strictly `int` (1/0). NEVER use Python<br>`True`/`False`. |
| **Config** | `config_` | Reserved for variables in `config.py`.<br>Single line assignment. |
| **Functions** | `func_` | Standard prefix for all functional logic. |
| **Clients** | `client_` | Persistent singletons (HTTP, DB, Redis, etc.). |
| **Cache** | `cache_` | Dictionary-based local or distributed state maps. |
</div>


### Repository Map
<div style="overflow-x: auto;">
| Path | Service | Responsibility |
| :--- | :--- | :--- |
| `main.py` | **Entry** | Lifespan, Middleware, App&nbsp;Initialization. |
| `router.py` | **API** | Definition of all endpoints and role&nbsp;assignments. |
| `function.py` | **Core** | Primary functional logic and database&nbsp;drivers. |
| `config.py` | **Settings** | Global configuration and schema&nbsp;definitions. |
| `consumer.py` | **Workers** | Background task processing (Celery, Kafka,&nbsp;etc.). |
| `static/` | **Assets** | Frontend files and documentation&nbsp;pages. |
| `tmp/` | **Runtime** | Workspace for temporary runtime&nbsp;operations. |
</div>


### Standardized Routing Logic
<div style="overflow-x: auto;">
| Rule | Pattern | Behavior |
| :--- | :--- | :--- |
| **Structure** | `/{cat}/{name}` | Strictly 2 levels deep. `{name}` maps to<br>a pure function. |
| **Consolidation**| Identical Params | Combine `create/update/delete` if all<br>parameters match. |
| **Isolation** | Divergent Params | Use unique endpoints if action-specific<br>parameters (e.g. `expiry`) exist. |
| **Audit** | Sync Check | Update all related files (configs, docs, HTML)<br>after any API change. |
</div>


### Development Workflow
<div style="overflow-x: auto;">
| Stage | File | Action |
| :--- | :--- | :--- |
| **1. Define** | `router.py` | Add route with path-based prefix code. |
| **2. Logic** | `function.py` | Create pure logic (use local imports). |
| **3. Config** | `config.py` | Add `config_` variables and table schemas. |
| **4. Init** | `main.py` | Initialize new `client_` singletons if required. |
| **5. Entry** | `static/api.html` | Sync OpenAPI and Test Runner entries. |
| **6. Audit** | - | Verify system-wide alignment and update<br>documentation. |
</div>


### Protected Resources
<div style="overflow-x: auto;">
| Resource | Constraint | Rationale |
| :--- | :--- | :--- |
</div>