#postgres
config_postgres_url=None
config_postgres_min_connection=5
config_postgres_max_connection=20

#redis
config_redis_url=None
config_redis_url_ratelimiter=config_redis_url
config_redis_cache_ttl_sec=3600

#queue
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
config_token_expiry_sec=10*365*24*24
config_token_refresh_expiry_sec=100*365*24*24
config_token_key=["id", "type", "role", "is_active"]

#aws
config_aws_access_key_id=None
config_aws_secret_access_key=None
config_s3_region_name=None
config_sns_region_name=None
config_ses_region_name=None
config_s3_limit_kb=100
config_s3_upload_limit_count=10
config_s3_presigned_expire_sec=60

#integration
config_google_login_client_id=None
config_gsheet_service_account_json_path=None
config_gsheet_scope=["https://www.googleapis.com/auth/spreadsheets"]
config_fast2sms_url=None
config_fast2sms_key=None
config_resend_url=None
config_resend_key=None
config_posthog_project_host=None
config_posthog_project_key=None
config_mongodb_url=None
config_openai_key=None
config_gemini_key=None
config_sentry_dsn=None

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

#switch
config_is_signup=1
config_is_log_api=1
config_is_traceback=1
config_is_prometheus=0
config_is_reset_tmp=0
config_is_index_html=0
config_is_otp_users_update_admin=0
config_is_postgres_init_startup=1

#system
config_index_html_path=None
config_auth_type=[1, 2, 3]
config_expiry_sec_otp=600

#enum
config_table_create_my=["test", "post", "support", "rating_test"]
config_table_create_public=["test", "support"]
config_table_read_public=["test", "post"]
config_column_blocked=["is_active", "is_verified", "role", "created_at", "updated_at", "created_by_id"]
config_column_single_update=["username", "password", "email", "mobile"]
config_api_roles=["index", "auth", "my", "public", "private", "admin"]
config_api_roles_auth=["/my/", "/private/", "/admin/"]

#dict
config_sql={
"cache_users_role":"select id,role from users where role is not null order by id asc limit 1000",
"cache_users_is_active":"select id,is_active from users order by id asc limit 1000",
"profile_metadata":{"test_count":"select count(*) from test where created_by_id=$1","test_object":"select * from test where created_by_id=$1 limit 1"},
}

config_table={
"test":{"buffer":100},
"log_api":{"retention_day":30,"buffer":10},
"log_users_password":{"retention_day":90},
"otp":{"retention_day":365},
}

config_api={
"/admin/sync":{"id":1,"user_role_check":["realtime",[1]]},
"/admin/object-create":{"id":2,"user_role_check":["token",[1]]},
"/admin/object-update":{"id":3,"user_role_check":["token",[1]]},
"/admin/object-read":{"id":4,"user_role_check":["inmemory",[1]]},
"/admin/ids-delete":{"id":5,"user_role_check":["realtime",[1]],"user_is_active_check":["realtime", 1]},
"/admin/postgres-runner":{"id":6,"user_role_check":["realtime",[1]]},
"/admin/postgres-export":{"id":7,"user_role_check":["inmemory",[1]]},
"/admin/postgres-import":{"id":8,"user_role_check":["realtime",[1]]},
"/admin/redis-import":{"id":9,"user_role_check":["token",[1]]},
"/admin/mongodb-import":{"id":11,"user_role_check":["token",[1]]},
"/admin/s3-bucket-ops":{"id":12,"user_role_check":["token",[1]]},
"/admin/s3-url-delete":{"id":13,"user_role_check":["token",[1]]},
"/public/object-read":{"id":14,"api_cache_sec":["inmemory",1]},
"/my/profile":{"id":15,"api_cache_sec":["inmemory",10]},
"/my/object-read":{"id":16,"api_cache_sec":["inmemory",1]},
"/info":{"id":17,"api_cache_sec":["inmemory",100]},
"/public/table-tag-read":{"id":18,"api_cache_sec":["inmemory",10]},
"/public/jira-worklog-export":{"id":19,"api_ratelimiting_times_sec":["inmemory",10,60]},
}

