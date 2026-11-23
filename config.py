# app
config_is_prod = True
config_is_read_only = False
config_is_tmp_reset = False
config_uvicorn_workers = 1
config_uvicorn_timeout_keep_alive_sec = 250
config_is_uvicorn_access_log = False
config_is_fastapi_telemetry = False
config_root_html_path = "static/home.html"
config_is_home_atom_listed = True
config_is_pgweb_enabled = False
config_request_body_max_kb = 10240
config_request_form_max_kb = 102400

# cors
config_cors_allow_origins = []
config_cors_allow_origin_regex = None
config_cors_allow_methods = ["*"]
config_cors_allow_headers = ["*"]
config_cors_expose_headers = ["*"]
config_cors_allow_credentials = True

# database
config_postgres_url_dict = {}
config_redis_url_dict = {}
config_mssql_url_dict = {}
config_clickhouse_url_dict = {}
config_mongodb_url = None

# postgres
config_is_postgres_schema_init = True
config_postgres_schema_lock_timeout_sec = 10
config_postgres_pool_min_size = 1
config_postgres_pool_max_size = 10
config_postgres_query_timeout_sec = 0
config_buffer_limit_default = 100
config_buffer_limit_log_api = 1000
config_buffer_rows_max = 100000
config_postgres_buffer_flush_auto_sec = 60

# mssql
config_mssql_pool_min_size = 1
config_mssql_pool_max_size = 10
config_mssql_pool_recycle_sec = 1800

# query
config_sql_read_limit_default = 100
config_sql_read_limit_max = 10000
config_page_offset_max = 10000
config_sql_read_relation_fetch_limit_max = 100
config_batch_item_limit = 1000
config_query_runner_read_limit = 5000
config_export_limit = 1000000

# cache
config_redis_cache_ttl_sec = 3600
config_inmemory_cache_cleanup_auto_sec = 300
config_api_cache_inmemory_max_kb = 102400
config_token_cache_max = 10000
config_cache_row_limit_config = 1000
config_cache_row_limit_users_role = 10000
config_cache_row_limit_users_deactivated = 10000
config_cache_row_limit_users_deleted = 10000

# auth
config_root_user_password = None
config_token_secret_key = None
config_access_token_expires_sec = 604800
config_refresh_token_expires_sec = 2592000
config_login_password = None
config_signup_allowed_roles = []
config_login_allowed_roles = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
config_is_user_delete = False
config_api_global_user_check_deleted = "token"
config_api_global_user_check_deactivated = "token"

# api_key
config_api_key_max = 20
config_api_key_cache_sec = 60

# otp
config_otp_length = 6
config_otp_expiry_sec = 600
config_otp_static = None
config_otp_max_attempt = 5
config_is_otp_require_users_update = False

# totp
config_totp_encryption_key = None
config_totp_issuer = None

# oidc
config_oidc_provider = {}

# profile
config_is_profile_update_last_active_at = True
config_profile_metadata_sql = {}

# log_api
config_is_log_api = True
config_is_log_api_all = False
config_is_log_api_detail = False
config_log_api_detail_max_kb = 64
config_is_log_api_detail_mask = False
config_postgres_db_log_api = "master"

# schedule
config_schedule_timezone = "UTC"
config_schedule_check_sec = 600
config_schedule_script_postgres_cleanup = "every 1h"
config_schedule_script_postgres_backup = "off"

# retention
config_retention_day_otp = 1
config_retention_day_log_api = 7
config_retention_day_users_delete = 30
config_retention_day_script_run = 90

# queue
config_queue_services = ["postgres", "redis", "rabbitmq", "kafka", "celery"]
config_queue_concurrency = 10
config_queue_retry_max = 3
config_queue_retry_wait_sec = 2
config_rabbitmq_url = None
config_kafka_url = None
config_kafka_username = None
config_kafka_password = None
config_celery_url = None

