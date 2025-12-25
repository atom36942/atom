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
"created_at-timestamptz-0-btree",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-btree",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-0",
"is_deleted-smallint-0-0",
"is_protected-smallint-0-0",
"type-bigint-0-btree",
"title-text-0-btree",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text[]-0-gin",
"tag_int-int[]-0-gin",
"rating-numeric(10,3)-0-0",
"remark-text-0-0",
"location-geography(POINT)-0-gist",
"dob-date-0-0",
"is_public-boolean-0-0",
"email-text-0-0",
"mobile-text-0-0",
"metadata-jsonb-0-gin"
],
"log_api":[
"created_at-timestamptz-0-btree",
"created_by_id-bigint-0-btree",
"type-bigint-0-0",
"ip_address-text-0-0",
"api-text-0-btree",
"api_id-smallint-0-0",
"method-text-0-0",
"query_param-text-0-0",
"status_code-smallint-0-btree",
"response_time_ms-numeric(1000,3)-0-0",
"description-text-0-0"
],
"users":[
"created_at-timestamptz-0-btree",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-bigint-1-btree",
"username-text-0-btree",
"password-text-0-btree",
"username_bigint-bigint-0-btree",
"password_bigint-bigint-0-btree",
"google_login_id-text-0-btree",
"google_login_metadata-jsonb-0-0",
"google_data-jsonb-0-0",
"email-text-0-btree",
"mobile-text-0-btree",
"api_access-text-0-0",
"last_active_at-timestamptz-0-0"
],
"otp":[
"created_at-timestamptz-0-btree",
"otp-integer-1-0",
"email-text-0-btree",
"mobile-text-0-btree"
],
"log_password":[
"created_at-timestamptz-0-0",
"user_id-bigint-0-0",
"password-text-0-0"
],
"message":[
"created_at-timestamptz-0-btree",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"user_id-bigint-1-btree",
"description-text-1-0",
"is_read-smallint-0-btree"
],
"report_test":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"test_id-bigint-1-btree"
],
"rating_test":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"test_id-bigint-1-btree",
"rating-numeric(10,3)-1-0"
],
"report_user":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"user_id-bigint-1-btree"
],
"config":[
"title-text-1-0",
"metadata-jsonb-1-gin"
],
},
"sql":{
"delete_disable_bulk_users":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure func_delete_disable_bulk(1);",
"username_check":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"unique_users_1":"alter table users add constraint constraint_unique_users_type_username unique (type,username);",
"unique_users_2":"alter table users add constraint constraint_unique_users_type_email unique (type,email);",
"unique_users_3":"alter table users add constraint constraint_unique_users_type_mobile unique (type,mobile);",
"unique_users_4":"alter table users add constraint constraint_unique_users_type_google_id unique (type,google_login_id);",
"unique_users_5":"alter table report_user add constraint constraint_unique_report_user unique (created_by_id,user_id);",
"unique_users_6":"alter table users add constraint constraint_unique_users_type_username_bigint unique (type,username_bigint);",
"unique_config":"alter table config add constraint constraint_unique_config_key unique (title);",
}
}

#namesapce datatype convert
from core.function import func_list_to_tuple
func_list_to_tuple(globals())
del func_list_to_tuple