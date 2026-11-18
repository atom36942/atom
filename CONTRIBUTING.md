# Contributing to Atom

Thanks for helping. Atom is a small framework with one line of history on `main`; these steps keep every project that syncs it working.

## Setup
```bash
git clone https://github.com/atom36942/atom.git
cd atom
python3.14 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
docker compose up -d                            # optional: Postgres (PostGIS), Redis, RabbitMQ for the integration tests
venv/bin/python -m script.check                 # startup checks, ruff, pages, tests
```
Windows: [docs/windows.md](docs/windows.md). Tests against real services: [tests/README.md](tests/README.md).

## Before a pull request
- Read [AGENTS.md](AGENTS.md): Atom's rules in short, each linking its doc ([backend](docs/backend.md), [front end](docs/frontend.md)). The design decisions in [docs/about.md](docs/about.md) stay unless the issue is about changing one.
- One focused change per pull request, with tests in `tests/` and the matching doc in `docs/` updated.
- `venv/bin/python -m script.check` passes.
- Raise `ATOM_VERSION` in `sync.py` by semver (major: projects must change code; minor: new feature; patch: fix), and add its dated entry at the top of [CHANGELOG.md](CHANGELOG.md) saying what changed and what projects must do (a major marked **Upgrade**). Don't tag or release by hand: CI creates the tag and GitHub Release once the tests pass.
- No personal or company data (names, emails, paths, secrets) in code, tests or docs.

## Issues
- Bugs and features: open an issue with the template.
- Security problems: never in an issue; see [SECURITY.md](SECURITY.md).

By contributing you agree your work is released under the [MIT License](LICENSE) and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
