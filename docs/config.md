# ⚙️ Configuration Reference

Atom is driven by `config.py` — a single file of plain Python values loaded onto `app.state` at startup.

---

## 1. How Config is Loaded & Overridden

Every `config_*` value is read once, at startup, in this order; a later one wins:

| Order | Where | For |
|---|---|---|
| 1 | `config.py` | Atom's defaults |
| 2 | `config_extend.py` | the project's defaults and structure (tables, routes); git-tracked, survives `sync.py`. See [extend.md](extend.md); startup stops if its `config_api`, `config_postgres_schema_master` or `config_users_role_label` drops any of Atom's routes, Postgres entries (a table may move to another database's schema) or role codes ([what is checked](extend.md#what-startup-checks-in-config_extendpy)) |
| 3 | `.env` | one machine's values: secrets, URLs, flags (or the file `ATOM_ENV_FILE` names: [local run](#local-run)) |
| 4 | environment variables | a server's settings (Azure app settings, `docker run -e`, CI); `.env` never overwrites a variable that is already set |

Example: `config_extend.py` has `config_schedule_script_report = "off"`; a laptop without the key in `.env` keeps `off`, a server with `config_schedule_script_report=daily 02:00` in its settings runs it at 02:00. `func_config_load` (`function/config.py`, called from `main.py`) does the merge; the result is `app.state.config_<name>`.

- **Type:** an overriding value takes the type of the default in code: a `True`/`False` default reads `true`/`false` (also `1`/`0`, `yes`/`no`, `on`/`off`; anything else stops startup), a number reads a number, a list or dict reads JSON (a value that is not valid JSON leaves the code's value), a string stays text (all digits become an integer). A key with no default in code is guessed the same way ([section 2](#2-dynamic-env-discovery--type-inference)).
- **When:** only at startup; a changed `.env` or server setting applies after a restart (Azure restarts the app when a setting changes).
- **Local run:** <a id="local-run"></a>`ATOM_ENV_FILE=<path>/local.env venv/bin/python main.py` makes the app (and Atom's scripts) read that file instead of `.env`, so none of `.env`'s real databases and services is reachable; a name that is not a file stops startup. Three keys are enough: `config_postgres_url_master` of a throwaway local database (with `postgis`, `pg_trgm` and `btree_gin`), `config_root_user_password` and `config_token_secret_key` (any random values); a feature that needs another service adds its own throwaway local one (`config_redis_url_<name>`, `config_clickhouse_url_<name>`, ...). Startup creates the schema and the `admin` user. An AI agent keeps the file and everything the run makes in its own folder `~/.atom/<project>/` outside the project, reused by its next run, and names its databases and containers `<project>_agent`, so the developer never sees them (AGENTS.md, Work).
- **Checks:** startup validates the merged values, so a bad one (`config_schedule_script_report=daily 2am`) stops the app with its name.

> **Rule of Thumb**: Use `.env` for secrets, credentials, and environment flags; use `config_extend.py` for structural changes (tables, custom route policies).

---

## 2. Dynamic `.env` Discovery & Type Inference

Developers can declare **any** custom variable in `.env` without modifying `config.py`. As long as the key starts with `CONFIG_` or `config_`, Atom will:
1. Detect the variable at startup.
2. Normalize the key to lowercase snake_case (`config_<name>`).
3. Automatically infer and cast the value to the appropriate Python type.
4. Mount it onto `app.state` as `app.state.config_<name>`.

### Example `.env`:
```dotenv
# String values (no quotes: docker --env-file and some hosts keep them as part of the value)
CONFIG_PAYMENT_GATEWAY_API_KEY=sk_test_123456789
CONFIG_EXTERNAL_WEBHOOK_URL=https://hooks.example.com/events

# Booleans (case-insensitive true/false, yes/no, on/off)
CONFIG_ENABLE_BETA_CHECKOUT=true
CONFIG_MAINTENANCE_BANNER_ENABLED=false

# Numbers
CONFIG_MAX_RETRY_ATTEMPTS=5
CONFIG_SYNC_INTERVAL_SEC=300

# JSON Arrays & Objects
CONFIG_WHITELISTED_IPS=["192.168.1.1", "10.0.0.1"]
CONFIG_TIER_LIMITS={"free": 100, "pro": 1000}
```

### Layout
A project `.env` has up to three kinds of sections, in this order:

```dotenv
# atom
config_postgres_url_master=postgresql://postgres:postgres@localhost:5432/postgres
config_root_user_password=your-strong-root-password
config_token_secret_key=your-secret-key-at-least-32-chars

# extend
config_payment_gateway_url=https://payments.example.com

# script.report_export
# config_postgres_url_master=postgresql://postgres:postgres@localhost:5432/postgres
# config_postgres_url_warehouse=postgresql://user:pass@host:5432/warehouse
# config_partner_api_key=your-partner-key
```

- `# atom`: Atom's keys the backend (`python main.py` or `uvicorn main:app`) uses.
- `# extend`: the project's own keys the backend uses.
- `# script.<name>`: one per script in `script_extend/` (`<name>` without `.py`), listing every key that script reads, under Atom's plain names, so pasting the section alone runs the script on another machine.

The sections are only comments: the backend and every script load the whole file, and a repeated key silently takes the last value. So `# atom` and `# extend` are active, and every line in a `# script.<name>` section is commented out; a developer uncomments the section where the script runs. An active copy of a backend key would change the backend's value, and an active `config_<db>_url_<name>` line makes the backend open a pool to that database at startup (startup fails when it can't be reached).

A script reads these values in its `# config` section with `load_dotenv(os.environ.get("ATOM_ENV_FILE", ".env"))` and `os.getenv("<exact key>")`, so the names in the script and in `.env` match. Settings that have a default in code (`config_batch_item_limit`, `config_users_token_column`) are imported in `# import` with `from config import ...`.

### Accessing in Routes:
```python
@router.get("/checkout/status")
async def get_checkout_status(request: Request):
    app_state = request.app.state
    api_key = app_state.config_payment_gateway_api_key   # "sk_test_123456789" (str)
    is_beta = app_state.config_enable_beta_checkout      # True (bool)
    retries = app_state.config_max_retry_attempts        # 5 (int)
    ips = app_state.config_whitelisted_ips               # ("192.168.1.1", "10.0.0.1") (tuple)
    limits = app_state.config_tier_limits                # {"free": 100, "pro": 1000} (dict)
```

---

## 3. Single Configuration Keys

All scalar and list settings in `config.py` grouped by section:

### Integrations

Disabled (`None`) by default; activated automatically when connection credentials are set. In `config.py` they are `# database` and the sections from `# queue` to `# monitoring`.

#### Database

| Key | Usage |
|---|---|
| `config_postgres_url_<name>` | PostgreSQL connection DSN per named database, collected into `config_postgres_url_dict`; `config_postgres_url_master` is required and is the default |
| `config_postgres_url_dict` | Runtime mapping of named PostgreSQL pools (populated via `config_postgres_url_<name>`) |
| `config_redis_url_<name>` | Redis URL per named connection, collected into `config_redis_url_dict`. Built-in roles: `api_response` (response cache), `user_state` (role and status lookups), `ratelimiter` (rate-limit counters), `queue` (job producer); any other name is a project connection in `client_redis_dict` |
| `config_redis_url_dict` | Runtime mapping of named Redis URLs (populated via `config_redis_url_<name>`) |
| `config_mongodb_url` | MongoDB (Motor) connection string DSN |
| `config_mssql_url_<name>` | MSSQL connection string per named server, collected into `config_mssql_url_dict`; the `/admin/mssql-*` routes pick one with body param `connection` (default `master`; unknown name → 404) |
| `config_mssql_url_dict` | Runtime mapping of named MSSQL connection strings; pools in `client_mssql_dict` |
| `config_clickhouse_url_<name>` | ClickHouse DSN per named server, collected into `config_clickhouse_url_dict`; the `/admin/clickhouse-*` routes pick one with body param `connection` (default `master`; unknown name → 404) |
| `config_clickhouse_url_dict` | Runtime mapping of named ClickHouse URLs; clients in `client_clickhouse_dict`, schemas in `cache_clickhouse_schema_dict` |

#### Queue

| Key | Usage |
|---|---|
| `config_kafka_url` | Apache Kafka broker URL |
| `config_kafka_username` | Kafka SASL username |
| `config_kafka_password` | Kafka SASL password |
| `config_rabbitmq_url` | RabbitMQ broker URL |
| `config_celery_url` | Celery broker/backend URL |

#### Cloud

| Key | Usage |
|---|---|
| `config_sftp_host` | SFTP server hostname |
| `config_sftp_port` | SFTP server port |
| `config_sftp_username` | SFTP server username |
| `config_sftp_password` | SFTP server password |
| `config_sftp_known_hosts_path` | known_hosts file the server's key is checked against (default `~/.ssh/known_hosts`; add it with `ssh-keyscan -p <port> <host> >> <file>`) |
| `config_sftp_is_host_verify` | Check the server's key (default true); false only for a server you trust on a network you trust |
| `config_aws_access_key_id` | AWS Access Key ID |
| `config_aws_secret_access_key` | AWS Secret Access Key |
| `config_aws_s3_region_name` | AWS S3 region name |
| `config_aws_sns_region_name` | AWS SNS region name |
| `config_aws_ses_region_name` | AWS SES region name |
| `config_azure_account_name` | Azure Storage account name |
| `config_azure_account_key` | Azure Storage account key |
| `config_azure_email_connection_string` | Azure email connection string |
| `config_azure_sms_connection_string` | Azure Communication Services SMS connection string |
| `config_azure_sms_from_number` | Azure SMS sender phone number or alphanumeric sender ID |

#### Messaging

| Key | Usage |
|---|---|
| `config_fast2sms_url` | Fast2SMS gateway URL |
| `config_fast2sms_key` | Fast2SMS API key |
| `config_resend_url` | Resend email API URL |
| `config_resend_key` | Resend email API key |

#### AI

| Key | Usage |
|---|---|
| `config_openai_key` | OpenAI API key |
| `config_gemini_key` | Google Gemini API key |
| `config_anthropic_key` | Anthropic API key: opens `client_anthropic` (Claude) |

#### Monitoring

| Key | Usage |
|---|---|
| `config_posthog_project_host` | PostHog analytics host URL |
| `config_posthog_project_key` | PostHog analytics project key |
| `config_sentry_dsn` | Sentry DSN for error tracking |
| `config_sentry_traces_sample_rate` | Share of requests Sentry traces and profiles, 0 to 1 (default `0.05`). Every error is still sent. Tracing every request (`1.0`) adds noticeable overhead to each one; raise it briefly while investigating a slow route. |

### System & Security

| Key | Usage |
|---|---|
| `config_root_user_password` | Password of the `admin` user (id 1, role 1), hashed at startup |
| `config_is_root_user` | `True` (default): at each start, create or reset `admin` (id 1, role 1) from `config_root_user_password`, guard id 1 from delete (trigger), and sync its `/admin` permissions. Master only |
| `config_is_users_password_log` | `True` (default): a trigger records every password change in `log_users_password` (audit only). Master only |
| `config_is_users_delete_log` | `True` (default): a trigger records every user soft delete, restore and hard delete in `log_users_delete`. The users-delete worker takes its tasks from that table, so `False` means a deleted user's data is never cleaned. Master only |
| `config_users_token_column` | The `master.users` columns in the login token and the API-key user (`request.state.user`); `id` is always added ([users columns](#users-columns)) |
| `config_users_private_read_column` | The `master.users` columns `/private/user-read` returns, filters and sorts on; `id` is always added |
| `config_users_update_alone_column` | The `master.users` login identities changed alone in their own request (`username`, `email`, `mobile`, `password`) |
| `config_login_password` | Static login password for `/auth/login-password` (Must set in `.env` if used) |
| `config_token_secret_key` | HMAC secret key for signing/verifying JWT tokens *(Must change)*. With `config_is_prod` on, startup refuses keys shorter than 32 bytes; generate one with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `config_root_html_path` | Path to static HTML file served at `/` (default: Atom's home page, which lists every page in `static/` and `static_extend/`) |
| `config_is_home_atom_listed` | `true` (default): the home page lists Atom's pages and the project's; `false`: only the project's pages (`static_extend/`). Applied by the server in `GET /static-pages`; Atom's pages still open at `/page/<name>` |
| `config_is_user_delete` | Enables user hard deletion through `/my/user-delete` and `/admin/user-delete` (default `False`); the database also needs `users` out of `control.row_delete_disabled` in `config_postgres_schema_master`. Soft delete (`mode=soft`) needs neither |
| `config_is_postgres_schema_init` | `True` (default): startup changes each database to match its `config_postgres_schema_<name>`. `False`: startup changes nothing, compares instead, and stops if a database differs, listing the changes; run them with `venv/bin/python -m script.postgres_schema_plan --apply` (for production, where schema changes should be a deliberate step). With `config_is_read_only` neither runs |
| `config_postgres_lock_timeout_sec` | Longest wait for a table lock during schema init (default 10); past it startup stops and changes nothing. See what would change: `venv/bin/python -m script.postgres_schema_plan` |
| `config_signup_allowed_roles` | Roles allowed for public signup, including new users created by OTP/OIDC login (default: `[]` disables signup; role `1` is always rejected). See [role settings](auth.md#signup-and-login-role-settings). |
| `config_login_allowed_roles` | Roles that may log in: `["*"]` (default, every role) or a list such as `[1, 2]`; checks the supplied login `role` parameter (optional for password login) |
| `config_users_role_label` | Each role's label, `{1: "Admin"}`; a project adds its own (`{**base_config_users_role_label, 2: "User"}`) and startup refuses one without Atom's `1`. Served by `/info` as `int_mapping.master.users.role` ([labels](#labels-int_mapping)) |
| `config_is_otp_require_users_update` | `/admin/user-update` needs `otp` for `email`/`mobile` (default `False`); `/my/user-update` always does |
| `config_is_read_only` | Boolean system-wide read-only mode toggle |
| `config_is_tmp_reset` | Wipe `tmp/` at app start (default: `False`); features and scripts delete their own `tmp/<feature>/` files |
| `config_api_global_user_check_deleted`, `config_api_global_user_check_deactivated` | The deleted and deactivated check on every route with a credential, as a mode: `"token"` (default: no query; reads `deleted_at`/`deactivated_at` from the token, so it blocks tokens issued while the user was already deleted or deactivated), `"realtime"` (one `users` lookup per request, shared with the role check: blocks at once), `"redis"`, `"inmemory"`, or `None` (only routes that set `user_check_deleted`/`user_check_deactivated` in `config_api`). A route's own key wins. Login and `/my/token-refresh` always refuse a deleted or deactivated user, so with `"token"` a user is cut off when their access token expires (`config_access_token_expires_sec`) |
| `config_profile_metadata_sql` | Extra lists in `GET /my/profile`, under `metadata`: `{"name": "SELECT ... WHERE user_id = $1"}`, each query run with the user's id (default `{}`) |
| `config_is_profile_update_last_active_at` | `GET /my/profile` also sets the user's `last_active_at` in the background without delaying the response, always on the master database even when `?connection=` reads the profile from a replica (default: `True`; skipped when `config_is_read_only`); written at most once per 5 minutes per user (within them, the profile row it just read shows it is recent, so no query is sent), and never changes `updated_at` |
| `config_is_pgweb_enabled` | Enable the PgWeb SQL console at `/pgweb` (default: `False`). Turn on only on a developer machine; even then it accepts only direct localhost requests from its own page |
| `config_is_fastapi_telemetry` | FastAPI's built-in OpenTelemetry tracing, metrics, and logs (default `False`). Off, each request skips FastAPI's check for an OpenTelemetry backend (about 2 µs); turn on only when an OpenTelemetry provider is configured; exporters are then also set up from the `OTEL_*` environment variables. Errors still go to Sentry either way |
| `config_is_uvicorn_access_log` | uvicorn's per-request console line (default `False`). Atom already records every request in `log_api`, and printing each line cost 12–31% throughput in a load test (see [performance.md](performance.md#8-uvicorn-access-log)). Set `True` to see requests in the console while debugging. Applies to `python main.py`; with `uvicorn main:app` pass `--no-access-log` yourself. |
| `config_uvicorn_timeout_keep_alive_sec` | Seconds uvicorn keeps an idle client connection open (default `250`; uvicorn's own default is 5). Behind a load balancer or proxy it must be longer than the proxy's idle timeout (Azure App Service 240 s, nginx 75 s, AWS ALB 60 s), so the proxy never reuses a connection uvicorn has just closed, which shows up as occasional 502 errors. Lower it only when clients connect to uvicorn directly with no proxy. Applies to `python main.py`. |
| `config_is_prod` | Boolean production-mode toggle (`True` disables debug and protects endpoints) |
| `config_is_log_api` | API logging to `log_api` (default `True`). `False` (`config_is_log_api=false` in `.env`) turns it off: no rows are written, cleanup skips it, the Monitor's Requests and Errors tabs say logging is off and `/my/api-usage` returns 503. Only routes in `config_api` are logged; to skip some of them, set `"is_log_api": False` on them (Atom does for the pages `/` and `/page/{name}`, the health checks and `/pgweb`). |
| `config_is_log_api_all` | Also log requests that are not a `config_api` route: static files, `/favicon.ico`, unknown paths and their 404s (default `False`, which keeps them out of `log_api`). Set `True` to see all traffic while debugging. |
| `config_is_log_api_detail` | Also store each logged request's headers, the response headers and both bodies in `log_api` (`request_header`, `response_header`, `request_body`, `response_body`; default `False`). Only text bodies are kept, by their `Content-Type`: JSON (`application/json`, `+json`), XML (`application/xml`, `+xml`), `text/*` and `multipart/mixed`; CSV exports, event streams, forms, uploads, files and compressed bodies are only named (`[skipped: text/csv, 52311 bytes]`), never copied. `query_param` keeps every value. Secret header and query names are always masked (`Authorization`, `Cookie`, `Set-Cookie`, keys, tokens); bodies are stored as sent unless `config_is_log_api_detail_mask` is on. For debugging: rows get much larger, and bodies hold users' data; lower `log_api`'s `retention_day` while it is on (it deletes them with the rest). |
| `config_log_api_detail_max_kb` | The most kept per body with `config_is_log_api_detail` (`64`); a longer body is cut and marked with its full size. |
| `config_is_log_api_detail_mask` | With `config_is_log_api_detail`, also mask secrets inside the bodies: JSON fields and XML elements named password, token, OTP, secret or key become `[REDACTED]` (`False`, for speed: about 2-5 ms per 64 KB body, after the reply is sent). Turn it on when the bodies carry credentials. |
| `config_uvicorn_workers` | Server processes started by `python main.py` (default: `1`). Above `1`, every `inmemory` cache, rate limit and user check in `config_api` must switch to `redis` (user checks may also use `realtime` or `token`), and startup warns if workers x pools x `config_postgres_pool_max_size` can exceed Postgres `max_connections` |

### Limits, OTP & Auth

| Key | Usage |
|---|---|
| `config_postgres_pool_min_size` | Minimum connections per PostgreSQL pool (default: `1`) |
| `config_postgres_pool_max_size` | Maximum connections per PostgreSQL pool (default: `10`) |
| `config_postgres_query_timeout_sec` | Longest a single query may run on any of the app's Postgres pools, in seconds; a longer one is cancelled (also on the server) and the request fails. Default `0`: no limit. It also limits startup's schema changes and long exports, so set it above the slowest query you expect |
| `config_mssql_pool_min_size` | Minimum connections per SQL Server pool (default: `1`) |
| `config_mssql_pool_max_size` | Maximum connections per SQL Server pool (default: `10`) |
| `config_postgres_pool_min_size_<name>`, `config_postgres_pool_max_size_<name>` | One database's pool size, e.g. `config_postgres_pool_max_size_test=3`; others keep the shared sizes. `config_mssql_pool_min_size_<name>`, `config_mssql_pool_max_size_<name>` do the same for SQL Server. An unknown `<name>` stops startup |
| `config_mssql_pool_recycle_sec` | Reopen SQL Server connections older than this, in seconds (default: `1800`) |
| `config_otp_length` | Digit length generated for OTP codes (default: `6`) |
| `config_otp_expiry_sec` | Expiry window for OTP codes in seconds (default: `600`) |
| `config_otp_max_attempt` | Verification guesses allowed per OTP code before it is locked (default: `5`) |
| `config_totp_encryption_key` | Turns two-factor (TOTP) on for the app: the key (32+ characters, in `.env`) that encrypts every user's TOTP secret. `None` (default): the 2FA routes answer "2FA not configured" ([auth.md](auth-totp.md)) |
| `config_totp_issuer` | The app's name in the authenticator app (default `None`: the master database name) |
| `config_is_totp_clear` | `True` (default): trigger `users_totp_clear` on `master.users`: clearing `totp_enabled_at` (two-factor off) clears `totp_secret`, `totp_last_step` and `totp_recovery` too, raw SQL included |
| `config_oidc_provider` | Single sign-on providers, `{name: {issuer, client_id, jwks_uri?, tenants?, link_email?}}` (JSON in `.env`); each adds the users column `oidc_<name>`. `{}` (default): `/auth/login-oidc` answers "OIDC not configured" ([auth-oidc.md](auth-oidc.md)) |
| `config_schedule_timezone` | Time zone of every `config_schedule_*` time (`UTC`; a zone name such as `Asia/Kolkata`) ([schedule.md](schedule.md)) |
| `config_schedule_script_<script>` | When `script/<script>.py` or `script_extend/<script>.py` runs by itself: `off`, `every 6h`, `daily 02:00`, `every 3d 02:00`, `weekly sun 02:00` or `monthly 1 02:00`. Atom's: `config_schedule_script_postgres_cleanup` (`every 1h`), `config_schedule_script_postgres_backup` (`off`) ([schedule.md](schedule.md)) |
| `config_retention_day_user_soft_deleted` | Days before soft-deleted users' data is purged by `script/worker_users_delete.py` (`30`) |
| `config_access_token_expires_sec` | JWT Access Token lifetime in seconds |
| `config_refresh_token_expires_sec` | JWT Refresh Token lifetime in seconds |
| `config_api_key_max` | API keys one user may hold (`20`) ([auth.md](auth-api-key.md)) |
| `config_api_key_cache_sec` | Seconds a resolved API key is reused per worker before it is read again (`60`), in the same cache as tokens (`config_token_cache_max`); a deleted key keeps working for at most this long. `0` reads the database on every request |
| `config_cache_row_limit_config` | Rows of the `config` table (key → value) loaded into `cache_config` at startup and by `/admin/sync` (`1000`); `0` = not loaded |
| `config_cache_row_limit_users_role`, `config_cache_row_limit_users_deactivated`, `config_cache_row_limit_users_deleted` | Users (lowest ids first) whose role, `deactivated_at` and `deleted_at` are loaded at startup and by `/admin/sync` for the `inmemory` user checks (`10000` each, about 1 MB in all); a user not loaded is read from the database. `0` = not loaded (a project that never uses `inmemory` checks can turn them off). Set them in `.env` like any number |
| `config_token_cache_max` | Verified tokens cached per worker (`10000`, about 1 KB each); `0` turns the cache off. A token is fully verified on first use, then reused until its own `exp`; the key is the whole signed token, so an edited token is verified again. Expired entries are swept every 5 minutes; when full, the oldest entry is dropped |
| `config_request_body_max_kb` | Largest request body in KB, except multipart uploads (`10240`, 10 MB); a bigger one gets `413` before it is read, since a JSON body is held in memory and parsing takes several times its size |
| `config_request_form_max_kb` | Largest multipart upload (`multipart/form-data`) in KB, all files and fields together (`102400`, 100 MB; files go to disk past 1 MB); a bigger one gets `413` |
| `config_blob_limit_size_kb` | Maximum file upload size in KB (default: `500`) |
| `config_blob_limit_upload` | Maximum files allowed per upload request (default: `100`) |
| `config_blob_expire_sec_upload` | Presigned upload URL lifetime in seconds (`3600`) |
| `config_blob_expire_sec_preview` | Presigned preview URL lifetime in seconds (`360000`) |
| `config_buffer_rows_max` | Max rows pending in each in-memory buffer during an outage (`100000`, at least `1000`). When full, `mode=buffer` creates return `503 buffer full, retry later` and API-log rows drop the oldest (counted as `buffer_dropped` on the Monitor page's Background tab) |
| `config_postgres_buffer_flush_auto_sec` | Timer interval in seconds to auto-flush write buffers (`60`) |
| `config_postgres_buffer_flush_auto_sec_<name>` | The same for one database's buffered rows (`config_postgres_url_<name>` must exist), e.g. `2` for device data while master keeps `60` ([database.md](database.md#periodic-background-flush-loop)) |
| `config_api_cache_inmemory_max_kb` | Largest total size, in KB, of the `inmemory` API response cache per worker, counting the stored (gzipped) bodies (`102400`, 100 MB); over it, the oldest entries are dropped and read from the route again on their next request |
| `config_batch_item_limit` | Maximum objects allowed per batch CRUD request, `/admin/user-update` included (`1000`) |
| `config_sql_read_limit_default` | Default page size for object read queries (`100`) |
| `config_sql_read_limit_max` | Hard cap limit for object read page size (`10000`) |
| `config_page_offset_max` | How deep `page` may jump: rows skipped, `(page - 1) × limit`, at most this (`10000`); deeper pages use `after` ([Paging](crud.md#paging)) |
| `config_sql_read_relation_fetch_limit_max` | Maximum rows fetched per joined relation (`100`) |
| `config_query_runner_read_limit` | Maximum row cap for admin SQL query runner (`5000`) |
| `config_export_limit` | Maximum rows in any CSV export, Atom's and a project's: every export goes through `func_postgres_export`, `func_mssql_export` or `func_clickhouse_export`, which stop at this many rows (`1000000`, about what Excel opens). The one place to change it |
| `config_redis_cache_ttl_sec` | TTL for Redis-cached role/user status lookups (`3600`) |

### CORS

| Key | Usage |
|---|---|
| `config_cors_allow_origins` | List of allowed CORS origin URLs (`[]`) |
| `config_cors_allow_origin_regex` | Regex pattern matching allowed CORS origins (`.*`) |
| `config_cors_allow_methods` | Allowed HTTP methods for CORS (`["*"]`) |
| `config_cors_allow_headers` | Allowed request headers for CORS (`["*"]`) |
| `config_cors_expose_headers` | Exposed headers for CORS (`["*"]`) |
| `config_cors_allow_credentials` | Allow cookies/credentials in CORS requests (`True`) |

### Table Access Control

Which routes may use a table is in its schema's `control` access lists ([control](#control)).

| Key | Usage |
|---|---|
| `config_public_create_honeypot` | Hidden form field (`"website"`) that only bots fill: `/public/object-create` refuses a row where it has a value and drops it when empty; the form adds it off-screen with `tabindex="-1"` and `autocomplete="off"`; `None` turns it off |
| `config_mongodb_my_create_allowed` | MongoDB collections writable on `/my/object-create-mongodb`, as `{database: [collection, ...]}`; empty disables the route |

### Service Registries

| Key | Usage |
|---|---|
| `config_queue_services` | Registered background queue providers (`postgres`, the default, `redis`, `rabbitmq`, `kafka`, `celery`) |
| `config_queue_concurrency` | Jobs a consumer runs at once (default 10) |
| `config_queue_retry_max` | Retries of a failed job before it is kept (Postgres: `status` 2 in `queue_job`; brokers: `<channel>_failed`) (default 3) |
| `config_queue_retry_wait_sec` | Wait before the first retry, doubled each time: 2, 4, 8 s (default 2) |
| `config_webhook_is_active` | Runs the webhook delivery loop in the app, one per worker (default `False`); timing is fixed: 10 s per delivery, 8 retries from 60 s doubling, 300 s signature tolerance ([webhook.md](webhook.md)) |
| `config_webhook_verify_scheme` | How each provider signs incoming webhooks: `standard`, `stripe`, `github`, `shopify`, `razorpay`; a project adds its own (`{**base, "acme": {...}}`), checked at startup ([webhook.md](webhook.md#schemes-are-data)) |
| `config_blob_services` | Registered blob storage providers (`s3`, `azure`) |
| `config_email_services` | Registered email providers (`ses`, `resend`, `azure`) |
| `config_mobile_services` | Registered SMS providers (`sns`, `fast2sms`, `azure`) |
| `config_ai_services` | Registered AI service providers (`gemini`, `openai`, `claude`) |

---

## Dict Configurations

Detailed breakdown of all dictionary settings in `config.py`.

### `config_api`

Per-endpoint security and execution policy table.

Keys are route paths as declared. A route with path parameters (`/page/{name}`) gets its entry for every path it matches (`/page/analytics`); an exact path is looked up first. A request whose path is no route gets no entry: no checks, and it is not logged (see `config_is_log_api_all`).

#### Policy Fields (Nested Keys)

| Key | Type / Value | Description & Usage |
|---|---|---|
| `id` | `int` | Unique numeric identifier for the endpoint |
| `is_active` | `bool` | Toggles endpoint availability (`False` disables the endpoint via middleware) |
| `auth` | `list` | Required. The credentials the route accepts: `[]` public, `["jwt"]` a JWT access token, `["api_key"]` an API key, `["jwt", "api_key"]` either; both are sent as `Authorization: Bearer` ([auth.md](auth-api-key.md)) |
| `is_connection_param` | `bool` | `True` lets `?connection=<name>` pick the database for this route (default master; unknown name is 404). Without it the route always uses master and `?connection=` is 400. On a write route, rows are checked against and written to that database, also when buffered or queued ([database.md](database.md#picking-a-database-per-request-connectionname)) |
| `webhook_verify` | `dict` | `{"scheme": <name in config_webhook_verify_scheme>, "secret": <config_ setting holding the secret>}`: the route is called by another service and runs only with a valid signature of its raw body; `auth` must be `[]` ([webhook.md](webhook.md#incoming)) |
| `ip_allow` | `list` | IP addresses or CIDR ranges (`["203.0.113.0/24"]`): any other caller gets 403, checked before the body is read; for senders that can't sign ([webhook.md](webhook.md#senders-that-cant-sign)) |
| `token_verify` | `dict` | `{"secret": <config_ setting holding the token>, "in": "header" or "query", "name": <its name>}`: the header (default `x-webhook-token`) or query value (its name must contain `token`) must equal the secret, else 403 ([webhook.md](webhook.md#senders-that-cant-sign)) |
| `is_log_api` | `bool` | `False` keeps this route's requests out of `log_api` (default `True`). Atom sets it for `/pgweb` (every click would add a row) and the health checks (probed every few seconds). |
| `user_check_role` | `{"mode": "...", "roles": [...]}` | Restricts access to users with listed role numbers |
| `user_check_permission` | `{"mode": "token"}` | Only users whose `permissions` hold this route's `id` ([Per-User Permissions](auth-permission.md)) |
| `user_check_deactivated` | `{"mode": "..."}` | Blocks request if user has `deactivated_at` timestamp set |
| `user_check_deleted` | `{"mode": "..."}` | Blocks request if user has `deleted_at` timestamp set |

Every route with a credential (a non-empty `auth`) gets `user_check_deleted` and `user_check_deactivated` from `config_api_global_user_check_deleted` and `config_api_global_user_check_deactivated` unless it sets its own (its own value wins, `None` included).
| `rate_limit` | `{"mode": "...", "limit": N, "window_sec": S}` | Limits requests to `limit` per `window_sec` seconds |
| `cache` | `{"mode": "...", "ttl_sec": S, "is_per_user": bool}` | Caches responses for `ttl_sec` seconds (`is_per_user: True` isolates entries per user) |

#### Inspection Modes (`mode` Nested Key)

| Mode Value | Data Source | Characteristics & Best Use Case |
|---|---|---|
| `token` | JWT Payload | Fastest (zero DB lookup); best for stable claims |
| `inmemory` | Redis / Memory Cache | High speed; subject to `config_redis_cache_ttl_sec` TTL |
| `realtime` | Live PostgreSQL Query | Guaranteed freshness; best for critical admin/delete ops |

The role, deactivated and deleted checks share one `users` query per request (`func_middleware_user_row_reader`): a route with all three in `realtime` mode makes one database round trip, not three.

---

### `config_postgres_schema_master` and `config_postgres_schema_<name>`

Declarative schema per database: `config_postgres_schema_<name>` is applied at startup to the database of `config_postgres_url_<name>`, master first. `config_postgres_schema_master` (Atom's tables) is required; add one for another database in `config_extend.py` (`config_postgres_schema_telematics = {...}`). A database gets exactly what its schema lists, nothing of Atom's. API logs go to the database whose schema has `log_api`. Startup stops when a schema names a database without a URL, or when API logging is on and `log_api` is in no schema or in two ([database.md](database.md)).

#### Parts

A schema is `{"table": {...}, "control": {...}, "sql": {...}}`, in that order. Each key below says who enforces it: **database rules** hold even against raw SQL; **API rules** hold only through Atom's routes (a project route or a SQL runner is not bound by them).

| Key | Type | Enforced by | Usage |
|---|---|---|---|
| `table` | `dict[str, dict]` | Structure | One object per table, `{"column": [...]}` and nothing else ([column keys](#column-keys)) |
| `control` | `dict` | (per key, [below](#control)) | The whole database's rules: extensions, switches, which tables each route group may use, row guards and per-table numbers |
| `sql` | `dict[str, str \| list]` | Structure | The project's own raw SQL (functions, triggers, hypertables), run at every startup after the tables; Atom's is empty |

```python
config_postgres_schema_master = {
"table": {
"task": {"column": [
{"name": "id", "datatype": "bigint", "identity": "always", "is_primary_key": True},
{"name": "created_at", "datatype": "timestamptz", "default": "now()", "index": ["btree(created_at)"]},
{"name": "created_by_id", "datatype": "bigint", "index": ["btree(created_by_id,id)"]},
{"name": "assigned_to_id", "datatype": "bigint", "index": ["btree(assigned_to_id)"], "ownership": ["read", "update"]},
{"name": "status", "datatype": "smallint", "allowed_values": [1, 2], "int_mapping": {1: "Open", 2: "Done"}},
{"name": "note", "datatype": "text", "read_blocked": ["private"]},
]},
},
"control": {
"private_read": ["task"],
"my_create": ["task"], "my_read": ["task"], "my_update": ["task"], "my_delete": ["task"],
"retention_day": {"task": 365},
},
"sql": {},
}
```

That shows the format. In a project, master's schema is written in `config_extend.py` starting from Atom's (`base_config_postgres_schema_master`: its tables, every `control` key and Atom's extensions must stay, or startup stops), as in [extend.md](extend.md#extend-atoms-dictionaries); another database's schema is written whole, as above ([database.md](database.md#2-declarative-schema-management)). Every part and key but `table` is optional.

Naming: a key ending in `_disabled` is enforced by the database (a trigger or constraint), one ending in `_blocked` by Atom's routes.

#### Column keys

| Key | Type | Enforced by | Usage |
|---|---|---|---|
| `name` | `str` | Structure | Column name. `id` is optional; when a table has it, it is an integer (Atom's update, delete, relation fetch and default order find rows by it, and answer 400 "table ... has no id" on a table without it) |
| `datatype` | `str` | Structure | PostgreSQL type (`bigint`, `timestamptz`, `text`, `jsonb`, `geography(Point, 4326)`, `vector(768)`) |
| `identity` | `str` | Structure | `"always"` or `"by_default"`, on an integer primary key column only |
| `is_primary_key` | `bool` | Structure | `True` on each column of the table's primary key: one column (`id`), several (`device`, `time`: one key over both), or none. Set when the table is created; such a column takes only `name`, `datatype`, `identity` and `is_primary_key` |
| `default` | `str` / `int` | Structure | Default value or expression (`"now()"`, `1`) |
| `generated` | `str` | Structure | SQL expression Postgres fills the column from (`GENERATED ALWAYS AS (...) STORED`); takes no `default`, `is_not_null`, `allowed_values`, `regex`, `check`, `unique` or `old_name`; rebuilt when the expression changes ([crud-search.md](crud-search.md)) |
| `old_name` | `str` | Structure | The column's previous name: startup renames it to `name`, keeping the data |
| `index` | `list[str]` | Structure | One text per index: `["btree(email)"]`, `["btree(status,type)", "gin(tags)"]`; types `btree`, `gin`, `gin_trgm`, `gist`, `hnsw` (a vector column). A btree column may add its sort order, so a list sorted that way reads in index order: `["btree(score desc nulls last,id)"]` |
| `is_not_null` | `bool` | Database rule | `True` adds `NOT NULL` |
| `unique` | `list[list[str]]` | Database rule | One list of columns per unique constraint: `[["code"]]`, `[["code", "type"], ["code", "slug"]]` |
| `check` | `str` | Database rule | SQL `CHECK` clause (`"rating >= 0 AND rating <= 10"`) |
| `allowed_values` | `list` | Database rule | The only values the column holds, integers or texts: `[1, 2, 3]`, `["schedule", "manual"]` (a `CHECK`) |
| `regex` | `str` | Both | The column's format: the API checks every create and update (error `regex_message`) and the database adds it as a `CHECK` (existing rows must already match). `users.password` is checked by the API only, before hashing (the database stores the hash). Each column has its own rule; no single quote in the pattern, not on an array column |
| `regex_message` | `str` | API rule | The error when the value does not match `regex` (default `<column>: invalid format`) |
| `int_mapping` | `dict` | API rule | Labels for an integer (or integer array) column's codes, `{1: "Open", 2: "Done"}` (`None` for no value yet); with `allowed_values`, the codes must be the same. Display only, never checked: use `allowed_values` to limit the values. Served by `/info` ([labels](#labels-int_mapping)) |
| `read_blocked` | `list[str]` | API rule | The route groups (`my`, `public`, `private`, `admin`) that may not select, filter, sort or group by the column; left out = none. Atom's `users.password`, `users.totp_secret`, `users.totp_recovery`, `api_key.key_hash` and `webhook.secret` list all four |
| `write_blocked` | `list[str]` | API rule | The route groups whose create and update refuse the column (400); left out = none. `["my"]`: only an admin sets it (`users.role`, `permissions`, `verified_at`, `deactivated_at`, ...); all four: only Atom or the database sets it (`users.is_protected`, `last_active_at`, `totp_secret`, `totp_last_step`, `totp_recovery`) |
| `ownership` | `list[str]` | API rule | The `/my` actions (`read`, `update`, `delete`) that may find a user's rows by this column (`?ownership_column=`; `delete` covers `/my/object-delete` and `-delete-all`); `created_by_id` is always the owner and takes no key (startup refuses one). Atom's: `message.received_by_id` and `notification.received_by_id` `["read", "delete"]`, `log_users_password.user_id` and `log_users_delete.user_id` `["read"]`. The users-delete worker cleans a deleted user's rows by the `delete` owners ([ownership.md](ownership.md)) |

`read_blocked`, `write_blocked` and `ownership` bind only Atom's routes: the table routes (`/public`, `/private`, `/my`, `/admin` object and table-column routes, CSV import) through `func_object_access`, and the user routes for `users`. A project route is free, and the SQL runners are not affected.

**Audit columns** need no key: `created_at` (database default `now()`), `created_by_id` (the token's user, on create; always the owner), `updated_at` (trigger, `is_updated_at_set`), `updated_by_id` (the token's user, on update), `deleted_at` (database clock, on soft delete) and `deleted_by_id` (the token's user, on soft delete) are always filled by Atom or the database, in every table that has them, and any request that sends one gets 400 (`AUDIT_COLUMNS` in `function/object.py`).

#### Users columns

Login users live in `master` only. What the user routes do with a `master.users` column is in three flat settings in `config.py` `# auth` ([System & Security](#system--security)), plus the column keys above:

| Setting / key | Meaning | Atom's columns |
|---|---|---|
| `config_users_token_column` | Written into the login token and the API-key user (`request.state.user`); `id` always added | `deactivated_at`, `deleted_at`, `role`, `permissions`, `username`, `id_ext` |
| `config_users_private_read_column` | The only `users` columns `/private/user-read` returns, filters and sorts on; `id` always added | `created_at`, `deactivated_at`, `role`, `permissions`, `username`, `name` |
| `config_users_update_alone_column` | A login identity: changed alone in its own request (`{password}`, `{email, otp}`) | `username`, `email`, `mobile`, `password` |
| `"write_blocked": ["my"]` | Refused by `/my/user-update` and `/admin/user-create`; set with `/admin/user-update` | `role`, `permissions`, `totp_enabled_at`, `verified_at`, `verified_by_id`, `deactivated_at`, `deactivated_by_id`, `parent_id`, `source`, `id_ext`, `oidc_<provider>` (added automatically) |

```python
# config_extend.py
config_postgres_schema_master = {**base_config_postgres_schema_master, "table": {**base_config_postgres_schema_master["table"], "users": {"column": [
*base_config_postgres_schema_master["table"]["users"]["column"],
{"name": "report_country", "datatype": "text[]", "write_blocked": ["my"]},
{"name": "company_id", "datatype": "bigint", "write_blocked": ["my"]},
]}}}
config_users_token_column = [*base_config_users_token_column, "company_id"]
```

A route reads a token column as `request.state.user["company_id"]` (a change reaches the token at the next login). Startup refuses a name that is not a `master.users` column, a repeat, `password` or a `read_blocked` `private` column in `config_users_private_read_column`, and a setting that needs a token column without it (`user_check_permission` mode `token` needs `permissions`; `config_api_global_user_check_deleted` / `deactivated` `"token"` need `deleted_at` / `deactivated_at`). Atom builds `app_state.cache_users_access` (`{token, private_read, update_alone: [columns]}`) at startup.

#### `control`

Flat, one per database. Lists and numbers name tables of the same schema. Every key is optional: a key left out is an empty list or map, and a switch left out takes its default, so a schema without `control` gets the three switches on and no table open to `/public`, `/private` or `/my`.

| Key | Type (default) | Enforced by | Usage |
|---|---|---|---|
| `extension` | `list[str]` | Structure | PostgreSQL extensions to install at startup (Atom's master: `["postgis", "pg_trgm", "btree_gin", "vector"]`); one the server lacks or the user may not install is skipped with a warning, and a column that needs it stops startup naming it |
| `is_updated_at_set` | `bool` (`True`) | Database rule | A trigger sets `updated_at` on every update |
| `is_protected_delete_disabled` | `bool` (`True`) | Database rule | A trigger refuses deleting a row with `is_protected = true` |
| `is_truncate_disabled` | `bool` (`True`) | Database rule | `True`: a trigger refuses `TRUNCATE` on every table of the schema, in every database. A database that truncates on purpose (nightly reloads) sets `False` in its own `control` |
| `row_update_disabled` | `list` of tables | Database rule | A trigger refuses every `UPDATE`, raw SQL included (Atom's: `log_api`, `api_key`, `log_users_password`). Not on `users`, `otp`, `script_run`, `queue_job` (Atom updates them) |
| `row_delete_disabled` | `list` of tables | Database rule | A trigger refuses every `DELETE`, raw SQL included (Atom's: `users`, `config`, `log_users_password`, `log_users_delete`) |
| `row_delete_max` | `{table: int}`, 1 up | Database rule | A trigger fails a single `DELETE` removing more rows (Atom's: `users` 100). Never on a table cleanup or the users-delete worker purges (they delete 5,000 at a time), nor on a hypertable |
| `public_create`, `public_read` | `list` of tables | API rule | `/public/*` object and table routes: anyone, no login. A create needs a `created_by_id` column (left empty) |
| `private_read` | `list` of tables | API rule | `/private/*` object and table routes: any logged-in user, all rows |
| `my_create`, `my_read`, `my_update`, `my_delete`, `my_delete_all` | `list` of tables | API rule | `/my/object-*`: a user's own rows (`created_by_id`, or a column whose `ownership` lists the action). The table needs `created_by_id` for create, `updated_by_id` for update |
| `buffer_limit` | `{table: int}`, 10-5000 | API rule | Rows held for a buffered create before they are written (default `100`; Atom's: `log_api` 1000) |
| `retention_day` | `{table: int}`, 1-36500 | Script | `script/postgres_cleanup.py` deletes rows older than this many days ([cleanup](#automatic-cleanup-retention_day); Atom's: `otp` 1, `log_api` 7, `script_run` 90) |

A table not in an access list is closed to that group and action: 403 naming the fix (`my delete not allowed for table: task (add "task" to control.my_delete in config_postgres_schema_master)`). The `/admin/*` object and table routes and `/admin/postgres-import` reach every table of the schema; who may call them is only the route's id in `users.permissions` ([auth-permission.md](auth-permission.md#admin-routes-one-id-each)). A table in no schema is refused by every table route. Each route checks the schema of the database it runs on (`?connection=<name>`, default `master`); a read with `relation=` needs the same group's read on each joined table. Rows of `users` change only through `/my/user-*` and `/admin/user-*` (`/admin/postgres-import` still imports `users`, hashing passwords).

Startup refuses an unknown key, a name that is not a table of the schema, `users` in any write access list, `row_update_disabled` on `users`, `otp`, `script_run` or `queue_job`, and `retention_day` on `users`, on a table in `row_delete_disabled` or `row_delete_max`, or on a table without `created_at`. In master, start from Atom's `control` and add to its lists, so Atom's tables stay open: `"control": {**base_config_postgres_schema_master["control"], "my_read": [*base_config_postgres_schema_master["control"]["my_read"], "task"]}`; a list replaced whole (`"public_read": []`) closes Atom's tables in it.

---

### `config_options`

Option lists set in code (gender, country, currency), exposed via `/info` for pages to show in selects and validate against.

| Key | Values | Usage |
|---|---|---|
| `gender` | `["male", "female"]` | Gender options |
| `country` | `"files/country.txt"` | 249 countries (ISO 3166), loaded from the file |
| `country_dial_code` | `"files/country_dial_code.json"` | 244 countries with phone codes: `{"code": "IN", "name": "India", "dial_code": "+91"}` (uninhabited territories without a code are left out) |
| `currency` | `"files/currency.json"` | 154 active ISO 4217 currencies: `{"code": "INR", "name": "Indian Rupee", "symbol": "₹"}` |

A value can be a list or a file path (relative to the project root, wherever the app is started from): `.txt` holds one item per line (blank lines skipped), `.json` holds a JSON list. Files load once at startup, after `config_extend.py` and `.env`, so `/info` always returns lists. A missing file, another extension, or invalid JSON stops startup. Keep project files in `files_extend/`:

```python
# config_extend.py
from config import config_options as base_config_options
config_options = {**base_config_options, "city": "files_extend/city.txt"}
```

---

### Labels (`int_mapping`)

Labels for integer-coded columns live on the column (`int_mapping`, [column keys](#column-keys)). Atom labels the codes its own code writes:

| Table / Column | Codes |
|---|---|
| `users.role` | `1` Admin (`config_users_role_label`) |
| `users.permissions` | every `config_api` route with `user_check_permission`: its `id` → its path |
| `blob.type` | `1` File, `2` Presigned Url |
| `script_run.status` | `1` Running, `2` Done, `3` Failed |
| `queue_job.status` | `1` Waiting, `2` Failed |
| `log_users_delete.type` | `1` User Soft Deleted, `2` User Restored, `3` User Hard Deleted |
| `log_users_delete.worker_status` | `None` Pending, `1` Processing, `2` Completed, `3` Failed, `4` Dead |

A project labels its roles in `config_users_role_label` and its own columns with `int_mapping`:

```python
# config_extend.py
config_users_role_label = {**base_config_users_role_label, 2: "User"}
```

Permission labels are not written anywhere: each is the route's path, so a new route with `user_check_permission` is labelled by itself. Pages show labels only from `/info` (saved by their sync, [frontend.md](frontend.md)), never written in the page. Labels are display text only: they do not grant access (role `1` is admin because routes check `roles: [1]`, not because of a label). Assigned permission ids are stored in `users.permissions` (`smallint[]`); see [Per-User Permissions](auth-permission.md).

### `/info` Response Keys

| Key under `message` | Source / Meaning |
|---|---|
| `api_list` | Paths of all registered routes |
| `int_mapping` | Every label, database → table → column → `{code: label}`, built at startup from every `config_postgres_schema_<name>` (`config.py` merged with `config_extend.py`) |
| `options` | `config_options` |
| `export_limit` | `config_export_limit`: the most rows any CSV export sends, for a page to show ("Up to 1,000,000 rows") |

A page reads `info.int_mapping.<db>.<table>.<column>[code]`, e.g. `info.int_mapping.master.users.role[2]`. Codes are integers in Python but strings as JSON keys (`info.int_mapping.master.users.permissions["205"]`). This public catalog describes available actions; it does not list the current user's assigned permissions.

---

### Automatic cleanup (`retention_day`)

`script/postgres_cleanup.py` runs on `config_schedule_script_postgres_cleanup` (every hour by default, [schedule.md](schedule.md)) and, in every database, permanently deletes the rows of each table in its schema's `control.retention_day` older than that many days, in batches of up to 5,000 with 0.1-second pauses, until none are left. Each run is a row in `script_run`, one step per table (`<db>.<table>`). Atom's defaults: `otp` 1, `log_api` 7, `script_run` 90 (a run still going is kept, whatever its age); a table not listed is kept. Successful OTP verification still deletes its code immediately; expiry alone does not delete it. `config_schedule_script_postgres_cleanup = "off"` stops it; `otp`'s retention must exceed `config_otp_expiry_sec`.

#### Sizing `log_api`'s `retention_day`

Atom writes one `log_api` row per request, so the table holds roughly requests per day × retention days. Rows take about 150–200 bytes plus indexes:

| Traffic | Rows kept at 7 days | Approx. size |
|---|---|---|
| 100k requests/day | 700k | ~0.25 GB |
| 1M requests/day | 7M | ~2.5 GB |
| 10M requests/day | 70M | ~25 GB |

The default of 7 days covers the Monitor page's longest range and keeps the table small. `/my/api-usage?days=N` reads this table, so users see at most that many days; for audits or problems found weeks later, raise it in `config_extend.py` (`"control": {**base_config_postgres_schema_master["control"], "retention_day": {**base_config_postgres_schema_master["control"]["retention_day"], "log_api": 30}}`). For high traffic, also consider keeping logs off the main database: move `log_api` into another database's `config_postgres_schema_<name>` ([database.md](database.md#5-api-logging--telemetry-log_api)). Load tests create log rows too; they are removed once they pass the retention cutoff.

Deleted space can be reused by PostgreSQL after vacuuming; deletion does not necessarily shrink the database files on disk.

---

📚 [Back to README](../README.md)
