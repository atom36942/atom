#import
from copy import deepcopy
from config import config_postgres as base_config_postgres
from config import config_api as base_config_api
from config import config_column_int_mapping as base_int_mapping

#column int mapping
config_column_int_mapping = {
**base_int_mapping,
"users": {
**base_int_mapping["users"],
"role": {1: "Admin", 4: "Pulse", 10: "MDM", 11: "WiseTech"},
},
"task": {
"project": {1: "Myshipment", 2: "Portal", 3: "Hirex", 4: "OBhai", 5: "Amazon", 6: "Quotation", 7: "Tradelane", 8: "Misc"},
"status": {1: "To Do", 2: "In Progress", 3: "Blocked", 4: "Review", 5: "Done"},
},
"jobseeker": {
"worker_status": {None: "Pending", 1: "Processing", 2: "Completed", 3: "Failed", 4: "Dead"},
},
}

# config postgres
config_postgres = deepcopy(base_config_postgres)
config_postgres["table"].update({
"jobseeker":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"verified_at","datatype":"timestamptz"},
{"name":"verified_by_id","datatype":"bigint"},
{"name":"deactivated_at","datatype":"timestamptz"},
{"name":"deactivated_by_id","datatype":"bigint"},
{"name":"deleted_at","datatype":"timestamptz"},
{"name":"deleted_by_id","datatype":"bigint"},
{"name":"profile","datatype":"text","index":"btree(profile)|gin_trgm(profile)"},
{"name":"name","datatype":"text"},
{"name":"email","datatype":"text"},
{"name":"college","datatype":"text[]"},
{"name":"resume_url","datatype":"text"},
{"name":"resume_content","datatype":"text"},
{"name":"video_url","datatype":"text"},
{"name":"skills","datatype":"text[]"},
{"name":"experience","datatype":"numeric(4,1)"},
{"name":"company_current","datatype":"text"},
{"name":"company_past","datatype":"text[]"},
{"name":"ctc_current","datatype":"integer"},
{"name":"ctc_expected","datatype":"integer"},
{"name":"currency","datatype":"text"},
{"name":"notice_period_days","datatype":"integer"},
{"name":"location_current","datatype":"text"},
{"name":"location_preferred","datatype":"text[]"},
{"name":"qualification_highest","datatype":"text"},
{"name":"source","datatype":"text"},
{"name":"linkedin_url","datatype":"text"},
{"name":"github_url","datatype":"text"},
{"name":"portfolio_url","datatype":"text"},
{"name":"languages","datatype":"text[]"},
{"name":"gender","datatype":"text"},
{"name":"worker_status","datatype":"smallint","in":(1,2,3,4),"index":"btree(worker_status,worker_next_retry_at,created_at)"},
{"name":"worker_retry_count","datatype":"integer","default":0},
{"name":"worker_next_retry_at","datatype":"timestamptz","default":"now()"},
{"name":"worker_processed_at","datatype":"timestamptz"},
{"name":"worker_last_error","datatype":"text"},
{"name":"ai_remark","datatype":"text"},
{"name":"ai_rating","datatype":"numeric(3,1)"},
{"name":"remark","datatype":"text"},
{"name":"rating","datatype":"numeric(3,1)"},
{"name":"status","datatype":"smallint","default":1},
{"name":"mobile","datatype":"text"},
{"name":"work_authorization","datatype":"text"},
{"name":"graduation_year","datatype":"integer"},
{"name":"certifications","datatype":"jsonb"},
{"name":"summary","datatype":"text"},
{"name":"projects","datatype":"jsonb",},
{"name":"industry","datatype":"text"}
],
"task":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(created_by_id,id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"project","datatype":"smallint","is_mandatory": True,"index":"btree(project,status,id)"},
{"name":"status","datatype":"smallint","is_mandatory": True,"default":1,"index":"btree(status,id)"},
{"name":"assigned_to_id","datatype":"bigint","is_mandatory": True,"index":"btree(assigned_to_id,id)"},
{"name":"due_date","datatype":"date","index":"btree(due_date)"},
{"name":"tags","datatype":"text[]","index":"gin(tags)"},
{"name":"link_url","datatype":"text"},
{"name":"title","datatype":"varchar(100)","is_mandatory": True,"index":"gin_trgm(title)"},
{"name":"description","datatype":"text"},
],
"task_comment":[
{"name":"id","datatype":"bigint","identity":"always","is_primary": True},
{"name":"created_at","datatype":"timestamptz","default":"now()","index":"btree(created_at)"},
{"name":"created_by_id","datatype":"bigint","is_mandatory": True,"index":"btree(created_by_id)"},
{"name":"updated_at","datatype":"timestamptz"},
{"name":"updated_by_id","datatype":"bigint"},
{"name":"task_id","datatype":"bigint","is_mandatory": True,"index":"btree(task_id,id)"},
{"name":"description","datatype":"text","is_mandatory": True}
],
})

# config api
config_api = {
**base_config_api,
# mdm
"/mdm/read": {"id": 114, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [10]}},
"/mdm/review": {"id": 115, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [10]}},
"/mdm/export": {"id": 116, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [10]}},
# wisetech
"/wisetech/reference": {"id": 118, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [11]}},
"/wisetech/search": {"id": 119, "is_token": True, "user_check_role": {"mode": "realtime", "roles": [11]}},
}
