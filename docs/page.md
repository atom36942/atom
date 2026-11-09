# Pages

Patterns that work well for an app page on Atom (`static_extend/<app>/`). They are Atom's defaults, already weighed: use them as written and differ only for a real reason (say why in the project's docs), so no page re-decides them. The page and its files are the project's own; Atom provides the backend they call. The firm rules (where code goes, storage keys, token refresh, speed) are in [AGENTS.md](../AGENTS.md); this page shows how they fit together.

## Structure
- One page per app: `index.html`, `css/<app>.css`, `js/app.js`, plus small shared helpers (a Sync dialog, a download helper) kept as their own files and copied unchanged between apps, so every app behaves the same. Plain HTML, CSS and JS work well; a framework or bundler is the project's choice.
- Every colour and size as a CSS variable in one theme block (brand, neutrals, status colours, text sizes, control heights, paddings), so a page never types a colour twice and a second app can share the look.
- Element ids, function names and routes stay each app's own; what users see (login, header, dialogs, words) is worth keeping the same across a project's apps.

## Login
- `POST /auth/login-username-password` with `{username, password, role}` (the role your app serves), then `GET /my/profile`; show the app only for that role and a user that is not deactivated or deleted.
- Keep the login alive with `POST /my/token-refresh` (refresh token as Bearer) shortly before the access token expires and when the tab comes back into view; a request that gets 401 refreshes once and retries. A refused refresh shows the login form with a plain sentence ("Your session has expired. Please log in again."), never a token error.
- Keep the form short: username, password (with show/hide) and one button.

## Header and account
- App name on the left, the app's views in the middle, actions on the right (icon plus a short label), then an avatar menu: My profile (read-only), Login details (only the password editable, through `PUT /my/user-update`), Logout (with a confirmation).

## Dialogs and loading
- One dialog structure everywhere: a header (title, optional subtitle, close), a body, an action row (Cancel first, the main action last). Escape and the close button close it; a running action keeps it open.
- Open a dialog at its final size: draw its frame (the empty table or calendar) first, faded, then fill in the data, so nothing jumps. A list that reloads keeps its rows, faded, until the new ones arrive; a bare "Loading…" only when there is nothing to show yet.

## Browser storage
- localStorage for small items (login, user, remembered choices), one key per app; IndexedDB for larger data the page keeps (filter options, dashboard totals); memory for what is on screen; logout clears all of it, in every open tab.
- Download reference data once after login and refresh it on a timer and on request (a Sync button); live lists always come from the server.

## Lists and paging
- The server sends a page plus `has_next_page` (it fetches one row more than asked), never a total count: counting a growing table gets slow, and a page only needs to know whether Next is possible.
- Page after the last row, not by page number: Atom's `object-read` routes take `after_id` and return `next_after_id` (order by `id`); a project's own list route returns a cursor (`next_after`) built from its sort column and `id`. Keep the cursors of the pages seen so Previous goes back without OFFSET. Details: [crud.md](crud.md).
- Give every filter and sort column an index that matches it (for "comments of a task, newest first": `btree(task_id,id)`).

## Export
- The project's export route (`/<feature>/export`) checks its params, builds one query and returns `func_postgres_export` (or `func_mssql_export`, `func_clickhouse_export`) through `func_csv_response`: streamed, compressed, at most `config_export_limit` rows. Details: [crud.md](crud.md) and [config.md](config.md).
- A simple dialog: "Use the list's filters" (showing the picked filters), a Rows box with a sensible default and a few choices up to the maximum (`/info` `export_limit`, also shown in the header), an order, and Download. No count before the download.
- Read the response as a stream to show progress ("Downloading… 12 MB"); for very large files, write straight to disk where the browser offers a save dialog (`showSaveFilePicker`), so the file never sits in memory.

## Words
- Short and plain: toasts in the past tense ("Task updated"); empty states "No <things>"; one general sentence in a confirmation ("This can't be undone."); no subtitle that repeats the title.
