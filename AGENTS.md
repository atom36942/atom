# About
This document serves as the primary source of truth for AI Agents working within the Atom framework. 
Adherence to these rules is imp to maintain codebase consistency and safety.

### Core Principles
- **AI Agent Behavior**: Always prefer explicitness over implicitness.
- **SOLID Principles**: Adhere strictly to SOLID principles across all logic. Every function and module must have a single responsibility and be easily testable.
- **Pure Functional Logic**: Place heavy focus on pure functional programming. All core logic must be stateless, without external dependencies or side effects.
- **Parameter Handling**: No defaults in signatures; use `None` and initialize internally for 1:1 explicit mapping.
- **IO Isolation**: Use `tmp/` strictly for all file operations.
- **Naming Conventions**: Strict prefixes required (`is_`, `config_`, `func_`, `client_`, `cache_`) including service/feature scope.
- **Booleans**: All boolean values must be integers (1/0) and must use the `is_` prefix.

### Repository Map
- **`main.py`**: Entry point for the application. Handles server execution and runtime orchestration.
- **`core/`**: Centralized framework core.
    - **`app.py`**: Initialization logic. Manages lifespan, middleware, and application setup.
    - **`config.py`**: Centralized settings and schema definitions.
    - **`function.py`**: Framework orchestration logic and common utilities.
    - **`consumer.py`**: Background task processing (Celery, Kafka, etc.).
- **`function/`**: Modular functional logic layer.
    - **`client.py`**: Centralized client initialization (DB, cache, cloud services).
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

