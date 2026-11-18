# User management

An optional feature: a page where some of an app's own users create and manage the app's other users (Atom's own pages don't have it). Build it only when the app needs it; it is not part of the account flow ([frontend.md](frontend.md)), which every page has. Atom has every route it needs: never write a project user API.

## Backend: settings and grants only
- The roles it manages: `config_permission_user_roles` in `config_extend.py` (the app's users, e.g. `[2]`; never 1). The same list limits both user routes.
- Who may manage: grant permission 61 (`/permission/user-create`) and 62 (`/permission/user-update`: profile, password, deactivate; no delete) with `/admin/user-update` (`permissions`); nobody holds them by default, root included. A granted user's page sees the ids in `/my/profile` `permissions` after a token renewal.
- What the list shows: `/private/user-read` returns the `config_column_users_private_read` columns; add `last_active_at` and the profile columns Edit profile needs in `config_extend.py`.
- What managers may not change: `config_permission_user_column_blocked` (Atom keeps `role`, `permissions` and the login columns in it).
- Set `config_api_global_user_check_deactivated = "realtime"` so a deactivated user is signed out at their next request, not at their next token renewal.
- Routes and checks in full: [auth.md](auth.md) (`/permission/user-create`, `/permission/user-update`).

## Page
- A header button, Users (people icon), the last before the avatar, open to every logged-in user; the list reads `GET /private/user-read` (columns: `config_column_users_private_read`, plus `last_active_at` and the profile columns Edit profile needs) filtered to the roles the page manages, active or inactive, and a username search; columns ID, Created, Username, Last active (`last_active_at`, set at most every 5 minutes by `/my/profile`: "5 min ago", "Never" when empty), Role, Permissions, Status, Action; 25 a page after the cursor, newest first.
- The roles it manages are one list in the page (`USERS_ROLES`), equal to `config_permission_user_roles`; today one role. New user (permission 61, `/permission/user-create`): Role first (always shown, each option `2 (General)`; disabled while the list has one role, a choice once it has several), then Username and Password; it sends `{username, password, role}`. Adding a role is config only: the page's list, `config_permission_user_roles` and the label in `config_column_int_mapping`.
- Each row's ⋯ (permission 62, `/permission/user-update`, every row, your own too): Edit profile, Reset password, Deactivate (Activate when inactive); each sends one request with only what changed. Your own Deactivate explains in a toast that you can't (Atom refuses it too).
- Actions shown to everyone (a UI default, not a rule): every user sees the same buttons and menu items, permission or not, on every row (their own too); clicking one they may not use shows a toast saying why ("You are not allowed to do this. Ask an admin for access.", "You can't deactivate yourself.") instead of the control being hidden or disabled. The server still refuses it; the toast only explains.
