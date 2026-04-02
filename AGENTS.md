### AGENTS Rules

### Style
* Senior level, compact; exactly 1 blank line before headers (outside functions); no blank lines or line breaks between comments/logic inside functions/APIs.

### Logic
* `function.py` strictly for pure functions; no external state dependencies; minimize side effects; SOLID.

### Vars
* Explicit names; switch vars: `is_[name]` (int 0/1, never bool); use int `1` vs `0` for all boolean logic; avoid Python `True`/`False`.

### Prefixes
* `config_` (strictly for `config.py` variables); use explicit names for others; `func_`, `client_`, `cache_`.

### IO
* `tmp/` only for temp files/folders. No exceptions.

### State
* `main.py` stores all integrations (DB, Redis, S3) in `request.state`.

### Pattern
* `#name` (lowercase, no brackets) for `.py` logic breaks; `### Name` (Proper Case, no brackets) for `.md` files.

### Errors
* No combined `or` logic in error checks. Break multiple failure conditions into individual `if` blocks with specific exception messages.

### Config
* Single line assignment only; no chain statements (e.g. `a, b = 1, 2`).

### Defaults
* No non-essential parameter defaults in signatures. Use `None` and handle internally (`p = p or default`) at start of function. (e.g. `func_postgres_obj_create`).

### Docs
* Use `<details><summary>` in `readme.md`; use tables wherever possible for configurations/lists; sync `readme.md` with new features/logic.

### Script
* `script/*/app.py` logic breaks: 1. #import, 2. #config, 3. #pure func, 4. #lifespan, 5. #app, 6. #middleware, 7. #api, 8. #app start.

### Repo Map
* `tmp/`: Runtime dumps; `script/`: utility apps; `secret/`: keys; `static/`: Assets; `venv/`: python env; `config.py`: Global config; `main.py`: Entry; `router.py`: API endpoints; `function.py`: Pure functions (Rule 2); `consumer.py`: Workers; `requirements.txt`: Deps; `Dockerfile`: Container; `readme.md`: Docs; `AGENTS.md`: AI Rules; `.gitignore`: Exclusions; `.env`: Overrides; `z.py`: Scratchpad.

### API Routes
* Each API is structured as `/{category}/{name}` (strictly 2 levels deep, no nested paths); `{name}` is mapped directly to a standalone pure function and shouldn't bleed into other categories.

### Workflow
* `router.py`: Add route with prefix; `function.py`: Core logic (use local imports); `config.py`: Add `config_` vars; `main.py`: Init `client_`; `static/api.html`: Sync entry.