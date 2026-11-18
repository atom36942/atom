# Atom agent guide
The rules for building on Atom, in short; each part links the doc with the detail: read it before working in that area. The same file in every project (synced, never edited there); a project's feature details and business rules go in `docs_extend/<feature>.md`. Read by AI agents: dense on purpose.

Three kinds of rule:
- **Enforced**: Atom fails (import, startup, sync, CI) when it is broken. Never work around one.
- **Rule**: not checked by code, always followed.
- **Default**: Atom's chosen way, already weighed. Follow it unless the project has a real reason, written in its `docs_extend/`.

Atom is a backend: its front-end parts are Defaults, so a project may build any page and keeps the shared flow where it fits. A new rule for every project is proposed to Atom (released, then synced), never kept in one project.

## Work
- Work autonomously; ask only for essential missing info or destructive actions outside the request.
- Before a project task: `python3 sync.py --status`; if Atom is behind, sync first ([sync.md](docs/sync.md)), then follow the latest rules. Bringing a project, or a folder of them, in line with Atom: [align.md](docs/align.md).
- Match surrounding code: naming, density, one-line statements, comments. Never expose `.env` values or credentials (key names only).
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
- Every route has a `config_api` entry: a unique `id` (a project's from 200), `is_token`; `/admin/*` needs role 1, `/permission/*` a permission, and every permission id a label in `config_column_int_mapping`.
- `func_*` names are unique across `function/` and `function_extend/`; `config_extend.py` has sections `# base`, `# atom`, `# extend` and only extends Atom's dicts (dropping an Atom route, table or code fails).
- Settings are typed: `config_is_<what>` is true or false, `config_schedule_script_<script>` a schedule; anything else stops startup.

Rules:
- Access is `config_api`'s job (the middleware runs it before the route): never re-check in a route; user id and role come only from `request.state.user`.
- Rows only through `func_check_table_permission` and `func_postgres_create/read/update/delete`; hand-written SQL only for what they can't express, values bound as `$1`, Postgres only through asyncpg.
- Reuse Atom's clients, pools and `func_*` helpers (search `function/` first); never a second pool or SDK client, never edit `main.py` (startup hook: `func_extend`).
- Users go through Atom's routes (`/admin/user-*`, `/my/user-*`, `/permission/user-*`): never a project user API ([auth.md](docs/auth.md)).
- Lists page after a cursor, never a total count; every CSV export goes through `func_<db>_export` ([crud.md](docs/crud.md)).
- Temporary files in `tmp/<feature>/`; data users change at runtime in the database; never placeholder or demo data.
- Security: secrets only in `.env`; no route returns more than its screen needs; values bound and escaped; nothing secret in a URL ([backend.md](docs/backend.md#security-rules-check-them-in-every-review)).

Defaults:
- Scale to 100× today's data: one SQL statement per screen read, an index for every filter and sort, aggregates in SQL, streamed exports, batched resumable scripts ([backend.md](docs/backend.md#scale-and-speed-defaults-a-project-keeps-working-at-100-todays-data)).
- Thin route in `router_extend/<f>.py` → logic in `function_extend/<f>.py` (`func_<f>_*`); files named after the feature in every folder ([extend.md](docs/extend.md)).
- Paths `/<feature>/<thing>-<verb>`; use Atom's generic routes (`/private/object-read`, `/my/object-*`) before writing one.
- Roles: 1 is Atom's admin; a project's users start at 2, each new kind takes the next number.
- Scripts: `# type`, `# command`, `# info`, then `# import`, `# config`, `# setting`, `# logic`, `# main` ([backend.md](docs/backend.md#scripts)).

## Front end ([frontend.md](docs/frontend.md))
Enforced:
- A page is `static_extend/<name>.html` or `static_extend/<name>/index.html`, served at `/page/<name>`; its other files at `/static/<path>`, linked by full path (Atom stamps `?v=`).

Rules:
- Each page is standalone: its own login and storage, every key named after it; logout clears all of it. Escape data before `innerHTML`.
- Keep the login alive with `/my/token-refresh`; a refused renewal shows the login form; a deactivated or deleted account is logged out with a plain message.

Defaults (one flow on every page, Atom's own included; the working code to copy is in `static/analytics.html`, the full example, and `static/monitor.html`, the smallest: their five `atom page` blocks go into a page unchanged, only `PAGE` and the page's own screens differ):
- Login with the page's one role (`/auth/login-username-password`), then `/my/profile`.
- Account menu (the avatar's initials): My profile, Login details, Sync, Settings, Logout. New needs grow inside them (Sync is the whole sync flow, Settings takes new settings); a sixth item only for a real account need. A page's own actions and features (Users included) are header buttons left of the avatar.
- Sync every 3 hours and from the menu: token, `/my/profile`, `/info` (labels and limits), the page's reference data in IndexedDB.
- Settings: Theme and Density; every colour and size a CSS variable; an app page starts light (`<html data-default-theme="light">`), Atom's own dark. One dialog, toast and password box style.
- Lists: cursor paging (Previous/Next), search on Enter, an export dialog up to `/info` `export_limit`.
- One page per app; a single `<name>.html` until it needs a folder.
- Screens: outlined header buttons, one filter row with Clear filters, one-column search on Enter, searchable dropdowns past 10 choices, chevron pager, tables that fit their width, one date format, frames that don't jump, actions shown to everyone with a toast saying why; the browser never downloads a growing table ([frontend.md](docs/frontend.md) (Screens; Scale and speed)).
- Up to 5 views as header tabs; from about 6, or grouped views, a left sidebar. Compact: 13px text, 36px controls, tight table cells. One palette, light by default, every colour a CSS variable with the hex codes in [frontend.md](docs/frontend.md) (Layout, size and colour).

## Optional features
Built only when an app needs them, each with its own doc: user management ([user-management.md](docs/user-management.md)), messaging, file storage, queues, schedules, Redis, ClickHouse and more (the list in [readme.md](readme.md)).

## Where the detail is
| Area | Doc |
| :--- | :--- |
| Backend rules in full (structure, `config_api`, data, settings, routes, users, scripts) | [backend.md](docs/backend.md) |
| Pages: login, account menu, sync, settings, dialogs, lists, export | [frontend.md](docs/frontend.md) |
| Auth, roles, permissions; user management | [auth.md](docs/auth.md), [user-management.md](docs/user-management.md) |
| Rows, paging, ownership, export | [crud.md](docs/crud.md), [ownership.md](docs/ownership.md) |
| Every setting; extending; syncing | [config.md](docs/config.md), [extend.md](docs/extend.md), [sync.md](docs/sync.md) |
| Bringing projects in line with Atom (a procedure, no rules) | [align.md](docs/align.md) |
| Why Atom is built this way | [about.md](docs/about.md) |

## Verify
- `venv/bin/python -m script.check` (Windows `venv\Scripts\`): startup checks, ruff, every page's JavaScript and every test, as CI runs it; a test name such as `tests_extend.test_invoice` runs just that.
- The check's last part, `standard Rules x/y, Defaults x/y`, reports what a project misses of the measurable Rules and Defaults (report only: it never fails the check); a Rule missed is fixed, a Default kept on purpose has its reason in `docs_extend/`.
- Database tests use a throwaway local database, never a shared or production one. Keep tests light: test the rules whose mistake gives wrong data without an error.
