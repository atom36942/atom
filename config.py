# Integrations
config_postgres_url = None
config_postgres_url_dict = None
config_redis_url = None
config_redis_url_user_state = None
config_redis_url_ratelimiter = None
config_redis_url_queue = None
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
config_kafka_url = None
config_kafka_username = None
config_kafka_password = None
config_rabbitmq_url = None
config_celery_url = None

# System
config_root_user_password = "123456"
config_login_password = "123456"
config_token_secret_key = "mysecretkey-mysecretkey-mysecretkey"
config_root_html_path = "static/api.html"
config_is_enable_user_delete = 0
config_is_enable_postgres_schema_init = 1
config_is_enable_signup = 1
config_is_enable_otp_require_users_update = 0
config_is_read_only = 0
config_is_debug = 1
config_postgres_pool_min_size = 5
config_postgres_pool_max_size = 20
config_otp_length = 6
config_otp_expiry_sec = 600
config_access_token_expires_sec = 3155695200 
config_refresh_token_expires_sec = 3155695200000
config_blob_limit_size_kb = 500
config_blob_limit_upload = 100
config_blob_expire_sec_upload = 3600
config_blob_expire_sec_preview = 360000
config_buffer_limit_default = 100
config_postgres_buffer_flush_auto_sec = 60
config_inmemory_cache_cleanup_auto_sec = 300
config_batch_item_limit = 1000
config_sql_read_limit_default = 100
config_sql_read_limit_max = 10000
config_sql_read_relation_fetch_limit_max = 100
config_query_runner_read_limit = 5000
config_query_runner_export_limit = 50000
config_allowed_users_role = [1, 2, 3, 4, 5]
config_redis_cache_ttl_sec = 3600
config_users_delete_data_retention_day = 30
config_cors_allow_origins = []
config_cors_allow_origin_regex = ".*"
config_cors_allow_methods = ["*"]
config_cors_allow_headers = ["*"]
config_cors_expose_headers = ["*"]
config_cors_allow_credentials = True
config_postgres_db_log_api = None

# Table
config_table_sensitive = ["spatial_ref_sys", "users", "log_users_delete"]
config_table_my_create_disable = ["users", "log_api", "log_users_password", "otp","spatial_ref_sys"]
config_table_my_delete_all_enable = ["test"]
config_table_my_delete_all_received_enable = ["message","notification"]
config_table_public_create_enable = ["test"]
config_table_public_read_enable = ["test"]

# Column
config_column_token_encode = ["id", "role", "username", "id_ext" ,"deactivated_at", "deleted_at"]
config_column_ownership = ["created_by_id", "user_id"]
config_column_admin = ["created_at", "updated_at", "created_by_id", "role", "verified_at", "verified_by_id"]
config_column_admin_users=["role"]
config_column_single_update = ["username", "password", "email", "mobile", "deleted_at"]

# Services
config_queue_services = ["redis", "rabbitmq", "kafka", "celery"]
config_blob_services = ["s3", "azure"]
config_email_services = ["ses", "resend", "azure"]
config_mobile_services = ["sns", "fast2sms"]
config_ai_services = ["gemini", "openai"]

# Dict
config_sql = {
"config": "select key,value from config where deactivated_at is null order by id asc limit 1000",
"users_role": "select id,role from users where role is not null order by id asc limit 1000",
"users_deactivated": "select id, deactivated_at from users order by id asc limit 1000",
"users_deleted": "select id, deleted_at from users order by id asc limit 1000",
"profile_metadata": {},
}

config_table = {
"test": {"buffer_limit": 10},
"log_api": {"retention_day": 30, "buffer_limit": 10},
"log_users_password": {"retention_day": 90},
"otp": {"retention_day": 30},
"notification": {"retention_day": 30, "buffer_limit": 10},
}

config_regex = {
"username": ["^(?=.{1,120}\\Z)\\S+\\Z", "Username must be 1-120 characters and contain no spaces"],
"password": ["^(?=.{6,120}\\Z)\\S+\\Z", "Password must be 6-120 characters and contain no spaces"],
}

config_dropdown = {"gender": ["male", "female"],}

config_column_int_mapping = {
"worker_status": {None: "Pending", 1: "Processing", 2: "Completed", 3: "Failed", 4: "Dead"},
"type": {
"log_users_delete": {1: "User Soft Deleted", 2: "User Restored", 3: "User Hard Deleted"},
"blob": {1: "File", 2: "Presigned Url"},
},
}

