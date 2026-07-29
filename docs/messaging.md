# 💬 Messaging & Notifications

Atom ships two related in-app features backed by dedicated tables: **direct messages** between users and **notifications** to a user. Both are ordinary tables, so they also work with the generic CRUD engine — the endpoints below add the conversation-specific logic on top.

---

## Direct messages

Messages live in the `message` table. Each row is one message from `created_by_id` (sender) to `user_id` (recipient), with a `read_at` timestamp.

### Send a message
Use generic create (see [crud.md](crud.md)) — the sender is stamped from the token:

```jsonc
POST /my/object-create?table=message
{"user_id": 42, "description": "hey there"}
```

### Inbox — `GET /my/message-inbox`
Returns the **latest message per conversation** (one row per person you've talked to), newest first — like a chat list.

- `mode` (required): `all`, `unread`, or `read`.
- `order`, `limit`, `page` for sorting/pagination (`has_next_page` included).

Conversations are grouped by the pair of participants, and only the most recent message in each is returned.

### Thread — `GET /my/message-thread?user_id=42`
Returns the full back-and-forth between you and one other user (both directions), paginated. **Side effect:** messages that other user sent you are marked read (`read_at = now()`) when you open the thread.

### Deleting
- `/my/object-delete` — delete messages you sent (own rows).
- `/my/object-delete-received` / `-received-all` — delete messages you *received* (for tables in `config_table_my_delete_all_received_enable`, which includes `message`).

---

## Notifications

The `notification` table targets a single user (`user_id`) with a `type`, `title`, `description`, an optional `reference_table` + `reference_id` (to link to the thing the notification is about), and a `read_at`.

Because it's a normal table, you use the generic engine:

```jsonc
// create a notification
POST /admin/object-create?table=notification
{"user_id": 42, "type": 1, "title": "Welcome", "reference_table": "test", "reference_id": 7}

// a user reads their own notifications
GET /my/object-read?table=notification&filter=["read_at is null"]&order=id desc

// mark read
PUT /my/object-update?table=notification
{"obj_list": [{"id": 100, "read_at": "2026-01-01T00:00:00Z"}]}
```

Bulk cleanup of received notifications is supported via `/my/object-delete-received*` (enabled for `notification`).

> Notifications can also be produced asynchronously — enqueue a create through a queue and let a worker insert it (see [workers.md](workers.md)).

---

## Table summary

| Table | Key columns | Used for |
|-------|-------------|----------|
| `message` | `created_by_id` (sender), `user_id` (recipient), `description`, `read_at` | 1:1 chat |
| `notification` | `user_id`, `type`, `title`, `description`, `reference_table`/`reference_id`, `read_at` | System alerts to a user |

Both carry the standard `created_at` / soft-delete columns and have retention settings in `config_table` (see [config.md](config.md#config_table)).

---

📚 [Back to README](../readme.md)
