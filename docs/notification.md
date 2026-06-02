# Notification System

The Notification System is designed to abstract business logic event triggers away from the API routing layer, relying entirely on the native high-performance asynchronous execution of the Atom Framework.

## Architecture

Notifications are generated securely via a decoupled mapping structure:
1. **API Router**: Detects updates and passes a raw payload dictionary (containing `table` and `obj_list`) directly to the core function via `asyncio.create_task()`. This instantaneously unblocks the API response.
2. **Notification Engine** (`func_notification_create`): Parses the payload asynchronously in the background. It identifies specific event types and maps the update data into standard notification dictionary objects.
3. **Buffer Execution**: The built notification dictionaries are pushed strictly via `app_state.func_postgres_create(mode="buffer")`. This avoids immediate database I/O and instead injects the events directly into the framework's high-speed memory cache queue (`cache_postgres_buffer_create`).

## Supported Types

- **Type 1: Password Change**: Triggers when an Admin resets/updates another user's password.
- **Type 2: Job Status Change**: Triggers when a Job's status is changed to Approved or Rejected by an admin or user other than the owner.

## Database Schema

The `notification` table exists with the 9 framework base columns, supplemented by:
- `type` (smallint): Indexed event type.
- `user_id` (bigint): Target receiver of the notification.
- `title` (text): The generated event title.
- `description` (text): Optional long-form context.
- `reference_table` (text): The source table that triggered the event (e.g. `job`, `users`).
- `reference_id` (bigint): The specific object ID in the reference table.
- `read_at` (timestamptz): Timestamp to track user engagement.

## How to Add a New Notification Type

Adding a new notification type is extremely simple and requires just three steps:

### 1. Register the Type in Configuration (`core/config.py`)
Update `config_column_int_mapping` so the system knows what the integer represents:
```python
"notification": {1: "Password Change", 2: "Job Status Change", 3: "My New Event"},
```

### 2. Trigger it in the Router (`core/router/admin.py` or similar)
Add a single background task line in the relevant router where the update/action occurs:
```python
import asyncio
asyncio.create_task(app_state.func_notification_create(
    type=3, 
    app_state=app_state, 
    payload={"table": oq["table"], "obj_list": obj_list}
))
```

### 3. Build the Logic Block (`core/function.py`)
Inside `func_notification_create`, add a flat conditional block to process the type, extract targets, and map them to the unified `notification_obj_list`.

```python
    if type == 3 and table == "my_target_table":
        for obj in payload.get("obj_list", []):
            target_id, actor_id = obj.get("id"), obj.get("updated_by_id")
            
            # Your custom conditions here
            if target_id and target_id != actor_id:
                notification_obj_list.append({
                    "type": type,
                    "created_by_id": actor_id, # The triggerer
                    "user_id": target_id,      # The receiver
                    "title": "New Event Alert",
                    "description": f"Target ID: {target_id} was updated.",
                    "reference_table": table,
                    "reference_id": target_id
                })
```

The unified buffer queue at the end of the function automatically handles bulk-inserting your payload into Postgres!
