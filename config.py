# Integrations
config_postgres_url = None
config_postgres_url_read = None
config_redis_url = None
config_redis_url_queue = None
config_mongodb_url = None
config_mssql_url = None
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
config_is_enable_user_delete = 1
config_is_enable_sql_write = 1
config_is_enable_signup = 1
config_is_enable_otp_require_users_update = 0
config_is_notification = 0
config_is_enable_object_delete_all_my = 1
config_otp_length = 6
config_otp_expiry_sec = 600
config_token_expiry_sec = 10*365*24*60*60
config_token_refresh_expiry_sec = 100*365*24*60*60
config_blob_limit_size_kb = 300
config_blob_limit_upload = 100
config_blob_expire_sec_upload = 3600
config_blob_expire_sec_preview = 360000
config_sql_read_limit_default = 100
config_sql_read_limit_max = 1000
config_sql_read_relation_fetch_limit_max = 100
config_allowed_auth_types = [1]
config_allowed_token_key = ["id", "type", "role", "deactivated_at", "deleted_at", "id_ext"]
config_users_delete_data_retention_day = 30
config_users_delete_exclude_table = ["users", "spatial_ref_sys", "log_*"]
config_redis_cache_ttl_sec = 3600
config_buffer_limit_default = 100
config_api_batch_item_limit = 1000
config_table_create_disable_my = ["users", "log_api", "log_users_password", "otp","spatial_ref_sys"]
config_table_create_enable_public = ["test", "support"]
config_table_read_enable_public = ["*"]
config_admin_columns = ["created_at", "updated_at", "created_by_id", "role", "verified_at", "verified_by_id", "deleted_by_id", "deactivated_by_id", "archived_by_id"]
config_column_enable_single_update = ["username", "password", "email", "mobile", "deleted_at"]

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
"username": ["^(?=.{3,20}\\Z)[A-Za-z0-9]([A-Za-z0-9_@.-]*[A-Za-z0-9])?\\Z", "Username must be 3-20 characters, start and end with a letter or number, and contain only letters, numbers, _, @, ., or -"],
"password": ["^\\S{6,30}\\Z", "Password must be 6-30 characters and contain no spaces"],
}

config_api = {
"/admin/sync": {"id": 1, "user_role_check": ["realtime", [1]]},
"/admin/object-create": {"id": 2, "user_role_check": ["token", [1]]},
"/admin/object-update": {"id": 3, "user_role_check": ["token", [1]]},
"/admin/object-read": {"id": 4, "user_role_check": ["token", [1]]},
"/admin/object-delete": {"id": 5, "user_role_check": ["realtime", [1]], "user_deactivated_check": ["realtime"], "user_deleted_check": ["realtime"]},
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
"department": {
"job": {1: "Engineering", 2: "Human Resources", 3: "Sales", 4: "Marketing", 5: "Finance", 6: "Operations", 7: "IT", 8: "Legal", 9: "Customer Support", 10: "Product Management", 11: "Research & Development", 12: "Administration", 13: "Quality Assurance", 14: "Data & Analytics", 15: "Management", 16: "Design", 17: "Procurement"},
},
"response_type": {1: "Direct No Cache Set", 2: "Direct Cache Set", 3: "Cache Response", 4: "Background Added", 5: "Error"},
"method": {
"log_api": {1: "GET", 2: "POST", 3: "PUT", 4: "PATCH", 5: "DELETE", 6: "OPTIONS", 7: "HEAD"},
},
"role": {
"users": {1: "Admin", 2: "Manager", 3: "User"},
},
"type": {
"test": {1: "Type 1", 2: "Type 2", 3: "Type 3", 4: "Type 4", 5: "Type 5"},
"users": {1: "Default", 2: "Internal", 3: "External"},
"blob": {1: "Upload File", 2: "Upload URL"},
"post": {1: "Article", 2: "News", 3: "Announcement"},
"interview": {1: "HR", 2: "Technical", 3: "Managerial", 4: "Cultural", 5: "Assignment"},
"notification": {1: "Password Change", 2: "Job Status Change", 3: "Account Created"},
},
"status": {
"test": {1: "Active", 2: "Inactive", 3: "Archived"},
"support": {1: "Open", 2: "In Progress", 3: "Resolved", 4: "Closed"},
"job": {1: "Draft", 2: "Approval Pending", 3: "Approved", 4: "Rejected", 5: "Published", 6: "On Hold", 7: "Closed", 8: "Cancelled", 9: "Archived"},
"candidate": {1: "Applied", 2: "Shortlisted", 3: "Interviewing", 4: "Under Review", 5: "Selected", 6: "Offer Approved", 7: "Offer Sent", 8: "Offer Accepted", 9: "Offer Declined", 10: "Joined", 11: "Rejected", 12: "Withdrawn", 13: "On Hold", 14: "Salary Negotiation", 15: "Background Check", 16: "Documentation Pending"},
"interview": {1: "Scheduled", 2: "Rescheduled", 3: "In Progress", 4: "Completed", 5: "Feedback Pending", 6: "Feedback Submitted", 7: "No Show - Candidate", 8: "No Show - Interviewer", 9: "Cancelled", 10: "On Hold"},
},
"worker_status": {1: "Pending", 2: "Processing", 3: "Completed", 4: "Failed"},
"event": {
"log_users_delete": {1: "User Soft Deleted", 2: "User Restored", 3: "User Hard Deleted"},
},
}

