#env
import os
from dotenv import load_dotenv
load_dotenv()
postgres_url=os.getenv("postgres_url")
redis_url=os.getenv("redis_url")
key_jwt=os.getenv("key_jwt")
key_root=os.getenv("key_root")
valkey_url=os.getenv("valkey_url")
sentry_dsn=os.getenv("sentry_dsn")
mongodb_url=os.getenv("mongodb_url")
rabbitmq_url=os.getenv("rabbitmq_url")
lavinmq_url=os.getenv("lavinmq_url")
kafka_url=os.getenv("kafka_url")
kafka_path_cafile=os.getenv("kafka_path_cafile")
kafka_path_certfile=os.getenv("kafka_path_certfile")
kafka_path_keyfile=os.getenv("kafka_path_keyfile")
aws_access_key_id=os.getenv("aws_access_key_id")
aws_secret_access_key=os.getenv("aws_secret_access_key")
s3_region_name=os.getenv("s3_region_name")
sns_region_name=os.getenv("sns_region_name")
ses_region_name=os.getenv("ses_region_name")
ses_sender_email=os.getenv("ses_sender_email")
google_client_id=os.getenv("google_client_id")
is_signup=int(os.getenv("is_signup",0))
postgres_url_read=os.getenv("postgres_url_read")
channel_name=os.getenv("channel_name","ch1")
user_type_allowed=[int(x) for x in os.getenv("user_type_allowed","1,2,3").split(",")]
column_disabled_non_admin=os.getenv("column_disabled_non_admin","is_active,is_verified,api_access").split(",")

