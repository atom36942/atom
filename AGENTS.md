### Principles
- **Explicit > Implicit**: Always prefer explicit logic.
- **SOLID**: Strictly adhere to SOLID principles.
- **Workspace Safety**: Use `scratch/` folder for temporary agent files.
- **IO Isolation**: Use `tmp/` for all router/function file operations.
- **Function**: Functions in `core/function/` must be self-contained and pure. All imports **MUST** be defined inside the function body (no global imports). Function names **MUST** start with the `func_` prefix (excluding `__init__.py`). Signatures **MUST** use explicit keyword-only parameters (`func(*, ...)`).
- **Strict Prefixes**: `client_`, `cache_`, `config_`, `func_` for all core logic.
- **How to Add API**: First add/update the appropriate router in `core/router/` (respective file), then move business logic into a pure function in the corresponding `core/function/` domain file; use `request.app.state` and `request.state.query` for clients/context.
