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
config_token_key = ["id", "type", "role", "is_active", "is_deleted", "id_ext"]
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
config_kafka_group_id = "group_1"
config_kafka_is_enable_auto_commit = 1
config_kafka_batch_limit = 100
config_kafka_batch_timeout_ms = 1000
config_consumer_concurrency = 10
config_queue = ["redis", "rabbitmq", "kafka", "celery"]
config_table_create_disable_my = ["users", "log_api", "log_users_password", "otp","spatial_ref_sys"]
config_table_create_enable_public = ["test", "support"]
config_table_read_enable_public = ["*"]
config_admin_only_fields = ["is_active", "is_verified", "role", "created_at", "updated_at", "created_by_id"]
config_column_enable_single_update = ["username", "password", "email", "mobile", "is_deleted"]
config_api_namespace = ["/", "/auth/", "/my/", "/public/", "/private/", "/admin/"]
config_api_namespace_auth = ["/my/", "/private/", "/admin/"]
config_api_namespace_user = ["/my/"]
config_mode_user = ["token", "realtime", "redis", "inmemory"]
config_mode_api = ["redis", "inmemory"]

#dict
config_func_check = {
"is_check_config_api_duplicate_id": 1,
"is_check_config_api_user_role_invalid_mode": 1,
"is_check_config_api_user_is_active_invalid_mode": 1,
"is_check_config_api_api_ratelimiting_invalid_mode": 1,
"is_check_config_api_api_cache_invalid_mode": 1,
"is_check_config_api_unused_route": 1,
"is_check_route_admin_rules_missing_config": 1,
"is_check_route_admin_rules_missing_role_check": 1,
"is_check_route_admin_rules_allow_role_1": 1,
"is_check_route_namespace_invalid": 1,
"is_check_route_endpoint_name_invalid": 1,
"is_check_config_naming_assign_invalid": 1,
"is_check_config_naming_ann_assign_invalid": 1,
"is_check_function_naming_invalid": 1,
"is_check_router_declaration_missing": 1,
"is_check_config_postgres_table_name_empty": 1,
"is_check_config_postgres_column_duplicate": 1,
"is_check_config_postgres_column_name_empty": 1,
"is_check_config_postgres_column_datatype_empty": 1,
"is_check_config_postgres_column_datatype_mismatch": 1,
"is_check_config_postgres_unique_constraint_invalid": 1,
"is_check_config_postgres_index_constraint_invalid": 1,
"is_check_config_postgres_index_duplicate": 1,
"is_check_config_postgres_index_redundant": 1,
}
config_sql = {
"users_role": "select id,role from users where role is not null order by id asc limit 1000",
"users_is_active": "select id,is_active from users order by id asc limit 1000",
"users_is_deleted": "select id,is_deleted from users order by id asc limit 1000",
"profile_metadata": {"test_count": "select count(*) from test where created_by_id=$1", "test_object": "select * from test where created_by_id=$1 limit 1"},
}
config_table = {
"test": {"buffer": 10},
"log_api": {"retention_day": 30, "buffer": 10},
"log_users_password": {"retention_day": 90},
"otp": {"retention_day": 365},
}
config_regex = {
"username": ["^(?=.{3,20}$)[a-z0-9]([a-z0-9_@-]*[a-z0-9])?$", "Username must be 3-20 characters, start and end with a letter or number, and contain only lowercase letters, numbers, _, @, or -"],
"password": ["^\\S{6,30}$", "Password must be 6-30 characters and contain no spaces"],
}
config_column_int_mapping = {
"is_active": {0: "Inactive", 1: "Active"},
"is_verified": {0: "Pending", 1: "Verified"},
"is_deleted": {0: "Not Deleted", 1: "Deleted"},
"is_protected": {0: "Not Protected", 1: "Protected"},
"is_read": {0: "Unread", 1: "Read"},
"response_type": {1: "Direct", 2: "Cache Hit", 3: "Background Accepted", 4: "Direct Cache Store", 5: "Middleware Error"},
"support_status": {1: "Open", 2: "In Progress", 3: "Resolved", 4: "Closed"},
"job_status": {1: "Draft", 2: "Approval Pending", 3: "Approved", 4: "Rejected", 5: "Published", 6: "On Hold", 7: "Closed", 8: "Cancelled", 9: "Archived"},
"candidate_status": {1: "Applied", 2: "Shortlisted", 3: "Interviewing", 4: "Under Review", 5: "Selected", 6: "Offer Approved", 7: "Offer Sent", 8: "Offer Accepted", 9: "Offer Declined", 10: "Joined", 11: "Rejected", 12: "Withdrawn", 13: "On Hold"},
"interview_status": {1: "Scheduled", 2: "Rescheduled", 3: "In Progress", 4: "Completed", 5: "Feedback Pending", 6: "Feedback Submitted", 7: "No Show - Candidate", 8: "No Show - Interviewer", 9: "Cancelled", 10: "On Hold"},
"gender": {1: "Male", 2: "Female", 3: "Other", 4: "Prefer not to say"},
"employment_type": {1: "Full-time", 2: "Part-time", 3: "Contract", 4: "Internship", 5: "Freelance"},
}
config_api = {
"/admin/sync": {"id": 1, "user_role_check": ["realtime", [1]]},
"/admin/object-create": {"id": 2, "user_role_check": ["token", [1]]},
"/admin/object-update": {"id": 3, "user_role_check": ["token", [1]]},
"/admin/object-read": {"id": 4, "user_role_check": ["token", [1]]},
"/admin/ids-delete": {"id": 5, "user_role_check": ["realtime", [1]], "user_is_active_check": ["realtime", 1], "user_is_deleted_check": ["realtime", 1]},
"/admin/postgres-sql-runner": {"id": 6, "user_role_check": ["realtime", [1]]},
"/admin/postgres-export": {"id": 7, "user_role_check": ["inmemory", [1]]},
"/admin/postgres-import": {"id": 8, "user_role_check": ["realtime", [1]]},
"/admin/redis-import": {"id": 9, "user_role_check": ["token", [1]]},
"/admin/blob-container-read": {"id": 10, "user_role_check": ["inmemory", [1]]},
"/admin/mongodb-import": {"id": 11, "user_role_check": ["token", [1]]},
"/admin/blob-container-ops": {"id": 12, "user_role_check": ["token", [1]]},
"/admin/blob-url-delete": {"id": 13, "user_role_check": ["token", [1]]},
"/admin/postgres-clean": {"id": 20, "user_role_check": ["realtime", [1]]},
"/admin/mssql-sql-runner": {"id": 21, "user_role_check": ["realtime", [1]]},
"/public/object-read": {"id": 14, "api_cache_sec": ["inmemory", 100]},
"/info": {"id": 17, "api_cache_sec": ["inmemory", 100]},
"/public/table-groupby": {"id": 18, "api_cache_sec": ["inmemory", 10]},
"/public/jira-worklog-export": {"id": 19, "api_ratelimiting_times_sec": ["inmemory", 10, 60]},
}
config_postgres = {
"extension": ["postgis", "pg_trgm", "btree_gin",],
"table":{
"test":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"scheduled_at","datatype":"timestamptz"},
{"name":"is_featured","datatype":"boolean","default":False},
{"name":"views","datatype":"integer","default":0},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"smallint","default":1,"in":(0,1)},
{"name":"is_verified","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_protected","datatype":"smallint","default":0,"in":(0,1)},
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
{"name":"dob","datatype":"date"},
{"name":"description","datatype":"text","index":"gin(description)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status,type)"},
{"name":"address","datatype":"text","old":"adress"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
],
"users":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"smallint","default":1,"in":(0,1)},
{"name":"is_verified","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"is_protected","datatype":"smallint","default":0,"in":(0,1)},
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
{"name":"email_communication","datatype":"text"},
{"name":"mobile_communication","datatype":"text"},
{"name":"address","datatype":"text"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text"},
{"name":"dob","datatype":"date"},
{"name":"gender","datatype":"smallint"},
{"name":"id_ext","datatype":"text"},
],
"log_api":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id,created_at)"},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"response_type","datatype":"smallint","in":(1,2,3,4,5),"index":"btree(response_type,created_at)"},
{"name":"ip_address","datatype":"text"},
{"name":"path","datatype":"text","index":"btree(path,created_at)"},
{"name":"method","datatype":"text"},
{"name":"query_param","datatype":"text"},
{"name":"status_code","datatype":"smallint","index":"btree(status_code)"},
{"name":"response_time_ms","datatype":"integer"},
{"name":"error","datatype":"text"}
],
"otp":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"otp","datatype":"integer","is_mandatory":1},
{"name":"email","datatype":"text","index":"btree(email)"},
{"name":"mobile","datatype":"text","index":"btree(mobile)"},
],
"log_users_password":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"message":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"is_read","datatype":"smallint","default":0}
],
"report_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"unique":"created_by_id,test_id"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text"}
],
"comment_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
],
"rating_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"rating","datatype":"numeric(3,1)","is_mandatory":1},
{"name":"description","datatype":"text"}
],
"support":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"},
{"name":"email","datatype":"text"},
{"name":"mobile","datatype":"text"},
],
"post":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"smallint","default":1,"in":(0,1)},
{"name":"is_verified","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"type","datatype":"smallint","index":"btree(type)"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin(tag)"},
],
"job":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"smallint","default":1,"in":(0,1)},
{"name":"is_verified","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_protected","datatype":"smallint","default":0,"in":(0,1)},
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
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"smallint","default":1,"in":(0,1)},
{"name":"is_verified","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_protected","datatype":"smallint","default":0,"in":(0,1)},
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
{"name":"dob","datatype":"date"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"},
{"name":"employment_type","datatype":"smallint","index":"btree(employment_type)"},
{"name":"remark","datatype":"text"},
{"name":"ai_rating","datatype":"numeric(3,1)"},
{"name":"ai_remark","datatype":"text"},
{"name":"metadata","datatype":"jsonb","index":"gin(metadata)"}
],
"interview":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"smallint","default":1,"in":(0,1)},
{"name":"is_verified","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_deleted","datatype":"smallint","default":0,"in":(0,1)},
{"name":"is_protected","datatype":"smallint","default":0,"in":(0,1)},
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
"is_enable_drop_schema_disable":0,
"is_enable_drop_table_disable":0,
"is_enable_truncate_disable":0,
"is_enable_drop_column_disable":0,
"is_enable_drop_column_mismatch":1,
"is_enable_users_delete_role_disable":1,
"is_enable_users_protect_root":1,
"is_enable_users_root_upsert":1,
"is_enable_users_password_log":1,
"is_enable_delete_disable_is_protected":1,
"is_enable_updated_at_set":1,
"is_enable_users_set_deleted_at":1,
"is_enable_autovacuum_optimize":1,
"table_delete_disable_row":["users"],
"table_delete_disable_row_bulk":[["users",1]],
},
"sql":{
"index": {
"idx_users_is_active_0": "CREATE INDEX IF NOT EXISTS idx_users_is_active_0 ON users (id) WHERE is_active = 0",
"idx_users_is_active_1_email_unique": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_is_active_1_email_unique ON users (email) WHERE is_active = 1",
"idx_users_is_active_1_username_unique": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_is_active_1_username_unique ON users (username) WHERE is_active = 1",
"idx_test_is_verified_0": "CREATE INDEX IF NOT EXISTS idx_test_is_verified_0 ON test (id) WHERE is_verified = 0",
"idx_test_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_test_is_deleted_1 ON test (id) WHERE is_deleted = 1",
"idx_test_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_test_is_protected_1 ON test (id) WHERE is_protected = 1",
"idx_users_is_verified_0": "CREATE INDEX IF NOT EXISTS idx_users_is_verified_0 ON users (id) WHERE is_verified = 0",
"idx_users_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_users_is_deleted_1 ON users (id) WHERE is_deleted = 1",
"idx_users_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_users_is_protected_1 ON users (id) WHERE is_protected = 1",
"idx_log_api_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_log_api_is_deleted_1 ON log_api (id) WHERE is_deleted = 1",
"idx_log_users_password_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_log_users_password_is_deleted_1 ON log_users_password (id) WHERE is_deleted = 1",
"idx_message_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_message_is_deleted_1 ON message (id) WHERE is_deleted = 1",
"idx_message_is_read_0": "CREATE INDEX IF NOT EXISTS idx_message_is_read_0 ON message (user_id) WHERE is_read = 0",
"idx_support_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_support_is_deleted_1 ON support (id) WHERE is_deleted = 1",
"idx_post_is_active_0": "CREATE INDEX IF NOT EXISTS idx_post_is_active_0 ON post (id) WHERE is_active = 0",
"idx_post_is_verified_0": "CREATE INDEX IF NOT EXISTS idx_post_is_verified_0 ON post (id) WHERE is_verified = 0",
"idx_post_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_post_is_deleted_1 ON post (id) WHERE is_deleted = 1",
"idx_job_is_active_0": "CREATE INDEX IF NOT EXISTS idx_job_is_active_0 ON job (id) WHERE is_active = 0",
"idx_job_is_verified_0": "CREATE INDEX IF NOT EXISTS idx_job_is_verified_0 ON job (id) WHERE is_verified = 0",
"idx_job_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_job_is_deleted_1 ON job (id) WHERE is_deleted = 1",
"idx_job_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_job_is_protected_1 ON job (id) WHERE is_protected = 1",
"idx_candidate_is_active_0": "CREATE INDEX IF NOT EXISTS idx_candidate_is_active_0 ON candidate (id) WHERE is_active = 0",
"idx_candidate_is_verified_0": "CREATE INDEX IF NOT EXISTS idx_candidate_is_verified_0 ON candidate (id) WHERE is_verified = 0",
"idx_candidate_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_candidate_is_deleted_1 ON candidate (id) WHERE is_deleted = 1",
"idx_candidate_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_candidate_is_protected_1 ON candidate (id) WHERE is_protected = 1",
"idx_interview_is_active_0": "CREATE INDEX IF NOT EXISTS idx_interview_is_active_0 ON interview (id) WHERE is_active = 0",
"idx_interview_is_verified_0": "CREATE INDEX IF NOT EXISTS idx_interview_is_verified_0 ON interview (id) WHERE is_verified = 0",
"idx_interview_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_interview_is_deleted_1 ON interview (id) WHERE is_deleted = 1",
"idx_interview_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_interview_is_protected_1 ON interview (id) WHERE is_protected = 1",
"idx_test_is_active_0": "CREATE INDEX IF NOT EXISTS idx_test_is_active_0 ON test (id) WHERE is_active = 0",
"idx_report_test_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_report_test_is_deleted_1 ON report_test (id) WHERE is_deleted = 1",
"idx_comment_test_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_comment_test_is_deleted_1 ON comment_test (id) WHERE is_deleted = 1",
"idx_rating_test_is_deleted_1": "CREATE INDEX IF NOT EXISTS idx_rating_test_is_deleted_1 ON rating_test (id) WHERE is_deleted = 1"
}
},
}

#override
from .function import func_config_override_from_env
func_config_override_from_env(global_dict=globals())