config_postgres = {
"extension": ["postgis", "pg_trgm", "btree_gin"],
"table":{
"test":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","index":"btree(type)"},
{"name":"title","datatype":"text","is_mandatory":1,"index":"gin_trgm(title)"},
{"name":"description","datatype":"text"},
{"name":"slug","datatype":"text","index":"btree(slug)"},
{"name":"code","datatype":"text","is_mandatory":0,"unique":"code,type|code,slug"},
{"name":"email","datatype":"text","regex":"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$","index":"btree(email)"},
{"name":"tag","datatype":"text[]","index":"gin(tag)"},
{"name":"tag_int","datatype":"integer[]","index":"gin(tag_int)"},
{"name":"tag_bigint","datatype":"bigint[]","index":"gin(tag_bigint)"},
{"name":"rating","datatype":"numeric(3,1)","check":"rating >= 0 AND rating <= 10"},
{"name":"coordinate","datatype":"geography(Point, 4326)","index":"gist(coordinate)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status,type)"},
{"name":"address","datatype":"text","old":"adress"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
],
"users":[
{"name":"id","datatype":"bigserial","is_primary":1},
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
{"name":"role","datatype":"smallint","is_mandatory":1,"index":"btree(role)"},
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
],
"config":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"key","datatype":"text","is_mandatory":1,"unique":"key"},
{"name":"value","datatype":"jsonb","is_mandatory":1},
],
"otp":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"otp","datatype":"integer","is_mandatory":1},
{"name":"email","datatype":"text","index":"btree(email)"},
{"name":"mobile","datatype":"text","index":"btree(mobile)"},
],
"blob":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory":1},
{"name":"service","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text","is_mandatory":1}
],
"message":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"read_at","datatype":"timestamptz"}
],
"notification":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory":1,"index":"btree(type)"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id)"},
{"name":"title","datatype":"text","is_mandatory":1},
{"name":"description","datatype":"text"},
{"name":"reference_table","datatype":"text"},
{"name":"reference_id","datatype":"bigint"},
{"name":"read_at","datatype":"timestamptz"}
],
"comment_test":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
],
"log_api":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
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
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"log_users_delete":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory":1,"in":(1,2,3),"index":"btree(type,created_at)"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id,created_at)"},
{"name":"worker_status","datatype":"smallint","in":(1,2,3,4),"index":"btree(worker_status,worker_next_retry_at,created_at)"},
{"name":"worker_retry_count","datatype":"integer","default":0},
{"name":"worker_next_retry_at","datatype":"timestamptz","default":"now()"},
{"name":"worker_processed_at","datatype":"timestamptz"},
{"name":"worker_last_error","datatype":"text"}
],
"jobseeker":[
{"name":"id","datatype":"bigserial","is_primary":1},
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
{"name":"profile","datatype":"text","index":"btree(profile)|gin_trgm(profile)"},
{"name":"name","datatype":"text"},
{"name":"email","datatype":"text"},
{"name":"college","datatype":"text[]"},
{"name":"resume_url","datatype":"text"},
{"name":"resume_content","datatype":"text"},
{"name":"video_url","datatype":"text"},
{"name":"skills","datatype":"text[]"},
{"name":"experience","datatype":"numeric(4,1)"},
{"name":"company_current","datatype":"text"},
{"name":"company_past","datatype":"text[]"},
{"name":"ctc_current","datatype":"integer"},
{"name":"ctc_expected","datatype":"integer"},
{"name":"currency","datatype":"text"},
{"name":"notice_period_days","datatype":"integer"},
{"name":"location_current","datatype":"text"},
{"name":"location_preferred","datatype":"text[]"},
{"name":"qualification_highest","datatype":"text"},
{"name":"source","datatype":"text"},
{"name":"linkedin_url","datatype":"text"},
{"name":"github_url","datatype":"text"},
{"name":"portfolio_url","datatype":"text"},
{"name":"languages","datatype":"text[]"},
{"name":"gender","datatype":"text"},
{"name":"worker_status","datatype":"smallint","in":(1,2,3,4),"index":"btree(worker_status,worker_next_retry_at,created_at)"},
{"name":"worker_retry_count","datatype":"integer","default":0},
{"name":"worker_next_retry_at","datatype":"timestamptz","default":"now()"},
{"name":"worker_processed_at","datatype":"timestamptz"},
{"name":"worker_last_error","datatype":"text"},
{"name":"ai_remark","datatype":"text"},
{"name":"ai_rating","datatype":"numeric(3,1)"},
{"name":"remark","datatype":"text"},
{"name":"rating","datatype":"numeric(3,1)"},
{"name":"status","datatype":"smallint","default":1},
{"name":"mobile","datatype":"text"},
{"name":"work_authorization","datatype":"text"},
{"name":"graduation_year","datatype":"integer"},
{"name":"certifications","datatype":"jsonb"},
{"name":"summary","datatype":"text"},
{"name":"projects","datatype":"jsonb",},
{"name":"industry","datatype":"text"}
],
},
"control":{
"is_enable_updated_at_set":1,
"is_enable_is_protected_delete_disable":1,
"is_enable_truncate_table":0,
"is_enable_log_users_password":1,
"is_enable_log_users_delete":1,
"is_enable_root_user_create":1,
"is_enable_root_user_delete_disable":1,
"table_row_delete_disable_all":["users", "config", "log_users_password", "log_users_delete"],
"table_row_delete_disable_bulk":[["*", 1000]],
},
"sql":{
},
}

