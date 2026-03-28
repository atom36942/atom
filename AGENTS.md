* **Style:** Senior level, compact; exactly one blank line before headers if outside functions; no blank lines between comments/logic inside functions/APIs.
* **Logic:** Pure functions in `function.py`, minimize side effects, SOLID.
* **Vars:** Explicit names; switch vars: `is_[name]` (0/1). 
* **Prefixes:** `config_` (strictly for `config.py` variables); use explicit names for others; `func_`, `client_`, `cache_`.
* **IO:** `tmp/` only for temp files/folders. No exceptions.
* **Functionality:** `function.py` strictly for pure functions; no external state dependencies.
* **State:** `main.py` stores all integrations (DB, Redis, S3) in `request.state`.
* **Boolean:** Use `is_active = 1` vs `0` for boolean logic. 
* **Pattern:** `# name` (lowercase, no brackets) for `.py` logic breaks; `### name` (lowercase, no brackets) for `.md` files.
* **Errors:** No combined `or` logic in error checks. Break multiple failure conditions into individual `if` blocks with specific exception messages.
* **Config:** Single line assignment only; no chain statements (e.g. `a, b = 1, 2`).

### repo map
* `tmp/`: Runtime dumps & temp storage (Rule 5); auto-created by `main.py`.
* `script/`: Standalone utility scripts (non-API context).
* `secret/`: Sensitive data; holds certs and keys.
* `static/`: Assets served at `/static`; contains `curl.html` & data templates.
* `venv/`: Python virtual environment.
* `config.py`: Centralized configuration; all vars prefixed with `config_`.
* `main.py`: App entry; initializes `app.state.client_*` & global middleware.
* `router.py`: API endpoints; logic delegated to `app.state.func_*`.
* `function.py`: Library of pure functions; no external state (Rule 8).
* `consumer.py`: Queue workers for asynchronous background tasks (Redis/Celery/Kafka/RabbitMQ).
* `curl.txt`: Reference list of all API endpoints in curl format for testing.
* `test.py`: Python script to automate API testing using `curl.txt`.
* `requirements.txt`: Python package dependencies for the project.
* `Dockerfile`: Containerization setup for consistent deployment.
* `readme.md`: Project overview, installation, and common developer commands.
* `AGENTS.md`: AI agent documentation; contains core rules and repo map.
* `.gitignore`: Git exclusion rules for `venv/`, `tmp/`, and `secret/`.
* `.env`: Environment-specific overrides for `config.py`.
* `z.py`: Developer scratchpad for temporary snippets.

### api workflow
1. `router.py`: Add route with correct prefix:
   * `root/`: Root user/Sudo access.
   * `auth/`: Auth operations (Login/Signup).
   * `my/`: Auth required + access `request.state.user`.
   * `public/`: No token required (Open access).
   * `private/`: Token required.
   * `admin/`: RBAC via `config_api.role_allowed`.
2. `function.py`: Core logic as pure func (use local imports).
3. `config.py`: Add required `config_` vars.
4. `main.py`: Init `client_` in lifespan; access via `request.state`.
5. `curl.txt` + `static/curl.html`: Sync entry in standard format.