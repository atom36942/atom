# Front end

How a project's pages (`static_extend/<app>/`) and Atom's own work with Atom: one login, account menu, sync and list flow on every page, so a user meets the same app everywhere and no page re-decides them. [AGENTS.md](../AGENTS.md) lists these in short; this page has the detail. Atom shares the backend only: the page, its build and its look are the project's own. Only how Atom serves pages and the route paths they call are enforced (said so below); everything else is a Default: a suggestion, never a rule. Pages may always differ; a project that differs on purpose writes why in its `docs_extend/`.

## Pages
What Atom enforces (startup or serving):
- A page is `static_extend/<name>.html` or `static_extend/<name>/index.html` (its other files inside `<name>/`): served at `/page/<name>`, listed on `/`, no route or `config_api` entry; `/` serves `config_root_html_path`. Every other file is served at `/static/<path>` only (`/static_extend/...` is not a URL); Atom's `static/` follows the same rule. Startup fails on a path in both folders or two pages with one name (ignoring case); restart after creating the folder.
- Link local files by full path (`/static/<name>/js/app.js`): Atom stamps `?v=<fingerprint>`, so no hand-kept `?v=`.

Defaults, not rules: suggestions a page may follow or not (the details below); the page, its build (plain files, modules or a bundler) and its look are the project's own, since Atom shares backend only.
- Escape data from the database or other systems before `innerHTML`.
- One page per app; state such as a tab goes in the query (`/page/<name>?tab=<tab>`), not a sub-path.
- Files: a page starts as one `<name>.html` with its CSS and JS inline (one place to search and change); it becomes a `<name>/` folder (`index.html`, `css/`, `js/`) when it carries its own assets (images, fonts) or one file grows hard to work in (about 3000+ lines). Pages never share CSS or JS files, even when code repeats, so each can change on its own path. Atom's own pages do the same.
- A page is standalone: its own login and storage, every key and database named after it (`<name>`), never general names like `token` or `user` (apps share `localhost` in development and may share a domain later).
- Storage by size and how long it lives: memory for what is on screen (gone on reload); sessionStorage for one tab's short-lived state; localStorage for small things kept across visits (login, user, choices) under one parent key holding one JSON object; IndexedDB for larger data (option lists, cached results). Live lists come from the server. Logout clears all of it.
- Use what Atom already has before writing a route for it: login `/auth/login-*`, renewal `/my/token-refresh`, the user `/my/profile`, password and profile changes `/my/user-update`, own-row writes `/my/object-create`/`-update`/`-delete`, settings and limits `/info` (`export_limit`, `config_options`), files `/public/blob-upload-*`, messages `/my/message-*`.
- Speed: calls that don't need each other's result go out together (`Promise.all`); only a call that needs an earlier result waits.
- A long file (300+ lines) marks its sections (`/* ==== <name> ==== */` in CSS and JS, `<!-- ==== <name> ==== -->` in HTML) so `grep -n '==== '` lists them.

