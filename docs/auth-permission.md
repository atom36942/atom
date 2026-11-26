# Permissions

Which users may call a route or act on a table, beyond their role. Part of [auth](auth.md).

`users.permissions` (`smallint[]`, nullable) holds the permission ids a user holds. A permission id is either a route's `config_api` id (a route that asks for it) or an id from `config_permission_table` (one table and action on the `/permission/object-*` routes). `NULL` and `[]` grant none.

It holds only those two kinds of id: what a user may call or do. Any other access a project needs, such as which rows a user may see (their countries, companies or branches), goes in its own `users` column added in `config_extend.py` (e.g. `report_country text[]`), never as made-up ids in `permissions`: the ids share one numbering with the routes, so a later route with the same id would be granted with it. Such a column is set only by an admin (`/admin/user-update`; add it to `config_column_users_my_blocked` and `config_permission_user_column_blocked`), and the project's routes read it from the database on each request, so a change applies without a new login.

A request passes these gates, in order, before the route runs. Role and permission are independent: a route sets either or both, and either one needs a credential (a non-empty `auth`). Startup enforces each group's gate: every `/admin/*` route checks role 1 (other roles and a permission may be added), every `/permission/*` route checks a permission (a role may be added).

| # | Gate | Route key | Fails with |
|---|---|---|---|
| 1 | Credential | `auth`: `["jwt"]` (access token), `["api_key"]` (API key) or both; `[]` is public | 401 |
| 2 | Role: the user's role is in the list | `"user_check_role": {"mode": "token", "roles": [2]}` | 403 |
| 3 | Permission: the route's own `id` is in the user's `permissions` | `"user_check_permission": {"mode": "token"}` | 403 |
| 3 | Permission on a `/permission/object-*` route: `config_permission_table[<?table=>][<action>]` is in the user's `permissions` | `"user_check_permission": {"mode": "token", "action": "update"}` | 403 (also when the table or action is not in the map) |

## Object permissions: one id per table and action

The `/permission/object-*` routes change or read anyone's rows of a table for selected users. One map in `config.py` says which tables they reach and which id each action needs:

```python
config_permission_table = {"ticket": {"read": 120, "update": 121, "delete": 122}, "ticket_comment": {"create": 123, "read": 124, "update": 125, "delete": 126}}
```

| Route | Action | Body / query |
|---|---|---|
| `POST /permission/object-create?table=` | `create` | the rows, as `/my/object-create`; `created_by_id` is the caller |
| `GET /permission/object-read?table=` | `read` | `filter`, `order`, `column`, `limit`, `after`/`page` (no relations: a related table would need its own read) |
| `GET /permission/object-read-export?table=` | `read` | `filter`, `order`, `column`, `limit`; CSV |
| `PUT /permission/object-update?table=` | `update` | the rows with `id`; `updated_by_id` is the caller |
| `POST /permission/object-delete?table=` | `delete` | `{"ids": [...]}` |

- The middleware reads `table` from the query, finds the id for the route's `action` and checks the user holds it; the routes check nothing more. A table or action missing from the map is refused, so a table is reachable only through what the map lists.
- A project adds its tables in `config_extend.py`, with ids from 200 that no route uses, each labelled:
  ```python
  config_permission_table = {**base_config_permission_table, "task": {"update": 211, "delete": 212}, "task_comment": {"update": 213, "delete": 214}}
  "permissions": {**base_config_column_int_mapping["users"]["permissions"], 211: "Task update", 212: "Task delete", 213: "Comment update", 214: "Comment delete"},
  ```
- **Startup refuses**: an action other than `create`, `read`, `update`, `delete`; `users` in the map (users go through `/permission/user-*`); an id used twice, used by a `config_api` route, or without a label; `action` on a route other than `/permission/object-*`.
- The routes' own ids (98, 99, 100, 59, 60) grant nothing: they only name the route in logs.

## Recipe: a team's create, read, update and delete on any table

No route or function to write: a table, one map entry, labels and grants.

| Step | Where | What |
|---|---|---|
| 1. The table | `config_extend.py`, `config_postgres_schema_master` | The columns, plus `created_by_id`, `updated_by_id`, `updated_at` (create and update stamp them) and an index for every filter and sort |
| 2. The actions | `config_extend.py`, `config_permission_table` | Only the actions the team needs, each its own id from 200 that no route uses: `"vendor": {"create": 220, "read": 221, "update": 222, "delete": 223}` |
| 3. The labels | `config_extend.py`, `config_column_int_mapping["users"]["permissions"]` | `220: "Vendor create", 221: "Vendor read", ...`; startup refuses an unlabelled id |
| 4. The grants | `PUT /admin/user-update` `{"id": <user>, "permissions": [221, 222]}` | Who may do what: a viewer 221, an editor 221 + 222, a lead all four; a user logs in again to get them (token mode); root holds them all |
| 5. The page | `static_extend/<page>/` | Calls the routes with `?table=vendor`: list `GET /permission/object-read` (`filter`, `order`, `limit`, `after`), CSV `GET /permission/object-read-export`, add `POST /permission/object-create`, edit `PUT /permission/object-update` (`{"id", ...changes}`), remove `POST /permission/object-delete` (`{"ids": [...]}`). It may read `/my/profile` `permissions` to know what to offer; the server checks every call anyway |