#variable
api_id={
"/admin/db-runner":1,
"/admin/user-create":2,
"/admin/object-create":3,
"/admin/user-update":4,
"/admin/object-update":5,
"/admin/ids-update":6,
"/admin/ids-delete":7,
"/admin/object-read":8
}
postgres_schema_default={
"table":{
"test":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-smallint-0-btree",
"title-text-0-0",
"description-text-0-0",
"file_url-text-0-0",
"link_url-text-0-0",
"tag-text-0-0",
"rating-numeric(10,3)-0-0",
"remark-text-0-gin,btree",
"location-geography(POINT)-0-gist",
"metadata-jsonb-0-0"
],
"log_api":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"api-text-0-0",
"method-text-0-0",
"query_param-text-0-0",
"status_code-smallint-0-0",
"response_time_ms-numeric(1000,3)-0-0",
"description-text-0-0"
],
"otp":[
"created_at-timestamptz-0-brin",
"otp-integer-1-0",
"email-text-0-btree",
"mobile-text-0-btree"
],
"log_password":[
"created_at-timestamptz-0-0",
"user_id-bigint-0-0",
"password-text-0-0"
],
"users":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-0",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_verified-smallint-0-btree",
"is_deleted-smallint-0-btree",
"is_protected-smallint-0-btree",
"type-smallint-1-btree",
"username-text-0-btree",
"password-text-0-btree",
"google_id-text-0-btree",
"google_data-jsonb-0-0",
"email-text-0-btree",
"mobile-text-0-btree",
"api_access-text-0-0",
"last_active_at-timestamptz-0-0"
],
"message":[
"created_at-timestamptz-0-brin",
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
],
"bookmark_workseeker":[
"created_at-timestamptz-0-0",
"created_by_id-bigint-1-btree",
"workseeker_id-bigint-1-btree"
],
"work_profile":[
"title-text-1-0"
],
"workseeker":[
"created_at-timestamptz-0-brin",
"updated_at-timestamptz-0-0",
"created_by_id-bigint-0-btree",
"updated_by_id-bigint-0-0",
"is_active-smallint-0-btree",
"is_deleted-smallint-0-btree",
"type-smallint-0-btree",
"work_profile_id-int-0-btree",
"experience-numeric(10,1)-0-btree",
"skill-text-0-0",
"description-text-0-0",
"salary_currency-text-0-0",
"salary_current-int-0-0",
"salary_expected-int-0-0",
"notice_period-smallint-0-0",
"college-text-0-0",
"degree-text-0-0",
"industry-text-0-0",
"certification-text-0-0",
"achievement-text-0-0",
"hobby-text-0-0",
"life_goal-text-0-0",
"strong_point-text-0-0",
"weak_point-text-0-0",
"name-text-0-0",
"gender-text-0-0",
"date_of_birth-date-0-0",
"nationality-text-0-0",
"language-text-0-0",
"email-text-0-0",
"mobile-text-0-0",
"country-text-0-0",
"state-text-0-0",
"city-text-0-0",
"current_location-text-0-0",
"is_remote-smallint-0-0",
"linkedin_url-text-0-0",
"github_url-text-0-0",
"portfolio_url-text-0-0",
"website_url-text-0-0",
"resume_url-text-0-0"
]
},
"query":{
"drop_all_index":"0 DO $$ DECLARE r RECORD; BEGIN FOR r IN (SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'index_%') LOOP EXECUTE 'DROP INDEX IF EXISTS public.' || quote_ident(r.indexname); END LOOP; END $$;",
"default_created_at":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='created_at' AND table_schema='public') LOOP EXECUTE FORMAT('ALTER TABLE ONLY %I ALTER COLUMN created_at SET DEFAULT NOW();', tbl.table_name); END LOOP; END $$;",
"default_updated_at_1":"create or replace function function_set_updated_at_now() returns trigger as $$ begin new.updated_at=now(); return new; end; $$ language 'plpgsql';",
"default_updated_at_2":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='updated_at' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE TRIGGER trigger_set_updated_at_now_%I BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION function_set_updated_at_now();', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"is_protected":"DO $$ DECLARE tbl RECORD; BEGIN FOR tbl IN (SELECT table_name FROM information_schema.columns WHERE column_name='is_protected' AND table_schema='public') LOOP EXECUTE FORMAT('CREATE OR REPLACE RULE rule_protect_%I AS ON DELETE TO %I WHERE OLD.is_protected=1 DO INSTEAD NOTHING;', tbl.table_name, tbl.table_name); END LOOP; END $$;",
"delete_disable_bulk_1":"create or replace function function_delete_disable_bulk() returns trigger language plpgsql as $$declare n bigint := tg_argv[0]; begin if (select count(*) from deleted_rows) <= n is not true then raise exception 'cant delete more than % rows', n; end if; return old; end;$$;",
"delete_disable_bulk_2":"create or replace trigger trigger_delete_disable_bulk_users after delete on users referencing old table as deleted_rows for each statement execute procedure function_delete_disable_bulk(1);",
"log_password_1":"CREATE OR REPLACE FUNCTION function_log_password_change() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$ BEGIN IF OLD.password <> NEW.password THEN INSERT INTO log_password(user_id,password) VALUES(OLD.id,OLD.password); END IF; RETURN NEW; END; $$;",
"log_password_2":"CREATE OR REPLACE TRIGGER trigger_log_password_change AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.password IS DISTINCT FROM NEW.password) EXECUTE FUNCTION function_log_password_change();",
"root_user_1":"insert into users (type,username,password,api_access) values (1,'atom','5994471abb01112afcc18159f6cc74b4f511b99806da59b3caf5a9c173cacfc5','1,2,3,4,5,6,7,8,9,10') on conflict do nothing;",
"root_user_2":"create or replace rule rule_delete_disable_root_user as on delete to users where old.id=1 do instead nothing;",
"default_1":"0 alter table users alter column is_active set default 1;",
"unique_1":"alter table users add constraint constraint_unique_users_type_username unique (type,username);",
"unique_2":"alter table users add constraint constraint_unique_users_type_google_id unique (type,google_id);",
"unique_3":"alter table users add constraint constraint_unique_users_type_email unique (type,email);",
"unique_4":"alter table users add constraint constraint_unique_users_type_mobile unique (type,mobile);",
"unique_5":"alter table workseeker add constraint constraint_unique_created_by_id unique (created_by_id);",
"unique_6":"alter table report_user add constraint constraint_unique_report_user unique (created_by_id,user_id);",
"unique_7":"alter table bookmark_workseeker add constraint constraint_unique_bookmark_workseeker unique (created_by_id,workseeker_id);",
"check_1":"alter table users add constraint constraint_check_users_username check (username = lower(username) and username not like '% %' and trim(username) = username);",
"check_2":"DO $$ DECLARE r RECORD; constraint_name TEXT; BEGIN FOR r IN (SELECT c.table_name FROM information_schema.columns c JOIN pg_class p ON c.table_name = p.relname JOIN pg_namespace n ON p.relnamespace = n.oid WHERE c.column_name = 'is_active' AND c.table_schema = 'public' AND p.relkind = 'r') LOOP constraint_name := format('constraint_check_%I_is_active', r.table_name); IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = constraint_name) THEN EXECUTE format('ALTER TABLE %I ADD CONSTRAINT %I CHECK (is_active IN (0,1) OR is_active IS NULL);', r.table_name, constraint_name); END IF; END LOOP; END $$;"
}
}
