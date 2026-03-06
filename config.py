#import
from function import *

#env
import os
from dotenv import load_dotenv
load_dotenv()

#project
config_project_name=os.getenv("config_project_name") or "atom"
config_folder_export=os.getenv("config_folder_export") or "export"
config_folder_static=os.getenv("config_folder_static") or "static"
config_folder_html=os.getenv("config_folder_html") or "static"
config_folder_router=os.getenv("config_folder_router") or "router"
config_index_html=os.getenv("config_index_html") or "social"
config_file_router_prefix=os.getenv("config_file_router_prefix") or "router"

#postgres
config_postgres_url=os.getenv("config_postgres_url")
config_postgres_min_connection=int(os.getenv("config_postgres_min_connection") or 5)
config_postgres_max_connection=int(os.getenv("config_postgres_max_connection") or 20)

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
config_kafka_consumer_batch=int(os.getenv("config_kafka_consumer_batch") or 100)

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

#otp
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
config_searchapi_key=os.getenv("config_searchapi_key")
config_gemini_key=os.getenv("config_gemini_key")

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
config_is_reset_export_folder=int(os.getenv("config_is_reset_export_folder") or 1)
config_is_debug_fastapi=int(os.getenv("config_is_debug_fastapi") or 1)
config_postgres_is_extension=int(os.getenv("config_postgres_is_extension") or 1)
config_postgres_is_match_column=int(os.getenv("config_postgres_is_match_column") or 0)
config_is_index_html=int(os.getenv("config_is_index_html") or 0)
config_is_profile_metadata=int(os.getenv("config_is_profile_metadata") or 0)

#table/column
config_table_create_my_list=(os.getenv("config_table_create_my_list") or "test,post,support,rating_test").split(",")
config_table_create_public_list=(os.getenv("config_table_create_public_list") or "test,support").split(",")
config_table_read_public_list=(os.getenv("config_table_read_public_list") or "test,post").split(",")
config_column_blocked_list=(os.getenv("config_column_blocked_list") or "is_active,is_verified,api_id_access,created_at,updated_at").split(",")

#token
config_token_expiry_sec=int(os.getenv("config_token_expiry_sec") or 3*24*60*60)
config_token_user_key_list=(os.getenv("config_token_user_key_list") or "id,type,is_active,api_id_access").split(",")

#zzz
config_mode_check_is_active=os.getenv("config_mode_check_is_active") or "token"
config_mode_check_is_admin=os.getenv("config_mode_check_is_admin") or "token"
config_auth_type_list=list(map(int,(os.getenv("config_auth_type_list") or "1,2,3").split(",")))
config_expiry_sec_otp=int(os.getenv("config_expiry_sec_otp") or 600)
config_limit_ids_delete=int(os.getenv("config_limit_ids_delete") or 1000)

#dict
config_sql={
"cache_users_api_id_access":"select id,api_id_access from users where api_id_access is not null limit 1000",
"cache_users_is_active":"select id,is_active from users limit 1000",
"user":{"test_count":"select count(*) from test where created_by_id=$1","test_object":"select * from test where created_by_id=$1 limit 1"},
}

config_table={
"test":{"buffer":3},
"log_api":{"retention_day":30,"buffer":3},
"log_users_password":{"retention_day":90},
"otp":{"retention_day":365},
}

