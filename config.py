#postgres
config_postgres_url=None
config_postgres_min_connection=5
config_postgres_max_connection=20

#redis
config_redis_url=None
config_redis_url_ratelimiter=config_redis_url
config_redis_cache_ttl_sec=3600

#queue
config_channel_name="channel_1"
config_redis_url_pubsub=config_redis_url
config_rabbitmq_url=None
config_celery_broker_url=config_redis_url
config_celery_backend_url=config_celery_broker_url
config_kafka_url=None
config_kafka_username=None
config_kafka_password=None
config_kafka_group_id="group_1"
config_kafka_is_auto_commit=1
config_kafka_batch_limit=100
config_kafka_batch_timeout_ms=1000
config_rabbitmq_batch_limit=1000
config_rabbitmq_batch_timeout_ms=1000
config_redis_batch_limit=1000
config_redis_batch_timeout_ms=1000

#token
config_token_secret_key="123"
config_token_expiry_sec=3*24*60*60
config_token_refresh_expiry_sec=3*24*60*60*100
config_token_key=["id", "type", "is_active", "role"]

#gsheet
config_gsheet_service_account_json_path=None
config_gsheet_scope=["https://www.googleapis.com/auth/spreadsheets"]

#fast2sms
config_fast2sms_url=None
config_fast2sms_key=None

#resend
config_resend_url=None
config_resend_key=None

#posthog
config_posthog_project_host=None
config_posthog_project_key=None

#aws
config_aws_access_key_id=None
config_aws_secret_access_key=None
config_s3_region_name=None
config_sns_region_name=None
config_ses_region_name=None
config_s3_limit_kb=100
config_s3_upload_limit_count=10
config_s3_presigned_expire_sec=60

#sftp
config_sftp_auth_method="password"
config_sftp_host=None
config_sftp_port=None
config_sftp_username=None
config_sftp_password=None
config_sftp_key_path=None

#cors
config_cors_origin=["*"]
config_cors_method=["*"]
config_cors_headers=["*"]
config_is_cors_allow_credentials=0

#enum
config_index_html=None
config_auth_type=[1, 2, 3]
config_table_create_my=["test", "post", "support", "rating_test"]
config_table_create_public=["test", "support"]
config_table_read_public=["test", "post"]
config_table_system=["spatial_ref_sys"]
config_column_blocked=["is_active", "is_verified", "role", "created_at", "updated_at"]
config_column_single_update=["username", "password", "email", "mobile"]
config_api_roles=["index", "auth", "my", "public", "private", "admin"]

#switch
config_is_signup=1
config_is_log_api=1
config_is_traceback=1
config_is_prometheus=0
config_is_reset_tmp=1
config_is_debug_fastapi=1
config_is_index_html=0
config_is_otp_users_update_admin=0
config_is_postgres_init_startup=1

#zzz
config_expiry_sec_otp=600
config_postgres_ids_delete_limit=1000
config_postgres_batch_limit=1000
config_google_login_client_id=None
config_mongodb_uri=None
config_openai_key=None
config_gemini_key=None
config_sentry_dsn=None

#dict
config_sql={
"cache_users_role":"select id,role from users where role is not null order by id asc limit 1000",
"cache_users_is_active":"select id,is_active from users order by id asc limit 1000",
"profile_metadata":{"test_count":"select count(*) from test where created_by_id=$1","test_object":"select * from test where created_by_id=$1 limit 1"},
}

config_table={
"test":{"buffer":3},
"log_api":{"retention_day":30,"buffer":10},
"log_users_password":{"retention_day":90},
"otp":{"retention_day":365},
}

config_api={
"/admin/sync":{"user_role_check":["realtime",[1]]},
"/admin/object-create":{"user_role_check":["token",[1]]},
"/admin/object-update":{"user_role_check":["token",[1]]},
"/admin/object-read":{"user_role_check":["inmemory",[1]]},
"/admin/ids-delete":{"user_role_check":["realtime",[1]],"user_is_active_check":["realtime", 1]},
"/admin/postgres-runner":{"user_role_check":["realtime",[1]]},
"/admin/postgres-export":{"user_role_check":["inmemory",[1]]},
"/admin/postgres-import":{"user_role_check":["realtime",[1]]},
"/admin/redis-import-create":{"user_role_check":["token",[1]]},
"/admin/redis-import-delete":{"user_role_check":["token",[1]]},
"/admin/mongodb-import":{"user_role_check":["token",[1]]},
"/admin/s3-bucket-ops":{"user_role_check":["token",[1]]},
"/admin/s3-url-delete":{"user_role_check":["token",[1]]},
"/public/object-read":{"api_cache_sec":["inmemory",1]},
"/my/profile":{"api_cache_sec":["inmemory",10]},
"/my/object-read":{"api_cache_sec":["inmemory",1]},
"/info":{"api_cache_sec":["inmemory",100]},
"/public/table-tag-read":{"api_cache_sec":["inmemory",10]},
"/public/jira-worklog-export":{"api_ratelimiting_times_sec":["inmemory",10,60]},
}