# webhook
config_webhook_is_active = False
config_webhook_timeout_sec = 10
config_webhook_retry_max = 8
config_webhook_retry_wait_sec = 60
config_webhook_poll_sec = 5
config_webhook_verify_tolerance_sec = 300
config_webhook_verify_scheme = {
"standard": {"header": "webhook-signature", "prefix": "v1,", "encoding": "base64", "signed": "{id}.{timestamp}.{body}", "id": {"header": "webhook-id"}, "timestamp": {"header": "webhook-timestamp"}, "secret_encoding": "base64"},
"stripe": {"header": "Stripe-Signature", "key": "v1", "encoding": "hex", "signed": "{timestamp}.{body}", "timestamp": {"key": "t"}},
"github": {"header": "X-Hub-Signature-256", "prefix": "sha256=", "encoding": "hex", "signed": "{body}"},
"shopify": {"header": "X-Shopify-Hmac-Sha256", "encoding": "base64", "signed": "{body}"},
"razorpay": {"header": "X-Razorpay-Signature", "encoding": "hex", "signed": "{body}"},
}

# blob
config_blob_services = ["s3", "azure"]
config_blob_limit_size_kb = 500
config_blob_limit_upload = 100
config_blob_expire_sec_upload = 3600
config_blob_expire_sec_preview = 360000

# email
config_email_services = ["ses", "resend", "azure"]
config_resend_url = None
config_resend_key = None

# mobile
config_mobile_services = ["sns", "fast2sms", "azure"]
config_fast2sms_url = None
config_fast2sms_key = None

# ai
config_ai_services = ["gemini", "openai", "claude"]
config_openai_key = None
config_gemini_key = None
config_anthropic_key = None

# aws
config_aws_access_key_id = None
config_aws_secret_access_key = None
config_aws_s3_region_name = None
config_aws_sns_region_name = None
config_aws_ses_region_name = None

# azure
config_azure_account_name = None
config_azure_account_key = None
config_azure_email_connection_string = None
config_azure_sms_connection_string = None
config_azure_sms_from_number = None

# msgraph
config_msgraph_tenant_id = None
config_msgraph_client_id = None
config_msgraph_client_secret = None

# sftp
config_sftp_host = None
config_sftp_port = None
config_sftp_username = None
config_sftp_password = None
config_sftp_known_hosts_path = None
config_sftp_is_host_verify = True

# monitoring
config_sentry_dsn = None
config_sentry_traces_sample_rate = 0.05
config_posthog_project_host = None
config_posthog_project_key = None

# table
config_table_exclude_from_users_delete = ["spatial_ref_sys", "users", "log_users_delete"]
config_table_write_blocked = ["log_api", "log_users_password", "log_users_delete", "script_run", "queue_job", "otp", "spatial_ref_sys"]
config_table_my_create_blocked = ["users", "api_key", "webhook", "ticket_comment", "log_api", "log_users_password", "otp", "script_run", "queue_job", "spatial_ref_sys"]
config_table_my_read_blocked = ["users", "config", "webhook", "log_users_password", "otp", "script_run", "queue_job", "spatial_ref_sys"]
config_table_my_delete_all_allowed = ["test", "message", "notification"]
config_table_public_create_allowed = ["test", "ticket"]
config_table_public_read_allowed = ["test"]
config_table_private_read_allowed = ["test"]
config_public_create_honeypot = "website"
config_mongodb_my_create_allowed = {"test": ["post"]}

# permission
config_permission_table = {"ticket": {"read": 120, "update": 121, "delete": 122}, "ticket_comment": {"create": 123, "read": 124, "update": 125, "delete": 126}}
config_permission_user_roles = []
config_permission_user_column_blocked = ["role", "permissions", "totp_enabled_at", "username", "email", "mobile", "verified_at", "verified_by_id", "deactivated_by_id", "parent_id", "source", "id_ext", "oidc_google"]