config_api={
"/admin/object-create":{"id":1},
"/admin/object-update":{"id":2},
"/admin/object-read":{"id":3},
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
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","index":"btree"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_active","datatype":"smallint","index":"btree","in":(0,1)},
{"name":"is_verified","datatype":"smallint","in":(0,1)},
{"name":"is_deleted","datatype":"smallint","in":(0,1)},
{"name":"is_protected","datatype":"smallint","in":(0,1)},
{"name":"type","datatype":"integer","index":"btree"},
{"name":"title","datatype":"text","index":"btree,gin","is_mandatory":1},
{"name":"description","datatype":"text"},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin","regex":"^[a-z0-9_@-]*$"},
{"name":"tag_int","datatype":"integer[]","index":"gin"},
{"name":"tag_bigint","datatype":"bigint[]","index":"gin"},
{"name":"rating","datatype":"numeric(3,1)"},
{"name":"remark","datatype":"text"},
{"name":"location","datatype":"geography(point)","index":"gist"},
{"name":"dob","datatype":"date"},
{"name":"is_public","datatype":"boolean"},
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
{"name":"is_active","datatype":"smallint","index":"btree"},
{"name":"is_verified","datatype":"smallint","index":"btree"},
{"name":"is_deleted","datatype":"smallint","index":"btree"},
{"name":"is_protected","datatype":"smallint","index":"btree"},
{"name":"type","datatype":"integer","is_mandatory":1,"index":"btree"},
{"name":"username","datatype":"text","index":"btree","unique":"username,type","regex":"^(?=.{3,20}$)[a-z][a-z0-9_@-]*$"},
{"name":"password","datatype":"text","index":"btree"},
{"name":"username_bigint","datatype":"bigint","index":"btree","unique":"username_bigint,type"},
{"name":"password_bigint","datatype":"bigint","index":"btree"},
{"name":"google_login_id","datatype":"text","index":"btree","unique":"google_login_id,type"},
{"name":"google_login_metadata","datatype":"jsonb"},
{"name":"email","datatype":"text","index":"btree","unique":"email,type"},
{"name":"mobile","datatype":"text","index":"btree","unique":"mobile,type"},
{"name":"api_id_access","datatype":"text"},
{"name":"last_active_at","datatype":"timestamptz"},
{"name":"name","datatype":"text"},
{"name":"country","datatype":"text"},
{"name":"state","datatype":"text"},
{"name":"city","datatype":"text"},
{"name":"email_communication","datatype":"text"},
{"name":"mobile_communication","datatype":"text"},
],
"log_api":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"created_by_id","datatype":"bigint","index":"btree"},
{"name":"type","datatype":"integer"},
{"name":"ip_address","datatype":"text"},
{"name":"api","datatype":"text","index":"btree"},
{"name":"api_id","datatype":"smallint"},
{"name":"method","datatype":"text"},
{"name":"query_param","datatype":"text"},
{"name":"status_code","datatype":"smallint","index":"btree"},
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
{"name":"user_id","datatype":"bigint"},
{"name":"password","datatype":"text"}
],
"message":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"is_deleted","datatype":"smallint","index":"btree"},
{"name":"user_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"is_read","datatype":"smallint","index":"btree"}
],
"report_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree","unique":"created_by_id,test_id"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree"}
],
"rating_test":[
{"name":"created_at","datatype":"timestamptz","default":"now()"},
{"name":"created_by_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"test_id","datatype":"bigint","is_mandatory":1,"index":"btree"},
{"name":"rating","datatype":"numeric(3,1)","is_mandatory":1}
],
"support":[
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree"},
{"name":"updated_at","datatype":"timestamptz"},
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
{"name":"is_active","datatype":"smallint","index":"btree","in":(0,1)},
{"name":"is_verified","datatype":"smallint"},
{"name":"is_deleted","datatype":"smallint"},
{"name":"type","datatype":"integer","index":"btree"},
{"name":"title","datatype":"text"},
{"name":"description","datatype":"text","is_mandatory":1},
{"name":"file_url","datatype":"text"},
{"name":"link_url","datatype":"text"},
{"name":"tag","datatype":"text[]","index":"gin"},
],
},
"sql":{
"drop_disable_table_1":"CREATE OR REPLACE FUNCTION func_drop_disable_table() RETURNS event_trigger LANGUAGE plpgsql AS $$ DECLARE r record; BEGIN FOR r IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP IF r.object_type='table' THEN RAISE EXCEPTION 'DROP TABLE not allowed: %',r.object_identity; END IF; END LOOP; END; $$;",
"drop_disable_table_2":"DROP EVENT TRIGGER IF EXISTS trigger_drop_disable_table; CREATE EVENT TRIGGER trigger_drop_disable_table ON sql_drop EXECUTE FUNCTION func_drop_disable_table();",
"truncate_disable_1":"CREATE OR REPLACE FUNCTION func_truncate_disable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'TRUNCATE not allowed on %',TG_TABLE_NAME; END; $$;",
"truncate_disable_2":"DO $$ DECLARE r record; BEGIN FOR r IN SELECT schemaname,tablename FROM pg_tables WHERE schemaname='public' LOOP EXECUTE format('DROP TRIGGER IF EXISTS trigger_truncate_disable_%s ON %I.%I;',r.tablename,r.schemaname,r.tablename); EXECUTE format('CREATE TRIGGER trigger_truncate_disable_%s BEFORE TRUNCATE ON %I.%I EXECUTE FUNCTION func_truncate_disable();',r.tablename,r.schemaname,r.tablename); END LOOP; END $$;",
"root_user_1":"INSERT INTO users (type,username,password,api_id_access) VALUES (1,'atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3','1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50') ON CONFLICT DO NOTHING;",
"root_user_2":"CREATE OR REPLACE FUNCTION func_delete_disable_root_user() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE v_root_id INT:=TG_ARGV[0]::INT; BEGIN IF OLD.id=v_root_id THEN RAISE EXCEPTION 'delete not allowed for root user (id=%)',v_root_id; END IF; RETURN OLD; END; $$;",
"root_user_3":"DROP TRIGGER IF EXISTS trigger_delete_disable_root_user ON users; CREATE TRIGGER trigger_delete_disable_root_user BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_root_user(1);",
"log_users_password_1":"CREATE OR REPLACE FUNCTION func_log_users_password() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN INSERT INTO log_users_password(user_id,password) VALUES(OLD.id,OLD.password); RETURN NEW; END; $$;",
"log_users_password_2":"DROP TRIGGER IF EXISTS trigger_log_users_password ON users; CREATE TRIGGER trigger_log_users_password AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION func_log_users_password();",
"is_protected_1":"CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected=1 THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %',TG_TABLE_NAME; END IF; RETURN OLD; END; $$;",
"is_protected_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('DROP TRIGGER IF EXISTS trigger_delete_disable_is_protected_%I ON %I;',tbl.table_name,tbl.table_name); EXECUTE FORMAT('CREATE TRIGGER trigger_delete_disable_is_protected_%I BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected();',tbl.table_name,tbl.table_name); END LOOP; END $$;",
"updated_at_default_1":"CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$;",
"updated_at_default_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public') LOOP EXECUTE FORMAT('DROP TRIGGER IF EXISTS trigger_set_updated_at_%I ON %I;',tbl.table_name,tbl.table_name); EXECUTE FORMAT('CREATE TRIGGER trigger_set_updated_at_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION func_set_updated_at();',tbl.table_name,tbl.table_name); END LOOP; END $$;",
"delete_disable_bulk_1":"CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$;",
"delete_disable_bulk_2":"DROP TRIGGER IF EXISTS trigger_delete_disable_bulk_users ON users; CREATE TRIGGER trigger_delete_disable_bulk_users AFTER DELETE ON users REFERENCING OLD TABLE AS deleted_rows FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_bulk(1);",
"delete_disable_1":"CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'delete not allowed on %',TG_TABLE_NAME; END; $$;",
"delete_disable_2":"DROP TRIGGER IF EXISTS trigger_delete_disable_users ON users; CREATE TRIGGER trigger_delete_disable_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table();",
}
}

#func
func_list_to_tuple(globals())

