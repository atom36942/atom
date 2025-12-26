#env
import os
from dotenv import load_dotenv
load_dotenv()

#postgres
config_postgres_url=os.getenv("config_postgres_url")
config_postgres_min_connection=int(os.getenv("config_postgres_min_connection") or 5)
config_postgres_max_connection=int(os.getenv("config_postgres_max_connection") or 20)
config_postgres_schema_name=os.getenv("config_postgres_schema_name") or "public"

#redis
config_redis_url=os.getenv("config_redis_url")
config_redis_url_ratelimiter=os.getenv("config_redis_url_ratelimiter") or config_redis_url

#key
config_key_jwt=os.getenv("config_key_jwt") or "123"
config_key_root=os.getenv("config_key_root") or "123"

#queue
config_celery_broker_url=os.getenv("config_celery_broker_url")
config_celery_backend_url=os.getenv("config_celery_backend_url") or config_celery_broker_url
config_kafka_url=os.getenv("config_kafka_url")
config_kafka_username=os.getenv("config_kafka_username")
config_kafka_password=os.getenv("config_kafka_password")
config_rabbitmq_url=os.getenv("config_rabbitmq_url")
config_redis_url_pubsub=os.getenv("config_redis_url_pubsub") or config_redis_url
config_channel_name=os.getenv("config_channel_name") or "channel_1"
config_kafka_group_id=os.getenv("config_kafka_group_id") or "group_1"
config_kafka_enable_auto_commit=(os.getenv("config_kafka_enable_auto_commit") or "True").lower()=="true"

#aws
config_aws_access_key_id=os.getenv("config_aws_access_key_id")
config_aws_secret_access_key=os.getenv("config_aws_secret_access_key")
config_s3_region_name=os.getenv("config_s3_region_name")
config_sns_region_name=os.getenv("config_sns_region_name")
config_ses_region_name=os.getenv("config_ses_region_name")
config_limit_s3_kb=int(os.getenv("config_limit_s3_kb") or 100)
config_s3_presigned_expire_sec=int(os.getenv("config_s3_presigned_expire_sec") or 60)

#sftp
config_sftp_auth_method=os.getenv("config_sftp_auth_method") or "password"
config_sftp_host=os.getenv("config_sftp_host")
config_sftp_port=os.getenv("config_sftp_port")
config_sftp_username=os.getenv("config_sftp_username")
config_sftp_password=os.getenv("config_sftp_password")
config_sftp_key_path=os.getenv("config_sftp_key_path")

#communication
config_fast2sms_url=os.getenv("config_fast2sms_url")
config_fast2sms_key=os.getenv("config_fast2sms_key")
config_resend_url=os.getenv("config_resend_url")
config_resend_key=os.getenv("config_resend_key")

#google
config_google_login_client_id=os.getenv("config_google_login_client_id")
config_gsheet_service_account_json_path=os.getenv("config_gsheet_service_account_json_path")
config_gsheet_scope_list=(os.getenv("config_gsheet_scope_list") or "https://www.googleapis.com/auth/spreadsheets").split(",")

#analytics
config_sentry_dsn=os.getenv("config_sentry_dsn")
config_posthog_project_host=os.getenv("config_posthog_project_host")
config_posthog_project_key=os.getenv("config_posthog_project_key")

#integration
config_mongodb_url=os.getenv("config_mongodb_url")
config_openai_key=os.getenv("config_openai_key")

#cors
config_cors_origin_list=(os.getenv("config_cors_origin_list") or "*").split(",")
config_cors_method_list=(os.getenv("config_cors_method_list") or "*").split(",")
config_cors_headers_list=(os.getenv("config_cors_headers_list") or "*").split(",")
config_cors_allow_credentials=(os.getenv("config_cors_allow_credentials") or "False").lower() == "true"

#switch
config_is_signup=int(os.getenv("config_is_signup") or 1)
config_is_log_api=int(os.getenv("config_is_log_api") or 1)
config_is_traceback=int(os.getenv("config_is_traceback") or 1)
config_is_prometheus=int(os.getenv("config_is_prometheus") or 0)
config_is_otp_verify_profile_update=int(os.getenv("config_is_otp_verify_profile_update") or 1)
config_is_reset_export_folder=int(os.getenv("config_is_reset_export_folder") or 1)
config_is_debug_fastapi=int(os.getenv("config_is_debug_fastapi") or 1)