# column
config_column_token_encode = ["id", "role", "username", "id_ext" ,"deactivated_at", "deleted_at", "permissions"]
config_column_ownership_read = ["created_by_id", "received_by_id", "assigned_to_id", "user_id"]
config_column_ownership_update = ["created_by_id", "assigned_to_id"]
config_column_ownership_delete = ["created_by_id", "received_by_id", "assigned_to_id"]
config_column_admin = ["created_at", "updated_at", "created_by_id", "role", "verified_at", "verified_by_id"]
config_column_single_update = ["username", "password", "email", "mobile"]
config_column_users_blocked = ["created_at", "created_by_id", "updated_at", "updated_by_id", "deleted_at", "deleted_by_id", "is_protected", "last_active_at", "totp_secret", "totp_last_step", "totp_recovery"]
config_column_audit_blocked = ["created_at", "created_by_id", "updated_at", "updated_by_id", "deleted_at", "deleted_by_id"]
config_column_users_my_blocked = ["role", "permissions", "totp_enabled_at", "verified_at", "verified_by_id", "deactivated_at", "deactivated_by_id", "parent_id", "source", "id_ext", "oidc_google"]
config_column_read_blocked = ["password", "key_hash", "secret", "totp_secret", "totp_recovery"]
config_column_users_private_read = ["id", "username", "name", "role", "permissions", "created_at", "deactivated_at"]
config_column_private_read_blocked = {"script_run": ["started_by", "host", "step", "message", "peak_memory_mb"]}

# column dict
config_column_regex = {
"username": ["^(?=.{1,120}\\Z)\\S+\\Z", "Username must be 1-120 characters and contain no spaces"],
"password": ["^(?=.{6,120}\\Z)\\S+\\Z", "Password must be 6-120 characters and contain no spaces"],
"email_secondary": ["^(?=.{3,254}\\Z)[^\\s@]+@[^\\s@]+\\.[^\\s@]+\\Z", "Email must look like name@example.com"],
"mobile_secondary": ["^\\+?[0-9][0-9 -]{5,19}\\Z", "Mobile must be 6-20 digits (spaces, dashes and a leading + allowed)"],
}

config_options = {
"gender": ["male", "female"],
"country": "files/country.txt",
"country_dial_code": "files/country_dial_code.json",
"currency": "files/currency.json",
}

config_column_int_mapping = {
"users": {
"role": {1: "Admin"},
"permissions": {61: "Create user", 62: "Update user", 86: "Postgres query runner write", 120: "Ticket read", 121: "Ticket update", 122: "Ticket delete", 123: "Ticket comment create", 124: "Ticket comment read", 125: "Ticket comment update", 126: "Ticket comment delete"},
},
"blob": {
"type": {1: "File", 2: "Presigned Url"},
},
"script_run": {
"status": {1: "Running", 2: "Done", 3: "Failed"},
},
"queue_job": {
"status": {1: "Waiting", 2: "Failed"},
},
"ticket": {
"type": {1: "Support", 2: "Feedback", 3: "Bug"},
"priority": {1: "Low", 2: "Normal", 3: "High"},
"status": {1: "New", 2: "In Progress", 3: "Blocked", 4: "Waiting", 5: "Done"},
},
"log_users_delete": {
"type": {1: "User Soft Deleted", 2: "User Restored", 3: "User Hard Deleted"},
"worker_status": {None: "Pending", 1: "Processing", 2: "Completed", 3: "Failed", 4: "Dead"},
},
}

