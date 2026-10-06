# Integrations
config_postgres_url_dict = {}
config_redis_url_api_response = None
config_redis_url_user_state = None
config_redis_url_ratelimiter = None
config_redis_url_queue = None
config_redis_url_misc = None
config_mongodb_url = None
config_mssql_url = None
config_clickhouse_url = None
config_google_login_client_id = None
config_openai_key = None
config_gemini_key = None
config_posthog_project_host = None
config_posthog_project_key = None
config_sentry_dsn = None
config_fast2sms_url = None
config_fast2sms_key = None
config_resend_url = None
config_resend_key = None
config_sftp_host = None
config_sftp_port = None
config_sftp_username = None
config_sftp_password = None
config_aws_access_key_id = None
config_aws_secret_access_key = None
config_aws_s3_region_name = None
config_aws_sns_region_name = None
config_aws_ses_region_name = None
config_azure_account_name = None
config_azure_account_key = None
config_azure_email_connection_string = None
config_azure_sms_connection_string = None
config_azure_sms_from_number = None
config_msgraph_tenant_id = None
config_msgraph_client_id = None
config_msgraph_client_secret = None
config_kafka_url = None
config_kafka_username = None
config_kafka_password = None
config_rabbitmq_url = None
config_celery_url = None

# System
config_root_user_password = None
config_login_password = None
config_token_secret_key = None
config_root_html_path = "static/api.html"
config_is_user_delete = False
config_is_postgres_schema_init = True
config_signup_allowed_roles = []
config_login_allowed_roles = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
config_is_otp_require_users_update = False
config_is_read_only = False
config_is_prod = True
config_is_tmp_reset = True
config_postgres_pool_min_size = 5
config_postgres_pool_max_size = 20
config_otp_length = 6
config_otp_expiry_sec = 600
config_otp_static = None
config_otp_max_attempt = 5
config_otp_retention_day = 1
config_log_api_retention_day = 30
config_access_token_expires_sec = 604800
config_refresh_token_expires_sec = 2592000
config_blob_limit_size_kb = 500
config_blob_limit_upload = 100
config_blob_expire_sec_upload = 3600
config_blob_expire_sec_preview = 360000
config_buffer_limit_default = 100
config_buffer_rows_max = 100000
config_postgres_buffer_flush_auto_sec = 60
config_inmemory_cache_cleanup_auto_sec = 300
config_batch_item_limit = 1000
config_sql_read_limit_default = 100
config_sql_read_limit_max = 10000
config_sql_read_relation_fetch_limit_max = 100
config_query_runner_read_limit = 5000
config_query_runner_export_limit = 50000
config_redis_cache_ttl_sec = 3600
config_users_delete_retention_day = 30
config_cors_allow_origins = []
config_cors_allow_origin_regex = None
config_cors_allow_methods = ["*"]
config_cors_allow_headers = ["*"]
config_cors_expose_headers = ["*"]
config_cors_allow_credentials = True
config_postgres_db_log_api = "master"

# Services
config_queue_services = ["redis", "rabbitmq", "kafka", "celery"]
config_blob_services = ["s3", "azure"]
config_email_services = ["ses", "resend", "azure"]
config_mobile_services = ["sns", "fast2sms", "azure"]
config_ai_services = ["gemini", "openai"]

# Table
config_table_exclude_from_users_delete = ["spatial_ref_sys", "users", "log_users_delete"]
config_table_my_create_blocked = ["users", "log_api", "log_users_password", "otp", "spatial_ref_sys"]
config_table_my_read_blocked = ["users", "config", "log_users_password", "otp", "spatial_ref_sys"]
config_table_my_delete_all_allowed = ["test", "message", "notification"]
config_table_public_create_allowed = ["test"]
config_table_public_read_allowed = ["test"]
config_table_private_read_allowed = ["test", "task", "task_comment"]

# Column
config_column_token_encode = ["id", "role", "username", "id_ext" ,"deactivated_at", "deleted_at"]
config_column_ownership_read = ["created_by_id", "received_by_id", "assigned_to_id", "user_id"]
config_column_ownership_update = ["created_by_id", "assigned_to_id"]
config_column_ownership_delete = ["created_by_id", "received_by_id", "assigned_to_id"]
config_column_admin = ["created_at", "updated_at", "created_by_id", "role", "verified_at", "verified_by_id"]
config_column_single_update = ["username", "password", "email", "mobile", "deleted_at"]
config_column_read_blocked = ["password"]

