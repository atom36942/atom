# About
This document serves as the primary source of truth for AI Agents working within the Atom framework. 
Adherence to these rules is imp to maintain codebase consistency and safety.
Pls use scratch folder only for your working temp file.

### Repository Map
- **`main.py`**: Entry point for the application. Handles server execution and runtime orchestration.
- **`core/`**: Centralized framework core. Manages application initialization (including **`function/`** and **`router/`**), settings, and background task processing.
- **`service/`**: Isolated, independent FastAPI applications with standalone logic and deployment configurations.
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
- **Blueprint Pattern (New APIs)**: Follow this strict development sequence: (1) Define endpoint in `core/router/`, (2) logic in `core/function/`, (3) inject context via `request.app.state`.
- **Naming Conventions**: Use strict prefixes (`client_`, `cache_`,`config_`, `func_`) for `core/app.py`, `core/function/*`, and `core/config/*` logic.
- **Functional Logic Layer**: Modular, stateless logic only; internal state persistence strictly prohibited; explicit dependency injection; side-effect free IO via injected clients.
- **Strict Function Signatures**: All functions in the `core/function/` directory MUST use the keyword-only separator (`*`) immediately after the opening parenthesis. Every parameter MUST be mandatory; internal default values are strictly prohibited.
- **API Parameter Definition**: All API parameters MUST be defined and extracted at the `core/router/` level using `func_request_param_read`. Functional modules in `core/function/` MUST receive pre-parsed objects and are prohibited from handling raw request parameter extraction.
