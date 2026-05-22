#env
config_postgres_url = None
config_postgres_url_read = None
config_redis_url = None
config_azure_account_name = None
config_azure_account_key = None
config_google_login_client_id = None
config_fast2sms_url = None
config_fast2sms_key = None
config_resend_url = None
config_resend_key = None
config_posthog_project_host = None
config_posthog_project_key = None
config_mongodb_url = None
config_mssql_url = None
config_openai_key = None
config_gemini_key = None
config_sentry_dsn = None
config_aws_access_key_id = None
config_aws_secret_access_key = None
config_s3_region_name = None
config_sns_region_name = None
config_ses_region_name = None
config_sftp_host = None
config_sftp_port = None
config_sftp_username = None
config_sftp_password = None
config_kafka_url = None
config_kafka_username = None
config_kafka_password = None
config_rabbitmq_url = None
config_celery_url = None
config_redis_queue_url = None

#default
config_index_html_path = "core/api.html"
config_router_path = "core/router"
config_config_path = "core/config.py"
config_function_path = "core/function.py"
config_root_user_password = "123456"
config_token_secret_key = "atom-development-token-secret-key-32b"
config_email_sender_default = "atom@atom.com"
config_auth_type = [1]
config_expiry_sec_otp = 600
config_otp_length = 6
config_query_limit_default = 100
config_relation_fetch_limit_max = 100
config_buffer_limit = 100
config_obj_list_limit = 1000
config_buffer_flush_interval_sec = 60
config_redis_cache_ttl_sec = 3600
config_token_expiry_sec = 10*365*24*60*60
config_token_refresh_expiry_sec = 100*365*24*60*60
config_token_key = ["id", "type", "role", "deactivated_at", "deleted_at", "id_ext"]
config_blob_container_default = "atom"
config_blob_limit_kb = 100
config_blob_upload_limit_count = 10
config_blob_expire_sec = 60
config_postgres_min_connection = 5
config_postgres_max_connection = 20
config_cors_origin = ["*"]
config_cors_method = ["*"]
config_cors_headers = ["*"]
config_cors_expose_headers = ["Content-Disposition", "x-cache"]
config_is_enable_cors_credentials = 1
config_is_enable_signup = 1
config_is_enable_log_api = 1
config_is_enable_traceback = 0
config_is_enable_reset_tmp = 0
config_is_enable_index_html = 0
config_is_enable_otp_users_update_admin = 0
config_is_enable_postgres_init_startup = 1
config_is_enable_postgres_sql_runner_write = 1
config_is_enable_background_workers = 1
config_is_enable_user_delete = 1
config_kafka_group_id = "group_1"
config_kafka_is_enable_auto_commit = 1
config_kafka_batch_limit = 100
config_kafka_batch_timeout_ms = 1000
config_consumer_concurrency = 10
config_queue = ["redis", "rabbitmq", "kafka", "celery"]
config_table_create_disable_my = ["users", "log_api", "log_users_password", "otp","spatial_ref_sys"]
config_table_create_enable_public = ["test", "support"]
config_table_read_enable_public = ["*"]
config_admin_only_fields = ["deactivated_at", "verified_at", "role", "created_at", "updated_at", "created_by_id"]
config_column_enable_single_update = ["username", "password", "email", "mobile", "deleted_at"]
config_api_namespace = ["/", "/auth/", "/my/", "/public/", "/private/", "/admin/"]
config_api_namespace_auth = ["/my/", "/private/", "/admin/"]
config_api_namespace_user = ["/my/"]
config_allowed_user_storage_backends = ["token", "realtime", "redis", "inmemory"]
config_allowed_api_storage_backends = ["redis", "inmemory"]

#dict
config_sql = {
"users_role": "select id,role from users where role is not null order by id asc limit 1000",
"users_deactivated": "select id, deactivated_at from users order by id asc limit 1000",
"users_deleted": "select id, deleted_at from users order by id asc limit 1000",
"profile_metadata": {"test_count": "select count(*) from test where created_by_id=$1", "test_object": "select * from test where created_by_id=$1 limit 1"},
}

config_table = {
"test": {"buffer": 10},
"log_api": {"retention_day": 30, "buffer": 10},
"log_users_password": {"retention_day": 90},
"otp": {"retention_day": 30},
}