# Dict
config_sql = {
"config": "select key,value from config where deactivated_at is null order by id asc limit 1000",
"users_role": "select id,role from users where role is not null order by id asc limit 1000",
"users_deactivated": "select id, deactivated_at from users order by id asc limit 1000",
"users_deleted": "select id, deleted_at from users order by id asc limit 1000",
"profile_metadata": {},
}

config_table = {
"log_api": {"buffer_limit": 10},
}

config_column_regex = {
"username": ["^(?=.{1,120}\\Z)\\S+\\Z", "Username must be 1-120 characters and contain no spaces"],
"password": ["^(?=.{6,120}\\Z)\\S+\\Z", "Password must be 6-120 characters and contain no spaces"],
}

config_dropdown = {"gender": ["male", "female"],}

config_column_int_mapping = {
"test": {
"type": {1: "Sample Type 1", 2: "Sample Type 2"},
"status": {1: "Active", 2: "Inactive"},
},
"users": {
"role": {1: "Admin", 2: "Sample Role 2", 3: "Sample Role 3"},
"source": {1: "Sample Source 1", 2: "Sample Source 2"},
"permissions": {1: "invoice.export", 2: "invoice.filter.apply", 3: "invoice.delete"},
},
"notification": {
"type": {1: "Sample Notification 1", 2: "Sample Notification 2"},
},
"blob": {
"type": {1: "File", 2: "Presigned Url"},
},
"log_users_delete": {
"type": {1: "User Soft Deleted", 2: "User Restored", 3: "User Hard Deleted"},
"worker_status": {None: "Pending", 1: "Processing", 2: "Completed", 3: "Failed", 4: "Dead"},
},
}

config_postgres = {
"extension": ["postgis", "pg_trgm", "btree_gin"],
"table":{
"test":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
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
{"name":"created_by_id","datatype":"bigint","is_mandatory": True},
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
{"name":"google_login_id","datatype":"text","unique":"google_login_id,role"},
{"name":"google_login_metadata","datatype":"jsonb"},
{"name":"last_active_at","datatype":"timestamptz"},
{"name":"name","datatype":"text","index":"gin_trgm(name)"},
{"name":"country","datatype":"text","index":"gin_trgm(country)"},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_secondary","datatype":"text",},
{"name":"mobile_secondary","datatype":"text"},
{"name":"address","datatype":"text"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text"},
{"name":"gender","datatype":"text"},
{"name":"date_of_birth","datatype":"date"},
{"name":"dashboard","datatype":"jsonb"},
{"name":"source","datatype":"smallint"},
{"name":"parent_id","datatype":"bigint"},
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
{"name":"error","datatype":"text"}
],
"log_users_password":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
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
"table_row_delete_disable_bulk":[["*", 1000]],
},
"sql":{
},
}