config_api = {
# index
"/": {"id": 35, "is_token_check": 0},
"/health": {"id": 36, "is_token_check": 0},
"/info": {"id": 17, "is_token_check": 0, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": 0}},
"/openapi.json": {"id": 37, "is_token_check": 0},
"/static": {"id": 77, "is_token_check": 0},
"/websocket": {"id": 38, "is_token_check": 0},
# auth
"/auth/login-password": {"id": 91, "is_token_check": 0},
"/auth/signup-username-password": {"id": 39, "is_token_check": 0},
"/auth/login-username-password": {"id": 40, "is_token_check": 0},
"/auth/login-email-password": {"id": 41, "is_token_check": 0},
"/auth/login-mobile-password": {"id": 42, "is_token_check": 0},
"/auth/login-email-otp": {"id": 43, "is_token_check": 0},
"/auth/login-mobile-otp": {"id": 44, "is_token_check": 0},
"/auth/login-google": {"id": 45, "is_token_check": 0},
# my
"/my/profile": {"id": 46, "is_token_check": 1},
"/my/ping": {"id": 92, "is_token_check": 1},
"/my/token-refresh": {"id": 47, "is_token_check": 1},
"/my/api-usage": {"id": 48, "is_token_check": 1},
"/my/object-create": {"id": 49, "is_token_check": 1},
"/my/object-read": {"id": 50, "is_token_check": 1},
"/my/object-update": {"id": 51, "is_token_check": 1},
"/my/object-delete": {"id": 52, "is_token_check": 1},
"/my/object-delete-all": {"id": 53, "is_token_check": 1},
"/my/object-delete-received": {"id": 54, "is_token_check": 1},
"/my/object-delete-received-all": {"id": 55, "is_token_check": 1},
"/my/message-inbox": {"id": 56, "is_token_check": 1},
"/my/message-thread": {"id": 57, "is_token_check": 1},
"/my/object-create-mongodb": {"id": 58, "is_token_check": 1},
"/my/blob-delete-all": {"id": 59, "is_token_check": 1},
"/my/blob-delete-url": {"id": 60, "is_token_check": 1},
# private
"/private/send-email": {"id": 61, "is_token_check": 1},
"/private/blob-upload-file": {"id": 62, "is_token_check": 1},
"/private/blob-upload-url": {"id": 63, "is_token_check": 1},
"/private/blob-container-sas": {"id": 64, "is_token_check": 1},
"/private/blob-preview-urls": {"id": 65, "is_token_check": 1},
# public
"/public/object-create": {"id": 66, "is_token_check": 0},
"/public/object-read": {"id": 14, "is_token_check": 0, "cache": {"mode": "inmemory", "ttl_sec": 100, "is_per_user": 0}},
"/public/converter-number": {"id": 67, "is_token_check": 0},
"/public/otp-verify": {"id": 68, "is_token_check": 0},
"/public/otp-send-email": {"id": 69, "is_token_check": 0},
"/public/otp-send-mobile": {"id": 70, "is_token_check": 0},
"/public/otp-send-mobile-sns-template": {"id": 71, "is_token_check": 0},
"/public/jira-worklog-export": {"id": 19, "is_token_check": 0},
"/public/table-groupby": {"id": 18, "is_token_check": 0, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": 0}},
"/public/table-distinct": {"id": 96, "is_token_check": 0, "cache": {"mode": "inmemory", "ttl_sec": 10, "is_per_user": 0}},
"/public/blob-upload-file": {"id": 97, "is_token_check": 0},
"/public/blob-upload-url": {"id": 98, "is_token_check": 0},
# admin
"/admin/sync": {"id": 1, "is_token_check": 1, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/object-create": {"id": 2, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/object-update": {"id": 3, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/object-read": {"id": 4, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1, 2]}},
"/admin/object-delete": {"id": 5, "is_token_check": 1, "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "user_check_deleted": {"mode": "realtime"}, "rate_limit": {"mode": "inmemory", "limit": 10, "window_sec": 60}},
"/admin/postgres-import": {"id": 8, "is_token_check": 1, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/redis-import": {"id": 9, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/mongodb-import": {"id": 11, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/blob-container-read": {"id": 10, "is_token_check": 1, "user_check_role": {"mode": "inmemory", "roles": [1]}},
"/admin/blob-container-ops": {"id": 12, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/blob-delete-url": {"id": 13, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1]}},
"/admin/postgres-info": {"id": 84, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1, 2]}, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": 0}},
"/admin/postgres-schema": {"id": 85, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1, 2]}, "cache": {"mode": "inmemory", "ttl_sec": 300, "is_per_user": 0}},
"/admin/postgres-query-runner-write": {"id": 6, "is_token_check": 1, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/postgres-query-runner-read": {"id": 22, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1, 2]}},
"/admin/postgres-query-runner-read-export": {"id": 7, "is_token_check": 1, "user_check_role": {"mode": "inmemory", "roles": [1, 2]}},
"/admin/postgres-query-generator-ai": {"id": 90, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1, 2]}},
"/admin/mssql-query-runner-write": {"id": 21, "is_token_check": 1, "user_check_role": {"mode": "realtime", "roles": [1]}},
"/admin/mssql-query-runner-read": {"id": 23, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1, 2]}},
"/admin/mssql-query-runner-read-export": {"id": 89, "is_token_check": 1, "user_check_role": {"mode": "realtime", "roles": [1, 2]}},
"/admin/clickhouse-query-runner-write": {"id": 93, "is_token_check": 1, "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deactivated": {"mode": "realtime"}, "user_check_deleted": {"mode": "realtime"}},
"/admin/clickhouse-query-runner-read": {"id": 94, "is_token_check": 1, "user_check_role": {"mode": "token", "roles": [1, 2]}},
"/admin/clickhouse-query-runner-read-export": {"id": 95, "is_token_check": 1, "user_check_role": {"mode": "inmemory", "roles": [1, 2]}},
}

#override
def func_config_override_from_env(*, global_dict: dict) -> None:
    import orjson, os, ast, contextlib; from dotenv import load_dotenv
    load_dotenv(".env")
    env = {k.lower(): v for k, v in os.environ.items()}
    env.update({k: v for k, v in os.environ.items() if k == k.lower()})
    for k, v in list(global_dict.items()):
        if k.startswith("config_") and (ev := env.get(k)) is not None:
            if isinstance(v, bool): global_dict[k] = 1 if ev.lower() in ("true", "1", "yes", "on", "ok") else 0
            elif isinstance(v, (list, tuple, dict)):
                with contextlib.suppress(Exception): global_dict[k] = orjson.loads(ev)
            else: global_dict[k] = int(ev) if ev.lstrip("-").isdigit() else ev
            if isinstance(global_dict[k], list): global_dict[k] = tuple(global_dict[k])
    postgres_url_prefix = "config_postgres_url_"
    for k, v in env.items():
        if k.startswith(postgres_url_prefix) and k not in (postgres_url_prefix, "config_postgres_url_dict"):
            if not isinstance(global_dict["config_postgres_url_dict"], dict):
                global_dict["config_postgres_url_dict"] = {}
            global_dict["config_postgres_url_dict"][k.removeprefix(postgres_url_prefix)] = v
    with contextlib.suppress(Exception):
        for n in ast.parse(open("config.py", encoding="utf-8").read()).body:
            if isinstance(n, ast.Assign) and len(n.targets)==1 and (t:=getattr(n.targets[0], "id", "")).startswith("config_") and (v:=getattr(n.value, "id", "")).startswith("config_") and t not in env: global_dict[t] = global_dict.get(v)
    return None
func_config_override_from_env(global_dict=globals())
