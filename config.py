# Integrations
config_postgres_url = None
config_postgres_url_read = None
config_redis_url = None
config_redis_url_queue = None
config_mongodb_url = None
config_mssql_url = None
config_mssql_url_read = None
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
config_token_secret_key = "mysecretkey-mysecretkey-mysecretkey"
config_root_html_path = "static/api.html"
config_is_enable_user_delete = 0
config_is_enable_postgres_schema_init = 1
config_is_enable_signup = 1
config_is_enable_otp_require_users_update = 0
config_is_notification = 0
config_is_debug = 1
config_otp_length = 6
config_otp_expiry_sec = 600
config_access_token_expires_in_sec = 3155695200 
config_refresh_token_expires_in_sec = 3155695200000
config_blob_limit_size_kb = 500
config_blob_limit_upload = 100
config_blob_expire_sec_upload = 3600
config_blob_expire_sec_preview = 360000
config_buffer_limit_default = 100
config_batch_item_limit = 1000
config_sql_read_limit_default = 100
config_sql_read_limit_max = 10000
config_sql_read_relation_fetch_limit_max = 100
config_allowed_auth_types = [1]
config_allowed_token_key = ["id", "type", "role", "username", "deactivated_at", "deleted_at"]
config_users_delete_data_retention_day = 30
config_sensitive_tables = ["spatial_ref_sys", "users", "log_users_delete", "jobseeker"]
config_redis_cache_ttl_sec = 3600
config_table_disable_create_my = ["users", "log_api", "log_users_password", "otp","spatial_ref_sys"]
config_table_enable_create_public = ["test"]
config_table_enable_read_public = ["*"]
config_table_enable_delete_all_my = ["*"]
config_table_enable_delete_all_my_user_id = ["message","notification"]
config_column_admin = ["created_at", "updated_at", "created_by_id", "role", "verified_at", "verified_by_id"]
config_column_single_update = ["username", "password", "email", "mobile", "deleted_at"]
config_cors_allow_origins = []
config_cors_allow_origin_regex = ".*"
config_cors_allow_methods = ["*"]
config_cors_allow_headers = ["*"]
config_cors_expose_headers = ["*"]
config_cors_allow_credentials = True

# General
config_allowed_queue_services = ["redis", "rabbitmq", "kafka", "celery"]
config_allowed_blob_services = ["s3", "azure"]
config_allowed_email_services = ["ses", "resend", "azure"]
config_allowed_mobile_services = ["sns", "fast2sms"]
config_allowed_user_storage_backends = ["token", "realtime", "redis", "inmemory"]
config_allowed_api_storage_backends = ["redis", "inmemory"]
config_allowed_api_namespace = ["/", "/auth/", "/my/", "/public/", "/private/", "/admin/"]
config_users_ownership_column = ["created_by_id", "user_id"]

