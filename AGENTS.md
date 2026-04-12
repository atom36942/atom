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
- **SOLID Principles**: Adhere strictly to SOLID principles across all logic. Every function and module must have a single responsibility and be easily testable.
- **Dependency Injection**: To maintain strict architectural explicitness, all external dependencies—including utility functions—must be passed as parameters. Implicit top-level imports of functional logic are prohibited. In the `router/` layer, all framework dependencies (`client_`, `cache_`, `func_`, `config_`) must be retrieved from `request.app.state`.
- **Parameter Handling**: No defaults in signatures; use `None` and initialize internally for 1:1 explicit mapping.
- **IO Isolation**: Use `tmp/` strictly for all file operations.
- **Naming Conventions**: Strict prefixes required (`is_`, `config_`, `func_`, `client_`, `cache_`) including service/feature scope. Specifically, all functions in the `function/` directory must start with `func_`, and all configuration variables in `core/config.py` must start with `config_`. Every variable prefixed with `config_` must be defined exclusively in `core/config.py`.
- **Booleans**: All boolean values must be integers (1/0) and must use the `is_` prefix.
- **New API Development Flow**: When creating a new API endpoint, follow this order strictly: (1) define the endpoint in the appropriate `router/` API file, (2) separate business logic into a function in the corresponding `function/` API file, and (3) consume request context explicitly (e.g., `request.app.state` for framework dependencies, `request.state` for authenticated user/roles) in the router layer and pass only required values into functional logic. **Manual top-level imports of `function/` or `core/config.py` in router files are strictly prohibited.**
- **Functional Logic**: All logic in `function/` must be modular and stateless; system clients, config settings, and other functional logic must be passed as parameters (not imported at top level), while built-in and external libraries may be imported inline. Logic should remain side-effect free whenever possible, with IO restricted to injected clients.
