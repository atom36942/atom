# Atom Development Standards
This document serves as the primary source of truth for AI Agents working within the Atom framework. Adherence to these rules is mandatory to maintain codebase consistency and safety.

## 📂 Repository Map
- **`main.py`**: Entry point for the application. Handles server execution and runtime orchestration.
- **`app.py`**: Initialization logic. Manages lifespan, middleware, and application setup.
- **`config.py`**: Centralized settings and schema definitions.
- **`function.py`**: The core logic layer. Contains primary functional logic and database drivers.
- **`consumer.py`**: Background task processing (Celery, Kafka, etc.).
- **`router/`**: API endpoint definitions and role assignments.
- **`script/`**: Isolated, independent scripts with standalone logic.
- **`static/`**: Frontend assets and documentation.
- **`tmp/`**: **Strictly** for temporary runtime operations (IO).
- **`secret/`**: Sensitive credentials (protected).

---

## 🛠 Core Development Principles

### 1. Pure Functional Logic
- All logic in `function.py` must be stateless.
- **Dependency Rule**: No external dependencies in logic blocks.
- **SOLID Compliance**: Maintain strict single-responsibility for all functions.

### 2. Safety & Error Isolation
- **No Logical Unions**: Never use `or` when checking for multiple failure conditions. Use individual `if` blocks.
- **Detailed Exceptions**: Avoid clubbed error messages (e.g., "Field A or B missing"). Each error must be explicit to the specific failure.
- **IO Isolation**: Only use `tmp/` for file operations.

### 3. Parameter Handling
- **No Defaults**: Do not use default values in function signatures.
- **Initialization**: Use `None` in signatures and handle actual initialization at the start of the function body.
- **Explicitness**: Every parameter must map 1:1 to global state or internal logic—no implicit behaviors.

### 4. Naming Conventions (Strict)
All variables and functions must follow these prefix rules:
- `is_`: Integers used as booleans (1/0).
- `config_`: Settings and configuration variables.
- `func_`: Logic functions.
- `client_`: Client initialization/drivers.
- `cache_`: Caching-related logic.
- **Scope**: All names must include the service or feature name (e.g., `func_auth_login`).

---

## 🚀 Development Workflow

1.  **Define (Routing)**: Start in `router/`. Add the route with a path-based prefix code.
2.  **Logic (Core)**: Implement the pure logic in `function.py` using local imports.
3.  **Config (Settings)**: Add any required `config_` variables or table schemas in `config.py`.
4.  **Setup (App)**: Register the logic in `app.py` via Lifespan or Middleware.
5.  **Run (Execution)**: Execute via `main.py` (Uvicorn).
6.  **Audit (Validation)**: Verify system-wide alignment and update relevant documentation.

---

> [!IMPORTANT]
> **AI Agent Behavior**: Always prefer explicitness over conciseness. If a rule in this file conflicts with a general coding best practice, the rule in this file takes precedence.