config_regex = {
"username": ["^(?=.{3,20}$)[a-z0-9]([a-z0-9_@-]*[a-z0-9])?$", "Username must be 3-20 characters, start and end with a letter or number, and contain only lowercase letters, numbers, _, @, or -"],
"password": ["^\\S{6,30}$", "Password must be 6-30 characters and contain no spaces"],
}

config_api = {
"/admin/sync": {"id": 1, "user_role_check": ["realtime", [1]]},
"/admin/object-create": {"id": 2, "user_role_check": ["token", [1]]},
"/admin/object-update": {"id": 3, "user_role_check": ["token", [1]]},
"/admin/object-read": {"id": 4, "user_role_check": ["token", [1]]},
"/admin/object-delete": {"id": 5, "user_role_check": ["realtime", [1]], "user_active_check": ["realtime"], "user_deleted_check": ["realtime"]},
"/admin/postgres-sql-runner": {"id": 6, "user_role_check": ["realtime", [1]]},
"/admin/postgres-export": {"id": 7, "user_role_check": ["inmemory", [1]]},
"/admin/postgres-import": {"id": 8, "user_role_check": ["realtime", [1]]},
"/admin/redis-import": {"id": 9, "user_role_check": ["token", [1]]},
"/admin/blob-container-read": {"id": 10, "user_role_check": ["inmemory", [1]]},
"/admin/mongodb-import": {"id": 11, "user_role_check": ["token", [1]]},
"/admin/blob-container-ops": {"id": 12, "user_role_check": ["token", [1]]},
"/admin/blob-url-delete": {"id": 13, "user_role_check": ["token", [1]]},
"/admin/mssql-sql-runner": {"id": 21, "user_role_check": ["realtime", [1]]},
"/public/object-read": {"id": 14, "api_cache_sec": ["inmemory", 100]},
"/info": {"id": 17, "api_cache_sec": ["inmemory", 100]},
"/public/table-groupby": {"id": 18, "api_cache_sec": ["inmemory", 10]},
"/public/jira-worklog-export": {"id": 19, "api_ratelimiting_times_sec": ["inmemory", 10, 60]},
}

config_column_int_mapping = {
"gender": {1: "Male", 2: "Female", 3: "Other", 4: "Prefer not to say"},
"employment_type": {1: "Full-time", 2: "Part-time", 3: "Contract", 4: "Internship", 5: "Freelance"},
"response_type": {1: "Direct", 2: "Cache Hit", 3: "Background Accepted", 4: "Direct Cache Store", 5: "Middleware Error"},
"method": {
"log_api": {1: "GET", 2: "POST", 3: "PUT", 4: "PATCH", 5: "DELETE", 6: "OPTIONS", 7: "HEAD"},
},
"role": {
"users": {1: "Admin", 2: "Manager", 3: "User"},
},
"type": {
"test": {1: "Type 1", 2: "Type 2", 3: "Type 3", 4: "Type 4", 5: "Type 5"},
"users": {1: "Default", 2: "Internal", 3: "External"},
"post": {1: "Article", 2: "News", 3: "Announcement"},
},
"status": {
"test": {1: "Active", 2: "Inactive", 3: "Archived"},
"support": {1: "Open", 2: "In Progress", 3: "Resolved", 4: "Closed"},
"log_users_delete": {1: "Pending", 2: "Processing", 3: "Completed", 4: "Failed"},
"job": {1: "Draft", 2: "Approval Pending", 3: "Approved", 4: "Rejected", 5: "Published", 6: "On Hold", 7: "Closed", 8: "Cancelled", 9: "Archived"},
"candidate": {1: "Applied", 2: "Shortlisted", 3: "Interviewing", 4: "Under Review", 5: "Selected", 6: "Offer Approved", 7: "Offer Sent", 8: "Offer Accepted", 9: "Offer Declined", 10: "Joined", 11: "Rejected", 12: "Withdrawn", 13: "On Hold"},
"interview": {1: "Scheduled", 2: "Rescheduled", 3: "In Progress", 4: "Completed", 5: "Feedback Pending", 6: "Feedback Submitted", 7: "No Show - Candidate", 8: "No Show - Interviewer", 9: "Cancelled", 10: "On Hold"},
},
"event": {
"log_users_delete": {1: "User Soft Deleted", 2: "User Restored", 3: "User Hard Deleted"},
},
}

