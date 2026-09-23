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
| Function loading | Custom modules, public exports, duplicate definitions, imported helpers, import failures |
| Syncing | Developer files and config overrides, dependency merging, validation failures, file retirement, rollback, locking |
| Security | Read-runner restrictions, blob signing authorization, bounded upload reads, credential redaction |

Database calls are mocked. The tests exercise real builders and serializers but
do not execute SQL, verify PostgreSQL transaction semantics, or exercise full HTTP
requests. They do not load the application config or connect to configured
databases, Redis, or cloud services. Sync tests create disposable local Git
repositories and do not fetch the real Atom repository.
