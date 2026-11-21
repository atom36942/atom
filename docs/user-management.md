# User management

An optional feature: a page where some of an app's own users create and manage the app's other users (Atom's own pages don't have it). Build it only when the app needs it; it is not part of the login flow ([frontend.md](frontend.md)) every page has. Atom has every route it needs: never write a project user API.

## Backend: settings and grants only
- The roles it manages: `config_permission_user_roles` in `config_extend.py` (the app's users, e.g. `[2]`; never 1). The same list limits both user routes.
- Who may manage: grant permission 61 (`/permission/user-create`) and 62 (`/permission/user-update`: profile, password, deactivate; no delete) with `/admin/user-update` (`permissions`); nobody but root holds them by default. A granted user's page sees the ids in `/my/profile` `permissions` after a token renewal.
- What the list shows: `/private/user-read` returns the `config_column_users_private_read` columns; add `last_active_at` and the profile columns Edit profile needs in `config_extend.py`.
- What managers may not change: `config_permission_user_column_blocked` (Atom keeps `role`, `permissions` and the login columns in it).
- Set `config_api_global_user_check_deactivated = "realtime"` so a deactivated user is signed out at their next request, not at their next token renewal.
- Routes and checks in full: [auth.md](auth.md) (`/permission/user-create`, `/permission/user-update`).

## Page (Defaults: what the page calls; its look is the project's own)
- The list: `GET /private/user-read` (the `config_column_users_private_read` columns) filtered to the managed roles (`role = 2`, several: `role in 2,3`), plus `deactivated_at is null` / `is not null` and `{"username": "ilike,%text%"}` when chosen; cursor paging, newest first. Status is Active while `deactivated_at` is empty; `last_active_at` is set at most every 5 minutes by `/my/profile`.
- The roles it manages are one list in the page (`USERS_ROLES`), equal to `config_permission_user_roles`; adding a role is config only: that list, `config_permission_user_roles` and the label in `config_column_int_mapping` (shown from `/info`).
- New user (permission 61): `POST /permission/user-create` `{username, password, role}`.
- Update user (permission 62): `PUT /permission/user-update` with `{id, ...only the changed profile columns}`, `{id, password}` or `{id, deactivated_at}` (now to deactivate, `null` to activate). Atom refuses the blocked columns, users outside the managed roles and deactivating yourself; the page shows Atom's refusal in plain words.
