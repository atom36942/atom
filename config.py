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
config_token_secret_key = "mysecretkey-mysecretkey-mysecretkey"
config_root_html_path = "static/api.html"
config_is_enable_user_delete = 0
config_is_enable_postgres_schema_init = 1
config_is_enable_signup = 1
config_is_enable_otp_require_users_update = 0
config_is_notification = 0
config_otp_length = 6
config_otp_expiry_sec = 600
config_access_token_expires_in_sec = 3155695200 
config_refresh_token_expires_in_sec = 3155695200000
config_blob_limit_size_kb = 300
config_blob_limit_upload = 100
config_blob_expire_sec_upload = 3600
config_blob_expire_sec_preview = 360000
config_buffer_limit_default = 100
config_batch_item_limit = 1000
config_sql_read_limit_default = 100
config_sql_read_limit_max = 1000
config_sql_read_relation_fetch_limit_max = 100
config_allowed_auth_types = [1]
config_allowed_token_key = ["id", "type", "role", "username", "deactivated_at", "deleted_at"]
config_users_delete_data_retention_day = 30
config_users_delete_exclude_table = ["users", "spatial_ref_sys", "log_*"]
config_redis_cache_ttl_sec = 3600
config_table_disable_create_my = ["users", "log_api", "log_users_password", "otp","spatial_ref_sys"]
config_table_enable_create_public = ["test", "support"]
config_table_enable_read_public = ["*"]
config_table_enable_delete_all_my = ["*"]
config_table_enable_delete_all_my_user_id = ["message","notification"]
config_column_admin = ["created_at", "updated_at", "created_by_id", "role", "verified_at", "verified_by_id", "deleted_by_id", "deactivated_by_id", "archived_by_id"]
config_column_single_update = ["username", "password", "email", "mobile", "deleted_at"]
config_column_my_block = ["username"]

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

config_sensitive_table = ["users", "spatial_ref_sys"]

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
"/admin/cargowise-360": {"id": 32, "user_role_check": ["token", [1]], "api_cache_sec": ["redis", 300]},
"/public/object-read": {"id": 14, "api_cache_sec": ["inmemory", 100]},
"/info": {"id": 17, "api_cache_sec": ["inmemory", 100]},
"/public/table-groupby": {"id": 18, "api_cache_sec": ["inmemory", 10]},
"/public/jira-worklog-export": {"id": 19, "api_ratelimiting_times_sec": ["inmemory", 10, 60]},
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
