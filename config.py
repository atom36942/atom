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

# database
config_postgres_url_dict = {}
config_redis_url_dict = {}
config_mssql_url_dict = {}
config_clickhouse_url_dict = {}
config_mongodb_url = None

# auth
config_root_user_password = None
config_is_root_user = True
config_is_users_password_log = True
config_is_users_delete_log = True
config_users_token_column = ["deactivated_at", "deleted_at", "role", "permissions", "username", "id_ext"]
config_users_private_read_column = ["created_at", "deactivated_at", "role", "permissions", "username", "name"]
config_users_update_alone_column = ["username", "email", "mobile", "password"]
config_token_secret_key = None
config_access_token_expires_sec = 604800
config_refresh_token_expires_sec = 2592000
config_login_password = None
config_signup_allowed_roles = []
config_login_allowed_roles = ["*"]
config_users_role_label = {1: "Admin"}
config_is_user_delete = False
config_api_global_user_check_deleted = "token"
config_api_global_user_check_deactivated = "token"

# cors
config_cors_allow_origins = []
config_cors_allow_origin_regex = None
config_cors_allow_methods = ["*"]
config_cors_allow_headers = ["*"]
config_cors_expose_headers = ["*"]
config_cors_allow_credentials = True

# postgres
config_is_postgres_schema_init = True
config_postgres_lock_timeout_sec = 10
config_postgres_pool_min_size = 1
config_postgres_pool_max_size = 10
config_postgres_query_timeout_sec = 0
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
config_api_cache_inmemory_max_kb = 102400
config_token_cache_max = 10000
config_cache_row_limit_config = 1000
config_cache_row_limit_users_role = 10000
config_cache_row_limit_users_deactivated = 10000
config_cache_row_limit_users_deleted = 10000

# log_api
config_is_log_api = True
config_is_log_api_all = False
config_is_log_api_detail = False
config_log_api_detail_max_kb = 64
config_is_log_api_detail_mask = False

# schedule
config_schedule_timezone = "UTC"
config_schedule_script_postgres_cleanup = "every 1h"
config_schedule_script_postgres_backup = "off"

# retention
config_retention_day_user_soft_deleted = 30

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
config_is_totp_clear = True

# oidc
config_oidc_provider = {}

# profile
config_is_profile_update_last_active_at = True
config_profile_metadata_sql = {}

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
config_public_create_honeypot = "website"
config_mongodb_my_create_allowed = {"test": ["post"]}

# dict
config_options = {
"gender": ["male", "female"],
"country": "files/country.txt",
"country_dial_code": "files/country_dial_code.json",
"currency": "files/currency.json",
}