#zzz
config_mode_check_is_active=os.getenv("config_mode_check_is_active") or "token"
config_mode_check_api_access=os.getenv("config_mode_check_api_access") or "token"
config_auth_type_list=list(map(int,(os.getenv("config_auth_type_list") or "1,2,3").split(",")))
config_token_expire_sec=int(os.getenv("config_token_expire_sec") or 365*24*60*60)
config_token_user_key_list=(os.getenv("config_token_user_key_list") or "id,type,is_active,api_access").split(",")
config_column_disabled_list=(os.getenv("config_column_disabled_list") or "is_active,is_verified,api_access").split(",")
config_my_table_create_list=(os.getenv("config_my_table_create_list") or "test,rating_test").split(",")
config_public_table_create_list=(os.getenv("config_public_table_create_list") or "test").split(",")
config_public_table_read_list=(os.getenv("config_public_table_read_list") or "test").split(",")
config_limit_ids_delete=int(os.getenv("config_limit_ids_delete") or 1000)
config_otp_expire_sec=int(os.getenv("config_otp_expire_sec") or 10*60)

#dict
config_sql={
"user":{"test_count":"select count(*) from test where created_by_id=$1","test_object":"select * from test where created_by_id=$1 limit 1"},
"cache_users_api_access":"select id,api_access from users where api_access is not null limit 1000",
"cache_users_is_active":"select id,is_active from users limit 1000",
"cache_config":"select title,metadata from config limit 1000;",
}

config_table={
"test":{"buffer":3},
"log_api":{"retention_day":30,"buffer":3},
"log_password":{"retention_day":90},
"otp":{"retention_day":365},
}

config_api={
"/admin/object-create":{"id":1},
"/admin/object-update":{"id":2},
"/admin/object-read":{"id":3},
"/admin/ids-update":{"id":4},
"/admin/ids-delete":{"id":5},
"/test":{"id":6,"is_token":0,"is_active_check":0,"cache_sec":["redis",0],"ratelimiter_times_sec":[10,3]},
"/public/object-read":{"id":7,"cache_sec":["inmemory",60]},
"/my/profile":{"id":8,"is_active_check":1,"cache_sec":["inmemory",10]},
"/my/object-read":{"id":9,"cache_sec":["inmemory",60]},
"/public/info":{"id":11,"cache_sec":["inmemory",10]},
}

