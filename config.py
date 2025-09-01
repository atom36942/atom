#env
import os
from dotenv import load_dotenv
load_dotenv()

#key
config_key_jwt=os.getenv("config_key_jwt")
config_key_root=os.getenv("config_key_root")

#postgres
config_postgres_url=os.getenv("config_postgres_url")
config_postgres_url_read=os.getenv("config_postgres_url_read")
config_postgres_min_connection=int(os.getenv("config_postgres_min_connection") or 5)
config_postgres_max_connection=int(os.getenv("config_postgres_max_connection") or 20)

#redis
config_redis_url=os.getenv("config_redis_url")
config_redis_url_ratelimiter=os.getenv("config_redis_url_ratelimiter") or config_redis_url

#kafka
config_kafka_url=os.getenv("config_kafka_url")
config_kafka_username=os.getenv("config_kafka_username")
config_kafka_password=os.getenv("config_kafka_password")

#celery
config_celery_broker_url=os.getenv("config_celery_broker_url")
config_celery_backend_url=os.getenv("config_celery_backend_url")

#rabbitmq
config_rabbitmq_url=os.getenv("config_rabbitmq_url")

#redis pubsub
config_redis_pubsub_url=os.getenv("config_redis_pubsub_url")

#mongodb
config_mongodb_url=os.getenv("config_mongodb_url")

#fast2sms
config_fast2sms_url=os.getenv("config_fast2sms_url")
config_fast2sms_key=os.getenv("config_fast2sms_key")

#resend
config_resend_url=os.getenv("config_resend_url")
config_resend_key=os.getenv("config_resend_key")

#posthog
config_posthog_project_host=os.getenv("config_posthog_project_host")
config_posthog_project_key=os.getenv("config_posthog_project_key")

#sentry
config_sentry_dsn=os.getenv("config_sentry_dsn")

#gogole login
config_google_login_client_id=os.getenv("config_google_login_client_id")

#openai
config_openai_key=os.getenv("config_openai_key")

#aws
config_aws_access_key_id=os.getenv("config_aws_access_key_id")
config_aws_secret_access_key=os.getenv("config_aws_secret_access_key")
config_s3_region_name=os.getenv("config_s3_region_name")
config_sns_region_name=os.getenv("config_sns_region_name")
config_ses_region_name=os.getenv("config_ses_region_name")
config_limit_s3_kb=int(os.getenv("config_limit_s3_kb") or 100)
config_s3_presigned_expire_sec=int(os.getenv("config_s3_presigned_expire_sec") or 60)

#switch
config_is_signup=int(os.getenv("config_is_signup") or 1)
config_is_log_api=int(os.getenv("config_is_log_api") or 1)
config_is_traceback=int(os.getenv("config_is_traceback") or 1)
config_is_prometheus=int(os.getenv("config_is_prometheus") or 0)
config_is_otp_verify_profile_update=int(os.getenv("config_is_otp_verify_profile_update") or 1)

#cors
config_cors_origin_list=(os.getenv("config_cors_origin_list") or "*").split(",")
config_cors_method_list=(os.getenv("config_cors_method_list") or "*").split(",")
config_cors_headers_list=(os.getenv("config_cors_headers_list") or "*").split(",")
config_cors_allow_credentials=(os.getenv("config_cors_allow_credentials") or "False").lower() == "true"

#token
config_token_expire_sec=int(os.getenv("config_token_expire_sec") or 365*24*60*60)
config_token_user_key_list=(os.getenv("config_token_user_key_list") or "id,type,is_active,api_access").split(",")

#batch
config_batch_log_api=int(os.getenv("config_batch_log_api") or 10)
config_batch_object_create=int(os.getenv("config_batch_object_create") or 3)

#public
config_public_table_create_list=(os.getenv("config_public_table_create_list") or "test").split(",")
config_public_table_read_list=(os.getenv("config_public_table_read_list") or "test").split(",")

#limit
config_limit_cache_users_api_access=int(os.getenv("config_limit_cache_users_api_access") or 10)
config_limit_cache_users_is_active=int(os.getenv("config_limit_cache_users_is_active") or 10)
config_limit_ids_delete=int(os.getenv("config_limit_ids_delete") or 100)

#misc
config_mode_check_api_access=os.getenv("config_mode_check_api_access") or "token"
config_mode_check_is_active=os.getenv("config_mode_check_is_active") or "token"
config_auth_type_list=list(map(int,(os.getenv("config_auth_type_list") or "1,2,3").split(",")))
config_column_disabled_list=(os.getenv("config_column_disabled_list") or "is_active,is_verified,api_access").split(",")

#dict
config_user_count_query={
"log_api_count":"select count(*) from log_api where created_by_id=:user_id",
"test_count":"select count(*) from test where created_by_id=:user_id"
}
config_postgres_clean={
"log_api":365,
"otp":365,
}
config_api={
"/admin/object-create":{"id":1},
"/admin/object-update":{"id":2},
"/admin/ids-update":{"id":3},
"/admin/ids-delete":{"id":4}, 
"/admin/object-read":{"id":5,"cache_sec":["redis",100]},
"/public/object-read":{"id":8,"cache_sec":["inmemory",60]},
"/test":{"id":100,"is_token":0,"is_active_check":1,"cache_sec":["redis",60],"ratelimiter_times_sec":[1,3]},
}
config_postgres_schema={
"table":{
"test":[
"created_at-timestamptz-0-btree,brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-bigint-0-btree",
"title-text-0-btree,gin",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0",
"rating-numeric(10,3)-0-0",
"remark-text-0-btree,gin",
"location-geography(POINT)-0-gist",
"metadata-jsonb-0-gin"
],
"log_api":[
"created_at-timestamptz-0-btree,brin",
"created_by_id-bigint-0-btree",
"response_type-smallint-0-btree",
"ip_address-text-0-0",
"api-text-0-btree,gin",
"api_id-smallint-0-btree",
"method-text-0-0",
"query_param-text-0-0",
"status_code-smallint-0-btree",
"response_time_ms-numeric(1000,3)-0-btree",
"description-text-0-0"
],
"users":[
"created_at-timestamptz-0-btree,brin",
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
"google_id-text-0-btree",
"google_data-jsonb-0-0",
"email-text-0-btree",
"mobile-text-0-btree",
"api_access-text-0-0",
"last_active_at-timestamptz-0-0",
"username_bigint-bigint-0-btree",
"password_bigint-bigint-0-btree"
],
"otp":[
"created_at-timestamptz-0-btree,brin",
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
"created_at-timestamptz-0-btree,brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"updated_by_id-bigint-0-0",
"is_deleted-smallint-0-btree",
"user_id-bigint-1-btree",
"description-text-1-0",
"is_read-smallint-0-btree"
],
"report_user":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"user_id-bigint-1-btree"
]
},
"query":{
"users_disable_bulk_delete":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"users_check_username":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"users_unique_1":"alter table users add constraint constraint_unique_users_type_username unique (type,username);",
"users_unique_2":"alter table users add constraint constraint_unique_users_type_email unique (type,email);",
"users_unique_3":"alter table users add constraint constraint_unique_users_type_mobile unique (type,mobile);",
"users_unique_4":"alter table users add constraint constraint_unique_users_type_google_id unique (type,google_id);",
"users_unique_5":"alter table report_user add constraint constraint_unique_report_user unique (created_by_id,user_id);",
"users_unique_6":"alter table users add constraint constraint_unique_users_type_username_bigint unique (type,username_bigint);",
}
}