# schema
config_postgres_schema_master = {
"table":{
"test": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint","index":["btree(created_by_id,id)"]},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","index":["btree(type)"]},
{"name":"title","datatype":"text","is_not_null": True,"index":["gin_trgm(title)"]},
{"name":"description","datatype":"text"},
{"name":"slug","datatype":"text","index":["btree(slug)"]},
{"name":"code","datatype":"text","is_not_null": False,"unique":[["code", "type"], ["code", "slug"]]},
{"name":"email","datatype":"text","index":["btree(email)"],"regex":"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$","regex_message":"Email must look like name@example.com"},
{"name":"tags","datatype":"text[]","index":["gin(tags)"]},
{"name":"tags_int","datatype":"integer[]","index":["gin(tags_int)"]},
{"name":"tags_bigint","datatype":"bigint[]","index":["gin(tags_bigint)"]},
{"name":"rating","datatype":"numeric(3,1)","check":"rating >= 0 AND rating <= 10"},
{"name":"coordinate","datatype":"geography(Point, 4326)","index":["gist(coordinate)"]},
{"name":"status","datatype":"smallint","default":1,"index":["btree(status,type)"]},
{"name":"address","datatype":"text","old_name":"adress"},
{"name":"metadata","datatype":"jsonb","index":["gin(metadata)"]},
],
},
"test_comment": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_not_null": True,"index":["btree(created_by_id,id)"]},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"test_id","datatype":"bigint","is_not_null": True,"index":["btree(test_id)"]},
{"name":"description","datatype":"text","is_not_null": True},
],
},
"users": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz","write_blocked":["my"]},
{"name":"verified_by_id","datatype":"bigint","write_blocked":["my"]},
{"name":"deactivated_at","datatype":"timestamptz","write_blocked":["my"]},
{"name":"deactivated_by_id","datatype":"bigint","write_blocked":["my"]},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"is_protected","datatype":"boolean","write_blocked":["my", "public", "private", "admin"]},
{"name":"role","datatype":"smallint","is_not_null": True,"index":["btree(role)"],"write_blocked":["my"]},
{"name":"permissions","datatype":"smallint[]","default": None,"write_blocked":["my"]},
{"name":"username","datatype":"text","unique":[["username", "role"]],"regex":"^(?=.{1,120}\\Z)\\S+\\Z","regex_message":"Username must be 1-120 characters and contain no spaces"},
{"name":"email","datatype":"text","unique":[["email", "role"]]},
{"name":"mobile","datatype":"text","unique":[["mobile", "role"]]},
{"name":"id_ext","datatype":"text","unique":[["id_ext", "role"]],"write_blocked":["my"]},
{"name":"password","datatype":"text","index":["btree(password)"],"regex":"^(?=.{6,120}\\Z)\\S+\\Z","regex_message":"Password must be 6-120 characters and contain no spaces","read_blocked":["my", "public", "private", "admin"]},
{"name":"oidc_google","datatype":"text","old_name":"google_login_id","unique":[["oidc_google", "role"]],"write_blocked":["my"]},
{"name":"last_active_at","datatype":"timestamptz","write_blocked":["my", "public", "private", "admin"]},
{"name":"name","datatype":"text","index":["gin_trgm(name)"]},
{"name":"country","datatype":"text","index":["gin_trgm(country)"]},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_secondary","datatype":"text","regex":"^(?=.{3,254}\\Z)[^\\s@]+@[^\\s@]+\\.[^\\s@]+\\Z","regex_message":"Email must look like name@example.com"},
{"name":"mobile_secondary","datatype":"text","regex":"^\\+?[0-9][0-9 -]{5,19}\\Z","regex_message":"Mobile must be 6-20 digits (spaces, dashes and a leading + allowed)"},
{"name":"address","datatype":"text"},
{"name":"job_title","datatype":"text"},
{"name":"about","datatype":"text"},
{"name":"gender","datatype":"text"},
{"name":"date_of_birth","datatype":"date"},
{"name":"dashboard","datatype":"jsonb"},
{"name":"source","datatype":"smallint","write_blocked":["my"]},
{"name":"parent_id","datatype":"bigint","write_blocked":["my"]},
{"name":"totp_secret","datatype":"text","read_blocked":["my", "public", "private", "admin"],"write_blocked":["my", "public", "private", "admin"]},
{"name":"totp_enabled_at","datatype":"timestamptz","write_blocked":["my"]},
{"name":"totp_last_step","datatype":"bigint","write_blocked":["my", "public", "private", "admin"]},
{"name":"totp_recovery","datatype":"text[]","read_blocked":["my", "public", "private", "admin"],"write_blocked":["my", "public", "private", "admin"]},
],
},
"config": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"key","datatype":"text","is_not_null": True,"unique":[["key"]]},
{"name":"value","datatype":"jsonb","is_not_null": True},
],
},
"otp": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint"},
{"name":"otp","datatype":"integer","is_not_null": True},
{"name":"email","datatype":"text","index":["btree(email)"]},
{"name":"mobile","datatype":"text","index":["btree(mobile)"]},
{"name":"attempt","datatype":"smallint","default":0},
],
},
"blob": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","index":["btree(created_by_id)"]},
{"name":"deleted_at","datatype":"timestamptz","index":["btree(deleted_at)"]},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_not_null": True,"int_mapping":{1: "File", 2: "Presigned Url"}},
{"name":"service","datatype":"text","is_not_null": True},
{"name":"file_url","datatype":"text","is_not_null": True},
],
},
"message": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint","is_not_null": True,"index":["btree(created_by_id)"]},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":["btree(deleted_at)"]},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"received_by_id","datatype":"bigint","is_not_null": True,"index":["btree(received_by_id)"],"ownership":["read", "delete"]},
{"name":"description","datatype":"text","is_not_null": True},
{"name":"read_at","datatype":"timestamptz"},
],
},
"notification": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint","index":["btree(created_by_id)"]},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":["btree(deleted_at)"]},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_not_null": True,"index":["btree(type)"]},
{"name":"received_by_id","datatype":"bigint","is_not_null": True,"index":["btree(received_by_id)"],"ownership":["read", "delete"]},
{"name":"title","datatype":"text","is_not_null": True},
{"name":"description","datatype":"text"},
{"name":"reference_table","datatype":"text"},
{"name":"reference_id","datatype":"bigint"},
{"name":"read_at","datatype":"timestamptz"},
],
},
"log_api": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint","index":["btree(created_by_id,created_at)"]},
{"name":"ip_address","datatype":"text"},
{"name":"response_type","datatype":"text"},
{"name":"method","datatype":"text"},
{"name":"path","datatype":"text"},
{"name":"query_param","datatype":"text"},
{"name":"status_code","datatype":"smallint","index":["btree(status_code)"]},
{"name":"response_time_ms","datatype":"integer"},
{"name":"error","datatype":"text"},
{"name":"request_id","datatype":"text"},
{"name":"request_header","datatype":"jsonb"},
{"name":"response_header","datatype":"jsonb"},
{"name":"request_body","datatype":"text"},
{"name":"response_body","datatype":"text"},
],
},
"api_key": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_not_null": True,"index":["btree(created_by_id)"]},
{"name":"name","datatype":"text","is_not_null": True},
{"name":"key_hash","datatype":"text","is_not_null": True,"unique":[["key_hash"]],"read_blocked":["my", "public", "private", "admin"]},
{"name":"key_prefix","datatype":"text","is_not_null": True},
{"name":"scopes","datatype":"text[]"},
{"name":"expires_at","datatype":"timestamptz"},
],
},
"webhook": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_not_null": True},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"url","datatype":"text","is_not_null": True},
{"name":"events","datatype":"text[]","is_not_null": True},
{"name":"secret","datatype":"text","is_not_null": True,"read_blocked":["my", "public", "private", "admin"]},
{"name":"is_active","datatype":"boolean","default":"true","is_not_null": True},
],
},
"log_users_password": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint","ownership":["read"]},
{"name":"password","datatype":"text"},
],
},
"script_run": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(script,created_at)"]},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"script","datatype":"text","is_not_null": True},
{"name":"started_by","datatype":"text","is_not_null": True,"allowed_values":["schedule", "manual"],"read_blocked":["private"]},
{"name":"host","datatype":"text","read_blocked":["private"]},
{"name":"status","datatype":"smallint","default":1,"is_not_null": True,"allowed_values":[1, 2, 3],"int_mapping":{1: "Running", 2: "Done", 3: "Failed"}},
{"name":"step","datatype":"text","read_blocked":["private"]},
{"name":"message","datatype":"text","read_blocked":["private"]},
{"name":"peak_memory_mb","datatype":"integer","read_blocked":["private"]},
{"name":"finished_at","datatype":"timestamptz"},
],
},
"queue_job": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"channel","datatype":"text","is_not_null": True},
{"name":"payload","datatype":"jsonb","is_not_null": True},
{"name":"status","datatype":"smallint","default":1,"is_not_null": True,"allowed_values":[1, 2],"int_mapping":{1: "Waiting", 2: "Failed"}},
{"name":"attempt","datatype":"integer","default":0,"is_not_null": True},
{"name":"run_at","datatype":"timestamptz","default":"now()","is_not_null": True,"index":["btree(channel,status,run_at,id)"]},
{"name":"error","datatype":"text"},
],
},
"log_users_delete": {
"column": [
{"name":"id","datatype":"bigint","identity":"always","is_primary_key": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":["btree(created_at)"]},
{"name":"created_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_not_null": True,"index":["btree(type,created_at)"],"allowed_values":[1, 2, 3],"int_mapping":{1: "User Soft Deleted", 2: "User Restored", 3: "User Hard Deleted"}},
{"name":"user_id","datatype":"bigint","is_not_null": True,"index":["btree(user_id,created_at)"],"ownership":["read"]},
{"name":"worker_status","datatype":"smallint","index":["btree(worker_status,worker_next_retry_at,created_at)"],"allowed_values":[1, 2, 3, 4],"int_mapping":{None: "Pending", 1: "Processing", 2: "Completed", 3: "Failed", 4: "Dead"}},
{"name":"worker_retry_count","datatype":"integer","default":0},
{"name":"worker_next_retry_at","datatype":"timestamptz","default":"now()"},
{"name":"worker_processed_at","datatype":"timestamptz"},
{"name":"worker_last_error","datatype":"text"},
],
},
},
"control":{
"extension": ["postgis", "pg_trgm", "btree_gin", "vector"],
"is_updated_at_set": True,
"is_protected_delete_disabled": True,
"is_truncate_disabled": True,
"public_create": ["test"],
"public_read": ["test"],
"private_read": ["test"],
"my_create": ["test", "test_comment", "blob", "message", "notification"],
"my_read": ["test", "test_comment", "blob", "message", "notification", "log_api", "api_key", "log_users_delete"],
"my_update": ["test", "test_comment", "blob", "message", "notification"],
"my_delete": ["test", "test_comment", "blob", "message", "notification", "api_key"],
"my_delete_all": ["test", "message", "notification"],
"admin_create": ["*"],
"admin_read": ["*"],
"admin_update": ["*"],
"admin_delete": ["*"],
"row_update_disabled": ["log_api", "api_key", "log_users_password"],
"row_delete_disabled": ["users", "config", "log_users_password", "log_users_delete"],
"row_delete_max": {"users": 100},
"buffer_limit": {"log_api": 1000},
"retention_day": {"otp": 1, "log_api": 7, "script_run": 90},
},
"sql":{},
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
"/my/profile": {"id": 19, "auth": ["jwt"]},
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
"/private/user-read": {"id": 56, "auth": ["jwt"]},
"/private/table-column-groupby": {"id": 57, "auth": ["jwt"], "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/private/table-column-distinct": {"id": 58, "auth": ["jwt"], "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
# admin
"/admin/sync": {"id": 63, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}},
"/admin/monitor": {"id": 64, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_log_api": False, "is_connection_param": True},
"/admin/object-create": {"id": 65, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}, "is_connection_param": True},
"/admin/object-update": {"id": 66, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}, "is_connection_param": True},
"/admin/object-read": {"id": 67, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_connection_param": True},
"/admin/object-read-export": {"id": 68, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_connection_param": True},
"/admin/user-create": {"id": 69, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/user-update": {"id": 70, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/user-delete": {"id": 71, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}, "user_check_deactivated": {"mode": "realtime"}},
"/admin/object-delete": {"id": 72, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "user_check_deleted": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}, "is_connection_param": True},
"/admin/table-column-groupby": {"id": 73, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/admin/table-column-distinct": {"id": 74, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_connection_param": True},
"/admin/postgres-import": {"id": 75, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "is_connection_param": True, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/mongodb-import": {"id": 76, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/blob-container-sas": {"id": 77, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/blob-preview-urls": {"id": 78, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}},
"/admin/blob-container-read": {"id": 79, "auth": ["jwt"], "user_check_permission": {"mode": "token"}},
"/admin/blob-container-ops": {"id": 80, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/blob-delete-url": {"id": 81, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/postgres-info": {"id": 82, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": False}, "is_connection_param": True},
"/admin/postgres-schema": {"id": 83, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_connection_param": True},
"/admin/postgres-slow-queries": {"id": 84, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_connection_param": True},
"/admin/postgres-slow-queries-reset": {"id": 85, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "is_connection_param": True, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/postgres-query-runner-write": {"id": 86, "is_active": True, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/postgres-query-runner-read": {"id": 87, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_connection_param": True},
"/admin/postgres-query-runner-read-export": {"id": 88, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_connection_param": True},
"/admin/postgres-query-ai": {"id": 89, "auth": ["jwt"], "user_check_permission": {"mode": "token"}, "is_connection_param": True},
"/admin/mssql-query-runner-write": {"id": 90, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/mssql-query-runner-read": {"id": 91, "auth": ["jwt"], "user_check_permission": {"mode": "token"}},
"/admin/mssql-query-runner-read-export": {"id": 92, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}},
"/admin/clickhouse-query-runner-write": {"id": 93, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
"/admin/clickhouse-query-runner-read": {"id": 94, "auth": ["jwt"], "user_check_permission": {"mode": "token"}},
"/admin/clickhouse-query-runner-read-export": {"id": 95, "auth": ["jwt"], "user_check_permission": {"mode": "token"}},
"/admin/clickhouse-query-ai": {"id": 96, "auth": ["jwt"], "user_check_permission": {"mode": "token"}},
"/admin/webhook-create": {"id": 101, "auth": ["jwt"], "user_check_permission": {"mode": "realtime"}, "user_check_deactivated": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 60, "window_sec": 60}},
}

# override
from function.config import func_config_load
func_config_load(global_dict=globals())