config_postgres = {
"extension": ["postgis", "pg_trgm", "btree_gin"],
"table":{
"test":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"archived_at","datatype":"timestamptz"},
{"name":"archived_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
{"name":"is_protected","datatype":"boolean"},
{"name":"is_featured","datatype":"boolean","default":False},
{"name":"views","datatype":"integer","default":0},
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
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
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
{"name":"email_secondary","datatype":"text",},
{"name":"mobile_secondary","datatype":"text"},
{"name":"address","datatype":"text"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text"},
{"name":"date_of_birth","datatype":"date"},
{"name":"gender","datatype":"smallint"},
{"name":"id_ext","datatype":"text","unique":"id_ext,type"},
],
"post":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","index":"btree(type)"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin(tag)"},
],
"support":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"},
{"name":"email","datatype":"text"},
{"name":"mobile","datatype":"text"},
],
"message":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"read_at","datatype":"timestamptz"}
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
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory":1,"index":"btree(type,created_at)"},
{"name":"service","datatype":"text","is_mandatory":1},
{"name":"container","datatype":"text","is_mandatory":1},
{"name":"blob_key","datatype":"text","is_mandatory":1,"unique":"service,container,blob_key"},
{"name":"file_url","datatype":"text","is_mandatory":1}
],
"config":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"key","datatype":"text","is_mandatory":1,"unique":"key"},
{"name":"value","datatype":"jsonb","is_mandatory":1},
],
"job":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
{"name":"profile","datatype":"text","index":"btree(profile)|gin(profile)"},
{"name":"description","datatype":"text","index":"gin(description)"},
{"name":"country","datatype":"text","index":"btree(country)|gin(country)"},
{"name":"department","datatype":"smallint","index":"btree(department)"},
{"name":"quantity","datatype":"integer","is_mandatory":0},
{"name":"employment_type","datatype":"smallint","index":"btree(employment_type)"},
{"name":"is_remote","datatype":"boolean","default":False},
{"name":"salary_min","datatype":"integer","index":"btree(salary_min)"},
{"name":"salary_max","datatype":"integer","index":"btree(salary_max)"},
{"name":"experience_min","datatype":"numeric(4,1)","index":"btree(experience_min)"},
{"name":"experience_max","datatype":"numeric(4,1)","index":"btree(experience_max)"},
{"name":"currency","datatype":"text"},
{"name":"skills","datatype":"text[]","index":"gin(skills)"},
{"name":"closing_date","datatype":"date"},
{"name":"location","datatype":"text","index":"btree(location)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"}
],
"candidate":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
{"name":"job_id","datatype":"bigint","is_mandatory":1,"index":"btree(job_id)"},
{"name":"profile","datatype":"text","index":"btree(profile)|gin(profile)"},
{"name":"name","datatype":"text","index":"btree(name)|gin(name)"},
{"name":"email","datatype":"text","index":"btree(email)"},
{"name":"mobile","datatype":"text","index":"btree(mobile)"},
{"name":"college","datatype":"text"},
{"name":"resume_url","datatype":"text"},
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
{"name":"gender","datatype":"smallint"},
{"name":"date_of_birth","datatype":"date"},
{"name":"worker_status","datatype":"smallint","default":1,"index":"btree(worker_status)"},
{"name":"worker_retry_count","datatype":"integer","default":0},
{"name":"worker_next_retry_at","datatype":"timestamptz","default":"now()","index":"btree(worker_next_retry_at)"},
{"name":"worker_processed_at","datatype":"timestamptz"},
{"name":"worker_last_error","datatype":"text"},
{"name":"ai_remark","datatype":"text"},
{"name":"ai_rating","datatype":"numeric(3,1)"},
{"name":"remark","datatype":"text"},
{"name":"rating","datatype":"numeric(3,1)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"}
],
"interview":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
{"name":"candidate_id","datatype":"bigint","is_mandatory":1,"index":"btree(candidate_id)"},
{"name":"type","datatype":"smallint","index":"btree(type)"},
{"name":"title","datatype":"text","is_mandatory":1,"index":"btree(title)|gin(title)"},
{"name":"description","datatype":"text"},
{"name":"meeting_url","datatype":"text"},
{"name":"location","datatype":"text"},
{"name":"scheduled_at","datatype":"timestamptz","index":"btree(scheduled_at)"},
{"name":"duration_minutes","datatype":"integer"},
{"name":"panel","datatype":"text[]","index":"gin(panel)"},
{"name":"status","datatype":"smallint","default":1,"index":"btree(status)"}
],
"notification":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"type","datatype":"smallint","is_mandatory":1,"index":"btree(type)"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id)"},
{"name":"title","datatype":"text","is_mandatory":1},
{"name":"description","datatype":"text"},
{"name":"reference_table","datatype":"text"},
{"name":"reference_id","datatype":"bigint"},
{"name":"read_at","datatype":"timestamptz"}
],
"action_test_comment":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text","is_mandatory":1},
],
"action_test_report":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"unique":"created_by_id,test_id"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text"}
],
"action_test_feedback":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree(test_id)"},
{"name":"description","datatype":"text"},
{"name":"rating","datatype":"numeric(3,1)"}
],
"action_users_report":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"unique":"created_by_id,user_id"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id)"},
{"name":"description","datatype":"text"}
],
"action_candidate_feedback":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz","index":"btree(deleted_at)"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"candidate_id","datatype":"bigint","is_mandatory":1,"index":"btree(candidate_id)"},
{"name":"description","datatype":"text"},
{"name":"rating","datatype":"numeric(3,1)"},
{"name":"job_id","datatype":"bigint","index":"btree(job_id)"},
{"name":"interview_id","datatype":"bigint","index":"btree(interview_id)"}
],
"log_api":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","index":"btree(created_by_id,created_at)"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"deleted_by_id","datatype":"bigint"},
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
{"name":"created_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"log_users_delete":[
{"name":"id","datatype":"bigserial","is_primary":1},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree(user_id,created_at)"},
{"name":"event","datatype":"smallint","is_mandatory":1,"in":(1,2,3),"index":"btree(event,created_at)"},
{"name":"worker_status","datatype":"smallint","default":1,"is_mandatory":1,"in":(1,2,3,4),"index":"btree(worker_status,worker_next_retry_at,created_at)"},
{"name":"worker_retry_count","datatype":"integer","default":0},
{"name":"worker_next_retry_at","datatype":"timestamptz","default":"now()"},
{"name":"worker_processed_at","datatype":"timestamptz"},
{"name":"worker_last_error","datatype":"text"}
],
},
"control":{
"is_enable_autovacuum_optimize":1,
"is_enable_is_protected_delete_disable":1,
"is_enable_updated_at_set":1,
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
"is_enable_users_role_delete_disable_soft":1,
"table_row_delete_disable_all":[],
"table_row_delete_disable_bulk":[],
"actor_tracking_column": {"deleted_at": "deleted_by_id","deactivated_at": "deactivated_by_id","archived_at": "archived_by_id","verified_at": "verified_by_id"},
},
"sql":{
"index": {
"idx_users_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_users_deactivated_at_not_null ON users (id) WHERE deactivated_at IS NOT NULL",
"idx_users_deactivated_at_null_email_unique": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_deactivated_at_null_email_unique ON users (email) WHERE deactivated_at IS NULL",
"idx_users_deactivated_at_null_username_unique": "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_deactivated_at_null_username_unique ON users (username) WHERE deactivated_at IS NULL",
"idx_users_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_users_deleted_at_not_null ON users (id) WHERE deleted_at IS NOT NULL",
"idx_users_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_users_is_protected_1 ON users (id) WHERE is_protected IS TRUE",
"idx_users_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_users_verified_at_null ON users (id) WHERE verified_at IS NULL",
"idx_test_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_test_deactivated_at_not_null ON test (id) WHERE deactivated_at IS NOT NULL",
"idx_test_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_test_deleted_at_not_null ON test (id) WHERE deleted_at IS NOT NULL",
"idx_test_is_protected_1": "CREATE INDEX IF NOT EXISTS idx_test_is_protected_1 ON test (id) WHERE is_protected IS TRUE",
"idx_test_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_test_verified_at_null ON test (id) WHERE verified_at IS NULL",
"idx_post_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_post_deactivated_at_not_null ON post (id) WHERE deactivated_at IS NOT NULL",
"idx_post_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_post_deleted_at_not_null ON post (id) WHERE deleted_at IS NOT NULL",
"idx_post_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_post_verified_at_null ON post (id) WHERE verified_at IS NULL",
"idx_support_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_support_deactivated_at_not_null ON support (id) WHERE deactivated_at IS NOT NULL",
"idx_support_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_support_deleted_at_not_null ON support (id) WHERE deleted_at IS NOT NULL",
"idx_job_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_job_deactivated_at_not_null ON job (id) WHERE deactivated_at IS NOT NULL",
"idx_job_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_job_deleted_at_not_null ON job (id) WHERE deleted_at IS NOT NULL",
"idx_job_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_job_verified_at_null ON job (id) WHERE verified_at IS NULL",
"idx_candidate_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_candidate_deactivated_at_not_null ON candidate (id) WHERE deactivated_at IS NOT NULL",
"idx_candidate_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_candidate_deleted_at_not_null ON candidate (id) WHERE deleted_at IS NOT NULL",
"idx_candidate_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_candidate_verified_at_null ON candidate (id) WHERE verified_at IS NULL",
"idx_interview_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_interview_deactivated_at_not_null ON interview (id) WHERE deactivated_at IS NOT NULL",
"idx_interview_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_interview_deleted_at_not_null ON interview (id) WHERE deleted_at IS NOT NULL",
"idx_interview_verified_at_null": "CREATE INDEX IF NOT EXISTS idx_interview_verified_at_null ON interview (id) WHERE verified_at IS NULL",
"idx_message_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_message_deactivated_at_not_null ON message (id) WHERE deactivated_at IS NOT NULL",
"idx_message_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_message_deleted_at_not_null ON message (id) WHERE deleted_at IS NOT NULL",
"idx_message_read_at_null": "CREATE INDEX IF NOT EXISTS idx_message_read_at_null ON message (user_id) WHERE read_at IS NULL",
"idx_action_test_comment_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_test_comment_deactivated_at_not_null ON action_test_comment (id) WHERE deactivated_at IS NOT NULL",
"idx_action_test_comment_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_test_comment_deleted_at_not_null ON action_test_comment (id) WHERE deleted_at IS NOT NULL",
"idx_action_test_report_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_test_report_deactivated_at_not_null ON action_test_report (id) WHERE deactivated_at IS NOT NULL",
"idx_action_test_report_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_test_report_deleted_at_not_null ON action_test_report (id) WHERE deleted_at IS NOT NULL",
"idx_action_test_feedback_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_test_feedback_deactivated_at_not_null ON action_test_feedback (id) WHERE deactivated_at IS NOT NULL",
"idx_action_test_feedback_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_test_feedback_deleted_at_not_null ON action_test_feedback (id) WHERE deleted_at IS NOT NULL",
"idx_action_users_report_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_users_report_deactivated_at_not_null ON action_users_report (id) WHERE deactivated_at IS NOT NULL",
"idx_action_users_report_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_users_report_deleted_at_not_null ON action_users_report (id) WHERE deleted_at IS NOT NULL",
"idx_action_candidate_feedback_deactivated_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_candidate_feedback_deactivated_at_not_null ON action_candidate_feedback (id) WHERE deactivated_at IS NOT NULL",
"idx_action_candidate_feedback_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_action_candidate_feedback_deleted_at_not_null ON action_candidate_feedback (id) WHERE deleted_at IS NOT NULL",
"idx_log_api_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_log_api_deleted_at_not_null ON log_api (id) WHERE deleted_at IS NOT NULL",
"idx_log_users_password_deleted_at_not_null": "CREATE INDEX IF NOT EXISTS idx_log_users_password_deleted_at_not_null ON log_users_password (id) WHERE deleted_at IS NOT NULL",
"idx_log_users_delete_worker": "CREATE INDEX IF NOT EXISTS idx_log_users_delete_worker ON log_users_delete (worker_next_retry_at, created_at, id) WHERE worker_status IN (1,4)",
}
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
