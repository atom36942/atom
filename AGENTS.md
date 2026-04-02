### AGENTS Rules

### Style
* Senior level, compact.
* Exactly 1 blank line before headers (outside functions).
* No blank lines or line breaks between comments/logic inside functions/APIs.

### Logic
* `function.py` strictly for pure functions.
* No external state dependencies.
* Minimize side effects.
* SOLID principles.

### Vars
* Explicit names.
* Switch vars: `is_[name]` (int 0/1, never bool).
* Use int `1` vs `0` for all boolean logic.
* Avoid Python `True`/`False`.

### Prefixes
* `config_` (strictly for `config.py` variables).
* Use explicit names for others.
* `func_`, `client_`, `cache_`.

### IO
* `tmp/` only for temp files/folders. No exceptions.

### State
* `main.py` stores all integrations (DB, Redis, S3) in `request.state`.

### Pattern
* `#name` (lowercase, no brackets) for `.py` logic breaks.
* `### Name` (Proper Case, no brackets) for `.md` files.

### Errors
* No combined `or` logic in error checks. Break multiple failure conditions into individual `if` blocks with specific exception messages.

### Config
* Single line assignment only.
* No chain statements (e.g. `a, b = 1, 2`).
* Strictly audit and update all `config.py` variables (especially `config_api`) whenever routes or logic change.

### Defaults
* No non-essential parameter defaults in signatures.
* Use `None` and handle internally (`p = p or default`) at start of function (e.g. `func_postgres_create`).

### Docs
* Use `<details><summary>` in `readme.md`.
* Use tables wherever possible for configurations/lists.
* Sync `readme.md` and related documentation (including `AGENTS.md`) with latest features/logic.

### Script
* `script/*/app.py` logic breaks: 1. #import, 2. #config, 3. #pure func, 4. #lifespan, 5. #app, 6. #middleware, 7. #api, 8. #app start.

### Repo Map
* `tmp/`: Runtime dumps.
* `script/`: utility apps.
* `secret/`: keys.
* `static/`: Assets.
* `venv/`: python env.
* `config.py`: Global config.
* `main.py`: Entry.
* `router.py`: API endpoints.
* `function.py`: Pure functions (Rule 2).
* `consumer.py`: Workers.
* `requirements.txt`: Deps.
* `Dockerfile`: Container.
* * `readme.md`: Docs.
* `AGENTS.md`: AI Rules.
* `.gitignore`: Exclusions.
* `.env`: Overrides.
* `z.py`: Scratchpad.

### API Routes
* Each API is structured as `/{category}/{name}` (strictly 2 levels deep, no nested paths).
* `{name}` is mapped directly to a standalone pure function and shouldn't bleed into other categories.
* Consolidate APIs using a `mode` parameter ONLY if all parameters are 100% identical and the actions belong to the same logical category.
    * **Merge Example**: `postgres-import` (modes `create`, `update`, `delete` all require exactly `table` and `file`).
* Never merge APIs with different underlying logic or purpose, even if their parameter sets are identical.
    * **Split Example**: `redis-import` (split into `redis-import-create` and `redis-import-delete` because `create` requires `expiry_sec` while `delete` does not).

### Workflow
* `router.py`: Add route with prefix.
* `function.py`: Core logic (use local imports).
* `config.py`: Add `config_` vars.
* `main.py`: Init `client_`.
* `static/api.html`: Sync entry.
* **Audit**: Perform a comprehensive check and update of all related files/folders (config, documentation, static assets) after any change to ensure total system synchronization.