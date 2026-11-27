# Front end

How a page works with Atom: the routes it calls, the login and token flow, storage, lists and export. Atom is a backend: a page's look, layout, words, build (plain files, modules or a bundler) and framework are the project's own, and a family of apps keeps its shared look in its own `docs_extend/`. Only how Atom serves pages and the route paths they call are enforced; everything else here is a Default, kept because breaking it gives a page that leaks, breaks or slows down at scale. A page that differs on purpose writes why in `docs_extend/`.

## Pages (enforced)
- A page is `static_extend/<name>.html` or `static_extend/<name>/index.html` (its other files inside `<name>/`): served at `/page/<name>`, listed on `/`, no route or `config_api` entry; `/` serves `config_root_html_path`. Every other file is served at `/static/<path>` only (`/static_extend/...` is not a URL); Atom's `static/` follows the same rule. Startup fails on a path in both folders or two pages with one name (ignoring case); restart after creating the folder.
- Link local files by full path (`/static/<name>/js/app.js`): Atom stamps `?v=<fingerprint>`, so no hand-kept `?v=`.
- A page calls routes by their full `config_api` path, written whole (values only after `?`, or as `${...}` where the route has `{name}`); `script.check` fails on a path not in `config_api`. When a route is renamed or removed, the page follows `CHANGELOG.md`, never `config_api` the page.

## Defaults
- Security: escape every value from the database or another system before `innerHTML`; nothing secret or personal in a URL. Hiding a button is not access control: `config_api` and the routes refuse what a user may not do, so a page may show or hide controls as it likes.
- Use Atom's routes before writing one: login `/auth/login-*`, renewal `/my/token-refresh`, the user `/my/profile`, password and profile changes `/my/user-update`, own rows `/my/object-*`, selected users' rows the admin object routes (granted per route), labels and limits `/info` (`config_column_int_mapping`, `export_limit`), files `/public/blob-upload-*`, messages `/my/message-*`, users `/admin/user-create` and `/admin/user-update`, granted by id ([user-management.md](user-management.md)).
- Labels (a role, a status) come from `/info` `config_column_int_mapping`, never written in the page; before `/info` loads, show the number.
- One page per app; state such as a tab goes in the query (`/page/<name>?tab=<tab>`), not a sub-path. Pages never share CSS or JS files, so each changes on its own path.
- Calls that don't need each other's result go out together (`Promise.all`); one screen task, one route.
- No script or style from another site: the page works without outside servers. A viewport meta tag, so it works on a phone.

