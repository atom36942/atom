# Changelog

Every Atom release with notes, newest first. Versions follow [semver](https://semver.org): **major** when projects must change their code or commands (its entry says what to change), **minor** for new features, **patch** for fixes. The version lives in `ATOM_VERSION` in `sync.py`; each one is a git tag `vX.Y.Z` and a GitHub Release, created by CI once its tests pass. Versions not listed here (before 7.0.0, and minor or patch releases between notes) have no notes beyond their commits.

Pin or roll back a project to a version: `python3 sync.py --ref v15.6.1` ([docs/sync.md](docs/sync.md)).

## [18.11.0] - 2026-11-21

- **Tickets' detail works like Pulse's task detail** (its code went out with the 18.10.0 commit; noted here): the header buttons in Pulse's order (Edit, Delete, Copy link, Duplicate, Refresh, Close); **Edit ticket** opens over the detail in the Add ticket layout, with Status too, and saves only what changed (ticket update, 121); **Copy link** copies `/page/ticket?ticket_id=<id>`, which opens only that ticket; **Duplicate** opens Add ticket filled from the ticket; "Created at" and "Updated at", a line under the description's title, "-" for an empty description, and the toast "Ticket ID copied".
- **Avatar spacing:** in Atom's pages the avatar sits 16px from the header's last button, as in the apps.

## [18.10.0] - 2026-11-21

- **`/info` says whether 2FA is available:** `is_totp_enabled` is `true` when the app has `config_totp_encryption_key`, so a page shows its Two-factor row only where it can work; the user's own state stays `totp_enabled_at` in `/my/profile` ([docs/auth.md](docs/auth.md#what-a-page-reads)).

## [18.9.0] - 2026-11-21

- **Two-factor authentication (TOTP), optional per user:** a user turns it on with `/my/totp-setup` (secret and `otpauth://` link for the QR code) and `/my/totp-enable` (a code from any authenticator app; returns 10 one-time recovery codes once), and off with `/my/totp-disable` (a code). Every `/auth/login-*` then answers `{"mfa_required": true, "mfa_token"}` instead of tokens, and the new `/auth/login-totp` (`mfa_token` and a code or recovery code, 5 tries a minute) gives the tokens; users without 2FA log in exactly as before. New `users` columns `totp_secret` (AES-GCM encrypted, bound to the user), `totp_enabled_at`, `totp_last_step` (a code works once) and `totp_recovery` (hashed); an admin resets a user with `/admin/user-update {"totp_enabled_at": null}`. Off for the app until `config_totp_encryption_key` is set in `.env`; `config_totp_issuer` names the app in the authenticator. Backend only: pages don't show the code step yet. `cryptography` is now pinned in `requirements.txt` ([docs/auth.md](docs/auth.md#8-two-factor-authentication-totp)).
- **`config.py` in standard sections:** settings are grouped by area (app, cors, database, postgres, mssql, query, cache, auth, api_key, otp, totp, profile, log_api, schedule, retention, queue, webhook, blob, email, mobile, ai, aws, azure, msgraph, sftp, monitoring, table, permission, column), then the column dicts, `# schema` (`config_postgres`) and `# api` (`config_api`). Only order and headers changed; every setting keeps its name and value.

## [18.8.1] - 2026-11-21

- **Permissions ✓ looks clickable:** a small bordered button like the copy and edit buttons beside it, with a hover state.

## [18.8.0] - 2026-11-21

- **Permissions at a glance:** Login details in Atom's pages shows Permissions as a ✓ when the user holds any and a ✗ when none; a click on the ✓ opens a small dialog over it with a table of each permission's ID and Name (from `/info` `config_column_int_mapping.users.permissions`, `-` without one).

## [18.7.2] - 2026-11-21

- **Row lists like the apps':** Login details, My profile, Sync and every `Page.kv` dialog in Atom's pages are now a bordered list of rows, an icon and label on the left and the value (with its copy or edit button) on the right, one line between rows, no shaded label column: the same design as the apps built on Atom.

## [18.7.1] - 2026-11-21

- **Key-value rows right-aligned:** in Atom's pages (Login details, My profile and every `Page.kv` dialog) the value and its copy or edit button sit at the right of the row, as in the apps built on Atom.

## [18.7.0] - 2026-11-21

- **Front end: the backend contract only.** `AGENTS.md`, `docs/frontend.md` and `docs/user-management.md` now say only how a page works with Atom: the routes it calls, the login and token flow, storage named after the page, labels and limits from `/info`, cursor lists, streamed export and scale, plus Atom's own pages as reference code. The look and layout (account menu items and order, Settings, toasts, dialogs, palette, sizes, header and navigation, words, User management's columns and menus) are each project's own, kept in its `docs_extend/`. `script.check`'s standard no longer scores the account menu, Settings or CSS variables (9 Defaults, was 12). No project change needed.

## [18.6.1] - 2026-11-21

- **Steadier queue test:** the Redis killed-consumer test waits for the job to leave `<channel>_processing` instead of checking the instant the job reports done, so CI no longer fails on that timing.

## [18.6.0] - 2026-11-21