config_postgres={
"table":{
"test":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"created_at(btree)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"created_by_id(btree)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"integer","in":(0,1),"index":"is_active(btree)"},
{"name":"is_verified","datatype":"integer","in":(0,1),"index":"is_verified(btree)"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"is_protected","datatype":"integer","in":(0,1),"index":"is_protected(btree)"},
{"name":"type","datatype":"integer","index":"type(btree)"},
{"name":"title","datatype":"text","is_mandatory":1,"index":"title(gin)"},
{"name":"code","datatype":"text","is_mandatory":0,"unique":"code,type|code,slug"},
{"name":"slug","datatype":"text"},
{"name":"email","datatype":"text","regex":"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"},
{"name":"mobile","datatype":"text"},
{"name":"category","datatype":"text","unique":"category"},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"tag(gin)"},
{"name":"tag_int","datatype":"integer[]","index":"tag_int(gin)"},
{"name":"tag_bigint","datatype":"bigint[]","index":"tag_bigint(gin)"},
{"name":"rating","datatype":"numeric(3,1)","check":"rating >= 0 AND rating <= 5"},
{"name":"price","datatype":"numeric(10,2)","check":"price > 0"},
{"name":"remark","datatype":"text"},
{"name":"location","datatype":"geography(point)","index":"location(gist)"},
{"name":"dob","datatype":"date"},
{"name":"description","datatype":"text","index":"description(btree)|description(gin)"},
{"name":"status","datatype":"integer","old":"status2","index":"status,type(btree)"},
{"name":"metadata","datatype":"jsonb","index":"metadata(gin)"}
],
"users":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"created_at(btree)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"integer","in":(0,1),"index":"is_active(btree)"},
{"name":"is_verified","datatype":"integer","in":(0,1),"index":"is_verified(btree)"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"is_protected","datatype":"integer","in":(0,1),"index":"is_protected(btree)"},
{"name":"type","datatype":"integer","is_mandatory":1,"index":"type(btree)"},
{"name":"username","datatype":"text","unique":"username,type","regex":"^(?=.{3,20}$)[a-z][a-z0-9_@-]*$"},
{"name":"password","datatype":"text","index":"password(btree)"},
{"name":"username_bigint","datatype":"bigint","unique":"username_bigint,type"},
{"name":"password_bigint","datatype":"bigint","index":"password_bigint(btree)"},
{"name":"google_login_id","datatype":"text","unique":"google_login_id,type"},
{"name":"google_login_metadata","datatype":"jsonb"},
{"name":"email","datatype":"text","unique":"email,type"},
{"name":"mobile","datatype":"text","unique":"mobile,type"},
{"name":"role","datatype":"integer"},
{"name":"last_active_at","datatype":"timestamptz"},
{"name":"name","datatype":"text"},
{"name":"country","datatype":"text"},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_communication","datatype":"text"},
{"name":"mobile_communication","datatype":"text"},
],
"log_api":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"created_at(btree)"},
{"name":"created_by_id","datatype":"bigint","index":"created_by_id(btree)"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"type","datatype":"integer"},
{"name":"ip_address","datatype":"text"},
{"name":"api","datatype":"text","index":"api(btree)"},
{"name":"api_id","datatype":"integer"},
{"name":"method","datatype":"text"},
{"name":"query_param","datatype":"text"},
{"name":"status_code","datatype":"integer","index":"status_code(btree)"},
{"name":"response_time_ms","datatype":"integer"},
{"name":"description","datatype":"text"}
],
"otp":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"created_at(btree)"},
{"name":"otp","datatype":"integer","is_mandatory":1},
{"name":"email","datatype":"text","index":"email(btree)"},
{"name":"mobile","datatype":"text","index":"mobile(btree)"},
],
"log_users_password":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"message":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"created_at(btree)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"created_by_id(btree)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"user_id(btree)"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"is_read","datatype":"integer","index":"is_read(btree)"}
],
"report_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"unique":"created_by_id,test_id"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"test_id(btree)"}
],
"rating_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"created_by_id(btree)"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"test_id(btree)"},
{"name":"rating","datatype":"numeric(3,1)","is_mandatory":1}
],
"support":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"created_at(btree)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"created_by_id","datatype":"bigint","index":"created_by_id(btree)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"status","datatype":"integer","index":"status(btree)"},
{"name":"email","datatype":"text"},
{"name":"mobile","datatype":"text"},
],
"post":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"created_at(btree)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"created_by_id(btree)"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"integer","in":(0,1),"index":"is_active(btree)"},
{"name":"is_verified","datatype":"integer","in":(0,1),"index":"is_verified(btree)"},
{"name":"is_deleted","datatype":"integer","in":(0,1),"index":"is_deleted(btree)"},
{"name":"type","datatype":"integer","index":"type(btree)"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"tag(gin)"},
]
},
"control":{
"root_user_password":"f2aca8bf32871f21d371a1ba1111b4890e64fadb854201cd77441ac816cc4bc6",
"is_extension":1,
"is_drop_disable_schema":0,
"is_drop_disable_table":1,
"is_truncate_disable":1,
"is_users_delete_child_soft":1,
"is_users_delete_child_hard":1,
"is_users_delete_disable_role":1,
"table_delete_disable_row":["users"],
"table_delete_disable_row_bulk":[["users",1]],
"is_autovacuum_optimize":1
},
"sql":{},
}

#override
from .function import func_config_override_from_env
func_config_override_from_env(global_dict=globals())