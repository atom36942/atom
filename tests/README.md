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

| Area | Coverage |
|------|----------|
| PostgreSQL | Schema init (idempotent, root admin seeded), filters as real SQL including `is true` and `= null`, sorting and pagination, update/delete ownership, relations, buffered writes, OTP attempt cap under concurrency, password signup and login |
| HTTP | App startup with test settings only, token 401s, role 403 and admin 200, create/read own objects, malformed filter 400, cache hit header, rate limit 429, security headers, no password hash in `/my/profile`, requests written to `log_api` |

The HTTP tests start the app from a temporary working directory with test-only
environment variables. `config.py` loads `.env` from the working directory and
startup resets `./tmp`, so running the app from the repo root would read your
real `.env` and wipe your `tmp/`.
