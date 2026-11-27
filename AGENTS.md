# Atom agent guide
The rules for building on Atom, in short; each part links the doc with the detail: read it before working in that area. The same file in every project (synced, never edited there); a project's feature details and business rules go in `docs_extend/<feature>.md`. Read by AI agents: dense on purpose.

Three kinds of rule:
- **Enforced**: Atom fails when it is broken: at import or startup, in sync, or in `script.check` (run in [Verify](#verify), [Update](#update) and Atom's CI). Never work around one.
- **Rule**: always followed, but code can't check it (a reviewer or agent does, in [Update](#update)). A rule that code can check is Enforced instead.
- **Default**: Atom's chosen way, already weighed. Follow it unless the project has a real reason, written in its `docs_extend/`.

Atom is a backend. Its front end is how a page works with it (routes, login, storage, lists, export), as Defaults; the look is each project's own. Only how Atom serves pages and their route paths is enforced. A new rule for every project is proposed to Atom (released, then synced), never kept in one project.

## Work
- Work autonomously; ask only for essential missing info or destructive actions outside the request.
- Before a project task: `python3 sync.py --status`; if Atom is behind, follow [Update](#update) first.
- Match surrounding code: naming, density, one-line statements, comments. Never expose `.env` values or credentials (key names only).
- Every database and service in `.env` is real, usually production: never start the app or run a script with it. Project scripts are imported or tested with mocks, never run.
- Test on your own local run, invisible to the developer: everything it makes lives in your own folder `~/.atom/<project>/`, outside the project and never in it; the developer sees only the result. There: `local.env` with `config_postgres_url_master` of a throwaway local database (`createdb <project>_agent`, or the `postgis/postgis` Docker image; it needs `postgis`, `pg_trgm`, `btree_gin`), `config_root_user_password` and `config_token_secret_key` (random values), plus a throwaway local Redis, ClickHouse, ... only when a feature needs one, never `.env`'s ([config.md](docs/config.md#local-run)). Start it with `ATOM_ENV_FILE=~/.atom/<project>/local.env venv/bin/uvicorn main:app --port <free port>` (Atom then reads only that file; a free port leaves the developer's own server alone); startup creates the schema and `admin`; add test data through the admin APIs. Stop the server when done.
- Keep in `~/.atom/<project>/` whatever saves the next run from starting at zero: `local.env`, the `<project>_agent` database and its test data (with the script that seeds it), and `notes.md` (the Atom version last audited, what was changed, what was skipped and why, what to check next). Read it first in every run and keep it current; drop and rebuild anything that no longer matches the code. Never save `.env` values or production data there.
- One simple rule over exceptions; no backward-compat shims. Docs describe patterns (`<feature>.py`, `/page/<name>`), never specific file names.
- A framework change keeps Atom's design decisions ([about.md](docs/about.md), with the reason for each) unless the user asks to change one.

## Project structure (enforced: the core and `*_extend` split, which sync keeps; default: one feature name in every folder)
```
<project>/
├── config.py  main.py  sync.py  AGENTS.md  ...   Atom core: synced, never edited in a project
├── function/  router/  script/  static/  files/  docs/   Atom core folders (static/: Atom's own pages, the reference code)
├── config_extend.py         the project's settings: # base, # atom, # extend
├── router_extend/<f>.py     thin routes (router = APIRouter()), each with a config_api entry
├── function_extend/<f>.py   the logic: func_<f>_*, available as app_state.func_*
├── files_extend/            constants, param_specs, templates, prompts (read-only at runtime)
├── static_extend/<page>/    pages, served at /page/<page>
├── script_extend/<job>.py   jobs and workers
├── tests_extend/test_<f>.py tests (unittest)
├── docs_extend/<f>.md       the project's feature behaviour and business rules
├── tmp/                     generated files (gitignored)
└── .env                     secrets, URLs, machine flags (never committed)
```
One feature, one name in every folder (`<f>`); a big one splits into `<f>_<part>.py`. Detail: [backend.md](docs/backend.md#where-code-goes).

## Backend ([backend.md](docs/backend.md))
Enforced:
- Atom owns every unsuffixed path (`function/`, `router/`, `docs/`, `script/`, `static/`, `files/`, `config.py`, `main.py`, `sync.py`, `AGENTS.md`, ...); sync overwrites them. A project's code lives only in `*_extend` paths, `config_extend.py` and `.env`.
- Every route has a `config_api` entry: a unique `id` (a project's from 200) and `auth` (`[]`, `["jwt"]`, `["api_key"]` or both); `/admin/*` needs `user_check_permission` (the route's id in `users.permissions`; root holds every one), and every permission id a label in `config_column_int_mapping`.
- `func_*` names are unique across `function/` and `function_extend/`; `config_extend.py` has sections `# base`, `# atom`, `# extend` and only extends Atom's dicts (dropping an Atom route, table or code fails).
- Settings are typed: `config_is_<what>` is true or false, `config_schedule_script_<script>` a schedule; anything else stops startup.
- `script.check` fails on: a secret in code or docs (only in `.env`); Postgres through anything but asyncpg (`psycopg`, `sqlalchemy`); `.env` missing from `.gitignore`; a pool or SDK client opened in `function_extend/` or `router_extend/` (use Atom's; a script is its own process and may open its own); a role or permission check in `router_extend/` (`config_api` does it).

Rules:
- User id and role come only from `request.state.user`.
- Rows only through `func_check_table_permission` and `func_postgres_create/read/update/delete`; hand-written SQL only for what they can't express, values bound as `$1`, Postgres only through asyncpg.
- Reuse Atom's `func_*` helpers (search `function/` first); never edit `main.py` (startup hook: `func_extend`).
- Users go through Atom's routes (`/admin/user-*`, `/my/user-*`): never a project user API ([auth.md](docs/auth.md)).
- `users.permissions` holds only route ids; any other access (which rows a user sees: countries, companies) is its own admin-only `users` column read on each request ([auth-permission.md](docs/auth-permission.md)).
- Scripts and other systems call the API with an API key (`Authorization: Bearer atk_...`, a service account's key, on routes whose `auth` has `"api_key"`), never a person's password or a shared login ([auth.md](docs/auth-api-key.md)).
- Another system that must know when something happens gets a webhook (`func_webhook_send` in the change's transaction, [webhook.md](docs/webhook.md)), never a loop of its own calling it. A route another service calls takes `webhook_verify` (its scheme in `config_webhook_verify_scheme`), never signature code in the route.
- Lists page after a cursor, never a total count; every CSV export goes through `func_<db>_export` ([crud.md](docs/crud.md)).
- Temporary files in `tmp/<feature>/`; data users change at runtime in the database; never placeholder or demo data.
- Security: no route returns more than its screen needs; values bound and escaped; nothing secret in a URL ([backend.md](docs/backend.md#security-rules-check-them-in-every-review)).

Defaults:
- Scale to 100× today's data: one SQL statement per screen read, an index for every filter and sort, aggregates in SQL, streamed exports, batched resumable scripts ([backend.md](docs/backend.md#scale-and-speed-defaults-a-project-keeps-working-at-100-todays-data)).
- Thin route in `router_extend/<f>.py` → logic in `function_extend/<f>.py` (`func_<f>_*`); files named after the feature in every folder ([extend.md](docs/extend.md)).
- Paths `/<feature>/<thing>-<verb>`; use Atom's generic routes (`/private/object-read`, `/my/object-*`, and the admin object routes granted by id for selected users' create, read, update, delete on any table) before writing one ([auth-permission.md](docs/auth-permission.md#admin-routes-one-id-each)).
- Roles: 1 is Atom's admin; a project's users start at 2, each new kind takes the next number.
- Scripts: `# type`, `# command`, `# info`, then `# import`, `# config`, `# setting`, `# logic`, `# main` ([backend.md](docs/backend.md#scripts)).
- Postgres is the base: background work that must not be lost goes on Atom's Postgres queue (`?queue=postgres`, `script.consumer_postgres`); Redis, RabbitMQ, Kafka or Celery only when Postgres can't keep up ([queue.md](docs/queue.md)).

## Front end ([frontend.md](docs/frontend.md))
Atom is a backend: a page's look, layout, words and build are the project's own (a family of apps keeps its shared look in its `docs_extend/`). Atom sets only how a page works with it.

Enforced:
- A page is `static_extend/<name>.html` or `static_extend/<name>/index.html`, served at `/page/<name>`; its other files at `/static/<path>`, linked by full path (Atom stamps `?v=`).
- A page calls Atom's and the project's routes by their full `config_api` path, written whole: values only after `?`, or as `${...}` where the route has `{name}`. `config_api` is the source of truth: when a route is renamed or removed, the page changes to the new path in `CHANGELOG.md`, never `config_api` to suit the page.

Defaults (the working code: `static/analytics.html`, the full flow, and `static/monitor.html`, the smallest; copy it or write your own):
- Escape data before `innerHTML`; nothing secret in a URL; hiding a button is not access control (`config_api` refuses).
- Each page is standalone: one localStorage key and one IndexedDB database named after it; logout clears both, in every tab.
- Login with the page's one role (`/auth/login-username-password`), then `/my/profile` and its user check; renew with `/my/token-refresh` before expiry; a refused renewal or a deactivated or deleted account logs out with a plain message.
- Labels and limits from `/info` (`config_column_int_mapping`, `export_limit`), never written in the page; reference data refreshed on a timer and on request.
- Lists page after a cursor with no total count; search asks the server; export streams from `/<feature>/export` up to `export_limit`; counts and totals in SQL: the browser never downloads a table that grows.
- One page per app; pages share no CSS or JS files; no script or style from another site; a viewport meta tag.

## Optional features
Built only when an app needs them, each with its own doc: user management ([user-management.md](docs/user-management.md)), messaging, file storage, queues, schedules, Redis, ClickHouse and more (the list in [readme.md](readme.md)).

## Where the detail is
| Area | Doc |
| :--- | :--- |
| Backend rules in full (structure, `config_api`, data, settings, routes, users, scripts) | [backend.md](docs/backend.md) |
| Pages: login and token, storage, lists, export, reference code | [frontend.md](docs/frontend.md) |
| Auth, roles, permissions, API keys, 2FA, single sign-on; user management | [auth.md](docs/auth.md) and its `auth-*.md`, [user-management.md](docs/user-management.md) |
| Rows, paging, ownership, export | [crud.md](docs/crud.md), [ownership.md](docs/ownership.md) |
| Every setting; extending; syncing | [config.md](docs/config.md), [extend.md](docs/extend.md), [sync.md](docs/sync.md) |
| Why Atom is built this way | [about.md](docs/about.md) |

## Verify
- `venv/bin/python -m script.check` (Windows `venv\Scripts\`): startup checks, ruff, the Enforced code rules, every `app_state.func_*` the project calls still defined and every route its pages call still in `config_api` (a renamed Atom function or route fails here, not in production), every page's JavaScript and every test, as CI runs it; a test name such as `tests_extend.test_invoice` runs just that.
- A failing check is fixed at its cause, in the project's code: never skip, weaken or delete a test, add `# noqa` or a mock only to pass, edit Atom's core, or change `config_api` to suit a page. A fix that needs Atom is proposed to Atom.
- The check's `rules` step fails on any Enforced rule the project's code breaks. Its last part, `standard Defaults x/y`, reports which measurable Defaults the project doesn't follow (report only: it never fails the check); a Default kept on purpose has its reason in `docs_extend/`.
- Database tests use a throwaway local database, never a shared or production one. Keep tests light: test the rules whose mistake gives wrong data without an error.

## Update
Two parts: `python3 sync.py` replaces Atom's files exactly (the shared core); then the AI agent brings the project's own code in line with the rules above. Started with `Update this repo to the latest Atom: follow Update in AGENTS.md` (or `each Atom-based repo of this folder`); sync prints that line too.
1. **Repos.** `./CLAUDE.md` first: it says what may change and how, and wins over this. A repo is Atom-based when it has `sync.py`, `config_extend.py` and `*_extend` folders. Show the list and wait for the OK; then one repo at a time:
2. **Sync.** With a clean `git status` (else stop and ask) and the app stopped, `python3 sync.py` outside the venv ([sync.md](docs/sync.md)); follow every **Upgrade** note in `CHANGELOG.md` between the versions sync printed (`Atom old -> new`); `script.check` passes.
3. **Audit**, from the check's `standard` lines, then every rule above and the docs it links, for the areas the repo has:
   - Structure: right `*_extend` folder, one feature name, no edited core file, generated files only in `tmp/`.
   - Security: secrets outside `.env` (also `git log -p`; a leaked key is reported for rotation), route access, responses wider than their screen, SQL built from strings, unescaped HTML, tokens or personal data in URLs or logs.
   - Speed and scale: a filter, sort or search without an index, one query per item, totals counted in the browser, tables downloaded whole, exports not streamed, caches without a limit; with database access, from the evidence too: `/admin/monitor` (database view) lists each table's sequential vs index scans and the slowest queries.
   - Pages: against [frontend.md](docs/frontend.md) and the project's own `docs_extend/` look; at phone width.
   - Clean-up: dead code, unused files, CSS and settings, duplicate helpers, `docs_extend/` out of date, missing tests for rules that fail silently.
4. **Propose** a table (area, now, the rule, its tier, the fix) and wait for the OK. A missed Rule is fixed; a Default is a suggestion: one kept on purpose gets its reason in `docs_extend/`, a risky change to a working page is optional.
5. **Refactor and verify.** Project files only (never Atom's core, `.env` values or data); the check passes; click through every page on the local run; report what changed and what was skipped. Commit or push only when asked or `CLAUDE.md` allows. A later run reads `notes.md` and proposes only what drifted.
