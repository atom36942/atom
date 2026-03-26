#postgres
config_postgres_url=None
config_postgres_min_connection=5
config_postgres_max_connection=20
config_postgres_is_extension=1
config_postgres_is_match_column=0

#redis
config_redis_url=None
config_redis_url_ratelimiter=config_redis_url

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
config_kafka_enable_auto_commit=True
config_kafka_consumer_batch=100

#token
config_token_secret_key="123"
config_token_expiry_sec=3*24*60*60
config_token_refresh_expiry_sec=3*24*60*60*100
config_token_key_list=['id', 'type', 'is_active', 'role']

#gsheet
config_gsheet_service_account_json_path=None
config_gsheet_scope_list=['https://www.googleapis.com/auth/spreadsheets']

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
config_s3_presigned_expire_sec=60

#sftp
config_sftp_auth_method="password"
config_sftp_host=None
config_sftp_port=None
config_sftp_username=None
config_sftp_password=None
config_sftp_key_path=None

#cors
config_cors_origin_list=['*']
config_cors_method_list=['*']
config_cors_headers_list=['*']
config_cors_allow_credentials=False

#table
config_table_create_my_list=['test', 'post', 'support', 'rating_test']
config_table_create_public_list=['test', 'support']
config_table_read_public_list=['test', 'post']
config_table_system_list=['spatial_ref_sys']

#column
config_column_blocked_list=['is_active', 'is_verified', 'role', 'created_at', 'updated_at']
config_column_single_update_list=['username', 'password', 'email', 'mobile']

#mode
config_mode_check_active="token"
config_mode_check_admin="token"

#switch
config_is_signup=1
config_is_log_api=1
config_is_traceback=1
config_is_prometheus=0
config_is_reset_export_folder=1
config_is_debug_fastapi=1
config_is_index_html=0
config_is_profile_metadata=0

#zzz
config_key_root="123"
config_auth_type_list=[1, 2, 3]
config_expiry_sec_otp=600
config_limit_ids_delete=1000
config_google_login_client_id=None
config_mongodb_url=None
config_openai_key=None
config_searchapi_key=None
config_gemini_key=None
config_sentry_dsn=None

#dict
config_sql={
"cache_users_role":"select id,role from users where role is not null limit 1000",
"cache_users_is_active":"select id,is_active from users limit 1000",
"profile_metadata":{"test_count":"select count(*) from test where created_by_id=$1","test_object":"select * from test where created_by_id=$1 limit 1"},
}

config_table={
"test":{"buffer":3},
"log_api":{"retention_day":30,"buffer":3},
"log_users_password":{"retention_day":90},
"otp":{"retention_day":365},
}

