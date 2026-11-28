# User management

An optional feature: a page where some of an app's own users create and manage the app's other users (Atom's own pages don't have it). Build it only when the app needs it; it is not part of the login flow ([frontend.md](frontend.md)) every page has. Atom has every route it needs: never write a project user API.

## Backend: grants only
- Users live in the `master` database only: every user route reads and writes `master`, whatever `?connection=` a page uses for its data.
- Who may manage: grant 69 (`/admin/user-create`) and 70 (`/admin/user-update`: profile, password, deactivate), and 71 (`/admin/user-delete`) only when the page deletes or restores users, with `PUT /admin/user-update {"id", "permissions"}`; nobody but root holds them by default. A granted user's page sees the ids in `/my/profile` `permissions` after a token renewal; a revoked id stops their next request (both routes check live).
- A manager holds the whole route: they can change any user, including `role` and `permissions` (their own too). Grant 70 only to people you would trust as admin ([auth-permission.md](auth-permission.md#admin-routes-one-id-each)).
- What the list shows: `/private/user-read` returns the `users` columns in `config_users_private_read_column`; add `last_active_at` and the profile columns Edit profile needs to it in `config_extend.py`.
- Set `config_api_global_user_check_deactivated = "realtime"` so a deactivated user is signed out at their next request, not at their next token renewal.
- Routes in full: [auth.md](auth.md#4-managing-users).

## Page (Defaults: what the page calls; its look is the project's own)
- The list: `GET /private/user-read` (the `config_users_private_read_column` columns) filtered to the app's roles (`role = 2`, several: `role in 2,3`), plus `deactivated_at is null` / `is not null` and `{"username": "ilike,%text%"}` when chosen; cursor paging, newest first. Status is Active while `deactivated_at` is empty; `last_active_at` is set at most every 5 minutes by `/my/profile`.
- The roles it manages are one list in the page (`USERS_ROLES`); New user offers only those, and their labels come from `/info` (`info.int_mapping.master.users.role`, set in `config_users_role_label`).
- New user (69): `POST /admin/user-create` `{username, password, role, ...profile columns}` → `{"id": ...}`; profile columns go in the same insert, while the `config_users_update_alone_column` columns (`email`, `mobile`) and those `write_blocked` for `my` or `admin` (`permissions`, `deactivated_at`, ...) are set afterwards with an update.
- Update user (70): `PUT /admin/user-update` with `{id, ...only the changed profile columns}`, `{id, password}` or `{id, deactivated_at}` (now to deactivate, `null` to activate). The page shows Atom's refusal in plain words.
- Delete user (71), only if the app needs it: `DELETE /admin/user-delete?id=<id>&mode=soft` (`deleted_at = now()`, `deleted_by_id` = the manager; the user is refused at once at login and renewal) and `mode=restore` to undo it (`deleted_at` back to `null`). Prefer deactivation for a user who may come back; a soft-deleted user's rows are cleaned by the users-delete worker after `config_retention_day_user_soft_deleted` days. Show deleted users only if the page restores them: add `deleted_at` to `config_users_private_read_column` and filter `deleted_at is null` / `is not null`. Never `mode=hard` from a page (off unless `config_is_user_delete` and `users` left out of `control.row_delete_disabled`). The root user (id 1) is refused (403).
