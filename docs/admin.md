# 🛠️ Admin Toolkit & Built-in Web Interfaces

Atom includes high-privilege administrative utilities, schema inspection tools, data import runners, and embedded zero-dependency web interfaces.

---

## 1. Built-in Web Interfaces

Atom embeds two single-page browser interfaces in `static/`:

### A. API Master (`static/api.html`)
Served by default at `/` (`config_root_html_path = "static/api.html"`):
- **Live Endpoint Introspection**: Dynamically displays all endpoints, schemas, and parameter requirements.
- **Interactive Request Runner**: Test GET, POST, PUT, DELETE, and WebSocket connections with headers and request payloads.
- **cURL Importer**: Paste raw curl commands to auto-populate request inputs.
- **Multi-View Response Inspector**: Tree view, raw JSON, and tabular renderers.

### B. PgWeb (`static/pgweb.html`)
Lightweight browser-based PostgreSQL database manager:
- **Schema & Table Inspector**: View tables, columns, indexes, and constraints.
- **SQL Runner**: Execute queries directly from the browser with tabular result visualization.
- **Data Browser**: Browse, sort, and filter live table data.

---

## 2. Administrative APIs (`/admin/*`)

Access to `/admin/*` requires an authenticated user with **`role: 1`** (root superadmin).

### 1. Raw SQL Query Runner (`POST /admin/query`)
Executes direct SQL against primary or secondary database pools:
```bash
POST /admin/query
{"sql": "SELECT count(*) FROM users;", "db": "primary"}
```

### 2. Table Data Imports (`POST /admin/*-import`)
Bulk import data from external systems into PostgreSQL:
- **Postgres Import** (`/admin/postgres-import`): Stream records from an external Postgres table.
- **Redis Import** (`/admin/redis-import`): Ingest cached hashes or lists into Postgres.
- **MongoDB Import** (`/admin/mongodb-import`): Ingest BSON collections into structured relational tables.

### 3. Schema Management
- **Schema Introspection** (`GET /admin/schema`): Returns runtime schema cache `cache_postgres_schema`.
- **Refresh Schema Cache** (`POST /admin/schema-refresh`): Re-queries PostgreSQL catalog to refresh table definitions without rebooting.

### 4. Downstream Sync Trigger (`POST /admin/sync`)
Triggers the framework upstream updater (`sync.py`) programmatically.