config_api={
"/admin/object-create":{"role_allowed":[1]},
"/admin/object-update":{"role_allowed":[1]},
"/admin/object-read":{"role_allowed":[1]},
"/admin/ids-delete":{"role_allowed":[1]},
"/test":{"role_allowed":[1,2,3],"is_token":0,"is_active_check":0,"cache_sec":["redis",0],"ratelimiter_times_sec":[10,3]},
"/public/object-read":{"role_allowed":[1],"cache_sec":["inmemory",60]},
"/my/profile":{"role_allowed":[1],"is_active_check":0,"cache_sec":["inmemory",10]},
"/my/object-read":{"role_allowed":[1],"cache_sec":["inmemory",60]},
"/public/info":{"role_allowed":[1],"cache_sec":["inmemory",10]},
"/public/table-tag-read":{"role_allowed":[1],"cache_sec":["redis",10]},
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
{"name":"email_communication","datatype":"text"},
{"name":"mobile_communication","datatype":"text"},
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
"sql":{
"drop_disable_table_1":"CREATE OR REPLACE FUNCTION func_drop_disable_table() RETURNS event_trigger LANGUAGE plpgsql AS $$ DECLARE r record; BEGIN FOR r IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP IF r.object_type='table' THEN RAISE EXCEPTION 'DROP TABLE not allowed: %',r.object_identity; END IF; END LOOP; END; $$;",
"drop_disable_table_2":"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtname = 'trigger_drop_disable_table') THEN CREATE EVENT TRIGGER trigger_drop_disable_table ON sql_drop EXECUTE FUNCTION func_drop_disable_table(); END IF; END $$;",
"truncate_disable_1":"CREATE OR REPLACE FUNCTION func_truncate_disable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'TRUNCATE not allowed on %',TG_TABLE_NAME; END; $$;",
"truncate_disable_2":"DO $$ DECLARE r record; BEGIN FOR r IN SELECT schemaname,tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT IN ('spatial_ref_sys', 'geometry_columns', 'geography_columns') LOOP EXECUTE format('CREATE TRIGGER trigger_truncate_disable_%s BEFORE TRUNCATE ON %I.%I EXECUTE FUNCTION func_truncate_disable();',r.tablename,r.schemaname,r.tablename); END LOOP; END $$;",
"root_user_1":"INSERT INTO users (type,username,password,role) VALUES (1,'atom','a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',1) ON CONFLICT DO NOTHING;",
"root_user_2":"CREATE OR REPLACE FUNCTION func_delete_disable_root_user() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE v_root_id INT:=TG_ARGV[0]::INT; BEGIN IF OLD.id=v_root_id THEN RAISE EXCEPTION 'delete not allowed for root user (id=%)',v_root_id; END IF; RETURN OLD; END; $$;",
"root_user_3":"CREATE TRIGGER trigger_delete_disable_root_user BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_root_user(1);",
"log_users_password_1":"CREATE OR REPLACE FUNCTION func_log_users_password() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN INSERT INTO log_users_password(user_id,password) VALUES(OLD.id,OLD.password); RETURN NEW; END; $$;",
"log_users_password_2":"CREATE TRIGGER trigger_log_users_password AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION func_log_users_password();",
"is_protected_1":"CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected=1 THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %',TG_TABLE_NAME; END IF; RETURN OLD; END; $$;",
"is_protected_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public' AND table_name NOT IN ('spatial_ref_sys')) LOOP EXECUTE FORMAT('CREATE TRIGGER trigger_delete_disable_is_protected_%I BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected();',tbl.table_name,tbl.table_name); END LOOP; END $$;",
"soft_delete_1":"CREATE OR REPLACE FUNCTION func_users_soft_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; BEGIN FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'is_deleted') THEN RAISE EXCEPTION 'Table %.% missing is_deleted column', r.table_schema, r.table_name; END IF; EXECUTE format('UPDATE %I.%I SET is_deleted = 1 WHERE %I = $1', r.table_schema, r.table_name, r.column_name) USING NEW.id; END LOOP; RETURN NEW; END; $$;",
"soft_delete_2":"CREATE TRIGGER trigger_users_soft_delete AFTER UPDATE ON users FOR EACH ROW WHEN (NEW.is_deleted = 1) EXECUTE FUNCTION func_users_soft_delete();",
"hard_delete_1":"CREATE OR REPLACE FUNCTION func_users_hard_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; BEGIN FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP EXECUTE format('DELETE FROM %I.%I WHERE %I = $1', r.table_schema, r.table_name, r.column_name) USING OLD.id; END LOOP; RETURN OLD; END; $$;",
"hard_delete_2":"CREATE TRIGGER trigger_users_hard_delete AFTER DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_users_hard_delete();",
"delete_disable_role_1":"CREATE OR REPLACE FUNCTION func_delete_disable_users_role() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL THEN RAISE EXCEPTION 'DELETE not allowed for user with role'; END IF; RETURN OLD; END; $$;",
"delete_disable_role_2":"CREATE TRIGGER trigger_delete_disable_users_role BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_users_role();",
"updated_at_default_1":"CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$;",
"updated_at_default_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public' AND table_name NOT IN ('spatial_ref_sys')) LOOP EXECUTE FORMAT('CREATE TRIGGER trigger_set_updated_at_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION func_set_updated_at();',tbl.table_name,tbl.table_name); END LOOP; END $$;",
"delete_disable_bulk_1":"CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$;",
"delete_disable_bulk_2":"CREATE TRIGGER trigger_delete_disable_bulk_users AFTER DELETE ON users REFERENCING OLD TABLE AS deleted_rows FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_bulk(1);",
"delete_disable_table_1":"CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'delete not allowed on %',TG_TABLE_NAME; END; $$;",
"delete_disable_table_2":"0 DO $$DECLARE r RECORD; BEGIN FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT IN ('spatial_ref_sys') LOOP IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trigger_delete_disable_'||r.tablename) THEN EXECUTE format('CREATE TRIGGER trigger_delete_disable_%I BEFORE DELETE ON public.%I FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table();',r.tablename,r.tablename); END IF; END LOOP; END$$;",
"delete_disable_table_3":"0 CREATE TRIGGER trigger_delete_disable_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table();"
}
}

#override
from function import func_config_override_from_env
func_config_override_from_env(globals())
