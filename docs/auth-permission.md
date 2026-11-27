# Permissions

Which users may call a route, beyond their role. Part of [auth](auth.md).

`users.permissions` (`smallint[]`, nullable) holds the route ids a user may call: each is a `config_api` route's `id`. `NULL` and `[]` grant none. One id is one route, nothing else: no table map, no actions.

It holds only route ids. Any other access a project needs, such as which rows a user may see (their countries, companies or branches), goes in its own `users` column added in `config_extend.py` (e.g. `report_country text[]`), never as made-up ids in `permissions`: the ids share one numbering with the routes, so a later route with the same id would be granted with it. Such a column is set only through `/admin/user-update` (add it to `config_column_users_my_blocked`), and the project's routes read it from the database on each request, so a change applies without a new login.

A request passes these gates, in order, before the route runs. Role and permission are independent: a route sets either or both, and either one needs a credential (a non-empty `auth`).

| # | Gate | Route key | Fails with |
|---|---|---|---|
| 1 | Credential | `auth`: `["jwt"]` (access token), `["api_key"]` (API key) or both; `[]` is public | 401 |
| 2 | Role: the user's role is in the list | `"user_check_role": {"mode": "token", "roles": [2]}` | 403 `access denied` |
| 3 | Permission: the route's own `id` is in the user's `permissions` | `"user_check_permission": {"mode": "token"}` or `{"mode": "realtime"}` | 403 `permission denied` |

## Admin routes: one id each

Every `/admin/*` route has `user_check_permission` and no role check (startup refuses an admin route without it). A user may call an admin route when its id is in their `permissions`, whatever their role; a role 1 user without the ids is refused like anyone else.

- **Root** (user id 1) holds every `/admin/*` route id, set at every start by `func_root_user_permissions_sync` (one `UPDATE`, only when they differ, also with schema init off): a new admin route reaches root without a grant, and an id that left goes at the next start. Root's next login carries the new ids. A project's other permission routes are never root's (a restart removes one granted by hand).
- **Others** get an id by `PUT /admin/user-update {"id": <user>, "permissions": [66, 72]}`. Each admin id is labelled with its path in `config_column_int_mapping["users"]["permissions"]` (`66: "/admin/object-update"`), so an admin page lists them; a project may relabel one in plain words.
- **Modes**: read routes check the token (`token`: a grant applies at the next login); write routes check the users row on every call (`realtime`: a revoked id stops the next request).
- **What a grant gives**: the whole route, as root has it. `/admin/object-update` (66) edits any row of any table (except `users` and `config_table_write_blocked`); `/admin/user-update` (70) changes any user, including their `role` and `permissions`, so someone holding 70 can make themselves admin. Grant those two only to people you would trust as admin. Every change is stamped (`updated_by_id`, `created_by_id`) and every call is in `log_api`.

| Need | Grant |
|---|---|
| Manage the app's users (create, edit, deactivate) | 69 `/admin/user-create`, 70 `/admin/user-update` |
| Edit or delete anyone's rows of the app's tables | 66 `/admin/object-update`, 72 `/admin/object-delete` (and 67 `/admin/object-read` to read them) |
| Raw SQL writes | 86 `/admin/postgres-query-runner-write` |

```bash
curl -X PUT "$BASE_URL/admin/object-update?table=task" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"id": 7, "status": 2}'
curl -X POST "$BASE_URL/admin/object-delete" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"table": "task", "ids": [7]}'
```

Which tier for which need: own rows only `/my/object-*` (no grant); every logged-in user reads `/private/object-read` (`config_table_private_read_allowed`); selected users act on anyone's rows: the admin route's id; a business rule (only some columns, a check across tables, a side effect): a project route with its own id.

## A project route

A project route works the same way, for example only some role 2 users may close a task:

```python
# config_extend.py
"/task/close": {"id": 205, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [2]}, "user_check_permission": {"mode": "token"}},
"users": {**base_config_column_int_mapping["users"], "role": {1: "Admin", 2: "User"}, "permissions": {**base_config_column_int_mapping["users"]["permissions"], 205: "Task close"}},
```

- **Granting**: only `/admin/user-update` writes `permissions`; `/my/user-update` refuses it (`config_column_users_my_blocked`) and the object routes refuse `table=users`.
- **Startup refuses**: a mode other than `token` or `realtime`; any other key (an `action`); an id without a label in `config_column_int_mapping["users"]["permissions"]`; `token` mode without `permissions` in `config_column_token_encode`.