config_postgres = {
"extension": ["postgis", "pg_trgm", "btree_gin",],
"table":{
"test":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"scheduled_at","datatype":"timestamptz"},
{"name":"is_featured","datatype":"boolean","default":False},
{"name":"views","datatype":"integer","default":0},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"is_protected","datatype":"boolean"},
{"name":"type","datatype":"smallint","index":"btree(type)"},
{"name":"title","datatype":"text","is_mandatory":1,"index":"gin(title)"},
{"name":"code","datatype":"text","is_mandatory":0,"unique":"code,type|code,slug"},
{"name":"slug","datatype":"text","index":"btree(slug)"},
{"name":"email","datatype":"text","regex":"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$","index":"btree(email)"},
{"name":"mobile","datatype":"text","index":"btree(mobile)"},
{"name":"category","datatype":"text","unique":"category"},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin(tag)"},
{"name":"tag_int","datatype":"integer[]","index":"gin(tag_int)"},
{"name":"tag_bigint","datatype":"bigint[]","index":"gin(tag_bigint)"},
{"name":"rating","datatype":"numeric(3,1)","check":"rating >= 0 AND rating <= 5"},
{"name":"price","datatype":"numeric(10,2)","check":"price > 0"},
{"name":"Price (USD)","datatype":"numeric(10,2)"},
{"name":"coordinate","datatype":"geography(Point, 4326)","index":"gist(coordinate)"},
{"name":"place","datatype":"text"},
{"name":"date_of_birth","datatype":"date"},
{"name":"description","datatype":"text","index":"gin(description)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status,type)"},
{"name":"address","datatype":"text","old":"adress"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
],
"users":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"is_protected","datatype":"boolean"},
{"name":"type","datatype":"smallint","is_mandatory":1,"index":"btree(type)"},
{"name":"username","datatype":"text","unique":"username,type"},
{"name":"password","datatype":"text","index":"btree(password)"},
{"name":"google_login_id","datatype":"text","unique":"google_login_id,type"},
{"name":"google_login_metadata","datatype":"jsonb"},
{"name":"email","datatype":"text","unique":"email,type"},
{"name":"mobile","datatype":"text","unique":"mobile,type"},
{"name":"role","datatype":"smallint"},
{"name":"last_active_at","datatype":"timestamptz"},
{"name":"name","datatype":"text"},
{"name":"country","datatype":"text"},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_secondary","datatype":"text","old":"email_communication"},
{"name":"mobile_secondary","datatype":"text","old":"mobile_communication"},
{"name":"address","datatype":"text"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text"},
{"name":"date_of_birth","datatype":"date"},
{"name":"gender","datatype":"smallint"},
{"name":"id_ext","datatype":"text"},
],
"log_api":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id,created_at)"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"ip_address","datatype":"text"},
{"name":"response_type","datatype":"smallint","in":(1,2,3,4,5),"index":"btree(response_type,created_at)"},
{"name":"method","datatype":"smallint","index":"btree(method,created_at)"},
{"name":"path","datatype":"text","index":"btree(path,created_at)"},
{"name":"query_param","datatype":"text"},
{"name":"status_code","datatype":"smallint","index":"btree(status_code)"},
{"name":"response_time_ms","datatype":"integer"},
{"name":"error","datatype":"text"}
],
"log_users_password":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"log_users_delete":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id,created_at)"},
{"name":"event","datatype":"smallint","is_mandatory":1,"in":(1,2,3),"index":"btree(event,created_at)"},
{"name":"status","datatype":"smallint","default":1,"is_mandatory":1,"in":(1,2,3,4),"index":"btree(status,next_retry_at,created_at)"},
{"name":"retry_count","datatype":"integer","default":0},
{"name":"next_retry_at","datatype":"timestamptz","default":"now()"},
{"name":"processed_at","datatype":"timestamptz"},
{"name":"last_error","datatype":"text"}
],
"otp":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"otp","datatype":"integer","is_mandatory":1},
{"name":"email","datatype":"text","index":"btree(email)"},
{"name":"mobile","datatype":"text","index":"btree(mobile)"},
],
"message":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"read_at","datatype":"timestamptz"}
],
"report_test":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"unique":"created_by_id,test_id"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text"}
],
"comment_test":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
],
"rating_test":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"rating","datatype":"numeric(3,1)","is_mandatory":1},
{"name":"description","datatype":"text"}
],
"support":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"},
{"name":"email","datatype":"text"},
{"name":"mobile","datatype":"text"},
],
"post":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"type","datatype":"smallint","index":"btree(type)"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin(tag)"},
],
"job":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"is_protected","datatype":"boolean"},
{"name":"country","datatype":"text","is_mandatory":0,"index":"btree(country)|gin(country)"},
{"name":"department","datatype":"text","is_mandatory":0,"index":"btree(department)|gin(department)"},
{"name":"profile","datatype":"text","index":"btree(profile)|gin(profile)"},
{"name":"quantity","datatype":"bigint","is_mandatory":0},
{"name":"description","datatype":"text","index":"gin(description)"},
{"name":"salary","datatype":"text"},
{"name":"experience","datatype":"text"},
{"name":"location","datatype":"text","index":"btree(location)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"},
{"name":"employment_type","datatype":"smallint","index":"btree(employment_type)"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
],
"candidate":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"is_protected","datatype":"boolean"},
{"name":"job_id","datatype":"bigint","is_mandatory":1,"index":"btree(job_id)"},
{"name":"name","datatype":"text","index":"btree(name)|gin(name)"},
{"name":"email","datatype":"text","index":"btree(email)"},
{"name":"mobile","datatype":"text","index":"btree(mobile)"},
{"name":"experience","datatype":"text"},
{"name":"college","datatype":"text"},
{"name":"resume_url","datatype":"text"},
{"name":"skills","datatype":"text","index":"gin(skills)"},
{"name":"total_exp","datatype":"numeric(4,1)","index":"btree(total_exp)"},
{"name":"current_company","datatype":"text"},
{"name":"current_ctc","datatype":"numeric(12,2)"},
{"name":"expected_ctc","datatype":"numeric(12,2)"},
{"name":"notice_period","datatype":"integer"},
{"name":"location","datatype":"text","index":"btree(location)"},
{"name":"preferred_location","datatype":"text[]"},
{"name":"highest_qualification","datatype":"text"},
{"name":"source","datatype":"text","index":"btree(source)"},
{"name":"linkedin_url","datatype":"text"},
{"name":"gender","datatype":"smallint"},
{"name":"date_of_birth","datatype":"date"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"},
{"name":"employment_type","datatype":"smallint","index":"btree(employment_type)"},
{"name":"remark","datatype":"text"},
{"name":"ai_rating","datatype":"numeric(3,1)"},
{"name":"ai_remark","datatype":"text"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
],
"interview":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"is_protected","datatype":"boolean"},
{"name":"candidate_id","datatype":"bigint","is_mandatory":1,"index":"btree(candidate_id)"},
{"name":"title","datatype":"text","is_mandatory":1,"index":"btree(title)|gin(title)"},
{"name":"description","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"scheduled_at","datatype":"timestamptz","index":"btree(scheduled_at)"},
{"name":"panel","datatype":"text"},
{"name":"feedback","datatype":"text"},
{"name":"remark","datatype":"text"},
{"name":"rating","datatype":"numeric(3,1)","check":"rating >= 1 AND rating <= 10"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
]
},
"control":{
"is_enable_extension":1,
"is_enable_drop_schema":1,
"is_enable_drop_table":1,
"is_enable_truncate":1,
"is_enable_drop_column":1,
"is_enable_drop_column_mismatch":1,
"is_enable_delete_disable_is_protected":1,
"is_enable_updated_at_set":1,
"is_enable_users_password_log":1,
"is_enable_users_root_upsert":1,
"is_enable_delete_disable_users_root":1,
"is_enable_delete_disable_users_role":1,
"is_enable_delete_disable_users_role_soft":1,
"is_enable_autovacuum_optimize":1,
"table_delete_disable_row":[],
"table_delete_disable_row_bulk":[],
},
"sql":{
"index": {
"idx_users_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_users_deactivated_at_not_null ON users (id) WHERE deactivated_at IS NOT NULL",
"idx_users_deactivated_at_null_email_unique": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_deactivated_at_null_email_unique ON users (email) WHERE deactivated_at IS NULL",
"idx_users_deactivated_at_null_username_unique": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_deactivated_at_null_username_unique ON users (username) WHERE deactivated_at IS NULL",
"idx_test_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_test_verified_at_null ON test (id) WHERE verified_at IS NULL",
"idx_test_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_test_deleted_at_not_null ON test (id) WHERE deleted_at IS NOT NULL",
"idx_test_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_test_is_protected_1 ON test (id) WHERE is_protected IS TRUE",
"idx_users_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_users_verified_at_null ON users (id) WHERE verified_at IS NULL",
"idx_users_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_users_deleted_at_not_null ON users (id) WHERE deleted_at IS NOT NULL",
"idx_users_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_users_is_protected_1 ON users (id) WHERE is_protected IS TRUE",
"idx_log_api_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_log_api_deleted_at_not_null ON log_api (id) WHERE deleted_at IS NOT NULL",
"idx_log_users_password_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_log_users_password_deleted_at_not_null ON log_users_password (id) WHERE deleted_at IS NOT NULL",
"idx_message_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_message_deleted_at_not_null ON message (id) WHERE deleted_at IS NOT NULL",
"idx_message_read_at_null": "CREATE INDEX IF NOT EXISTS idx_message_read_at_null ON message (user_id) WHERE read_at IS NULL",
"idx_support_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_support_deleted_at_not_null ON support (id) WHERE deleted_at IS NOT NULL",
"idx_post_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_post_deactivated_at_not_null ON post (id) WHERE deactivated_at IS NOT NULL",
"idx_post_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_post_verified_at_null ON post (id) WHERE verified_at IS NULL",
"idx_post_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_post_deleted_at_not_null ON post (id) WHERE deleted_at IS NOT NULL",
"idx_job_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_job_deactivated_at_not_null ON job (id) WHERE deactivated_at IS NOT NULL",
"idx_job_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_job_verified_at_null ON job (id) WHERE verified_at IS NULL",
"idx_job_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_job_deleted_at_not_null ON job (id) WHERE deleted_at IS NOT NULL",
"idx_job_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_job_is_protected_1 ON job (id) WHERE is_protected IS TRUE",
"idx_candidate_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_candidate_deactivated_at_not_null ON candidate (id) WHERE deactivated_at IS NOT NULL",
"idx_candidate_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_candidate_verified_at_null ON candidate (id) WHERE verified_at IS NULL",
"idx_candidate_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_candidate_deleted_at_not_null ON candidate (id) WHERE deleted_at IS NOT NULL",
"idx_candidate_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_candidate_is_protected_1 ON candidate (id) WHERE is_protected IS TRUE",
"idx_interview_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_interview_deactivated_at_not_null ON interview (id) WHERE deactivated_at IS NOT NULL",
"idx_interview_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_interview_verified_at_null ON interview (id) WHERE verified_at IS NULL",
"idx_interview_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_interview_deleted_at_not_null ON interview (id) WHERE deleted_at IS NOT NULL",
"idx_interview_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_interview_is_protected_1 ON interview (id) WHERE is_protected IS TRUE",
"idx_test_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_test_deactivated_at_not_null ON test (id) WHERE deactivated_at IS NOT NULL",
"idx_report_test_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_report_test_deleted_at_not_null ON report_test (id) WHERE deleted_at IS NOT NULL",
"idx_comment_test_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_comment_test_deleted_at_not_null ON comment_test (id) WHERE deleted_at IS NOT NULL",
"idx_rating_test_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_rating_test_deleted_at_not_null ON rating_test (id) WHERE deleted_at IS NOT NULL",
"idx_log_users_delete_worker": "CREATE INDEX IF NOT EXISTS idx_log_users_delete_worker ON log_users_delete (next_retry_at, created_at, id) WHERE status IN (1,4)"
}
},
}

#override
from .function import func_config_override_from_env
func_config_override_from_env(global_dict=globals())