## Login and account (defaults: every page with a login, Atom's own included, so every project has one flow)
- Login: `POST /auth/login-username-password` `{role, username, password}` with the one role the page serves (set in one place in the page), then `GET /my/profile`; a user of another role is refused ("<App> access is unavailable."). Role 1 (admin) is a backend user, never a project page's user: an admin tests a page with their own account of the page's role.
- Keep the login alive: renew with `POST /my/token-refresh` shortly before the access token expires; when renewal is refused, show the login form with a plain sentence, never a raw token error.
- Deactivated or deleted account (403 `account deactivated` / `account deleted` at login, renewal or any route; or `/my/profile` with `deactivated_at`/`deleted_at`): log out, clear storage, say which and "Please contact your admin." The page's regular sync (token renewal and `/my/profile`) catches a block on an open page ([auth.md](auth.md#deactivated-or-deleted-accounts)).
- Account menu: the avatar (the username's initials: the words before an `@`, `jane.doe` → JD) opens the same five items on every page and project, in this order: My profile, Login details, Sync, Settings, Logout (Logout asks first). Grow inside the five, not beside them: Sync is the whole sync flow (whatever a page keeps in the browser), Settings takes any new setting, My profile any new profile field. A sixth item only for a real account need, its reason in `docs_extend/`. A page's own actions and features (Export, Refresh, Users, any feature's button) are header buttons, left of the avatar, never in the menu.
- My profile: the person (Created, then the `users` profile columns a user changes without OTP: `name`, `job_title`, `email_secondary`, `mobile_secondary`, `city`, `country`, `about`); Edit in place, Save sends only the changed fields, `PUT /my/user-update`. Login details: Username (copy), Password (dots, a pencil to the password form), Role as `2 (General)` (label from `/info` `config_column_int_mapping`, the number alone before the first Sync), Permissions as the ids. Each field shows in one of the two only.
- Password boxes: every one (login, Update password, New user, Reset password) has a show/hide eye at its end; passwords are 6–120 characters without spaces, checked in the page as Atom checks them.
- Notifications (toasts): bottom right, centred on a phone; one at a time; an icon (success or error), the message, a × to close; about 6 s, kept while the mouse is over it; shown as a popover (top layer) so an open dialog doesn't hide it. Atom's own pages do the same.
- Settings (account menu): Theme (Light, Dark, System; a project's pages default to Light, Atom's own to Dark) and Density (Comfortable, Compact), saved in the page's own localStorage key (`<html data-storage-key>`) under `settings`, removed with it at logout, and set as `<html data-theme data-density>` before the page draws; every colour and size is a CSS variable with a value for each. Atom's own pages do the same.
- Sync (account menu, and by itself every 3 hours): renews the token, reloads `/my/profile` (with the user check) and `/info`, downloads the page's reference data into IndexedDB and records when; its dialog shows when it last ran and what the browser holds.

## Lists, search and export
- Option lists from data: every dropdown list a page builds from data (users, tags, customers, countries), filter or form, comes from one route, `/<app>/option-read`, all lists in one call, kept in IndexedDB and downloaded again by Sync. Each list that grows returns at most `config_option_limit` rows (`config_extend.py`, 50000; the most used or by name) plus `<list>_has_more`, and its dropdown then says "Showing the first …"; past that, the dropdown becomes a server search. Fixed lists (status, priority, role labels) come from `/info`, uncapped.
- Screens: a search looks in one picked column and runs on Enter or its button, not on each keystroke (× clears it and searches again); one date format per page; names and titles shown in full; a link to one item opens only that item, the rest loads after.
- Export: a dialog with the list's filters, a row count up to `/info` `export_limit` and Download, calling the feature's `/<feature>/export` (backed by `func_<db>_export`); the file is read as a stream to show progress, with no count first.

## Layout, size and colour (defaults for a project's pages; Atom's own pages keep their dark look)
- Navigation by how many views a page has: up to 5, tabs in the middle of the header; from about 6, or when views fall into groups, a left sidebar (about 220px, collapsible, grouped with small headings), the header keeping the app name, actions and avatar. Tables need the width, so never a sidebar for 2–5 views.
- Compact: small type and tight controls, so lists show more rows and columns: text 13px (`--fs`), small 12px, extra small 11px, dialog titles 17px; controls and buttons 36px high (small buttons 30px; Settings > Compact makes them smaller), table cells `10px 12px`, header 64px, 8px corners. No large headings or wide padding inside an app; one font, the system stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
- Colour: one fixed palette, light by default, every colour a CSS variable named as below (a project changes the brand only when it has its own; status colours keep their meaning):

| Variable | Light | Dark | Use |
| :--- | :--- | :--- | :--- |
| `--brand` | `#1a396f` | `#24508f` | buttons, dialog headers (white text on it) |
| `--brand-hover` | `#142c57` | `#2c5aa0` | the brand under the mouse |
| `--brand-ink` | `#1a396f` | `#9db9ea` | the brand as text and icons |
| `--brand-soft` | `#edf2fa` | `#1b293d` | selected rows, soft highlights |
| `--brand-tint` | `#dce6f5` | `#1d2e47` | table and column headers |
| `--brand-line` | `#b7c8e3` | `#2f4a73` | brand borders |
| `--bg` | `#f7f8fa` | `#0e1216` | the page |
| `--surface` | `#ffffff` | `#161b21` | cards, dialogs, tables |
| `--surface-2` | `#f2f4f7` | `#1d232a` | inputs, zebra rows |
| `--ink` | `#1f2933` | `#e4e9ee` | text |
| `--muted` | `#5f6b7a` | `#9aa6b2` | secondary text |
| `--faint` | `#8a94a3` | `#6e7a86` | hints, placeholders |
| `--line` | `#e3e7ed` | `#283039` | borders |
| `--success` / `--warning` / `--danger` / `--info` | `#2e7d4f` / `#9a6200` / `#c62828` / `#2f6bad` | lighter versions in the same names | status, each with a `-soft` background |

## Screens (defaults learned from apps built on Atom)
- Header buttons all look alike (outlined, icon plus a short label), the main action included: a filled button reads as "selected", so header buttons are never filled.
- Filters: one row above the list holding only the filters; a filter in use is tinted (the brand's soft colour), and `Clear filters` at its end stays disabled until one is in use. Every change starts the list again at page 1.
- Search: one box with the column picked at its left, × (clear and search again) and → (run) shown only while it has text; it runs on Enter or →, never while typing, and asks the server.
- Dropdowns: any list that can grow gets a search box inside once it has more than about 10 choices.
- Pager: Previous and Next as square chevron buttons with `Page N` between them (`Page N of M` only when the total is known for free); never worded buttons or a total count.
- Tables: header row tinted, numbers right-aligned, row hover; a long value ends in "…" with the full text on hover, so a table fits its width without sideways scrolling; an empty list is one row, "No <things>" (searching: "No results").
- Cards: the same rows on every card, "Not available" when a value is missing, never a row that comes and goes; names and titles in full.
- Dates: one format per app (e.g. `06-Nov-2026`), relative times for recent events ("5 min ago", the date on hover); past due in red.
- Loading: a dialog opens at its final size (its frame drawn first, dimmed), a list that reloads keeps its rows dimmed until the new ones arrive; "Loading…" only when there is nothing to show yet.
- Actions shown to everyone: a user sees the same buttons whatever they may do; a click they may not use shows a toast saying why ("You are not allowed to do this. Ask an admin for access."), the server refusing it too.
- Words: toasts in the past tense without a period ("Task created"); confirmations ask a question with one plain sentence ("Delete task?" / "This can't be undone.") and name the action on the button; a subtitle only when it adds a fact the title doesn't.
- Contrast: text on its background passes 4.5:1; the faintest grey only for placeholders.
- Plain CSS and JS from the page's own files: no CDN, no UI framework unless the project has a reason; the page loads fast and works without outside servers.

## Scale and speed (a page keeps working at 100× today's rows and users)
- The browser never downloads a table that grows: lists, search and export are paged or streamed by the server; counts, totals and dashboards are computed in SQL, never from rows in the browser.
- IndexedDB holds only bounded reference data (option lists, labels, totals); a dropdown stays a synced list up to about 10,000 options or 1 MB, past that a server search.
- Calls that don't depend on each other go out together (`Promise.all`); one screen task, one route.
- Memory caches are bounded (newest N): nothing grows without a limit while the page stays open.

# Details

## Structure
- One page per app, starting as one `<app>.html` with its CSS and JS inline; once it has its own assets or grows large (about 3000+ lines), a folder: `index.html`, `css/<app>.css`, `js/app.js`, plus small helpers (a Sync dialog, a download helper) as their own files, each app keeping its own copy (copied unchanged between apps, never one file two pages load), so every app behaves the same. Plain HTML, CSS and JS work well; a framework or bundler is the project's choice.
- Every colour and size as a CSS variable in one theme block (brand, neutrals, status colours, text sizes, control heights, paddings), so a page never types a colour twice and a second app can share the look.
- Element ids, function names and routes stay each app's own; what users see (login, header, dialogs, words) is worth keeping the same across a project's apps.

## Page standard
Reference code: `static/analytics.html` (the full example: one-role login, Sync with the IndexedDB cache, lists with Previous/Next, the export limit) and `static/monitor.html` (the smallest: the same flow without a cache). Every project has both through sync; a new page copies their five blocks unchanged, sets `PAGE` and `<html data-storage-key data-default-theme>`, and builds its own screens with `Page.*`. Its look is its own through the CSS variables (an app page is usually light: `data-default-theme="light"` and its own palette); the structure stays the same.

Atom's pages that log in (Analytics, Monitor, API, Message, Tickets) are built the same way, so a new page or project copies the structure instead of deciding it again. Each page carries five blocks, copied unchanged from page to page (a test, `tests/test_page_auth.py`, fails when a copy differs); only what is around them is the page's own.

| Block | Where in the page | What it holds |
| :--- | :--- | :--- |
| theme (`<!-- ==== atom page: theme ==== -->`) | in `<head>`, before `<style>` | sets `<html data-theme data-density>` before the page draws from the page's own localStorage key (`<html data-storage-key>`, the same as `PAGE.key`), under `settings`: `theme` (`dark`, `light`, or `system`: the computer's mode, followed as it changes; the default is `<html data-default-theme>`, `light` on an app page, else `dark`) and `density` (`comfortable`, the default, or `compact`: `--control-h` and `--cell-y` smaller). Each page keeps its own; logout removes the whole key, so the page is back on its defaults; every tab of the page follows a change |
| look (`/* ==== atom page: look ==== */`) | first in `<style>` | the palette (dark on `:root`, light on `:root[data-theme="light"]`; `--hl` is the overlay colour, white on dark and ink on light, so a page writes `rgba(var(--hl),.06)`, never a fixed white), one type scale (13px controls and dialog text, 12px small text, 15px dialog titles, 14px page text), base controls, the dialog (a header filled with the brand colour, a padded body, actions on their own band), the login page, key-value rows, the toast (bottom right, centred on a phone: a check or !, the message, ×; 6 s, kept while hovered; a popover above any dialog), the account menu. Base element rules use `:where()`, so the page's own classes always win |
| account (`/* ==== atom page: account ==== */`) | first in `<script>`, after `PAGE` | `Page`: storage, login, token renewal, the user check, the cache, the sync, the account dialogs and the shared dialog |
| account header (`<!-- ==== atom page: account header ==== -->`) | the right end of the page's header | Log in (logged out, on a page that works without a login) and the avatar with its menu (logged in) |
| dialogs (`<!-- ==== atom page: dialogs ==== -->`) | the end of `<body>` | the login page, the blocked-account dialog, the shared dialog, the toast |

**`PAGE`**, set just above the account block, is the only part that differs: `key` (the localStorage key and IndexedDB database), `title`, `role` (the login role; `null` for any role), `loginRequired` (`false` lets the page work logged out, with a Log in button), `idb` (whether it keeps data in IndexedDB), and the hooks `refresh` (downloads the page's data into the cache), `onIn` (logged in: show the page), `onOut` (logged out: forget what it shows), `onSynced` (a sync finished: draw again), `login` (optional: the page's own login instead of the login card; API opens the runner of the login route) and `intro` (the login page's left side: `{heading, text, features: [[svg paths, title, line], …]}`, four features). The page calls `Page.start()` last.

**`Page`** is what the page's own code uses: `api(path, options)` (Atom's `{status, message}` answer, the token added, a 401 renewed once), `request` (the raw response, for downloads), `read()` and `save(changes)` (the localStorage object), `user()`, `cacheGet(name)` and `cacheSet(name, data)` (IndexedDB records `{name, user_id, saved_at, data}`), `syncData()` (the page's download, one at a time), `dialog`, `form({title, body, ok, tone, submit})`, `confirm(title, text, ok, danger)`, `toast(text, isError)`, `kv(rows)`, `esc`, `loggedIn()`, `signIn(token)`, `logOut(message)`, `tokenFresh()` and `tokenRefresh()`. Every dialog of the page (its own forms and confirmations too) goes through `dialog`, `form` and `confirm`, so all of them look and behave alike.

**The flow**: open with a valid token object → `onIn` draws from the cache; no cache yet (the first login, a cleared browser) → `syncData()` downloads it first. The cache is used until the next sync: every 3 hours (checked every minute and when the tab comes back) or Sync now in the Sync dialog. Logged out → the login page (it cannot be closed on a page that needs a login) or, on a page that works logged out (API), the Log in button, which shows only the login card over the page (× or Escape closes it).

| Page | `PAGE` | Its data in IndexedDB |
| :--- | :--- | :--- |
| Analytics | `key: "analytics", role: 1, loginRequired: true, idb: true` | `reference`: schema, `/info`, row estimates, settings; `analytics`: each section's saved cards |
| Monitor | `key: "monitor", role: 1, loginRequired: true, idb: false` | none (every tab reads live) |
| API | `key: "api", role: null, loginRequired: false, idb: true` | `openapi`: `/openapi.json` (logged out, a copy over 3 hours old is downloaded again on open) |
| Message | `key: "message", role: null, loginRequired: true, idb: false` | none (messages are live) |
| Tickets | `key: "ticket", role: null, loginRequired: true, idb: false` | none (the list is live; light by default, the apps' navy palette) |

## Login
The account block does this; it is the default for a project's pages too.
- **Storage**: one localStorage key named after the page, holding one JSON object `{v, token, user, info, synced_at, ...small choices}`. `token` is exactly what `/auth/login-*` and `/my/token-refresh` return: `{access_token, refresh_token, access_token_expires_at, refresh_token_expires_at}` (the two times are unix seconds). `user` is `GET /my/profile`, the only copy of the user (never a separate `username`). `info` is `{config_column_int_mapping, export_limit}` from `GET /info`: every label (a role, a status) and setting the page shows comes from it, never written in the page; before the first sync a role shows as its number. `synced_at` is when the user (and the page's reference data) was last downloaded. `v` is the layout version: a different `v` keeps the token and the user and drops the rest.
- **Logged in = a valid token object**: both tokens as non-empty text, both expiry times as numbers, and `refresh_token_expires_at` still in the future. Anything else (no `token`, a missing field, an expired refresh token) means logged out: the page clears its key (and its IndexedDB database) and shows the login form. An expired access token alone is not a logout while the refresh token is valid: the page renews first. A token is stored only after it passes this check, from login or refresh.
- **Login**: `POST /auth/login-username-password` `{role, username, password}` (the role the page serves), store `token`, `GET /my/profile` into `user`, then check the user: the page's role (otherwise "<Title> access is unavailable."), `deactivated_at` and `deleted_at` empty (otherwise the blocked-account dialog, below). Then the first sync (`/info`, reference data into IndexedDB, then `synced_at`) and the page.
- **Keep it alive**: on open, every minute and when the tab comes back into view, read `token.access_token_expires_at`; with 5 minutes or less left, `POST /my/token-refresh` (refresh token as Bearer) and store the new token object. A refused refresh (401/403) or an expired refresh token shows the login form with "Your session has expired. Please log in again.", never a token error; a network failure keeps the token and tries again at the next check. A request that gets 401 refreshes once (one shared refresh for every request in flight) and retries; refused again, log out.
- **Sync**: when `synced_at` is 3 hours old (checked with the token) and from Sync in the account menu: new token, `/my/profile` (with the user check), `/info`, the page's reference data, then `synced_at`; a browser with no `info` syncs at once. The Sync dialog is described under Header and account.
- **Logout**: a confirmation, then remove the localStorage key, delete the IndexedDB database and clear memory. Other open tabs get the `storage` event for the key, find no valid token and show the login form ("You logged out in another tab.").
- **Login page** (the same layout as the projects' pages, in Atom's dark colours): a wordmark top left (the page's title); on the left a badge "Atom", a serif heading, one line and four feature cards (`PAGE.intro`); on the right the login card: a filled header "Login" with "For role N accounts" (or "For any role", then a Role box), Username and Password (icons, show/hide), a full-width Login button; the apps' measures: fields and button 45px with the `--radius` corners and 14px text, label 8px over its field, 16px between fields, 22px to the button, a 75px header, 370px wide. Phones: the cards hide and the card stacks under the heading. While it shows, the rest of the page is inert.
- **Blocked account**: Atom's refusal (403 "account deactivated" / "account deleted", at login, token renewal or any route) or a profile with `deactivated_at` / `deleted_at` logs out and opens a dialog over the login page, "Account deactivated" ("Your account is deactivated. Please contact your admin.") or "Account deleted" ("Your account was deleted. Please contact your admin."), with one OK; only OK closes it.
- A download that finishes after a logout saves nothing (no stray `info` or cache records).

## Header and account
- App name on the left, the app's views in the middle, actions on the right (icon plus a short label), then an avatar with the username's initials (the words before an `@`: `jane.doe` → JD; one word gives its first two letters) and its menu: My profile (read-only), Login details (only the password editable, through `PUT /my/user-update`), Sync, Settings, Logout (with a confirmation).
- The account parts use the same words on every page:

| Part | Shows |
| :--- | :--- |
| Menu | My profile, Login details, Sync, Settings, Logout (Logout in red), the order of the apps' menu; icons in the text colour |
| Settings | Title "Settings", subtitle "Saved in this browser"; one bordered row per setting, then Done: Theme (Dark, Light, System) and Density (Comfortable, Compact), each one choice applied at once (arrow keys move it). A new setting is a new entry in `SETTINGS` |
| My profile | Created (how long ago: Today, Yesterday, `N days ago`; the date on hover), then Name, Job title, Email, Mobile, City, Country, About (`users` columns `name`, `job_title`, `email_secondary`, `mobile_secondary`, `city`, `country`, `about`: what a user changes without OTP; the login email and mobile are not shown). Edit turns the same rows into inputs in place (the label stays on the left); Save sends only the changed ones, `PUT /my/user-update` (an emptied field is `null`), then reloads the profile. Email and Mobile are checked as `config_column_regex` checks them. Each field is in My profile or Login details, never both |
| Login details | Username (with a copy button, toast "Username copied"), Password (8 dots and a pencil), Role (`1 (Admin)`: the number first, the label from `info` in brackets; the number alone before the first sync), Permissions (the ids as stored, comma separated, `59, 86`; `None` when there are none) |
| Update password | New password, Confirm new password, "6–120 characters, no spaces."; Cancel (back to Login details), Update password; errors "Use 6–120 characters, no spaces" and "Passwords don't match"; success closes the dialog with the toast "Password updated" |
| Logout | "Logout?", "Are you sure you want to logout?", Cancel, Logout; nothing shown after |
| Sync | Title "Sync", subtitle "Last synced 5 min ago (auto sync every 3 hours)" ("just now", "3 hr ago", or "Never synced"); Local storage and IndexedDB as "Used, N items" or "Not used", with no empty line under them; Close, Sync now. While it runs, the steps ("Renewing login… (1 of 4)") and a progress bar, the dialog locked; then "Everything is up to date." or "Sync failed. Please try again." |

## Dialogs and loading
- One dialog structure everywhere (the shared dialog: `Page.dialog`, `Page.form`, `Page.confirm`): a header filled with the brand colour (white title, optional light subtitle, close), a padded body, an action row on its own band (Cancel first, the main action last). Escape and the close button close it; a running action keeps it open, and its error stays in the dialog.
- Open a dialog at its final size: draw its frame (the empty table or calendar) first, faded, then fill in the data, so nothing jumps. A list that reloads keeps its rows, faded, until the new ones arrive; a bare "Loading…" only when there is nothing to show yet.

## Browser storage
- localStorage for small items (login, user, remembered choices), one key per app; IndexedDB for larger data the page keeps (filter options, dashboard totals); memory for what is on screen; logout clears all of it, in every open tab.
- Download reference data once after login and refresh it on a timer and on request (a Sync button); live lists always come from the server.

## Lists and paging
- Every list pages after a cursor, the same way everywhere ([crud.md](crud.md#paging)): the page sends `after` (none for the first page) and the server returns the rows and the next `after`, `null` on the last page. Next is enabled while `after` is not `null`. A page-number box may send `page` to jump near the start (capped by the server); never a total count.
- Keep the `after` sent for each page shown (`[null, a1, a2, ...]`) so Previous goes back to it; a new filter, sort or page size starts again from the first page.
- Give every filter and sort column an index that matches it (for "comments of a task, newest first": `btree(task_id,id)`).

## Export
- The project's export route (`/<feature>/export`) checks its params, builds one query and returns `func_postgres_export` (or `func_mssql_export`, `func_clickhouse_export`) through `func_csv_response`: streamed, compressed, at most `config_export_limit` rows. Details: [crud.md](crud.md) and [config.md](config.md).
- A simple dialog: "Use the list's filters" (showing the picked filters), a Rows box with a sensible default and a few choices up to the maximum (`/info` `export_limit`, also shown in the header), an order, and Download. No count before the download.
- Read the response as a stream to show progress ("Downloading… 12 MB"); for very large files, write straight to disk where the browser offers a save dialog (`showSaveFilePicker`), so the file never sits in memory.

## Words
- Short and plain: toasts in the past tense ("Task updated"); empty states "No <things>"; one general sentence in a confirmation ("This can't be undone."); no subtitle that repeats the title.
