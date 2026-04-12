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
- **New API Development Flow**: When creating a new API endpoint, follow this order strictly: (1) define the endpoint in the appropriate `router/` API file, (2) separate business logic into a function in the corresponding `function/` API file, and (3) consume request context explicitly (e.g., `request.app.state` for framework dependencies, `request.state` for authenticated user/roles) in the router layer and pass only required values into functional logic.
- **Naming Conventions**: Strict prefixes required (`client_`, `cache_`,`config_`, `func_`) for core/app.py, function/* and core/config/* logic.
- **Functional Logic**: All logic in `function/` must be modular and stateless. Internal state persistence within functions (e.g., `func_name.state`) is strictly prohibited. All dependencies—including system clients, configuration settings, and temporary runtime caches or buffers—must be passed explicitly as parameters from the router or core layers. Logic should remain side-effect free whenever possible, with IO restricted to injected clients.
- **Parameter Naming**: All parameters in `function/` layer functions must match exactly with the query or body parameter names defined in the `router/` layer. This ensures a 1:1 consistent mapping between the API contract and internal business logic (e.g., use `order` instead of `sort_order`, `limit` instead of `limit_count`, `page` instead of `page_number`).