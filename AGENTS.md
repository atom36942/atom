### Repository Map
- **`main.py`**: Application entry point.
- **`core/`**: Framework core (initialization, functions, routers).
- **`service/`**: Independent FastAPI apps.
- **`static/`**: Frontend assets.
- **`tmp/`**: Strictly for temporary runtime operations (IO).
- **`secret/`**: Sensitive credentials.
- **`AGENTS.md`**: AI framework rules.
- **`Dockerfile`**: Container configuration.
- **`readme.md`**: Project overview.
- **`requirements.txt`**: Dependencies.

### Core Principles
- **Explicit > Implicit**: Always prefer explicit logic.
- **SOLID**: Strictly adhere to SOLID principles.
- **IO Isolation**: Use `tmp/` for all file operations.
- **Blueprint Pattern**: Sequence: `core/router/` -> `core/function/` -> `request.app.state`.
- **Strict Prefixes**: `client_`, `cache_`, `config_`, `func_` for all core logic.
- **Stateless Logic**: Modules must be stateless; side-effect free IO via injected clients.
- **Strict Signatures**: `func(*, ...)` separator; all parameters mandatory; no defaults.
- **Standalone Portability**: All imports MUST be inside function bodies for copy-paste safety.
- **Router-Level Parsing**: Use `func_request_param_read` in routers; functions receive objects.
- **Logical Grouping**: Organise `core/function/` by domain (e.g., `user.py`, `integration.py`); target 150–400 lines per file to balance modularity and discoverability.
- **Workspace Safety**: Use `scratch/` folder only for temporary agent files.
