# Architecture Overview

Atom is designed as a high-performance, developer-centric ASGI orchestrator. 

## Core Design Principles
- **Modular Core**: Decoupled architecture separating logic, routing, and infrastructure.
- **Stateless Functional Logic**: Business logic is separated from routing and state.
- **Unified IO**: Centralized async clients for databases and external services.

## Directory Structure
- `core/`: The heart of the application containing logic, configuration, and routing.
  - `app.py`: FastAPI application initialization, middleware setup, and global configurations.
  - `config.py`: Core configuration settings, environment variables, and database schema mappings (`config_postgres`, `config_column_int_mapping`).
  - `function.py`: The monolithic functional logic layer containing the core business methods.
  - `router/`: Contains the FastAPI routers divided by domain (e.g., `auth.py`, `index.py`, `admin.py`, `public.py`, `private.py`, `my.py`).
  - `script/`: Holds standalone scripts using purpose prefixes: `consumer_*` for queue listeners, `cron_*` for scheduled jobs, `worker_*` for long-running workers, and `task_*` for manual one-off tasks.
- `tests/`: Automated test suite for validating core logic and API endpoints.
- `docs/`: Project documentation, including architecture, setup, deployment, and coding conventions.
- `static/`: Static assets (such as HTML, CSS, JavaScript, and images) served by the application.

## Data Flow
1. **Routing**: Incoming requests are handled by FastAPI routers defined in `core/router/`.
2. **Logic**: Routers pass data to functional layers (e.g., `core/function.py`).
3. **Data Access**: The functional layers interact with the database via centralized clients.
