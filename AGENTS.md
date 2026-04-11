# About
This document serves as the primary source of truth for AI Agents working within the Atom framework. 
Adherence to these rules is imp to maintain codebase consistency and safety.

### Core Principles
- **AI Agent Behavior**: Always prefer explicitness over implicitness.
- **SOLID Principles**: Adhere strictly to SOLID principles across all logic. Every function and module must have a single responsibility and be easily testable.
- **Dependency Injection**: To maintain 100% purity and explicitness, all external dependencies—including utility functions—must be passed as parameters. Implicit top-level imports of functional logic are prohibited.
- **Parameter Handling**: No defaults in signatures; use `None` and initialize internally for 1:1 explicit mapping.
- **IO Isolation**: Use `tmp/` strictly for all file operations.
- **Naming Conventions**: Strict prefixes required (`is_`, `config_`, `func_`, `client_`, `cache_`) including service/feature scope.
- **Booleans**: All boolean values must be integers (1/0) and must use the `is_` prefix.
- **Pure Functional Logic**: All logic in the `function/` directory must be 100% pure, stateless, and without side effects. To maintain this purity, the following MUST be passed as parameters and NEVER imported at the top level:
    1. **System Clients** (e.g., `client_postgres`).
    2. **Configuration Settings** (e.g., `config_api`).
    3. **Functional Logic** (i.e., other functions passed as callables).
    4. **Built-in Python libraries and External Packages** Built-in Python libraries (e.g., `time`, `json`, `re`, `uuid`, `traceback`, `hashlib`, `gzip`, `base64`) and external packages (e.g., `jwt`, `orjson`, `httpx`) can be imported inline.

### Repository Map
- **`main.py`**: Entry point for the application. Handles server execution and runtime orchestration.
- **`core/`**: Centralized framework core.
    - **`app.py`**: Initialization logic. Manages lifespan, middleware, and application setup.
    - **`config.py`**: Centralized settings and schema definitions.
    - **`consumer.py`**: Background task processing (Celery, Kafka, etc.).
- **`function/`**: Modular pure functional logic layer (100% pure, no IO).
- **`router/`**: API endpoint definitions and role assignments.
- **`script/`**: Isolated, independent scripts with standalone logic.
- **`static/`**: Frontend assets and documentation.
- **`tmp/`**: **Strictly** for temporary runtime operations (IO).
- **`secret/`**: Sensitive credentials (protected).

### Development Workflow
- **Define (Routing)**: Add API in `router/`. Add the route with a path-based prefix code.
- **State & Clients**: Access system clients via `request.app` and user context via `request.state`.
- **Config (Settings)**: Add any required `config_` variables or table schemas in `core/config.py`.
- **Logic (Core)**: Implement framework logic in `core/function.py` and domain/feature logic in `function/`. If a new function is needed, use the `func_` prefix.
- **Lifespan (Clients)**: For new system clients, define initialization in `func_lifespan` using functions from `function/client.py` and assign to `app.state`.
- **Naming Conventions**: Use the `func_client_read_` prefix for client initializers in `function/client.py`.
- **Caching**: Use the `cache_` prefix for any new caching-related state or logic.
- **Client Lifecycle**: All clients must be defined as pure functions in `function/client.py` and managed via the application state (`request.app.state`).
- **HTML Modularization**: Large HTML files must be refactored into a dedicated directory with separate CSS and JS components (e.g., `static/api/`) to maintain maintainability.
- **Pure Functional Logic**: All functions in the `function/` directory must be 100% pure and stateless. Strictly pass external clients, configs, and other logic as parameters. Built-in and external libraries can be imported inline.