- **Incoming webhook verification:** a route another service calls (Stripe, GitHub, Razorpay, another Atom app) takes `"webhook_verify": {"scheme": "stripe", "secret": "config_webhook_secret_stripe"}` with `"auth": []` in its `config_api` entry; the middleware checks the HMAC-SHA256 signature of the raw body and the timestamp (`config_webhook_verify_tolerance_sec`, 300) before the route runs, answers 401 to a missing, forged or replayed call, gives the route `request.state.webhook`, and replays the body so the route reads it as usual. Schemes are data, not code: `config_webhook_verify_scheme` ships `standard` (Standard Webhooks, so Atom apps receive each other's webhooks), `stripe`, `github`, `shopify` and `razorpay`, and a project adds a provider with one dict (header, prefix or key, encoding, signed bytes, timestamp and id), checked at startup. OpenAPI adds `x-webhook-verify` ([docs/webhook.md](docs/webhook.md#incoming)).

## [18.5.1] - 2026-11-21

- **Webhook tests hold no secret-shaped string:** the integration tests make their signing secret per run, and the unit test's Standard Webhooks spec vector (public, not a key) is split, so GitHub secret scanning no longer reports it as a Stripe webhook secret.

## [18.5.0] - 2026-11-21

- **Outgoing webhooks:** Atom tells other systems when something happens, with a signed POST in the [Standard Webhooks](https://www.standardwebhooks.com) format (`webhook-id`, `webhook-timestamp`, `webhook-signature: v1,<HMAC-SHA256>`). An admin subscribes a URL to events with the new route `/admin/webhook-create` (it returns the `whsec_` signing secret once); a project's code calls `app_state.func_webhook_send(client_postgres=conn, event="shipment.delivered", data={...})`, which queues one delivery per active subscriber as a `queue_job` row on channel `channel_webhook`, in the caller's transaction (a rollback sends nothing). With `config_webhook_is_active` on (off by default), each app worker delivers them (`FOR UPDATE SKIP LOCKED`, never twice at once), retries a failure after 60 s doubled each time, and keeps it as failed with its error after 8 retries (`config_webhook_timeout_sec`, `config_webhook_retry_max`, `config_webhook_retry_wait_sec`, `config_webhook_poll_sec`). New table `webhook`; the URL must be `https` to a public address, checked at creation and before every delivery; `secret` joins `config_column_read_blocked`. Webhooks are listed, paused and deleted through the generic admin routes ([docs/webhook.md](docs/webhook.md)).

## [18.4.0] - 2026-11-21

- **Ticket statuses for support:** New, In Progress, Blocked (stuck inside the company), Waiting (on the customer), Done. Only the labels of 1 (was To Do) and 4 (was Review) change; codes, colours and `closed_at` on Done stay, so no data changes.

## [18.3.1] - 2026-11-20

- **Tickets page:** Add ticket's fields have no placeholders and no Markdown hint, as in Pulse's Add task (formatting still shows in the ticket).

## [18.3.0] - 2026-11-20

- **Login details in two groups, with the ID:** the account menu's Login details now shows **Sign in** (Username with copy, Password with its pencil) and **Account** (ID, the `users` id User management shows, with a copy button and the toast "ID copied"; Role; Permissions), each a small caption (`.kv-group`) over its own row list, on every Atom page with a login. A suggestion for a project's pages too ([docs/frontend.md](docs/frontend.md#header-and-account)).

## [18.2.0] - 2026-11-20

- **Honeypot on public create:** `/public/object-create` refuses a row whose hidden `website` field has a value (only bots fill it) and drops the field when empty (`config_public_create_honeypot`, `None` turns it off). A project's public form adds the hidden field ([docs/crud.md](docs/crud.md#tickets-a-small-support-desk-in-every-project)).
- **Ticket statuses as in Pulse:** To Do, In Progress, Blocked, Review, Done (from Open, In Progress, Closed). `closed_at` is now set when a ticket becomes Done (5). A project with tickets moves its Closed ones (3) to Done before or right after syncing: `UPDATE ticket SET status = 5 WHERE status = 3` (inside a transaction with `ALTER TABLE ticket DISABLE TRIGGER ticket_closed_at` and `ENABLE` after, to keep their `closed_at`).
- **Add ticket is the customer's ticket:** the Tickets page's Add ticket now sends `/public/object-create` without the agent's token, so `created_by_id` stays empty and the ticket shows as Public, like one from the customer's form (before, it carried the agent's id and read as "Logged in (agent)"). The form, laid out like Pulse's Add task (a card for the title and description, a card for type, priority and the customer's contact), says so in its header, needs an email or mobile to reply to, and opens the new ticket.

## [18.1.1] - 2026-11-20

- **Tickets board on one row:** every status column stays side by side at any width (at least 200px each); a narrow screen scrolls the board sideways instead of stacking the columns.

## [18.1.0] - 2026-11-20

- **Tickets, a small support desk:** customers send tickets from a project's form (`/my/object-create` logged in, `/public/object-create` without a login), with their `name`, `email` and `mobile` kept on the ticket; `ticket` gets `priority` (Low, Normal, High), `closed_at` (set by a trigger when the status becomes Closed) and three statuses, Open, In Progress, Closed (from 18.0.0's five; no project had tickets yet). The 18.0.0 column `reply` is no longer used (Atom keeps columns it doesn't manage; it stays empty) ([docs/crud.md](docs/crud.md#tickets-a-small-support-desk-in-every-project)).
- **Ticket comments:** a new table `ticket_comment`, the team's notes on a ticket in Markdown, with its own permissions (create 123, read 124, update 125 and delete 126 anyone's; an author edits and deletes their own through `/my`); deleting a ticket deletes its comments. `/my/object-create` refuses `ticket_comment`.
- **The Tickets page, in the apps' look:** a board (Open, In Progress, Closed; drag a card to change its status) or a table, filters (status, priority, type, source, created) and a search (title, name, email, mobile, ID), the ticket detail with the contact and the comments, Add ticket, CSV export. Ticket read (120) opens it: any other user is told "Tickets access is unavailable.". Built for millions of tickets: one statement for the board's first pages, cursor paging everywhere, no counts, an index for every filter and search.
- **`/permission/object-read` reads a board:** `group_column` and `group_values` (the first page of each value in one statement), as `/private/object-read`.

## [18.0.0] - 2026-11-20

**Upgrade (projects must change):** `config_permission_table_write_allowed` is replaced by `config_permission_table`, one permission id per table and action: `config_permission_table_write_allowed = ["task"]` becomes `config_permission_table = {**base_config_permission_table, "task": {"update": 211, "delete": 212}}` (`from config import config_permission_table as base_config_permission_table`), each id labelled in `config_column_int_mapping["users"]["permissions"]`, from 200 and used by no route. Permissions 59 and 60 grant nothing any more: move each user holding them to the new ids (`/admin/user-update`, `permissions`), and drop 59 and 60 from every user (they are no longer labelled, so an update that keeps them is refused). `/permission/object-delete` takes `table` in the query (`?table=task`, body `{"ids": [...]}`). Startup names the old setting.

- **Object permissions per table and action:** `/permission/object-create`, `/permission/object-read`, `/permission/object-read-export` (new), `/permission/object-update` and `/permission/object-delete` check `config_permission_table[table][action]` in the middleware: a user may read tickets without deleting them, or edit one table without another. A table or action not in the map is refused. Startup refuses an unknown action, `users` in the map, an id used twice, used by a route or without a label ([docs/auth.md](docs/auth.md#object-permissions-one-id-per-table-and-action)).
- **Root holds every admin and permission flow:** at each startup root gets every `/admin/*` and `/permission/*` route id with a permission check (86, 61, 62) and every `config_permission_table` id, Atom's and the project's, exactly that list. A project's other permission routes stay for the users it grants.
- **Tickets:** a new Atom table `ticket` (`type` Support, Feedback, Bug; `status` To Do, In Progress, Blocked, Review, Done; `title`, `description`, `email`, `reply`), created from any page with `/my/object-create` or, without login, `/public/object-create` (now rate limited, 10 a minute per caller). The support team works them on the new page `/page/ticket` (any role, with read 120, update 121, delete 122; light, in the apps' navy look): filters, status and reply, delete, CSV export ([docs/crud.md](docs/crud.md#tickets-a-small-support-desk-in-every-project)).

## [17.0.0] - 2026-11-20

**Upgrade (projects must change):** `config_api` entries take `auth` instead of `is_token` (and the 16.9.0 `is_api_key`), in `config_extend.py`: `"is_token": True` → `"auth": ["jwt"]`, `"is_token": False` → `"auth": []`, `"is_api_key": True` → add `"api_key"` (`["jwt", "api_key"]`, or `["api_key"]` for machines only). Startup names any entry still using the old keys. A client sending an API key as `Authorization: ApiKey atk_...` sends `Authorization: Bearer atk_...`.

- **`auth`, one list per route:** the credentials a route accepts, as OpenAPI's per-route security does: `[]` public, `["jwt"]` a JWT access token (people), `["api_key"]` an API key (machines), `["jwt", "api_key"]` either. It replaces the two flags `is_token` and `is_api_key`, so no meaningless mix is possible and a machine-only route can refuse a person's login. A role, permission or user check needs a non-empty `auth` (startup refuses it otherwise; before, it switched the token on silently). A credential the route does not list is 401 (`jwt not allowed on this route`, `api_key not allowed on this route`); none is `authorization missing`. `func_middleware_check_token` is now `func_middleware_check_auth`; `/openapi.json` adds `x-auth` per route.
- **API keys are sent as `Authorization: Bearer atk_...`**, the standard header (GitHub, Stripe, OpenAI); the `atk_` prefix tells a key from a JWT (which starts `eyJ`).
- **API keys use the generic routes:** list keys with `/my/object-read?table=api_key` and revoke them with `/my/object-delete` (or `/admin/object-read`, `/admin/object-delete` for any user's); `/my/api-key-read`, `/my/api-key-delete` and `/admin/api-key-delete` from 16.9.0 are gone, and `/my/api-key-create` is the only key route. The database refuses every `UPDATE` of `api_key` (`table_row_update_disable`), so a key is never edited, and `last_used_at` is dropped (a key's requests are in `log_api` under its owner). `key_hash` joins `config_column_read_blocked`.
- **Docs:** the standard terms (API key, service account, scopes, revocation, rotation) and a partner system sending data through a project route with `"auth": ["api_key"]` ([docs/auth.md](docs/auth.md#7-api-keys-machine-access)).

## [16.9.0] - 2026-11-20

- **API keys:** scripts and other systems call the API with `Authorization: ApiKey atk_...` instead of a password login. A key is an opaque random string (not a JWT) owned by the user who created it, stored only as its sha256 in the new table `api_key`, and resolved in the middleware to the owner's `request.state.user` (cached per worker for `config_api_key_cache_sec`, 60 s), so role, permission and ownership checks work unchanged. A route accepts keys only with `"is_api_key": True` in its `config_api` entry (none by default); a key may be limited to `scopes` (paths) and `expire_days`. New routes `/my/api-key-create`, `/my/api-key-read`, `/my/api-key-delete`, `/admin/api-key-delete`; new settings `config_api_key_max` (20 keys per user) and `config_api_key_cache_sec`. An unknown or expired key, or a deleted or deactivated owner, is 401 ([docs/auth.md](docs/auth.md#7-api-keys-machine-access)).

## [16.8.2] - 2026-11-19

- **Shorter placeholders:** the API page's cURL box ("Paste cURL…"), the message box ("Type a message…") and pgweb's saved-connection search ("Search…").

## [16.8.1] - 2026-11-19

- **API page:** a boolean field (in a query, form or JSON body) is a true/false list instead of a text box, and a JSON row switched to `bool` gets the same list; a response object's key/value table gives its values the full width, with the expand button at the right.

## [16.8.0] - 2026-11-19

- **Redis keys start with the app's name:** every response-cache, user-state and rate-limit key now starts with the app's master database name (`finance:cache:api:...`, `pulse:ratelimiter:...`), so apps sharing one Redis never read each other's keys; nothing to set. Old unprefixed keys are no longer read and expire on their own (the first requests after the update miss the cache once). Queue channels are unchanged: each app keeps its own `config_redis_url_queue`. Monitor's Redis tab shows the app's prefix ([docs/redis.md](docs/redis.md)).

## [16.7.0] - 2026-11-19

- **Postgres queue, the default:** background jobs need no broker. `?queue=postgres` on `/my/object-create` and `/my/object-update` (or `app_state.func_producer(queue="postgres", client_postgres=...)`) adds a row to the new table `queue_job` and returns its id; `venv/bin/python -m script.consumer_postgres <channel>` runs it. Jobs are taken with `FOR UPDATE SKIP LOCKED` inside a transaction held until the job is finished, so several consumers can share a channel and a killed one leaves nothing stuck; `LISTEN/NOTIFY` wakes consumers at once; retries wait in `run_at`; a job failed after `config_queue_retry_max` retries stays with `status` 2 and its error. Redis, RabbitMQ, Kafka and Celery are unchanged ([docs/queue.md](docs/queue.md)).
- **Rules are checked by code:** `script.check` has a `rules` step that fails a project on: a secret in code or docs, Postgres through anything but asyncpg, `.env` missing from `.gitignore`, a pool or SDK client opened in `function_extend/` or `router_extend/` (scripts may open their own), a role or permission check in `router_extend/` (`config_api` does it). Each break is named with its file and line. The report-only score is now `standard Defaults x/y` (no Rules part).
- **Front end is Defaults only:** `AGENTS.md` and `docs/frontend.md` say plainly that every front-end point is a suggestion a page may follow or not; the two former front-end Rules (standalone page storage and escaping, keeping the login alive) are Defaults. Only how Atom serves pages and the route paths they call stay enforced.

## [16.6.0] - 2026-11-19

- **Monitor: Redis tab:** `/page/monitor` has a Redis tab (`GET /admin/monitor?view=redis`) with one block per `config_redis_url_<name>`, headed by its key name and URL: ping from the server, memory and its limit, keys, hit ratio, ops per second, clients, evictions, eviction policy, version and uptime; read-only, an unreachable one shows its error, and none configured says so ([docs/admin.md](docs/admin.md)).
- **`config_postgres_storage_gb` removed:** Monitor shows only what the servers report. The upgrade check's Disk signal becomes **Data size** (size and growth, marked Info, never an upgrade), since PostgreSQL can't see the disk size; a project that set the key can drop it from `.env` (it is ignored).

## [16.5.3] - 2026-11-19

- **AGENTS.md: agents reuse their work:** the agent's local run lives in its own folder `~/.atom/<project>/` (outside the project, so the developer never sees it), kept between runs instead of removed: `local.env`, the `<project>_agent` database with its test data and seed script, and `notes.md` (Atom version last audited, what changed, what was skipped and why, what to check next). Every run reads it first and keeps it current; anything that no longer matches the code is rebuilt; no `.env` values or production data. Update's later run reads `notes.md` to propose only what drifted.

## [16.5.2] - 2026-11-19

- **AGENTS.md local run is invisible to the developer:** the agent keeps `local.env` and everything its run makes in its own scratch folder outside the project (its scratchpad, else a temporary folder), never in the project's `tmp/`; it names its databases and containers `<project>_agent` (never a developer's own `_local` one), starts the app on a free port with `uvicorn`, and removes it all when done; the developer sees only the result.

## [16.5.1] - 2026-11-19

- **AGENTS.md local run:** a feature that needs another service (Redis, ClickHouse, RabbitMQ, ...) also gets a throwaway local one in `tmp/local.env`, never `.env`'s; everything the run makes stays in `tmp/`, local databases and containers are named `<project>_local` and removed when done ([docs/config.md](docs/config.md#local-run)).

## [16.5.0] - 2026-11-19

- **Local run on a throwaway database:** `ATOM_ENV_FILE=tmp/local.env venv/bin/python main.py` makes the app and Atom's scripts read that file instead of `.env`, so a local run never reaches `.env`'s real databases and services; a name that is not a file stops startup. Three keys are enough: `config_postgres_url_master` of a throwaway local database, `config_root_user_password`, `config_token_secret_key` ([docs/config.md](docs/config.md#local-run)). A script's `# config` now reads `load_dotenv(os.environ.get("ATOM_ENV_FILE", ".env"))`; a project script may switch to the same line.
- **AGENTS.md:** an agent never starts the app or runs a script with `.env`; it runs the app on the local run above and clicks through pages there. This replaces 16.4.1's "back up first", which did not work for large databases.

## [16.4.1] - 2026-11-19

- **AGENTS.md for agents working alone:** Enforced now names `script.check` with import, startup and sync; Work says every database and service in `.env` is real (starting the app applies schema changes to it; never run a script to see if it starts); Verify says a failing check is fixed at its cause, never by skipping or weakening a test, `# noqa`, editing Atom's core or changing `config_api` to suit a page.

## [16.4.0] - 2026-11-19

- **AI query routes run read-only:** `/admin/postgres-query-generator-ai` is now `/admin/postgres-query-ai` and `/admin/clickhouse-query-generator-ai` is now `/admin/clickhouse-query-ai` (same `config_api` ids; functions `func_postgres_query_ai`, `func_clickhouse_query_ai`). New body param `execute` (default `false`): with `true` the generated SQL also runs through the read runner (read-only transaction or `readonly=1`, 30 s timeout, row limit) and the response adds `rows`. A caller of the old path switches to the new one ([docs/database.md](docs/database.md)).
- **`script.check` routes step:** in a project, every quoted path in `static_extend/` pages and `.js` files that starts like a `config_api` route (`/admin`, `/my`, `/auth`, the project's own `/<feature>`, ...) must be a `config_api` route; `${...}` counts as one route value, anything after `?` or `#` is ignored, `/static/` files and third-party URLs are not checked. A route Atom renames or removes now fails the check after sync with the page, line and path, instead of failing in production. AGENTS.md (Front end) says how to fix it: change the page, never `config_api`.

## [16.3.1] - 2026-11-19

- **`config.py` sections:** the one `# integration` section is split by kind of service into `# database`, `# queue`, `# cloud` (aws, azure, msgraph, sftp), `# messaging`, `# ai` and `# monitoring`; `config_google_login_client_id` moves to `# auth`. Keys and defaults are unchanged; [docs/config.md](docs/config.md) splits its Integrations table the same way.

## [16.3.0] - 2026-11-18

- **`script.check` names step:** in a project, every `app_state.func_*` its code calls (`function_extend`, `router_extend`, `script_extend`, `files_extend`, `config_extend.py`) must be defined in Atom or the project; an unknown name fails the check with its file and line, so a function Atom renamed or removed fails in the check after sync instead of on that route in production.
- **pgweb filter:** `LIKE`/`ILIKE` without a `%` in the value now search for it anywhere (`adm` finds `admin`; before it matched only the whole value), and they are offered on every column type (numbers, dates, uuid, json, arrays, enums), compared as text.
- **AGENTS.md Update:** the speed audit also reads the evidence in `/admin/monitor` (each table's sequential vs index scans, the slowest queries) when the agent has database access.

## [16.2.0] - 2026-11-18

- **Index sort order:** a btree index column may name its order, `"btree(score desc nulls last,id)"`, so a list sorted `score desc nulls last, id` reads in index order instead of sorting the whole table; startup refuses an unknown order or one on another index type.
- **`config_column_private_read_blocked`:** per table, the columns `/private/*` reads (object-read, its export, groupby, distinct) may not select, filter, sort or group by. Atom blocks `script_run`'s `started_by`, `host`, `step`, `message` and `peak_memory_mb`, so any user may read the run list but not the server details. A project that read those through `/private/*` reads them through `/admin/*` instead.
- **readme:** an Update section: step 1 `python3 sync.py` (Atom's core), step 2 the prompt that brings the project's own code in line with `AGENTS.md`.

## [16.1.0] - 2026-11-18

Updating a project is two steps: `python3 sync.py` (Atom's files, exactly) and one prompt, `Update this repo to the latest Atom: follow Update in AGENTS.md`, which sync now prints at the end. `docs/align.md` moved into `AGENTS.md` as its **Update** section (sync removes the old file), so the rules and how to apply them are in one file. Nothing to change in projects.

## [16.0.1] - 2026-11-18

Account menu rule clarified in `AGENTS.md` and `docs/frontend.md`: the five items stay; new needs grow inside them (Sync is the whole sync flow, Settings takes new settings, My profile new profile fields), a sixth item only for a real account need; a page's actions and features, Users included, are header buttons left of the avatar. Nothing to change in projects.

## [16.0.0] - 2026-11-18

**Upgrade (projects must change):** `config_api` ids are renumbered 1, 2, 3, … in route order (a project's own routes stay at 200 and up). The permission routes are now `/permission/object-update` 59, `/permission/object-delete` 60, `/permission/user-create` 61, `/permission/user-update` 62, and the Postgres query runner write 86 (was 136, 137, 138, 139 and 6). In each project: change these ids in its pages and docs (for example a page's create and update permission constants), and in `users.permissions` replace the old ids with the new ones (back up first; root gets its `/admin` ids again at startup).

- **Rules for every project:** `AGENTS.md` is shorter and the source of truth, each rule marked Enforced, Rule or Default, with the project structure; the detail moves to `docs/backend.md` (structure, data, settings, routes, scripts, scale and speed, security) and `docs/frontend.md` (replaces `docs/page.md`: login, the 5-item account menu, sync, settings, screens, layout, size and colour, scale), with user management in its own `docs/user-management.md`. Atom is a backend: front-end parts are Defaults.
- **`docs/align.md`:** one procedure for an AI agent to bring a project, or a folder of them, up to the latest Atom and in line with `AGENTS.md`, auditing structure, security, speed and scale, pages and clean-up in one run.
- **`script.check` standard score:** in a project, the summary line ends with `standard Rules x/y, Defaults x/y` and lists what is missed (secrets in code, asyncpg only, `.env` ignored, feature files, page login flow, account menu, sync, settings, export, no outside scripts, viewport, CSS variables). Report only: it never fails the check.
- **Page theme default:** the theme block reads `<html data-default-theme>`; an app page starts light, Atom's own pages stay dark.
- **PgWeb:** a field modal of one size for every type, editing by type (JSON editor, array item rows, true/false, date and date-time pickers, `users.password` hashed); a compact Add row form with the columns set later folded; filters on the Columns, Indexes and Constraints tabs with a Reset; every download asks first and says what it holds; the row panel shows `table.key` with a copy icon and downloads the row vertically; the query runner reports a write's status, and Explain refuses a script.

## [15.8.0] - 2026-11-17

Monitor, Analytics and PgWeb get clearer, shorter and more consistent; Monitor gains a database upgrade check. Nothing to change in projects; set `config_postgres_storage_gb` to use the disk part of the check.

- **Monitor, Database tab: upgrade check.** One verdict (no upgrade needed, keep an eye on it, upgrade recommended) from the server's own counters: disk (how full, and when it fills, with the new optional `config_postgres_storage_gb`), connections, memory (reads served from RAM), work memory (spills to disk), write load (WAL per checkpoint interval against `max_wal_size`) and deadlocks; an upgrade lists what to ask DevOps for, with a button that copies the request. The connection picker is gone: the tab reads the master database, named once in the page header.
- **Monitor:** shorter texts on every tab; chart bars show their value on hover (a tip drawn by the page, not the browser's slow `title`).
- **Analytics:** each figure in one section only, with the range dropdown above the figures it changes and each one's change against the previous period; new charts (active users, response time, error rate) and an Overview of headlines that open their section; tiles with rows behind them open a list in a dialog, paged after a cursor (`/admin/object-read` for users, no total count); chart values on hover.
- **Monitor, Analytics and PgWeb:** the database under the page name as host / database (the host shortened where narrow, so the database shows); a click opens its URL, password hidden, with a copy icon.
- **PgWeb:** the query runner is the first row of the table list; dialogs restyled; copy buttons work where the browser blocks the clipboard API.
- **API page:** the refresh icon is gone from the search bar (Sync re-downloads the list).

## [15.7.1] - 2026-11-17

`readme.md` shows the version as a release badge (the latest GitHub Release, updated by CI) instead of a `Version` line, so a release no longer edits `readme.md`; a test still checks `ATOM_VERSION` and the top `CHANGELOG.md` entry agree. Nothing to change in projects.

## [15.7.0] - 2026-11-17

Standard versioning: release notes moved from `docs/sync.md` to `CHANGELOG.md` at the root (synced to projects); each version is a git tag `vX.Y.Z` and a GitHub Release, created by CI once the tests pass on the version's commit (every earlier version is tagged too). `python3 sync.py --ref v15.7.0` pins or rolls back a project by version (a commit id still works). Tests check `ATOM_VERSION`, `readme.md` and the top `CHANGELOG.md` entry agree. Nothing to change in projects.

## [15.6.1] - 2026-11-17

The fast route lookup uses only public FastAPI and Starlette APIs (no private `_IncludedRouter`, `_get_fastapi_scope`, `_FASTAPI_*`), so a FastAPI upgrade can't silently break it; it covers the same Atom routes. API page: the runner's cURL button sits in the request line before Copy, and the duplicate header download buttons (runner and cURL dialog) are gone; each cURL card keeps its own download. Nothing to change in projects.

## [15.6.0] - 2026-11-17

Limits even admins have: every `/admin/*` route that writes or grants access checks the role, deactivation and permission against the database on each call and is rate limited (60 a minute; user and object delete keep their own); `user_check_permission` gains a `realtime` mode. Audit columns (new `config_column_audit_blocked`) are refused in admin create, update and CSV import, and imported rows get the importing admin as `created_by_id`. `/admin/postgres-query-runner-write` takes one `INSERT`, `UPDATE` or `DELETE`, the last two with a `WHERE` (schema changes go through `config_postgres`, PgWeb for anything else). No user changes their own role, permissions or deactivation through the admin or permission routes. Nothing to change in projects, unless a project's own `config_api` overrides an `/admin/*` entry: give it the same checks.

## [15.5.0] - 2026-11-17

`/admin/user-create` and `/permission/user-create` also take other `users` columns (profile fields, a project's own columns such as a region) and create the user with them in one insert, so a user never exists half set up. Refused by name, nothing created: columns in `config_permission_user_column_blocked` and `config_column_users_blocked` (sign-up, login, verification, permissions, system), `id` and `deactivated_at`; values get the usual column rules and the password is hashed. Callers sending only role, username and password are unchanged. Nothing to change in projects.

## [15.4.1] - 2026-11-17

Atom's repository gets the files open-source contributors expect: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue and pull request templates in `.github/`, and `docker-compose.yml` for local Postgres (PostGIS), Redis and RabbitMQ. None of them is synced; `.gitignore` `# atom` now allows those three root names. Nothing to change in projects.

## [15.4.0] - 2026-11-16

A Claude client: with `config_anthropic_key` in `.env`, Atom opens `app_state.client_anthropic` (the official `anthropic` SDK, async) and closes it at shutdown; without the key nothing is imported. `func_anthropic_json` returns JSON that always matches a schema (example in [extend.md](extend.md)), and the AI SQL generators accept `ai: "claude"`. Sync without `--no-venv` once, to install `anthropic`. Nothing else to change in projects.

## [15.3.1] - 2026-11-16

[timescaledb.md](timescaledb.md) now opens with the main steps for a TimescaleDB database of its own (`config_postgres_url_<name>`, a normal Postgres URL, so the app gets its pool in `client_postgres_dict`; the schema in `files_extend/<feature>_schema.sql`, run in that database; then the feature's APIs and page) and a table of standard practices. Docs only; nothing to change in projects.

## [15.3.0] - 2026-11-16

The Admin page is now **Analytics** (`/page/analytics`; `/page/admin` is gone): read-only insights for developers, the same role 1 login, sections Overview, Users, Access, API traffic, Errors and Data, and each table's insights. Rows, SQL and exports are PgWeb's, and changes go through PgWeb or the API page. Also: the API page's Log in opens the login route's runner (any user, any role), PgWeb's SQL Runner sits at the top of its sidebar, every Atom page shows the Atom version after its title, and the monitor's server info names the master database (host / database). Nothing to change in projects; bookmarks to `/page/admin` must move to `/page/analytics`.

## [15.2.0] - 2026-11-16

Root (id 1) holds exactly the `/admin` permission routes: every startup sets its `permissions` to that list instead of only adding to it, so a stale id (a route that lost its permission check) or a `/permission` route granted to root by hand is removed at the next start. Grant `/permission` routes to other users. Nothing to change in projects.

## [15.0.0] - 2026-11-16

**Upgrade (projects must change):** The `/permission` route settings are together in one `# permission` section, all named `config_permission_*`: rename `config_table_permission_write_allowed` to `config_permission_table_write_allowed` and `config_column_users_permission_blocked` to `config_permission_user_column_blocked` in `config_extend.py` (startup names the new key if an old one is still set). `config_permission_user_roles` keeps its name.

## [14.3.0] - 2026-11-16

`PUT /permission/user-update` takes any `users` column except those in the new `config_column_users_permission_blocked` (`role`, `permissions`, `username`, `email`, `mobile`, ...; startup refuses a list without `role` and `permissions`), several at once, for an app's Edit profile; `password` still goes alone. Nothing to change in projects.

## [14.0.0] - 2026-11-16

**Upgrade (projects must change):** `config_permission_user_create_roles` is now `config_permission_user_roles` (startup names the new key if the old one is still set): rename it in `config_extend.py`. The same list now also limits the new `PUT /permission/user-update` (permission 139): `{id, name}`, `{id, password}` or `{id, deactivated_at}` (a timestamp blocks, `null` restores), only for users whose role is in the list. Nobody holds 139 by default. To make a block take effect at once instead of at the user's next token renewal, set `config_api_global_user_check_deactivated = "realtime"`.

## [13.2.0] - 2026-11-16

`POST /permission/user-create` (permission 138): `{username, password, role}`, for an app's own user management. Off twice by default: nobody holds 138, and `config_permission_user_create_roles` (now `config_permission_user_roles`) is `[]`; set the roles it may create in `config_extend.py` (from 2; startup refuses 1).

## [13.0.0] - 2026-11-15

**Upgrade (projects must change):** A new route group, `/permission/*` (`router/permission.py`, between private and admin): token plus a permission, any role. `/private/object-update` and `/private/object-delete` are now `/permission/object-update` and `/permission/object-delete` (same ids 136, 137, so granted users keep them), and `config_table_private_write_allowed` is `config_table_permission_write_allowed`: rename both in `config_extend.py` and in the page. Startup now refuses a `/permission/*` route without `user_check_permission`, and a route with a role, permission, deactivated or deleted check whose `is_token` is not `True`. Root gets every `/admin` permission route at startup, a project's too.

## [12.0.0] - 2026-11-15

**Upgrade (projects must change):** `/private/users-list` is now `/private/user-read` (same id 112, token only). It reads `users` like `/private/object-read`: `filter`, `order` (default `id desc`), `after`, `page` and `limit`, and no `role`; send `filter=["role = 2"]` instead. It returns the columns in `config_column_users_private_read` (`id`, `username`, `role`, `created_at`, `deactivated_at`) and refuses filters or order on any other `users` column. Rename the route wherever a project or client calls it.

## [11.0.0] - 2026-11-14

**Upgrade (projects must change):** The `users` columns `title` and `description` are now `job_title` and `about` (clearer on a user). Startup adds the new ones; Atom never drops a column, so the old two stay in the database: copy any values across and drop them yourself (`ALTER TABLE users DROP COLUMN title, DROP COLUMN description`), and rename `title` and `description` wherever a project reads or writes them on `users`. `email_secondary` and `mobile_secondary` are now checked by `config_column_regex` (an email; 6–20 digits with spaces, dashes and a leading +).

## [10.0.0] - 2026-11-14

**Upgrade (projects must change):** Per-user permissions are enforced: a route with `user_check_permission: {"mode": "token"}` admits only users whose `users.permissions` holds its `id` ([auth.md](auth.md#per-user-permissions)). Atom's samples: `/admin/postgres-query-runner-write` (6) needs role 1 and permission 6; `/admin/user-delete` (132) needs permission 132 only. Root (id 1) gets both at startup; root logs in again to use them, and other admins need a grant through `/admin/user-update`.

A project that sets `config_column_int_mapping["users"]` keeps Atom's labels (startup refuses a permission route without one):

```python
"users": {**base_config_column_int_mapping["users"], "role": {1: "Admin", 2: "General"}},
```

## [9.0.0] - 2026-11-14

**Upgrade (projects must change):** `config_sql` and `config_table` are removed: the startup queries are Atom's own code now, and a table's buffer size is a plain setting. A project that set either (startup stops, naming the new keys) sets plain values instead, in `config_extend.py` or `.env`:

| Before | 9.0.0 |
|---|---|
| `config_sql["config"]` (its `limit`) | `config_cache_row_limit_config` |
| `config_sql["users_role"]`, `["users_deactivated"]`, `["users_deleted"]` | `config_cache_row_limit_users_role`, `_users_deactivated`, `_users_deleted` (`0` = off) |
| `config_sql["profile_metadata"]` | `config_profile_metadata_sql` |
| `config_table["<table>"]["buffer_limit"]` | `config_buffer_limit_<table>` (Atom sets `config_buffer_limit_log_api = 1000`) |

`config_extend.py` sections are now `# base`, `# atom`, `# extend` (was `# misc`): move plain overrides of Atom's settings into `# atom`, keep only the project's own settings under `# extend` ([extend.md](extend.md)). Layout only; nothing checks it.

A script's schedule is `config_schedule_script_<script>` (was `config_schedule_<script>`), so it never clashes with the scheduler's own `config_schedule_timezone` and `config_schedule_check_sec`. Rename each one in `config_extend.py`, `.env` and the server's settings (`config_schedule_postgres_cleanup` → `config_schedule_script_postgres_cleanup`); an old name, even `off`, stops startup naming the new one.

## [8.0.0] - 2026-11-12

**Upgrade (projects must change):** - Two of Atom's scripts were renamed: `script/cleanup.py` → `script/postgres_cleanup.py` and `script/schema_plan.py` → `script/postgres_schema_plan.py` (run them as `venv/bin/python -m script.postgres_cleanup` and `script.postgres_schema_plan`). The setting `config_schedule_cleanup` is now `config_schedule_postgres_cleanup`: a project that sets the old name renames it (an old name that is not `off` stops startup: no script named cleanup).
- Every script starts with `# type: job` (runs once and exits) or `# type: continuous` (runs until stopped). Add it as the first line of each `script_extend/` script, then a blank line; a scheduled script without `# type: job` stops startup, and a `continuous` one is never scheduled ([schedule.md](schedule.md)).

## [7.0.0] - 2026-11-11

**Upgrade (projects must change):** Three settings were renamed; a project that sets one in `config_extend.py` or `.env` renames it (the old name stops startup, naming the new one):

| Before | 7.0.0 |
|---|---|
| `config_otp_retention_day` | `config_retention_day_otp` |
| `config_log_api_retention_day` | `config_retention_day_log_api` |
| `config_users_delete_retention_day` | `config_retention_day_users_delete` |

OTP and API-log cleanup now run as `script/cleanup.py` on `config_schedule_cleanup` ([schedule.md](schedule.md)); a new table, `script_run`, is created at startup.