config_api = {
# index
"/": {"id": 35, "is_token": False},
"/health": {"id": 36, "is_token": False},
"/info": {"id": 17, "is_token": False, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": False}},
"/openapi.json": {"id": 37, "is_token": False},
"/static": {"id": 77, "is_token": False},
"/pgweb": {"id": 99, "is_token": False},
"/websocket": {"id": 38, "is_token": False, "is_active": False},
# auth
"/auth/login-password": {"id": 91, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/signup-username-password": {"id": 39, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/auth/login-username-password": {"id": 40, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-email-password": {"id": 41, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-mobile-password": {"id": 42, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-id-ext-password": {"id": 103, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/auth/login-email-otp": {"id": 43, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/auth/login-mobile-otp": {"id": 44, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/auth/login-google": {"id": 45, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
# my
"/my/profile": {"id": 46, "is_token": True, "is_postgres_param": True},
"/my/ping": {"id": 92, "is_token": True},
"/my/token-refresh": {"id": 47, "is_token": True},
"/my/api-usage": {"id": 48, "is_token": True},
"/my/object-create": {"id": 49, "is_token": True},
"/my/object-read": {"id": 50, "is_token": True, "is_postgres_param": True},
"/my/object-update": {"id": 51, "is_token": True},
"/my/object-delete": {"id": 52, "is_token": True},
"/my/object-delete-all": {"id": 53, "is_token": True},
"/my/message-inbox": {"id": 56, "is_token": True, "is_postgres_param": True},
"/my/message-thread": {"id": 57, "is_token": True, "is_postgres_param": True},
"/my/object-create-mongodb": {"id": 58, "is_token": True},
"/my/blob-preview-urls": {"id": 65, "is_token": True},
"/my/blob-delete-all": {"id": 59, "is_token": True},
"/my/blob-delete-url": {"id": 60, "is_token": True},
# private
"/private/send-email": {"id": 61, "is_token": True},
"/private/blob-upload-file": {"id": 62, "is_token": True},
"/private/blob-upload-presigned": {"id": 63, "is_token": True},
"/private/object-read": {"id": 102, "is_token": True, "is_postgres_param": True},
"/private/users-list": {"id": 112, "is_token": True, "is_postgres_param": True},
"/private/table-column-groupby": {"id": 107, "is_token": True, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_postgres_param": True},
"/private/table-column-distinct": {"id": 108, "is_token": True, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_postgres_param": True},
# public
"/public/object-create": {"id": 66, "is_token": False},
"/public/object-read": {"id": 14, "is_token": False, "cache": {"mode": "inmemory", "ttl_sec": 100, "is_per_user": False}, "is_postgres_param": True},
"/public/converter-number": {"id": 67, "is_token": False},
"/public/otp-verify": {"id": 68, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
"/public/otp-send-email": {"id": 69, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 3, "window_sec": 60}},
"/public/otp-send-mobile": {"id": 70, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 3, "window_sec": 60}},
"/public/otp-send-mobile-sns-template": {"id": 71, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 3, "window_sec": 60}},
"/public/table-column-groupby": {"id": 18, "is_token": False, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_postgres_param": True},
"/public/table-column-distinct": {"id": 105, "is_token": False, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_postgres_param": True},
"/public/blob-upload-file": {"id": 97, "is_active": False, "is_token": False},
"/public/blob-upload-presigned": {"id": 98, "is_active": False, "is_token": False},
"/public/password-hash": {"id": 100, "is_token": False, "rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}},
# admin
"/admin/sync": {"id": 1, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/runtime-status": {"id": 120, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/object-create": {"id": 2, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/object-update": {"id": 3, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/object-read": {"id": 4, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}, "is_postgres_param": True},
"/admin/object-delete": {"id": 5, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "user_check_deleted": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/admin/table-column-groupby": {"id": 104, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_postgres_param": True},
"/admin/table-column-distinct": {"id": 106, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": False}, "is_postgres_param": True},
"/admin/postgres-import": {"id": 8, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}, "is_postgres_param": True},
"/admin/mongodb-import": {"id": 11, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/blob-container-sas": {"id": 64, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/blob-preview-urls": {"id": 113, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/blob-container-read": {"id": 10, "is_token": True, "user_check_role": {"mode": "inmemory", "roles": [1]}},
"/admin/blob-container-ops": {"id": 12, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/blob-delete-url": {"id": 13, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/postgres-info": {"id": 84, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": False}, "is_postgres_param": True},
"/admin/postgres-schema": {"id": 85, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": False}, "is_postgres_param": True},
"/admin/postgres-query-runner-write": {"id": 6, "is_active": True, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/postgres-query-runner-read": {"id": 22, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}, "is_postgres_param": True},
"/admin/postgres-query-runner-read-export": {"id": 7, "is_token": True, "user_check_role": {"mode": "inmemory", "roles": [1]}, "is_postgres_param": True},
"/admin/postgres-query-generator-ai": {"id": 90, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}, "is_postgres_param": True},
"/admin/mssql-query-runner-write": {"id": 21, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/mssql-query-runner-read": {"id": 23, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/mssql-query-runner-read-export": {"id": 89, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/clickhouse-query-runner-write": {"id": 93, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "user_check_deleted": {"mode": "realtime"}},
"/admin/clickhouse-query-runner-read": {"id": 94, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/clickhouse-query-runner-read-export": {"id": 95, "is_token": True, "user_check_role": {"mode": "inmemory", "roles": [1]}},
"/admin/clickhouse-query-generator-ai": {"id": 101, "is_token": True, "user_check_role": {"mode": "token", "roles": [1]}},
}

# override
from function.config import func_config_load_env
func_config_load_env(global_dict=globals())