```python
# config_extend.py
from config import config_permission_table as base_config_permission_table
config_permission_table = {**base_config_permission_table, "vendor": {"create": 220, "read": 221, "update": 222, "delete": 223}}
config_column_int_mapping = {**base_config_column_int_mapping, "users": {**base_config_column_int_mapping["users"], "permissions": {**base_config_column_int_mapping["users"]["permissions"], 220: "Vendor create", 221: "Vendor read", 222: "Vendor update", 223: "Vendor delete"}}}
```
```bash
curl -G "$BASE_URL/permission/object-read" -H "Authorization: Bearer $TOKEN" --data-urlencode 'table=vendor' --data-urlencode 'filter=["status = 1"]'
curl -X PUT "$BASE_URL/permission/object-update?table=vendor" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"id": 7, "status": 2}'
curl -X POST "$BASE_URL/permission/object-delete?table=vendor" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"ids": [7]}'
```

Which tier for which need: own rows only `/my/object-*` (no grant); every logged-in user reads `/private/object-read` (`config_table_private_read_allowed`); selected users act on anyone's rows `/permission/object-*` (this recipe); a business rule (only some columns, a check across tables, a side effect) a project route with its own permission id.

## Atom's permission ids

```python
"/admin/postgres-query-runner-write": {"id": 86, "is_active": True, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_permission": {"mode": "realtime"}, ...},
"/permission/object-update": {"id": 59, "auth": ["jwt"], "user_check_permission": {"mode": "token", "action": "update"}},
"/permission/user-create": {"id": 61, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "rate_limit": {...}},
"/permission/user-update": {"id": 62, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "rate_limit": {...}},

config_column_int_mapping = {"users": {"role": {1: "Admin"}, "permissions": {61: "Create user", 62: "Update user", 86: "Postgres query runner write", 120: "Ticket read", 121: "Ticket update", 122: "Ticket delete", 123: "Ticket comment create", 124: "Ticket comment read", 125: "Ticket comment update", 126: "Ticket comment delete"}}, ...}
```

| Id | Checks | Who may call it |
|---|---|---|
| 86, raw SQL writes | role 1 + permission | admins granted 86; a role 2 user granted 86 is still refused by the role |
| 120, 121, 122: `ticket` read, update, delete; 123–126: `ticket_comment` create, read, update, delete (anyone's) on `/permission/object-*` | permission only | users granted it, any role (a support team); 120 also opens the Tickets page |
| 61, 62: `/permission/user-create`, `/permission/user-update` | permission only | users granted it, any role; only users of roles in `config_permission_user_roles` (default none, never 1) |

Root (id 1) holds exactly these at every startup: every `/admin/*` and `/permission/*` route id with a permission check (86, 61, 62 and a project's) and every `config_permission_table` id (Atom's and a project's). So root can use every admin and permission flow, the Tickets page included, and keeps nothing stale (an id that left goes at the next start). A project's other permission routes (outside `/admin` and `/permission`) are for other users, granted explicitly; root never holds them (a restart removes one granted by hand).

A project route works the same way, for example only some role 2 users may delete a task:

```python
# config_extend.py
"/task/delete": {"id": 205, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [2]}, "user_check_permission": {"mode": "token"}},
"users": {**base_config_column_int_mapping["users"], "role": {1: "Admin", 2: "User"}, "permissions": {**base_config_column_int_mapping["users"]["permissions"], 205: "Task delete"}},
```

- **Mode**: `token` only (the token's `permissions`); a change applies when the user logs in again.
- **Granting**: only `/admin/user-update` writes `permissions`; `/my/user-update` refuses it (`config_column_users_my_blocked`) and the object APIs refuse `table=users`.
- **Permission without role**: drop `user_check_role` and any role granted the `id` may call the route.
- `user_check_permission` modes: `token` (from the token) or `realtime` (from the users row on each call, so a revoked permission stops at once; Atom's admin write routes use it). **Startup refuses** any other mode, or an `id` without a label in `config_column_int_mapping["users"]["permissions"]`.