config_postgres={
"table":{
"test":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_verified","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_protected","datatype":"integer","index":"btree","in":(0,1)},
{"name":"type","datatype":"integer","index":"btree"},
{"name":"title","datatype":"text","index":"btree,gin","is_mandatory":1},
{"name":"description","datatype":"text"},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin","regex":"^[a-z0-9 _@-]*$"},
{"name":"tag_int","datatype":"integer[]","index":"gin"},
{"name":"tag_bigint","datatype":"bigint[]","index":"gin"},
{"name":"rating","datatype":"numeric(3,1)"},
{"name":"remark","datatype":"text"},
{"name":"location","datatype":"geography(point)","index":"gist"},
{"name":"dob","datatype":"date"},
{"name":"email","datatype":"text"},
{"name":"mobile","datatype":"text"},
{"name":"status","datatype":"integer","index":"btree","old":"status2"},
{"name":"metadata","datatype":"jsonb","index":"gin"}
],
"users":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_verified","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_protected","datatype":"integer","index":"btree","in":(0,1)},
{"name":"type","datatype":"integer","is_mandatory":1,"index":"btree"},
{"name":"username","datatype":"text","index":"btree","unique":"username,type","regex":"^(?=.{3,20}$)[a-z][a-z0-9_@-]*$"},
{"name":"password","datatype":"text","index":"btree"},
{"name":"username_bigint","datatype":"bigint","index":"btree","unique":"username_bigint,type"},
{"name":"password_bigint","datatype":"bigint","index":"btree"},
{"name":"google_login_id","datatype":"text","index":"btree","unique":"google_login_id,type"},
{"name":"google_login_metadata","datatype":"jsonb"},
{"name":"email","datatype":"text","index":"btree","unique":"email,type"},
{"name":"mobile","datatype":"text","index":"btree","unique":"mobile,type"},
{"name":"role","datatype":"integer"},
{"name":"last_active_at","datatype":"timestamptz"},
{"name":"name","datatype":"text"},
{"name":"country","datatype":"text"},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_comm","datatype":"text"},
{"name":"mobile_comm","datatype":"text"},
],
"log_api":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"created_by_id","datatype":"bigint","index":"btree"},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"type","datatype":"integer"},
{"name":"ip_address","datatype":"text"},
{"name":"api","datatype":"text","index":"btree"},
{"name":"api_id","datatype":"integer"},
{"name":"method","datatype":"text"},
{"name":"query_param","datatype":"text"},
{"name":"status_code","datatype":"integer","index":"btree"},
{"name":"response_time_ms","datatype":"integer"},
{"name":"description","datatype":"text"}
],
"otp":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"otp","datatype":"integer","is_mandatory":1},
{"name":"email","datatype":"text","index":"btree"},
{"name":"mobile","datatype":"text","index":"btree"}
],
"log_users_password":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"message":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"is_read","datatype":"integer","index":"btree"}
],
"report_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree","unique":"created_by_id,test_id"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree"}
],
"rating_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"rating","datatype":"numeric(3,1)","is_mandatory":1}
],
"support":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"created_by_id","datatype":"bigint","index":"btree"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"status","datatype":"integer","index":"btree"},
{"name":"email","datatype":"text"},
{"name":"mobile","datatype":"text"},
],
"post":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_verified","datatype":"integer","index":"btree","in":(0,1)},
{"name":"is_deleted","datatype":"integer","index":"btree","in":(0,1)},
{"name":"type","datatype":"integer","index":"btree"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin"},
]
},
"sql":{},
"control":{
"root_user_password":"57628ad8592242cbd02129a2ac94bb8ac3e16ac91fa240b812c6176415f04f92",
"is_extension":1,
"is_column_match":0,
"is_table_drop_disable":1,
"is_table_truncate_disable":1,
"is_users_child_delete_soft":1,
"is_users_child_delete_hard":1,
"is_users_delete_disable_role":1,
"table_delete_disable":["*"],
"table_delete_disable_bulk":[["*", 1000]],
"is_autovacuum_optimize":1,
"is_analyze_init":1
}
}

#override
from function import func_config_override_from_env
func_config_override_from_env(globals())