config_postgres={
"table":{
"test":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":"btree"},
{"column":"updated_at","datatype":"timestamptz","mandatory":0,"index":0},
{"column":"created_by_id","datatype":"bigint","mandatory":0,"index":"btree"},
{"column":"updated_by_id","datatype":"bigint","mandatory":0,"index":0},
{"column":"is_active","datatype":"smallint","mandatory":0,"index":"btree"},
{"column":"is_verified","datatype":"smallint","mandatory":0,"index":0},
{"column":"is_deleted","datatype":"smallint","mandatory":0,"index":0},
{"column":"is_protected","datatype":"smallint","mandatory":0,"index":0},
{"column":"type","datatype":"int","mandatory":0,"index":"btree"},
{"column":"title","datatype":"text","mandatory":0,"index":"btree"},
{"column":"description","datatype":"text","mandatory":0,"index":0},
{"column":"file_url","datatype":"text","mandatory":0,"index":0},
{"column":"link_url","datatype":"text","mandatory":0,"index":0},
{"column":"tag","datatype":"text[]","mandatory":0,"index":"gin"},
{"column":"tag_int","datatype":"int[]","mandatory":0,"index":"gin"},
{"column":"tag_bigint","datatype":"bigint[]","mandatory":0,"index":"gin"},
{"column":"rating","datatype":"numeric(3,1)","mandatory":0,"index":0},
{"column":"remark","datatype":"text","mandatory":0,"index":0},
{"column":"location","datatype":"geography(POINT)","mandatory":0,"index":"gist"},
{"column":"dob","datatype":"date","mandatory":0,"index":0},
{"column":"is_public","datatype":"boolean","mandatory":0,"index":0},
{"column":"email","datatype":"text","mandatory":0,"index":0},
{"column":"mobile","datatype":"text","mandatory":0,"index":0},
{"column":"status","datatype":"int","mandatory":0,"index":"btree"},
{"column":"metadata","datatype":"jsonb","mandatory":0,"index":"gin"}
],
"log_api":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":"btree"},
{"column":"created_by_id","datatype":"bigint","mandatory":0,"index":"btree"},
{"column":"type","datatype":"int","mandatory":0,"index":0},
{"column":"ip_address","datatype":"text","mandatory":0,"index":0},
{"column":"api","datatype":"text","mandatory":0,"index":"btree"},
{"column":"api_id","datatype":"smallint","mandatory":0,"index":0},
{"column":"method","datatype":"text","mandatory":0,"index":0},
{"column":"query_param","datatype":"text","mandatory":0,"index":0},
{"column":"status_code","datatype":"smallint","mandatory":0,"index":"btree"},
{"column":"response_time_ms","datatype":"int","mandatory":0,"index":0},
{"column":"description","datatype":"text","mandatory":0,"index":0}
],
"users":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":"btree"},
{"column":"updated_at","datatype":"timestamptz","mandatory":0,"index":0},
{"column":"created_by_id","datatype":"bigint","mandatory":0,"index":0},
{"column":"updated_by_id","datatype":"bigint","mandatory":0,"index":0},
{"column":"is_active","datatype":"smallint","mandatory":0,"index":"btree"},
{"column":"is_verified","datatype":"smallint","mandatory":0,"index":"btree"},
{"column":"is_deleted","datatype":"smallint","mandatory":0,"index":"btree"},
{"column":"is_protected","datatype":"smallint","mandatory":0,"index":"btree"},
{"column":"type","datatype":"int","mandatory":1,"index":"btree"},
{"column":"username","datatype":"text","mandatory":0,"index":"btree","is_trim":1,"is_lowercase":1,"unique":"username,type"},
{"column":"email","datatype":"text","mandatory":0,"index":"btree","unique":"email,type"},
{"column":"mobile","datatype":"text","mandatory":0,"index":"btree","unique":"mobile,type"},
{"column":"google_login_id","datatype":"text","mandatory":0,"index":"btree","unique":"google_login_id,type"},
{"column":"username_bigint","datatype":"bigint","mandatory":0,"index":"btree","unique":"username_bigint,type"},
{"column":"password","datatype":"text","mandatory":0,"index":"btree"},
{"column":"password_bigint","datatype":"bigint","mandatory":0,"index":"btree"},
{"column":"google_login_metadata","datatype":"jsonb","mandatory":0,"index":0},
{"column":"google_data","datatype":"jsonb","mandatory":0,"index":0},
{"column":"api_access","datatype":"text","mandatory":0,"index":0},
{"column":"last_active_at","datatype":"timestamptz","mandatory":0,"index":0}
],
"otp":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":"btree"},
{"column":"otp","datatype":"integer","mandatory":1,"index":0},
{"column":"email","datatype":"text","mandatory":0,"index":"btree"},
{"column":"mobile","datatype":"text","mandatory":0,"index":"btree"}
],
"log_password":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":0},
{"column":"user_id","datatype":"bigint","mandatory":0,"index":0},
{"column":"password","datatype":"text","mandatory":0,"index":0}
],
"message":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":"btree"},
{"column":"updated_at","datatype":"timestamptz","mandatory":0,"index":0},
{"column":"created_by_id","datatype":"bigint","mandatory":1,"index":"btree"},
{"column":"updated_by_id","datatype":"bigint","mandatory":0,"index":0},
{"column":"is_deleted","datatype":"smallint","mandatory":0,"index":"btree"},
{"column":"user_id","datatype":"bigint","mandatory":1,"index":"btree"},
{"column":"description","datatype":"text","mandatory":1,"index":0},
{"column":"is_read","datatype":"smallint","mandatory":0,"index":"btree"}
],
"report_test":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":0},
{"column":"created_by_id","datatype":"bigint","mandatory":1,"index":"btree","unique":"created_by_id,test_id"},
{"column":"test_id","datatype":"bigint","mandatory":1,"index":"btree"}
],
"rating_test":[
{"column":"created_at","datatype":"timestamptz","mandatory":0,"index":0},
{"column":"created_by_id","datatype":"bigint","mandatory":1,"index":"btree"},
{"column":"test_id","datatype":"bigint","mandatory":1,"index":"btree"},
{"column":"rating","datatype":"numeric(3,1)","mandatory":1,"index":0}
],
"config":[
{"column":"title","datatype":"text","mandatory":1,"index":0,"unique":"title"},
{"column":"metadata","datatype":"jsonb","mandatory":1,"index":"gin"}
]
},
"sql":{
"delete_disable_bulk_users":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure func_delete_disable_bulk(1);"
}
}

#namesapce datatype convert
from core.function import func_list_to_tuple
func_list_to_tuple(globals())
del func_list_to_tuple