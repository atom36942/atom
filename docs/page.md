# Pages

Patterns that work well for an app page on Atom (`static_extend/<app>/`). They are Atom's defaults, already weighed: use them as written and differ only for a real reason (say why in the project's docs), so no page re-decides them. The page and its files are the project's own; Atom provides the backend they call. The firm rules (where code goes, storage keys, token refresh, speed) are in [AGENTS.md](../AGENTS.md); this page shows how they fit together.

## Structure
- One page per app, starting as one `<app>.html` with its CSS and JS inline; once it has its own assets or grows large (about 3000+ lines), a folder: `index.html`, `css/<app>.css`, `js/app.js`, plus small helpers (a Sync dialog, a download helper) as their own files, each app keeping its own copy (copied unchanged between apps, never one file two pages load), so every app behaves the same. Plain HTML, CSS and JS work well; a framework or bundler is the project's choice.
- Every colour and size as a CSS variable in one theme block (brand, neutrals, status colours, text sizes, control heights, paddings), so a page never types a colour twice and a second app can share the look.
- Element ids, function names and routes stay each app's own; what users see (login, header, dialogs, words) is worth keeping the same across a project's apps.

## Page standard
Atom's pages that log in (Admin, Monitor, API, Message) are built the same way, so a new page or project copies the structure instead of deciding it again. Each page carries five blocks, copied unchanged from page to page (a test, `tests/test_page_auth.py`, fails when a copy differs); only what is around them is the page's own.

| Block | Where in the page | What it holds |
| :--- | :--- | :--- |
| theme (`<!-- ==== atom page: theme ==== -->`) | in `<head>`, before `<style>` | sets `<html data-theme data-density>` before the page draws from the page's own localStorage key (`<html data-storage-key>`, the same as `PAGE.key`), under `settings`: `theme` (`dark`, the default, `light`, or `system`: the computer's mode, followed as it changes) and `density` (`comfortable`, the default, or `compact`: `--control-h` and `--cell-y` smaller). Each page keeps its own; logout removes the whole key, so the page is back on its defaults; every tab of the page follows a change |
| look (`/* ==== atom page: look ==== */`) | first in `<style>` | the palette (dark on `:root`, light on `:root[data-theme="light"]`; `--hl` is the overlay colour, white on dark and ink on light, so a page writes `rgba(var(--hl),.06)`, never a fixed white), one type scale (13px controls and dialog text, 12px small text, 15px dialog titles, 14px page text), base controls, the dialog (a header filled with the brand colour, a padded body, actions on their own band), the login page, key-value rows, the toast (bottom right, centred on a phone: a check or !, the message, ×; 6 s, kept while hovered; a popover above any dialog), the account menu. Base element rules use `:where()`, so the page's own classes always win |
| account (`/* ==== atom page: account ==== */`) | first in `<script>`, after `PAGE` | `Page`: storage, login, token renewal, the user check, the cache, the sync, the account dialogs and the shared dialog |
| account header (`<!-- ==== atom page: account header ==== -->`) | the right end of the page's header | Log in (logged out, on a page that works without a login) and the avatar with its menu (logged in) |
| dialogs (`<!-- ==== atom page: dialogs ==== -->`) | the end of `<body>` | the login page, the blocked-account dialog, the shared dialog, the toast |

**`PAGE`**, set just above the account block, is the only part that differs: `key` (the localStorage key and IndexedDB database), `title`, `role` (the login role; `null` for any role), `loginRequired` (`false` lets the page work logged out, with a Log in button), `idb` (whether it keeps data in IndexedDB), and the hooks `refresh` (downloads the page's data into the cache), `onIn` (logged in: show the page), `onOut` (logged out: forget what it shows), `onSynced` (a sync finished: draw again) and `intro` (the login page's left side: `{heading, text, features: [[svg paths, title, line], …]}`, four features). The page calls `Page.start()` last.

