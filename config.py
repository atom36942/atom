#env
import os
from dotenv import load_dotenv
load_dotenv()

#postgres
config_postgres_url=os.getenv("config_postgres_url")
config_postgres_url_read=os.getenv("config_postgres_url_read")
config_postgres_min_connection=int(os.getenv("config_postgres_min_connection") or 5)
config_postgres_max_connection=int(os.getenv("config_postgres_max_connection") or 20)

#redis
config_redis_url=os.getenv("config_redis_url")
config_redis_url_ratelimiter=os.getenv("config_redis_url_ratelimiter") or config_redis_url

#celery
config_celery_broker_url=os.getenv("config_celery_broker_url")
config_celery_backend_url=os.getenv("config_celery_backend_url")

#kafka
config_kafka_url=os.getenv("config_kafka_url")
config_kafka_username=os.getenv("config_kafka_username")
config_kafka_password=os.getenv("config_kafka_password")

#rabbitmq
config_rabbitmq_url=os.getenv("config_rabbitmq_url")

#redis pubsub
config_redis_pubsub_url=os.getenv("config_redis_pubsub_url")

#sentry
config_sentry_dsn=os.getenv("config_sentry_dsn")

#mongodb
config_mongodb_url=os.getenv("config_mongodb_url")

#openai
config_openai_key=os.getenv("config_openai_key")

#gogole login
config_google_login_client_id=os.getenv("config_google_login_client_id")

#fast2sms
config_fast2sms_url=os.getenv("config_fast2sms_url")
config_fast2sms_key=os.getenv("config_fast2sms_key")

#resend
config_resend_url=os.getenv("config_resend_url")
config_resend_key=os.getenv("config_resend_key")

#posthog
config_posthog_project_host=os.getenv("config_posthog_project_host")
config_posthog_project_key=os.getenv("config_posthog_project_key")

#aws
config_aws_access_key_id=os.getenv("config_aws_access_key_id")
config_aws_secret_access_key=os.getenv("config_aws_secret_access_key")
config_s3_region_name=os.getenv("config_s3_region_name")
config_sns_region_name=os.getenv("config_sns_region_name")
config_ses_region_name=os.getenv("config_ses_region_name")
config_limit_s3_kb=int(os.getenv("config_limit_s3_kb") or 100)
config_s3_presigned_expire_sec=int(os.getenv("config_s3_presigned_expire_sec") or 60)

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

#key
config_key_jwt=os.getenv("config_key_jwt")
config_key_root=os.getenv("config_key_root")

#token
config_token_expire_sec=int(os.getenv("config_token_expire_sec") or 365*24*60*60)
config_token_user_key_list=(os.getenv("config_token_user_key_list") or "id,type,is_active,api_access").split(",")

#check active
config_mode_check_is_active=os.getenv("config_mode_check_is_active") or "token"
config_limit_cache_users_is_active=int(os.getenv("config_limit_cache_users_is_active") or 10)

#check admin
config_mode_check_api_access=os.getenv("config_mode_check_api_access") or "token"
config_limit_cache_users_api_access=int(os.getenv("config_limit_cache_users_api_access") or 10)

#public
config_public_table_create_list=(os.getenv("config_public_table_create_list") or "test").split(",")
config_public_table_read_list=(os.getenv("config_public_table_read_list") or "test").split(",")

#zzz
config_auth_type_list=list(map(int,(os.getenv("config_auth_type_list") or "1,2,3").split(",")))
config_column_disabled_list=(os.getenv("config_column_disabled_list") or "is_active,is_verified,api_access").split(",")
config_limit_ids_delete=int(os.getenv("config_limit_ids_delete") or 100)

#dict
config_user_count_query={
"log_api_count":"select count(*) from log_api where created_by_id=$1",
"test_count":"select count(*) from test where created_by_id=$1"
}
config_postgres_clean={
"log_api":365,
"otp":365,
}
config_api={
"/admin/object-create":{"id":1},
"/admin/object-update":{"id":2},
"/admin/object-read":{"id":3},
"/admin/ids-update":{"id":4},
"/admin/ids-delete":{"id":5},
"/test":{"id":100,"is_token":0,"is_active_check":0,"cache_sec":["redis",60],"ratelimiter_times_sec":[1,3]},
# "/public/object-read":{"id":101,"cache_sec":["inmemory",60]},
"/my/profile":{"id":102,"is_active_check":1,"cache_sec":["inmemory",10]},
"/my/object-read":{"id":103,"cache_sec":["redis",60]},
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
"dob-date-0-0",
"is_public-boolean-0-btree",
"tags-text[]-0-gin",
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
"created_at_default":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='created_at' AND table_schema='public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"updated_at_default_1":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';",
"updated_at_default_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected=1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"delete_disable_bulk_1":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;",
"delete_disable_bulk_2":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"check_is_active":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_active' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_active', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_active IN (0,1) OR is_active IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_is_verified":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_verified' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_verified', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_verified IN (0,1) OR is_verified IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_is_deleted":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_deleted' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_deleted', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_deleted IN (0,1) OR is_deleted IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"check_is_protected":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_protected' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_protected', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_protected IN (0,1) OR is_protected IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;",
"root_user_1":"insert into users (type,username,password,api_access) values (1,'atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3','1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100') on conflict do nothing;",
"root_user_2":"create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"log_password_1":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;",
"log_password_2":"CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"username_check":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"unique_users_1":"alter table users add constraint constraint_unique_users_type_username unique (type,username);",
"unique_users_2":"alter table users add constraint constraint_unique_users_type_email unique (type,email);",
"unique_users_3":"alter table users add constraint constraint_unique_users_type_mobile unique (type,mobile);",
"unique_users_4":"alter table users add constraint constraint_unique_users_type_google_id unique (type,google_id);",
"unique_users_5":"alter table report_user add constraint constraint_unique_report_user unique (created_by_id,user_id);",
"unique_users_6":"alter table users add constraint constraint_unique_users_type_username_bigint unique (type,username_bigint);",
}
}


