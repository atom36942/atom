# Tests

Atom's own tests, standard-library `unittest`, run from the project root (Git must be installed for the sync tests):

```bash
venv/bin/python -m unittest discover -s tests -t .
```

## Unit tests
Everything outside `tests/integration/` mocks the database: real builders and serializers, no SQL, no config, no connections to databases, Redis or cloud services. Sync tests create throwaway local Git repositories and never fetch the real Atom repository.

## Tests with real services
Skipped unless their environment variable is set:

| Variable | Runs | Needs |
|---|---|---|
| `ATOM_TEST_POSTGRES_URL` | Integration tests: real SQL and HTTP | A PostgreSQL user that can `CREATE DATABASE` and install `postgis`, `pg_trgm`, `btree_gin`; each test gets its own throwaway `atom_test_*` database, dropped afterwards |
| `ATOM_TEST_REDIS_URL` | `redis`-mode user checks and rate limits | A spare Redis database number; the tests write and delete a few keys |
| `ATOM_TEST_VENV_REAL=1` | Real venv builds by `sync.py` | Network for pip |

```bash
ATOM_TEST_POSTGRES_URL=postgresql://user@localhost:5432/postgres ATOM_TEST_REDIS_URL=redis://localhost:6379/15 venv/bin/python -m unittest discover -s tests -t .
```

CI sets all three against PostgreSQL (PostGIS) and Redis services. The HTTP tests start the app from a temporary working directory with test-only settings, so they never read your `.env` or touch your `tmp/`.

## Coverage
```bash
venv/bin/python -m coverage run --source=function,router,main,config -m unittest discover -s tests -t .
venv/bin/python -m coverage report --show-missing --sort=cover
```
`coverage html` writes a browsable report to `htmlcov/` (not committed). Without the service variables the integration tests are skipped, so the local number is lower than CI's. CI fails when total coverage drops below 70%.

## Dependency checks
CI runs `pip-audit` on `requirements.txt` and fails on a package with a known vulnerability; the log names the package and the fixed version. Locally:

```bash
venv/bin/pip install pip-audit && venv/bin/pip-audit
```

Dependabot opens weekly pull requests for newer pinned packages and GitHub Actions, once a release is a week old; CI tests each before you merge. Packages it excludes (see its config in `.github/`) are updated by hand together, then checked with `venv/bin/pip check`.
