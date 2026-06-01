# Object APIs Overview

Atom provides a set of dynamic, generic API endpoints designed to handle CRUD (Create, Read, Update, Delete) operations across any database table defined in your schema. Instead of writing separate endpoints for `/users`, `/jobs`, or `/posts`, you use the generic `/object-*` endpoints and specify the `table` query parameter.

These endpoints exist across different namespaces (`/public`, `/my`, `/admin`), each enforcing different levels of security, ownership tracking, and data visibility automatically.

---

## 1. Object Endpoints

### `object-create` (POST)
Handles single or bulk insertions of JSON objects into a database table.

- **Query Parameters**: 
  - `table` (str): The name of the database table.
  - `mode` (str): Defaults to `"now"`. Can be set to `"buffer"` to enqueue the insert into memory instead of writing immediately.
  - `queue` (str): Optional. Specify a message broker (e.g., `"celery"`, `"kafka"`) to offload the insertion task to a background worker.
- **Body**: A JSON object or an array of objects wrapped in `{"obj_list": [...]}`.

### `object-read` (GET)
Fetches data dynamically with support for filtering, pagination, and relational joins.

- **Query Parameters**:
  - `table` (str): The name of the database table.
  - `limit` (int): Number of records to return.
  - `page` (int): Offset calculation.
  - `order` (str): e.g., `"id desc"`.
  - `column` (str): Specific columns to fetch, e.g., `"id, name, created_at"`.
  - `filter` (list): JSON-encoded list of conditions, e.g., `[["status", "=", 1]]`.
  - `relation` (list): JSON-encoded list for fetching joined tables.

### `object-update` (PUT)
Modifies existing records. Requires every object in the payload to have a valid primary key (`id`).

- **Query Parameters**:
  - `table` (str): The name of the database table.
  - `queue` (str): Optional. Offload to a message broker.
- **Body**: Array of objects containing the `id` and the fields to update.

### `object-delete` (POST)
Performs bulk soft or hard deletions based on an array of IDs.

- **Body**: 
  - `table` (str): The database table.
  - `ids` (list of integers): Array of IDs to delete.

---

## 2. Namespace Behaviors

The core logic of these endpoints remains the same, but the namespace (`/admin`, `/my`, `/public`) drastically alters their security boundaries.

### `/my` (Authenticated User Namespace)
This is the standard namespace for logged-in users interacting with their own data.
- **Security Check**: Enforced by global middleware (requires valid JWT).
- **Creation (`/my/object-create`)**: The API completely ignores any provided `created_by_id`. It forcibly attaches the logged-in user's ID to the payload, ensuring absolute ownership tracking. Restricted admin columns (like `is_superuser`) are automatically blocked.
- **Reading (`/my/object-read`)**: The API automatically injects a `created_by_id = <user_id>` constraint into every `filter` condition. A user can *only* read records they own.
- **Updating (`/my/object-update`)**: Will only update records if the user owns them. Adds `updated_by_id = <user_id>` automatically. For user profile updates, strictly controls which fields can be modified.
- **Deleting (`/my/object-delete`)**: Forces the `created_by_id` constraint into the delete query so users cannot delete records owned by others.

### `/admin` (Elevated Privilege Namespace)
This namespace is for system administrators and internal dashboards.
- **Security Check**: Enforced by global middleware (`user_role_check`).
- **Creation / Updating (`/admin/object-create`, `/admin/object-update`)**: Unlike `/my`, the admin routes do **not** force `created_by_id` or `updated_by_id` to match the admin. Admins can create records on behalf of other users, and they can freely modify restricted columns.
- **Reading (`/admin/object-read`)**: Does not inject the ownership constraint. Admins can read the entire database table.
- **Deleting (`/admin/object-delete`)**: Allows deletion of any record across the system.

### `/public` (Unauthenticated Namespace)
This namespace is completely open and requires no JWT.
- **Security Check**: Only protected by global rate limiting (`api_ratelimiting_times_sec` per IP address) and caching.
- **Reading (`/public/object-read`)**: Openly readable, but restricted heavily by `config_table_read_enable_public` in `core/config.py` to prevent data leakage. Used for fetching public lists (e.g., job postings, available categories).
- **Creation (`/public/object-create`)**: Used primarily for things like lead capture forms, signups, or contact requests where no user ID exists yet. 

---

## 3. Specialized Object APIs

- **`/my/object-create-mongodb`**: A specialized MongoDB insertion endpoint allowing users to drop unstructured logs or documents into a Mongo database natively.