## Login and token (Defaults: Atom's own pages do exactly this)
- **Storage**: one localStorage key named after the page (never a general name like `token` or `user`: apps share `localhost` in development and may share a domain), holding one JSON object `{v, token, user, info, synced_at, ...}`. `token` is exactly what `/auth/login-*` and `/my/token-refresh` return: `{access_token, refresh_token, access_token_expires_at, refresh_token_expires_at}` (unix seconds). `user` is `GET /my/profile`, the only copy of the user. `info` is what the page uses of `GET /info`. `v` is the layout version: a different `v` keeps the token and user and drops the rest. Larger data (option lists, cached results) in an IndexedDB database of the same name; memory for what is on screen.
- **Logged in = a valid token object**: both tokens non-empty, both expiry times numbers, `refresh_token_expires_at` in the future. Anything else is logged out: clear the key and the IndexedDB database, show the login. An expired access token alone is not a logout: renew first.
- **Login**: `POST /auth/login-username-password` `{role, username, password}` with the role the page serves (set in one place), store `token`, then `GET /my/profile` into `user` and check it: the page's role (else refuse: "<App> access is unavailable."), `deactivated_at` and `deleted_at` empty. Role 1 is Atom's admin, a backend user, never a project page's user.
- **Keep it alive**: on open, every minute and when the tab comes back, renew with `POST /my/token-refresh` (refresh token as Bearer) when 5 minutes or less are left. A refused renewal (401/403) or an expired refresh token logs out with a plain sentence, never a token error; a network failure keeps the token and retries. A request that gets 401 renews once (one shared renewal for every request in flight) and retries; refused again, log out.
- **Blocked account**: 403 `account deactivated` / `account deleted` (at login, renewal or any route), or `/my/profile` with `deactivated_at` / `deleted_at`: log out, clear storage, say which and to contact the admin ([auth.md](auth.md#deactivated-or-deleted-accounts)). Regular renewal and `/my/profile` catch a block on an open page.
- **Refresh what the browser keeps**: renew the token, reload `/my/profile` (with the user check) and `/info`, and the page's reference data, on a timer (Atom's pages: every 3 hours) and on request; a browser with no `info` loads it at once.
- **Logout**: remove the key, delete the IndexedDB database, clear memory. Other tabs get the `storage` event, find no valid token and show the login.
- A download that finishes after a logout saves nothing.
- Passwords: 6–120 characters without spaces, checked in the page as Atom checks them.

## Lists, search and export
- Every list pages after a cursor ([crud.md](crud.md#paging)): send `after` (none for the first page); the server returns the rows and the next `after`, `null` on the last page. Keep the `after` of each page shown (`[null, a1, a2, ...]`) for Previous; a new filter, sort or page size starts from the first page. Never a total count.
- Search asks the server (on Enter or a button, not on each keystroke); every filter and sort column has a matching index (comments of a task, newest first: `btree(task_id,id)`).
- Option lists from data (users, tags, customers): one route, `/<app>/option-read`, all lists in one call, kept in IndexedDB and refreshed with the rest. A list that grows returns at most `config_option_limit` rows plus `<list>_has_more`; past about 10,000 options or 1 MB, the dropdown becomes a server search. Fixed lists (status, role labels) come from `/info`.
- Export: the feature's `/<feature>/export` checks its params, builds one query and returns `func_postgres_export` (or `func_mssql_export`, `func_clickhouse_export`) through `func_csv_response`: streamed, compressed, at most `config_export_limit` rows ([crud.md](crud.md), [config.md](config.md)). The page offers rows up to `/info` `export_limit`, reads the response as a stream to show progress, with no count first; for very large files it writes straight to disk where the browser allows (`showSaveFilePicker`).

## Scale (a page keeps working at 100× today's rows and users)
- The browser never downloads a table that grows: lists, search and export are paged or streamed by the server; counts, totals and dashboards are computed in SQL, never from rows in the browser.
- IndexedDB holds only bounded reference data (option lists, labels, totals); memory caches are bounded (newest N).

## Reference code
Atom's own pages (`static/`) implement all of the above and are synced into every project: `static/analytics.html` (the full flow: one-role login, renewal, the IndexedDB cache with a timed refresh, cursor lists, the export limit) and `static/monitor.html` (the smallest: the same flow without a cache). A page may copy their code or write its own; their look is Atom's, not a standard.

Each logged-in Atom page carries five blocks, identical in every Atom page (`tests/test_page_auth.py` fails when a copy differs): theme (`<!-- ==== atom page: theme ==== -->`, in `<head>`), look (`/* ==== atom page: look ==== */`, first in `<style>`), account (`/* ==== atom page: account ==== */`, first in `<script>`, after `PAGE`), account header (`<!-- ==== atom page: account header ==== -->`) and dialogs (`<!-- ==== atom page: dialogs ==== -->`, end of `<body>`).

**`PAGE`**, set just above the account block, is all that differs: `key` (the localStorage key and IndexedDB database), `title`, `role` (the login role; `null` for any role), `loginRequired` (`false` lets the page work logged out), `idb` (whether it keeps data in IndexedDB), and the hooks `refresh` (downloads the page's data into the cache), `onIn` (logged in: show the page), `onOut` (logged out: forget what it shows), `onSynced` (a refresh finished: draw again), `login` (optional: the page's own login) and `intro` (the login page's text). The page calls `Page.start()` last.

**`Page`** is what the page's code uses: `api(path, options)` (Atom's `{status, message}` answer, the token added, a 401 renewed once), `request` (the raw response, for downloads), `read()` and `save(changes)` (the localStorage object), `user()`, `cacheGet(name)` and `cacheSet(name, data)` (IndexedDB records `{name, user_id, saved_at, data}`), `syncData()`, `dialog`, `form({title, body, ok, tone, submit})`, `confirm(title, text, ok, danger)`, `toast(text, isError)`, `kv(rows)`, `esc`, `loggedIn()`, `signIn(token)`, `logOut(message)`, `tokenFresh()` and `tokenRefresh()`.

| Page | `PAGE` | Its data in IndexedDB |
| :--- | :--- | :--- |
| Analytics | `key: "analytics", role: 1, loginRequired: true, idb: true` | `reference`: schema, `/info`, row estimates, settings; `analytics`: each section's saved cards |
| Monitor | `key: "monitor", role: 1, loginRequired: true, idb: false` | none (every tab reads live) |
| API | `key: "api", role: null, loginRequired: false, idb: true` | `openapi`: `/openapi.json` |
| Message | `key: "message", role: null, loginRequired: true, idb: false` | none (messages are live) |