# schema
config_postgres = {
"extension": ["postgis", "pg_trgm", "btree_gin", "vector"],
"table":{
"test":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id,id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","index":"btree(type)"},
{"name":"title","datatype":"text","is_mandatory": True,"index":"gin_trgm(title)"},
{"name":"description","datatype":"text"},
{"name":"slug","datatype":"text","index":"btree(slug)"},
{"name":"code","datatype":"text","is_mandatory": False,"unique":"code,type|code,slug"},
{"name":"email","datatype":"text","regex":"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$","index":"btree(email)"},
{"name":"tags","datatype":"text[]","index":"gin(tags)"},
{"name":"tags_int","datatype":"integer[]","index":"gin(tags_int)"},
{"name":"tags_bigint","datatype":"bigint[]","index":"gin(tags_bigint)"},
{"name":"rating","datatype":"numeric(3,1)","check":"rating >= 0 AND rating <= 10"},
{"name":"coordinate","datatype":"geography(Point, 4326)","index":"gist(coordinate)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status,type)"},
{"name":"address","datatype":"text","old":"adress"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
],
"test_comment":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(created_by_id,id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"test_id","datatype":"bigint","is_mandatory": True,"index":"btree(test_id)"},
{"name":"description","datatype":"text","is_mandatory": True},
],
"users":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"is_protected","datatype":"boolean"},
{"name":"role","datatype":"smallint","is_mandatory": True,"index":"btree(role)"},
{"name":"permissions","datatype":"smallint[]","default": None},
{"name":"username","datatype":"text","unique":"username,role"},
{"name":"email","datatype":"text","unique":"email,role"},
{"name":"mobile","datatype":"text","unique":"mobile,role"},
{"name":"id_ext","datatype":"text","unique":"id_ext,role"},
{"name":"password","datatype":"text","index":"btree(password)"},
{"name":"oidc_google","datatype":"text","old":"google_login_id","unique":"oidc_google,role"},
{"name":"last_active_at","datatype":"timestamptz"},
{"name":"name","datatype":"text","index":"gin_trgm(name)"},
{"name":"country","datatype":"text","index":"gin_trgm(country)"},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_secondary","datatype":"text",},
{"name":"mobile_secondary","datatype":"text"},
{"name":"address","datatype":"text"},
{"name":"job_title","datatype":"text"},
{"name":"about","datatype":"text"},
{"name":"gender","datatype":"text"},
{"name":"date_of_birth","datatype":"date"},
{"name":"dashboard","datatype":"jsonb"},
{"name":"source","datatype":"smallint"},
{"name":"parent_id","datatype":"bigint"},
{"name":"totp_secret","datatype":"text"},
{"name":"totp_enabled_at","datatype":"timestamptz"},
{"name":"totp_last_step","datatype":"bigint"},
{"name":"totp_recovery","datatype":"text[]"},
],
"config":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"key","datatype":"text","is_mandatory": True,"unique":"key"},
{"name":"value","datatype":"jsonb","is_mandatory": True},
],
"otp":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"otp","datatype":"integer","is_mandatory": True},
{"name":"email","datatype":"text","index":"btree(email)"},
{"name":"mobile","datatype":"text","index":"btree(mobile)"},
{"name":"attempt","datatype":"smallint","default":0},
],
"blob":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory": True},
{"name":"service","datatype":"text","is_mandatory": True},
{"name":"file_url","datatype":"text","is_mandatory": True}
],
"message":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"received_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(received_by_id)"},
{"name":"description","datatype":"text","is_mandatory": True},
{"name":"read_at","datatype":"timestamptz"}
],
"notification":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory": True,"index":"btree(type)"},
{"name":"received_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(received_by_id)"},
{"name":"title","datatype":"text","is_mandatory": True},
{"name":"description","datatype":"text"},
{"name":"reference_table","datatype":"text"},
{"name":"reference_id","datatype":"bigint"},
{"name":"read_at","datatype":"timestamptz"}
],
"ticket":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id,id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory": True,"default":1,"in":(1,2,3),"index":"btree(type,id)"},
{"name":"priority","datatype":"smallint","is_mandatory": True,"default":2,"in":(1,2,3),"index":"btree(priority,id)"},
{"name":"status","datatype":"smallint","is_mandatory": True,"default":1,"in":(1,2,3,4,5),"index":"btree(status,id)"},
{"name":"title","datatype":"text","is_mandatory": True,"index":"gin_trgm(title)"},
{"name":"description","datatype":"text"},
{"name":"name","datatype":"text","index":"gin_trgm(name)"},
{"name":"email","datatype":"text","index":"gin_trgm(email)"},
{"name":"mobile","datatype":"text","index":"gin_trgm(mobile)"},
{"name":"closed_at","datatype":"timestamptz"},
{"name":"search","datatype":"tsvector","generated":"setweight(to_tsvector('english', coalesce(title, '')), 'A') || setweight(to_tsvector('english', coalesce(description, '')), 'B')","index":"gin(search)"}
],
"ticket_comment":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(created_by_id,id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"ticket_id","datatype":"bigint","is_mandatory": True,"index":"btree(ticket_id,id)"},
{"name":"description","datatype":"text","is_mandatory": True}
],
"log_api":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id,created_at)"},
{"name":"ip_address","datatype":"text"},
{"name":"response_type","datatype":"text"},
{"name":"method","datatype":"text"},
{"name":"path","datatype":"text"},
{"name":"query_param","datatype":"text"},
{"name":"status_code","datatype":"smallint","index":"btree(status_code)"},
{"name":"response_time_ms","datatype":"integer"},
{"name":"error","datatype":"text"},
{"name":"request_id","datatype":"text"},
{"name":"request_header","datatype":"jsonb"},
{"name":"response_header","datatype":"jsonb"},
{"name":"request_body","datatype":"text"},
{"name":"response_body","datatype":"text"}
],
"api_key":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(created_by_id)"},
{"name":"name","datatype":"text","is_mandatory": True},
{"name":"key_hash","datatype":"text","is_mandatory": True,"unique":"key_hash"},
{"name":"key_prefix","datatype":"text","is_mandatory": True},
{"name":"scopes","datatype":"text[]"},
{"name":"expires_at","datatype":"timestamptz"}
],
"webhook":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory": True},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"url","datatype":"text","is_mandatory": True},
{"name":"events","datatype":"text[]","is_mandatory": True},
{"name":"secret","datatype":"text","is_mandatory": True},
{"name":"is_active","datatype":"boolean","is_mandatory": True,"default":"true"}
],
"log_users_password":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"script_run":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(script,created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"script","datatype":"text","is_mandatory": True},
{"name":"started_by","datatype":"text","is_mandatory": True,"in":("schedule","manual")},
{"name":"host","datatype":"text"},
{"name":"status","datatype":"smallint","is_mandatory": True,"default":1,"in":(1,2,3)},
{"name":"step","datatype":"text"},
{"name":"message","datatype":"text"},
{"name":"peak_memory_mb","datatype":"integer"},
{"name":"finished_at","datatype":"timestamptz"}
],
"queue_job":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"channel","datatype":"text","is_mandatory": True},
{"name":"payload","datatype":"jsonb","is_mandatory": True},
{"name":"status","datatype":"smallint","is_mandatory": True,"default":1,"in":(1,2)},
{"name":"attempt","datatype":"integer","is_mandatory": True,"default":0},
{"name":"run_at","datatype":"timestamptz","is_mandatory": True,"default":"now()","index":"btree(channel,status,run_at,id)"},
{"name":"error","datatype":"text"}
],
"log_users_delete":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory": True,"in":(1,2,3),"index":"btree(type,created_at)"},
{"name":"user_id","datatype":"bigint","is_mandatory": True,"index":"btree(user_id,created_at)"},
{"name":"worker_status","datatype":"smallint","in":(1,2,3,4),"index":"btree(worker_status,worker_next_retry_at,created_at)"},
{"name":"worker_retry_count","datatype":"integer","default":0},
{"name":"worker_next_retry_at","datatype":"timestamptz","default":"now()"},
{"name":"worker_processed_at","datatype":"timestamptz"},
{"name":"worker_last_error","datatype":"text"}
],
},
"control":{
"is_updated_at_set": True,
"is_protected_delete_disabled": True,
"is_truncate_table": False,
"is_log_users_password": True,
"is_log_users_delete": True,
"is_root_user_create": True,
"is_root_user_delete_disabled": True,
"table_row_delete_disable":["users", "config", "log_users_password", "log_users_delete"],
"table_row_update_disable":["log_api", "log_users_password", "api_key"],
"table_row_delete_disable_bulk":[["users", 100]],
},
"sql":{
"ticket_closed_at":"CREATE OR REPLACE FUNCTION ticket_closed_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.status = 5 THEN NEW.closed_at = CASE WHEN TG_OP = 'UPDATE' AND OLD.status = 5 THEN OLD.closed_at ELSE now() END; ELSE NEW.closed_at = NULL; END IF; RETURN NEW; END $$; CREATE OR REPLACE TRIGGER ticket_closed_at BEFORE INSERT OR UPDATE OF status ON ticket FOR EACH ROW EXECUTE FUNCTION ticket_closed_at();",
"users_totp_clear":"CREATE OR REPLACE FUNCTION users_totp_clear() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.totp_enabled_at IS NULL AND OLD.totp_enabled_at IS NOT NULL THEN NEW.totp_secret = NULL; NEW.totp_last_step = NULL; NEW.totp_recovery = NULL; END IF; RETURN NEW; END $$; CREATE OR REPLACE TRIGGER users_totp_clear BEFORE UPDATE OF totp_enabled_at ON users FOR EACH ROW EXECUTE FUNCTION users_totp_clear();",
"ticket_delete_comments":"CREATE OR REPLACE FUNCTION ticket_delete_comments() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN DELETE FROM ticket_comment WHERE ticket_id = OLD.id; RETURN OLD; END $$; CREATE OR REPLACE TRIGGER ticket_delete_comments AFTER DELETE ON ticket FOR EACH ROW EXECUTE FUNCTION ticket_delete_comments();",
},
}

