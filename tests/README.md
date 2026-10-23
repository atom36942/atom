# Regression tests

From the project root, use the environment with Atom's dependencies installed:

```bash
venv/bin/python -m unittest discover -s tests -v
```

The suite uses the standard-library `unittest` runner; no extra test framework is
required. Authentication tests use the installed PyJWT, orjson, and argon2-cffi
libraries. Git must be installed for the updater tests.

| Area | Coverage |
|------|----------|
| Authentication | Password verification and hashing, signup policy, ambiguous login, token expiry/signatures/types, OTP success and rejection |
| Permissions | Table and relation policies, roles, account status, restricted fields, ownership, OTP-protected changes, batch limits |
| CRUD | Parameter binding, serialization, restricted reads, pagination, ownership predicates, buffered writes, error propagation |
| Query language | Every filter operator and alias, per-type operator limits, typed values, OR/AND nesting and placeholder order, ownership predicates that user filters cannot widen, relation count/aggregate/fetch strings, blocked columns, malformed relations |
| Function loading | Custom modules, public exports, duplicate definitions, imported helpers, import failures |
| Syncing | Developer files and config overrides, dependency merging, validation failures, file retirement, rollback, locking |
| Security | Read-runner restrictions, blob signing authorization, bounded upload reads, credential redaction |
| Errors | HTTP status for `func_api_error`, each middleware check (401/403/404/429/500), token decoding, and database, Redis, and external-API failures; plain exceptions stay 400 |

## Coverage

`coverage` records which lines of core code (`function/`, `router/`, `main.py`, `config.py`) the tests run:

```bash
venv/bin/python -m coverage run --source=function,router,main,config -m unittest discover -s tests
venv/bin/python -m coverage report --show-missing --sort=cover
```

`coverage html` writes a browsable report to `htmlcov/`. The data files are not committed (`.gitignore` denies everything not listed). Without `ATOM_TEST_POSTGRES_URL` the integration tests are skipped, so the local number is lower than CI's. CI fails when total coverage drops below 70%.

## Dependency checks

CI runs `pip-audit` after installing `requirements.txt` and fails when an installed package has a known vulnerability; the log names the package and the fixed version. To check locally:

```bash
venv/bin/pip install pip-audit && venv/bin/pip-audit
```

Dependabot (`.github/dependabot.yml`) opens one weekly pull request for newer pinned packages and one for GitHub Actions, waiting until a release is a week old. CI tests each one before you merge it. `boto3` and `aiobotocore` are excluded: `boto3` must stay inside the `botocore` range the installed `aiobotocore` supports, so update them by hand together (newest `aiobotocore` first, then the `boto3` version in its range) and check with `venv/bin/pip check`.

## Unit tests

Everything outside `tests/integration/` mocks the database. These tests exercise
real builders and serializers without executing SQL; they do not load the
application config or connect to databases, Redis, or cloud services. Sync tests
create disposable local Git repositories and do not fetch the real Atom repository.

## Integration tests (real PostgreSQL and HTTP)

`tests/integration/` runs real SQL and real HTTP requests. It is skipped unless
`ATOM_TEST_POSTGRES_URL` points at a PostgreSQL server where the user can
`CREATE DATABASE` and install `postgis`, `pg_trgm`, and `btree_gin`:

```bash
ATOM_TEST_POSTGRES_URL=postgresql://user@localhost:5432/postgres venv/bin/python -m unittest discover -s tests -v
```

Each test gets its own throwaway `atom_test_*` database, dropped afterwards, so
existing databases on that server are never touched. CI runs these against a
`postgis/postgis` service.

`tests/test_redis_checks.py` runs the `redis`-mode user checks and rate limit against a real Redis. It is skipped unless `ATOM_TEST_REDIS_URL` is set; use a spare database number, since it writes and deletes a few `cache:user:*` and `ratelimiter:*` keys:

```bash
ATOM_TEST_REDIS_URL=redis://localhost:6379/15 venv/bin/python -m unittest tests.test_redis_checks -v
```

`tests/test_sync_venv_real.py` builds real venvs with `sync.py` (build, skip when unchanged, drop a hand-installed package, restore after a failed install). It needs network for pip and is skipped unless `ATOM_TEST_VENV_REAL=1`; CI runs it on Linux and macOS:

```bash
ATOM_TEST_VENV_REAL=1 python3.14 -m unittest tests.test_sync_venv_real -v
```

| Area | Coverage |
|------|----------|
| PostgreSQL | Schema init (idempotent, root admin seeded), filters as real SQL including `is true` and `= null`, sorting and pagination, update/delete ownership, relations, buffered writes, OTP attempt cap under concurrency, password signup and login |
| HTTP | App startup with test settings only, token 401s, role 403 and admin 200, create/read own objects, malformed filter 400, cache hit header, rate limit 429, security headers, no password hash in `/my/profile`, requests written to `log_api` |

The HTTP tests start the app from a temporary working directory with test-only
environment variables. `config.py` loads `.env` from the working directory and
startup resets `./tmp`, so running the app from the repo root would read your
real `.env` and wipe your `tmp/`.
