# 🌐 Built-in Web Interfaces (API Master & PgWeb)

Atom includes zero-dependency, single-page web applications located in `static/` to streamline developer workflows, API testing, route introspection, and PostgreSQL database management.

---

## ⚡ API Master (`static/api.html`)

**API Master** is an interactive, browser-based API testing console and route inspector served by default at `/` (configured via `config_root_html_path="static/api.html"` in `config.py`).

### Key Features

- **Endpoint Introspection**: Automatically fetches and categorizes API routes, parameters, and metadata from `/info` and `/openapi.json`.
- **Interactive Runner**: Send `GET`, `POST`, `PUT`, `DELETE`, and `WebSocket` requests directly from the browser with custom headers, query params, path overrides, and JSON/Form bodies.
- **cURL Importer**: Paste raw `curl` commands to instantly populate request parameters in the interactive runner.
- **Rich Response Viewers**: View API responses in multiple formats:
  - **Tree View**: Interactive collapsible JSON structure view.
  - **Raw JSON**: Clean, syntax-highlighted JSON payload.
  - **Table View**: Tabular rendering for array-based JSON responses.
  - **Header Inspection**: HTTP response headers and status metadata.
  - **Performance Metrics**: Request timing and latency indicators.
- **WebSocket Console**: Built-in interactive console for testing real-time WebSocket connections, sending messages, and streaming event logs.
- **CSV Catalog Export**: Export a downloadable CSV catalog containing all registered endpoints and parameter specifications.

### Configuration & Access

- **Default Route**: `/`
- **Configuration Parameter**: `config_root_html_path = "static/api.html"` (in `config.py` or `config_extend.py`)
- **Direct Asset URL**: `/static/api.html`

---

## 🗃️ PgWeb (`static/pgweb.html`)

**PgWeb** is a lightweight, single-page PostgreSQL management interface embedded in Atom and served at `/static/pgweb.html`. It provides direct database access without requiring external desktop software or separate standalone database servers.

### Key Features

- **Database Exploration**: Inspect schemas, tables, views, columns, data types, indexes, and primary/foreign key constraints.
- **Interactive SQL Runner**: Write and run raw SQL queries directly against Postgres with syntax highlighting and tabular results.
- **Data Browser**: Browse, filter, paginate, and inspect table records directly from your browser.
- **Backend Integration**: Powered by Atom's internal `/pgweb` administration endpoint.
- **Zero Additional Setup**: Embedded directly in the framework static directory with no external dependencies required.

### Access & Navigation

- **Direct Asset URL**: `/static/pgweb.html`
- **Navigation Shortcut**: Click the database icon in the top header of **API Master** (`/`) to jump directly to PgWeb.

---

## 🛠️ Static Files & Maintenance

The HTML interfaces are self-contained single-page applications located in `static/`:

```
atom/
└── static/
    ├── api.html       # API Master testing & introspection console
    └── pgweb.html     # Lightweight PostgreSQL management interface
```

Both files are tracked in `files_to_sync` in `sync.py` so downstream projects can keep these tools updated via:

```bash
python sync.py
```

---

📚 [Back to README](../readme.md) | [Documentation Sitemap](about.md#---complete-technical-documentation-sitemap)