# api
config_api = {
# index
"/": {"id": 1, "auth": [], "is_log_api": False},
"/health": {"id": 2, "auth": [], "is_log_api": False},
"/health-ready": {"id": 3, "auth": [], "is_log_api": False, "cache": {"mode": "inmemory", "ttl_sec": 5, "is_per_user": False}},
"/info": {"id": 4, "auth": [], "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": False}},
"/openapi.json": {"id": 5, "auth": []},
"/static": {"id": 6, "auth": []},
"/static-pages": {"id": 7, "auth": [], "is_log_api": False},
"/page/{name}": {"id": 8, "auth": [], "is_log_api": False},
"/pgweb": {"id": 9, "auth": [], "is_log_api": False},
# auth
"/auth/login-password": {"id": 10, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/signup-username-password": {"id": 11, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/auth/login-username-password": {"id": 12, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-email-password": {"id": 13, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-mobile-password": {"id": 14, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-id-ext-password": {"id": 15, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-email-otp": {"id": 16, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/auth/login-mobile-otp": {"id": 17, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/auth/login-oidc": {"id": 106, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-totp": {"id": 102, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
# my
"/my/profile": {"id": 19, "auth": ["jwt"], "is_connection_param": True},
"/my/ping": {"id": 20, "auth": ["jwt"]},
"/my/token-refresh": {"id": 21, "auth": ["jwt"]},
"/my/api-usage": {"id": 22, "auth": ["jwt"]},
"/my/user-update": {"id": 23, "auth": ["jwt"], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/my/user-delete": {"id": 24, "auth": ["jwt"], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/my/object-create": {"id": 25, "auth": ["jwt"]},
"/my/object-read": {"id": 26, "auth": ["jwt"], "is_connection_param": True},
"/my/object-read-export": {"id": 27, "auth": ["jwt"], "is_connection_param": True},
"/my/object-update": {"id": 28, "auth": ["jwt"]},
"/my/object-delete": {"id": 29, "auth": ["jwt"]},
"/my/object-delete-all": {"id": 30, "auth": ["jwt"]},
"/my/message-inbox": {"id": 31, "auth": ["jwt"], "is_connection_param": True},
"/my/message-thread": {"id": 32, "auth": ["jwt"], "is_connection_param": True},
"/my/message-socket": {"id": 33, "is_active": False},
"/my/object-create-mongodb": {"id": 34, "auth": ["jwt"]},
"/my/blob-preview-urls": {"id": 35, "auth": ["jwt"]},
"/my/blob-delete-all": {"id": 36, "auth": ["jwt"]},
"/my/blob-delete-url": {"id": 37, "auth": ["jwt"]},
"/my/totp-setup": {"id": 103, "auth": ["jwt"], "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/my/totp-enable": {"id": 104, "auth": ["jwt"], "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/my/totp-disable": {"id": 105, "auth": ["jwt"], "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/my/api-key-create": {"id": 97, "auth": ["jwt"], "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
# public
"/public/object-create": {"id": 38, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/public/object-read-export": {"id": 39, "auth": [], "is_connection_param": True},
"/public/object-read": {"id": 40, "auth": [], "cache": {"mode": "inmemory", "ttl_sec": 100, "is_per_user": False}, "is_connection_param": True},
"/public/converter-number": {"id": 41, "auth": []},
"/public/otp-verify": {"id": 42, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/public/otp-send-email": {"id": 43, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 3, "window_sec": 60}},
"/public/otp-send-mobile": {"id": 44, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 3, "window_sec": 60}},
"/public/otp-send-mobile-sns-template": {"id": 45, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 3, "window_sec": 60}},
"/public/password-set": {"id": 107, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/public/table-column-groupby": {"id": 46, "auth": [], "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/public/table-column-distinct": {"id": 47, "auth": [], "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/public/blob-upload-file": {"id": 48, "is_active": False, "auth": []},
"/public/blob-upload-presigned": {"id": 49, "is_active": False, "auth": []},
"/public/password-hash": {"id": 50, "auth": [], "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
# private
"/private/send-email": {"id": 51, "auth": ["jwt"]},
"/private/blob-upload-file": {"id": 52, "auth": ["jwt"]},
"/private/blob-upload-presigned": {"id": 53, "auth": ["jwt"]},
"/private/object-read": {"id": 54, "auth": ["jwt"], "is_connection_param": True},
"/private/object-read-export": {"id": 55, "auth": ["jwt"], "is_connection_param": True},
"/private/user-read": {"id": 56, "auth": ["jwt"], "is_connection_param": True},
"/private/table-column-groupby": {"id": 57, "auth": ["jwt"], "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/private/table-column-distinct": {"id": 58, "auth": ["jwt"], "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
# permission
"/permission/object-create": {"id": 98, "auth": ["jwt"], "user_check_permission": {"mode": "token", "action": "create"}},
"/permission/object-read": {"id": 99, "auth": ["jwt"], "user_check_permission": {"mode": "token", "action": "read"}},
"/permission/object-read-export": {"id": 100, "auth": ["jwt"], "user_check_permission": {"mode": "token", "action": "read"}},
"/permission/object-update": {"id": 59, "auth": ["jwt"], "user_check_permission": {"mode": "token", "action": "update"}},
"/permission/object-delete": {"id": 60, "auth": ["jwt"], "user_check_permission": {"mode": "token", "action": "delete"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/permission/user-create": {"id": 61, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/permission/user-update": {"id": 62, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
# admin
"/admin/sync": {"id": 63, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/monitor": {"id": 64, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "is_log_api": False, "is_connection_param": True},
"/admin/object-create": {"id": 65, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/object-update": {"id": 66, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/object-read": {"id": 67, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "is_connection_param": True},
"/admin/object-read-export": {"id": 68, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "is_connection_param": True},
"/admin/user-create": {"id": 69, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/user-update": {"id": 70, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/user-delete": {"id": 71, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}, "user_check_deactivated": {"mode": "realtime"}},
"/admin/object-delete": {"id": 72, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "user_check_deleted": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/admin/table-column-groupby": {"id": 73, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/admin/table-column-distinct": {"id": 74, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/admin/postgres-import": {"id": 75, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "is_connection_param": True, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/mongodb-import": {"id": 76, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/blob-container-sas": {"id": 77, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/blob-preview-urls": {"id": 78, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/blob-container-read": {"id": 79, "auth": ["jwt"], "user_check_role": {"mode": "inmemory", "roles": [1]}},
"/admin/blob-container-ops": {"id": 80, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/blob-delete-url": {"id": 81, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/postgres-info": {"id": 82, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": False}, "is_connection_param": True},
"/admin/postgres-schema": {"id": 83, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "is_connection_param": True},
"/admin/postgres-slow-queries": {"id": 84, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "is_connection_param": True},
"/admin/postgres-slow-queries-reset": {"id": 85, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "is_connection_param": True, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/postgres-query-runner-write": {"id": 86, "is_active": True, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/postgres-query-runner-read": {"id": 87, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "is_connection_param": True},
"/admin/postgres-query-runner-read-export": {"id": 88, "auth": ["jwt"], "user_check_role": {"mode": "inmemory", "roles": [1]}, "is_connection_param": True},
"/admin/postgres-query-ai": {"id": 89, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}, "is_connection_param": True},
"/admin/mssql-query-runner-write": {"id": 90, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/mssql-query-runner-read": {"id": 91, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/mssql-query-runner-read-export": {"id": 92, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/clickhouse-query-runner-write": {"id": 93, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/clickhouse-query-runner-read": {"id": 94, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/clickhouse-query-runner-read-export": {"id": 95, "auth": ["jwt"], "user_check_role": {"mode": "inmemory", "roles": [1]}},
"/admin/clickhouse-query-ai": {"id": 96, "auth": ["jwt"], "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/webhook-create": {"id": 101, "auth": ["jwt"], "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
}

# override
from function.config import func_config_load
func_config_load(global_dict=globals())
