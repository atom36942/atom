# About
This document serves as the primary source of truth for AI Agents working within the Atom framework. 
Adherence to these rules is imp to maintain codebase consistency and safety.

### Repository Map
- **`main.py`**: Entry point for the application. Handles server execution and runtime orchestration.
- **`core/`**: Centralized framework core.
    - **`app.py`**: Initialization logic. Manages lifespan, middleware, and application setup.
    - **`config.py`**: Centralized settings and schema definitions.
    - **`consumer.py`**: Background task processing (Celery, Kafka, etc.).
- **`function/`**: Modular functional logic layer (IO allowed via injected clients).
- **`router/`**: API endpoint definitions and role assignments.
- **`script/`**: Isolated, independent scripts with standalone logic.
- **`static/`**: Frontend assets and documentation.
- **`tmp/`**: **Strictly** for temporary runtime operations (IO).
- **`secret/`**: Sensitive credentials (protected).
- **`AGENTS.md`**: Framework rules, AI agent guidelines, and repository map.
- **`Dockerfile`**: Containerization configuration for the application environment.
- **`readme.md`**: General project overview, installation, and usage instructions.
- **`requirements.txt`**: Application dependencies and package versions.

### Core Principles/Rules
- **AI Agent Behavior**: Always prefer explicitness over implicitness.
- **SOLID Principles**: Adhere strictly to SOLID principles across all logic.
- **IO Isolation**: Use `tmp/` strictly for all file operations.
- **Blueprint Pattern (New APIs)**: Follow this strict development sequence: (1) Define endpoint in `router/`, (2) logic in `function/`, (3) inject context via `request.app.state`.
- **Naming Conventions**: Use strict prefixes (`client_`, `cache_`,`config_`, `func_`) for `core/app.py`, `function/*`, and `core/config/*` logic.
- **Functional Logic Layer**: Modular, stateless logic only; internal state persistence strictly prohibited; explicit dependency injection; side-effect free IO via injected clients.
- **API Parameter Matching**: Parameter names in functional logic (`function/`) MUST exactly match the names used in the corresponding API endpoints (`router/`), especially those defined in `func_request_param_read`.