# Dict
config_sql = {
"config": "select key,value from config order by id asc limit 1000",
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

config_api = {
"/admin/sync": {"id": 1, "user_role_check": ["realtime", [1]]},
"/admin/object-create": {"id": 2, "user_role_check": ["token", [1]]},
"/admin/object-update": {"id": 3, "user_role_check": ["token", [1]]},
"/admin/object-read": {"id": 4, "user_role_check": ["token", [1]]},
"/admin/object-delete": {"id": 5, "user_role_check": ["realtime", [1]], "user_deactivated_check": ["realtime"], "user_deleted_check": ["realtime"]},
"/admin/postgres-sql-runner": {"id": 6, "user_role_check": ["realtime", [1]]},
"/admin/postgres-sql-runner-read": {"id": 22, "user_role_check": ["realtime", [1]]},
"/admin/postgres-export": {"id": 7, "user_role_check": ["inmemory", [1]]},
"/admin/postgres-import": {"id": 8, "user_role_check": ["realtime", [1]]},
"/admin/redis-import": {"id": 9, "user_role_check": ["token", [1]]},
"/admin/blob-container-read": {"id": 10, "user_role_check": ["inmemory", [1]]},
"/admin/mongodb-import": {"id": 11, "user_role_check": ["token", [1]]},
"/admin/blob-container-ops": {"id": 12, "user_role_check": ["token", [1]]},
"/admin/blob-url-delete": {"id": 13, "user_role_check": ["token", [1]]},
"/admin/mssql-sql-runner": {"id": 21, "user_role_check": ["realtime", [1]]},
"/admin/mssql-sql-runner-read": {"id": 23, "user_role_check": ["realtime", [1]]},
"/my/cargowise-profile": {"id": 24, "api_cache_sec": ["redis", 300]},
"/my/cargowise-purchase-orders": {"id": 25, "api_cache_sec": ["redis", 300]},
"/my/cargowise-purchase-orders-line-items": {"id": 33, "api_cache_sec": ["redis", 300]},
"/my/cargowise-shipments": {"id": 26, "api_cache_sec": ["redis", 300]},
"/my/cargowise-containers": {"id": 27, "api_cache_sec": ["redis", 300]},
"/my/cargowise-tracking": {"id": 28, "api_cache_sec": ["redis", 300]},
"/my/cargowise-exceptions": {"id": 29, "api_cache_sec": ["redis", 300]},
"/my/cargowise-documents": {"id": 30, "api_cache_sec": ["redis", 300]},
"/my/cargowise-analytics": {"id": 31, "api_cache_sec": ["redis", 300]},
"/admin/cargowise-buyer-360": {"id": 32, "user_role_check": ["token", [1]], "api_cache_sec": ["redis", 1000]},
"/public/object-read": {"id": 14, "api_cache_sec": ["inmemory", 100]},
"/info": {"id": 17, "api_cache_sec": ["inmemory", 100]},
"/public/table-groupby": {"id": 18, "api_cache_sec": ["inmemory", 10]},
"/public/jira-worklog-export": {"id": 19, "api_ratelimiting_times_sec": ["inmemory", 10, 60]},
}

config_column_int_mapping = {
"worker_status": {None: "Pending", 1: "Processing", 2: "Completed", 3: "Failed", 4: "Dead"},
"type": {
"notification": {1: "Password Change", 2: "Job Status Change", 3: "Account Created"},
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
{"name":"title","datatype":"text","is_mandatory":1,"index":"gin(title)"},
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
{"name":"type","datatype":"smallint","is_mandatory":1,"index":"btree(type)"},
{"name":"username","datatype":"text","is_mandatory":1,"unique":"username,type"},
{"name":"password","datatype":"text","index":"btree(password)"},
{"name":"google_login_id","datatype":"text","unique":"google_login_id,type"},
{"name":"google_login_metadata","datatype":"jsonb"},
{"name":"email","datatype":"text","unique":"email,type"},
{"name":"mobile","datatype":"text","unique":"mobile,type"},
{"name":"role","datatype":"smallint","is_mandatory":0,"index":"btree(role)"},
{"name":"last_active_at","datatype":"timestamptz"},
{"name":"name","datatype":"text"},
{"name":"country","datatype":"text"},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_secondary","datatype":"text",},
{"name":"mobile_secondary","datatype":"text"},
{"name":"address","datatype":"text"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text"},
{"name":"gender","datatype":"text"},
{"name":"date_of_birth","datatype":"date"},
{"name":"id_ext","datatype":"text","unique":"id_ext,type"},
],
"config":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"key","datatype":"text","is_mandatory":1,"unique":"key"},
{"name":"value","datatype":"jsonb","is_mandatory":1},
],
"otp":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"otp","datatype":"integer","is_mandatory":1},
{"name":"email","datatype":"text","index":"btree(email)"},
],
"blob":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory":1},
{"name":"service","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text","is_mandatory":1,"unique":"file_url"}
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
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"profile","datatype":"text","index":"btree(profile)|gin(profile)"},
{"name":"name","datatype":"text","index":"btree(name)|gin(name)"},
{"name":"email","datatype":"text","index":"btree(email)"},
{"name":"college","datatype":"text"},
{"name":"resume_url","datatype":"text"},
{"name":"resume_content","datatype":"text"},
{"name":"video_url","datatype":"text"},
{"name":"skills","datatype":"text[]","index":"gin(skills)"},
{"name":"experience","datatype":"numeric(4,1)","index":"btree(experience)"},
{"name":"company_current","datatype":"text"},
{"name":"company_past","datatype":"text"},
{"name":"ctc_current","datatype":"integer","index":"btree(ctc_current)"},
{"name":"ctc_expected","datatype":"integer","index":"btree(ctc_expected)"},
{"name":"currency","datatype":"text"},
{"name":"notice_period_days","datatype":"integer"},
{"name":"location_current","datatype":"text","index":"btree(location_current)"},
{"name":"location_preferred","datatype":"text[]","index":"gin(location_preferred)"},
{"name":"qualification_highest","datatype":"text"},
{"name":"source","datatype":"text","index":"btree(source)"},
{"name":"linkedin_url","datatype":"text"},
{"name":"github_url","datatype":"text"},
{"name":"portfolio_url","datatype":"text"},
{"name":"languages","datatype":"text[]","index":"gin(languages)"},
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
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"}
],
},
"control":{
"is_enable_autovacuum_optimize":1,
"is_enable_updated_at_set":1,
"is_enable_is_protected_delete_disable":1,
"is_enable_drop_schema":1,
"is_enable_drop_table":1,
"is_enable_truncate_table":1,
"is_enable_drop_column":1,
"is_enable_drop_column_mismatch":1,
"is_enable_log_users_password":1,
"is_enable_log_users_delete":1,
"is_enable_root_user_create":1,
"is_enable_root_user_delete_disable":1,
"is_enable_users_role_delete_disable_hard":1,
"is_enable_users_role_delete_disable_soft":0,
"table_row_delete_disable_all":[],
"table_row_delete_disable_bulk":[],
},
"sql":{
},
}

# override
def func_config_override_from_env(*, global_dict: dict) -> None:
    import orjson, os, ast, contextlib; from dotenv import load_dotenv
    load_dotenv(".env")
    for k, v in list(global_dict.items()):
        if k.startswith("config_") and (ev := os.getenv(k)) is not None:
            if isinstance(v, bool): global_dict[k] = 1 if ev.lower() in ("true", "1", "yes", "on", "ok") else 0
            elif isinstance(v, (list, tuple, dict)):
                with contextlib.suppress(Exception): global_dict[k] = orjson.loads(ev)
            else: global_dict[k] = int(ev) if ev.lstrip("-").isdigit() else ev
            if isinstance(global_dict[k], list): global_dict[k] = tuple(global_dict[k])
    with contextlib.suppress(Exception):
        for n in ast.parse(open("config.py", encoding="utf-8").read()).body:
            if isinstance(n, ast.Assign) and len(n.targets)==1 and (t:=getattr(n.targets[0], "id", "")).startswith("config_") and (v:=getattr(n.value, "id", "")).startswith("config_") and os.getenv(t) is None: global_dict[t] = global_dict.get(v)
    return None
func_config_override_from_env(global_dict=globals())
