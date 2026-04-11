# About
This document serves as the primary source of truth for AI Agents working within the Atom framework. 
Adherence to these rules is imp to maintain codebase consistency and safety.

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
- **`AGENTS.md`**: Framework rules, AI agent guidelines, and repository map.
- **`Dockerfile`**: Containerization configuration for the application environment.
- **`readme.md`**: General project overview, installation, and usage instructions.
- **`requirements.txt`**: Application dependencies and package versions.

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