**`Page`** is what the page's own code uses: `api(path, options)` (Atom's `{status, message}` answer, the token added, a 401 renewed once), `request` (the raw response, for downloads), `read()` and `save(changes)` (the localStorage object), `user()`, `cacheGet(name)` and `cacheSet(name, data)` (IndexedDB records `{name, user_id, saved_at, data}`), `syncData()` (the page's download, one at a time), `dialog`, `form({title, body, ok, tone, submit})`, `confirm(title, text, ok, danger)`, `toast(text, isError)`, `kv(rows)`, `esc`, `loggedIn()`, `signIn(token)`, `logOut(message)`, `tokenFresh()` and `tokenRefresh()`. Every dialog of the page (its own forms and confirmations too) goes through `dialog`, `form` and `confirm`, so all of them look and behave alike.

**The flow**: open with a valid token object → `onIn` draws from the cache; no cache yet (the first login, a cleared browser) → `syncData()` downloads it first. The cache is used until the next sync: every 3 hours (checked every minute and when the tab comes back) or Sync now in the Sync dialog. Logged out → the login page (it cannot be closed on a page that needs a login) or, on a page that works logged out (API), the Log in button, which shows only the login card over the page (× or Escape closes it).

| Page | `PAGE` | Its data in IndexedDB |
| :--- | :--- | :--- |
| Admin | `key: "admin", role: 1, loginRequired: true, idb: true` | `reference`: schema, `/info`, row counts, settings, triggers, CHECK constraints |
| Monitor | `key: "monitor", role: 1, loginRequired: true, idb: false` | none (every tab reads live) |
| API | `key: "api", role: null, loginRequired: false, idb: true` | `openapi`: `/openapi.json` (logged out, a copy over 3 hours old is downloaded again on open) |
| Message | `key: "message", role: null, loginRequired: true, idb: false` | none (messages are live) |

## Login
The account block does this; it is the default for a project's pages too.
- **Storage**: one localStorage key named after the page, holding one JSON object `{v, token, user, info, synced_at, ...small choices}`. `token` is exactly what `/auth/login-*` and `/my/token-refresh` return: `{access_token, refresh_token, access_token_expires_at, refresh_token_expires_at}` (the two times are unix seconds). `user` is `GET /my/profile`, the only copy of the user (never a separate `username`). `info` is `{config_column_int_mapping, export_limit}` from `GET /info`: every label (a role, a status) and setting the page shows comes from it, never written in the page; before the first sync a role shows as its number. `synced_at` is when the user (and the page's reference data) was last downloaded. `v` is the layout version: a different `v` keeps the token and the user and drops the rest.
- **Logged in = a valid token object**: both tokens as non-empty text, both expiry times as numbers, and `refresh_token_expires_at` still in the future. Anything else (no `token`, a missing field, an expired refresh token) means logged out: the page clears its key (and its IndexedDB database) and shows the login form. An expired access token alone is not a logout while the refresh token is valid: the page renews first. A token is stored only after it passes this check, from login or refresh.
- **Login**: `POST /auth/login-username-password` `{role, username, password}` (the role the page serves), store `token`, `GET /my/profile` into `user`, then check the user: the page's role (otherwise "<Title> access is unavailable."), `deactivated_at` and `deleted_at` empty (otherwise the blocked-account dialog, below). Then the first sync (`/info`, reference data into IndexedDB, then `synced_at`) and the page.
- **Keep it alive**: on open, every minute and when the tab comes back into view, read `token.access_token_expires_at`; with 5 minutes or less left, `POST /my/token-refresh` (refresh token as Bearer) and store the new token object. A refused refresh (401/403) or an expired refresh token shows the login form with "Your session has expired. Please log in again.", never a token error; a network failure keeps the token and tries again at the next check. A request that gets 401 refreshes once (one shared refresh for every request in flight) and retries; refused again, log out.
- **Sync**: when `synced_at` is 3 hours old (checked with the token) and from Sync in the account menu: new token, `/my/profile` (with the user check), `/info`, the page's reference data, then `synced_at`; a browser with no `info` syncs at once. The Sync dialog is described under Header and account.
- **Logout**: a confirmation, then remove the localStorage key, delete the IndexedDB database and clear memory. Other open tabs get the `storage` event for the key, find no valid token and show the login form ("You logged out in another tab.").
- **Login page** (the same layout as the projects' pages, in Atom's dark colours): a wordmark top left; on the left a badge (the page's title), a serif heading, one line and four feature cards (`PAGE.intro`); on the right the login card: a filled header "Login" with "For role N accounts" (or "For any role", then a Role box), Username and Password (icons, show/hide), a full-width Login button. Phones: the cards hide and the card stacks under the heading. While it shows, the rest of the page is inert.
- **Blocked account**: Atom's refusal (403 "account deactivated" / "account deleted", at login, token renewal or any route) or a profile with `deactivated_at` / `deleted_at` logs out and opens a dialog over the login page, "Account deactivated" ("Your account is deactivated. Please contact your admin.") or "Account deleted" ("Your account was deleted. Please contact your admin."), with one OK; only OK closes it.
- A download that finishes after a logout saves nothing (no stray `info` or cache records).

## Header and account
- App name on the left, the app's views in the middle, actions on the right (icon plus a short label), then an avatar with the username's initials (the words before an `@`: `om.srivastava` → OS; one word gives its first two letters) and its menu: My profile (read-only), Login details (only the password editable, through `PUT /my/user-update`), Settings, Sync, Logout (with a confirmation).
- The account parts use the same words on every page:

| Part | Shows |
| :--- | :--- |
| Menu | My profile, Login details, Settings, Sync, Logout (Logout in red); icons in the text colour |
| Settings | Title "Settings", subtitle "Saved in this browser"; one bordered row per setting, then Done: Theme (Dark, Light, System) and Density (Comfortable, Compact), each one choice applied at once (arrow keys move it). A new setting is a new entry in `SETTINGS` |
| My profile | Created (how long ago: Today, Yesterday, `N days ago`; the date on hover), then Name, Job title, Email, Mobile, City, Country, About (`users` columns `name`, `job_title`, `email_secondary`, `mobile_secondary`, `city`, `country`, `about`: what a user changes without OTP; the login email and mobile are not shown). Edit opens one form with them all; Save sends only the changed ones, `PUT /my/user-update` (an emptied field is `null`), then reloads the profile. Email and Mobile are checked as `config_column_regex` checks them. Each field is in My profile or Login details, never both |
| Login details | Username (with a copy button, toast "Username copied"), Password (8 dots and a pencil), Role (`Admin (1)`, the label from `info`; the number alone before the first sync), Permissions (one tag per permission, `User delete (132)` from `config_column_int_mapping["users"]["permissions"]`, wrapping onto more lines; `None` when there are none) |
| Update password | New password, Confirm new password, "6–120 characters, no spaces."; Cancel (back to Login details), Update password; errors "Use 6–120 characters, no spaces" and "Passwords don't match"; success closes the dialog with the toast "Password updated" |
| Logout | "Logout?", "Are you sure you want to logout?", Cancel, Logout; nothing shown after |
| Sync | Title "Sync", subtitle "Last synced 5 min ago (auto sync every 3 hours)" ("just now", "3 hr ago", or "Never synced"); Local storage and IndexedDB as "Used, N items" or "Not used"; Close, Sync now. While it runs, the steps ("Renewing login… (1 of 4)") and a progress bar, the dialog locked; then "Everything is up to date." or "Sync failed. Please try again." |

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
