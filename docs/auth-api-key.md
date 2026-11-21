# API keys (machine access)

Machine-to-machine authentication for scripts, scheduled jobs and other companies' systems: a long-lived **API key** instead of a password login, owned by a **service account**. Terms used here, as in the industry:

| Term | Meaning in Atom |
| :--- | :--- |
| API key | An opaque secret (`atk_` + 32 random bytes), not a JWT: it carries no data. Sent as `Authorization: Bearer atk_...`, like a JWT; the `atk_` prefix tells them apart (a JWT starts `eyJ`) |
| Service account | A `users` row that stands for a system, not a person (e.g. `wms@company.com`); it owns the system's keys |
| Key prefix | The first 12 characters (`atk_7Hk2xQ9p`), stored in clear so a key can be recognised in a list |
| Key hash | sha256 of the key: the only form stored, so the key is shown once, at creation |
| Scopes | Optional list of route paths a key may call; empty means every route that allows keys |
| Expiry | Optional `expire_days`; an expired key is refused |
| Revocation | Deleting the key; deactivating the service account revokes all its keys |
| Rotation | Create a new key, switch the system to it, delete the old one (keys are never edited) |

| Step | How |
| :--- | :--- |
| Create | `POST /my/api-key-create {"name": "Warehouse push", "scopes": ["/shipment/event-create"], "expire_days": 365}` → `{"id", "key", "key_prefix", ...}`. The key is shown only here. At most `config_api_key_max` keys per user (`20`) |
| Allow a route | `"api_key"` in its `config_api` `auth` list: `["api_key"]` for machines only, `["jwt", "api_key"]` for people and machines (a project sets it in `config_extend.py`). No Atom route allows keys by default |
| Call | `Authorization: Bearer atk_...` on any allowed route |
| List | `GET /my/object-read?table=api_key` (own keys; `/admin/object-read` for all): name, prefix, scopes, expiry; `key_hash` is in `config_column_read_blocked`, so never returned |
| Revoke | `POST /my/object-delete {"table": "api_key", "ids": [3]}` (own keys); `POST /admin/object-delete` (any key). A hard delete of the key row only; the service account is untouched |

How a request is checked (middleware, right after the JWT step):
```
Bearer atk_... → sha256 → api_key JOIN users (cached per worker for config_api_key_cache_sec, 60 s)
→ unknown or expired key, deleted or deactivated owner: 401
→ request.state.user = the owner's config_column_token_encode columns + _token_type "api_key", _api_key_id, _api_key_scopes
→ route whose auth lacks api_key: 401 · key with scopes not listing this path: 403
→ role, permission, rate-limit and the other checks run as for a JWT
```

## Example: a partner system sends data
A warehouse system (WMS) pushes shipment events into the app.
1. **Service account** (admin, once): `POST /admin/user-create {"role": 2, "username": "wms@company.com", "password": "..."}`.
2. **Key**: log in once as that account, `POST /my/api-key-create {"name": "WMS push", "scopes": ["/shipment/event-create"]}`; give the key to the WMS team (it lives in their system's settings, never in code or chat).
3. **Route**: the project writes the route the partner calls, like any route (`router_extend/shipment.py`, `function_extend/shipment.py`), and allows keys on it:
   ```python
   # config_extend.py
   "/shipment/event-create": {"id": 210, "auth": ["api_key"], "rate_limit": {"mode": "inmemory", "limit": 600, "window_sec": 60}},
   ```
4. **Call** (WMS side):
   ```bash
   curl -X POST https://app.company.com/shipment/event-create \
     -H "Authorization: Bearer atk_..." -H "Content-Type: application/json" \
     -d '{"shipment_no": "S123", "status": "loaded", "at": "2026-11-20T10:00:00Z"}'
   ```
   The row is saved with `created_by_id` = the service account.

Prefer a project route like this for an outside system over opening a generic route: it is a fixed contract (its own fields and checks, unchanged when the app changes) and reaches one table only. Scopes limit paths, not tables, so a key allowed on `/my/object-create` can create rows in every table that route accepts. Generic routes suit your own scripts (`/my/object-read` for a report).

- **One owner:** a key acts as the user who created it (`created_by_id`), with that user's role, permissions and row ownership. Use one service account per system: the integration outlives any person, and its rows and `log_api` entries (`/my/api-usage`) show which system made them.
- **Only one route of its own:** creating needs the server to make and hash the key, so it has `/my/api-key-create`; reading and revoking use the generic routes. `api_key` is in `config_table_my_create_blocked` (no generic create) and in `config_postgres` `table_row_update_disable`, so the database refuses every `UPDATE`: a key is never edited, only revoked and created again.
- **Revocation delay:** a resolved key is cached per worker, so a revoked key stops within `config_api_key_cache_sec` (60 s; `0` for at once). Deactivating or deleting the service account stops all its keys the same way; a deleted user's keys are removed with their other rows.
- **Machine or person:** a route that must tell them apart reads `request.state.user["_token_type"] == "api_key"`. `/my/token-refresh` and the message socket never accept a key.
