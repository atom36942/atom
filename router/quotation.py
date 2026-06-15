# packages
from datetime import datetime, timezone
import orjson
from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.get("/admin/quotation-bootstrap")
async def func_api_admin_quotation_bootstrap(*, request:Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        access_row = await conn.fetchrow("SELECT id user_id,role,pricing_category,allowed_origins,freight_status status FROM users WHERE id=$1", user_id)
        if not access_row: raise Exception("user not found")
        access, role = dict(access_row), int(access_row["role"])
        if role != 1 and access["status"] != "active": raise Exception("freight access disabled")
        customers = [dict(r) for r in await conn.fetch("SELECT id,code,name,cw_code,pricing_category,currency,kyc_status,credit_status,status FROM freight_customer WHERE status='active' ORDER BY name LIMIT 500")]
        rates = [dict(r) for r in await conn.fetch("SELECT id,created_at,created_by_id,mode,movement,origin,destination,carrier,service,currency,buy_rates,floor_rates,sell_rates_a,sell_rates_b,sell_rates_c,transit_time,valid_from,valid_to,source_reference,status FROM freight_rate WHERE status='draft' ORDER BY id DESC LIMIT 100")] if role in (1,3,4) else []
        exceptions = [dict(r) for r in await conn.fetch("SELECT e.*,q.reference,q.customer_id,q.origin,q.destination,q.total_sell FROM freight_quote_exception e JOIN freight_quote q ON q.id=e.quote_id WHERE e.status='pending' ORDER BY e.id DESC LIMIT 100")] if role in (1,5) else []
        users = [dict(r) for r in await conn.fetch("SELECT id,username,email,name,role,pricing_category,allowed_origins,freight_status FROM users WHERE deleted_at IS NULL AND deactivated_at IS NULL ORDER BY id LIMIT 500")] if role == 1 else []
        access_list = [dict(r) for r in await conn.fetch("SELECT id user_id,username,email,name,role,pricing_category,allowed_origins,freight_status status FROM users WHERE role IS NOT NULL AND deleted_at IS NULL ORDER BY id LIMIT 500")] if role == 1 else []
    for row in rates:
        for key in ("buy_rates","floor_rates","sell_rates_a","sell_rates_b","sell_rates_c"):
            if isinstance(row.get(key), str): row[key] = orjson.loads(row[key])
    user = {**request.state.user,"role":role}
    return {"status":1,"message":{"user":user,"access":access,"customers":customers,"pending_rates":rates,"pending_exceptions":exceptions,"users":users,"access_list":access_list,"mapping":{"role":{1:"Administrator",2:"Sales",3:"Pricing Manager",4:"Rate Approver",5:"Exception Approver"}}}}

@router.post("/admin/quotation-access-save")
async def func_api_admin_quotation_access_save(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("user_id","int",1,None,None),("role","int",1,[2,3,4,5],None),("pricing_category","str",0,["A","B","C"],"B"),("allowed_origins","list",0,None,[]),("status","str",0,["active","disabled"],"active")])
    async with app_state.client_postgres.acquire() as conn:
        row = await conn.fetchrow("UPDATE users SET role=$1,pricing_category=$2,allowed_origins=$3,freight_status=$4,updated_by_id=$5 WHERE id=$6 RETURNING id user_id,role,pricing_category,allowed_origins,freight_status status", ob["role"], ob["pricing_category"], ob["allowed_origins"], ob["status"], request.state.user["id"], ob["user_id"])
        if not row: raise Exception("user not found")
    return {"status":1,"message":dict(row)}

@router.post("/admin/quotation-customer-save")
async def func_api_admin_quotation_customer_save(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("customer_id","int",0,None,None),("name","str",1,None,None),("code","str",0,None,None),("cw_code","str",0,None,None),("pricing_category","str",0,["A","B","C"],"B"),("currency","str",0,None,"USD"),("metadata","dict",0,None,{})])
    async with app_state.client_postgres.acquire() as conn:
        if ob["customer_id"]:
            row = await conn.fetchrow("UPDATE freight_customer SET name=$1,code=$2,cw_code=$3,pricing_category=$4,currency=$5,metadata=$6,updated_by_id=$7 WHERE id=$8 RETURNING *", ob["name"].strip(), ob["code"] or None, ob["cw_code"] or None, ob["pricing_category"], ob["currency"].upper(), orjson.dumps(ob["metadata"]).decode(), request.state.user["id"], ob["customer_id"])
            if not row: raise Exception("customer not found")
        else:
            row = await conn.fetchrow("INSERT INTO freight_customer (created_by_id,code,name,cw_code,sales_owner_id,pricing_category,currency,metadata) VALUES ($1,$2,$3,$4,$1,$5,$6,$7) RETURNING *", request.state.user["id"], ob["code"] or None, ob["name"].strip(), ob["cw_code"] or None, ob["pricing_category"], ob["currency"].upper(), orjson.dumps(ob["metadata"]).decode())
    return {"status":1,"message":dict(row)}

@router.post("/admin/quotation-kyc-save")
async def func_api_admin_quotation_kyc_save(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("customer_id","int",1,None,None),("legal_name","str",1,None,None),("registration_no","str",0,None,None),("tax_no","str",0,None,None),("address","str",0,None,None),("document_blob_ids","list:bigint",0,None,[]),("status","str",0,["pending","approved","rejected"],"pending"),("remark","str",0,None,None)])
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            role = await conn.fetchval("SELECT role FROM users WHERE id=$1", request.state.user["id"])
            status = ob["status"] if role == 1 else "pending"
            if not await conn.fetchval("SELECT id FROM freight_customer WHERE id=$1", ob["customer_id"]): raise Exception("customer not found")
            row = await conn.fetchrow("INSERT INTO freight_kyc (created_by_id,customer_id,legal_name,registration_no,tax_no,address,document_blob_ids,status,reviewed_at,reviewed_by_id,remark) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,CASE WHEN $8<>'pending' THEN now() END,CASE WHEN $8<>'pending' THEN $1::bigint END,$9) RETURNING *", request.state.user["id"], ob["customer_id"], ob["legal_name"], ob["registration_no"] or None, ob["tax_no"] or None, ob["address"] or None, ob["document_blob_ids"], status, ob["remark"] or None)
            await conn.execute("UPDATE freight_customer SET kyc_status=$1,updated_by_id=$2 WHERE id=$3", status, request.state.user["id"], ob["customer_id"])
    return {"status":1,"message":dict(row)}

@router.post("/admin/quotation-credit-save")
async def func_api_admin_quotation_credit_save(*, request:Request):
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("customer_id","int",1,None,None),("currency","str",0,None,"USD"),("requested_limit","float",1,None,None),("requested_days","int",1,None,None),("approved_limit","float",0,None,None),("approved_days","int",0,None,None),("status","str",0,["pending","approved","rejected"],"pending"),("justification","str",0,None,None),("remark","str",0,None,None)])
    if ob["requested_limit"] < 0 or ob["requested_days"] < 0: raise Exception("credit limit and days must be positive")
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            role = await conn.fetchval("SELECT role FROM users WHERE id=$1", request.state.user["id"])
            status = ob["status"] if role == 1 else "pending"
            if not await conn.fetchval("SELECT id FROM freight_customer WHERE id=$1", ob["customer_id"]): raise Exception("customer not found")
            row = await conn.fetchrow("INSERT INTO freight_credit_request (created_by_id,customer_id,currency,requested_limit,requested_days,approved_limit,approved_days,status,decided_at,decided_by_id,justification,remark) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,CASE WHEN $8<>'pending' THEN now() END,CASE WHEN $8<>'pending' THEN $1::bigint END,$9,$10) RETURNING *", request.state.user["id"], ob["customer_id"], ob["currency"].upper(), ob["requested_limit"], ob["requested_days"], ob["approved_limit"], ob["approved_days"], status, ob["justification"] or None, ob["remark"] or None)
            await conn.execute("UPDATE freight_customer SET credit_status=$1,updated_by_id=$2 WHERE id=$3", status, request.state.user["id"], ob["customer_id"])
    return {"status":1,"message":dict(row)}

@router.post("/admin/quotation-rate-create")
async def func_api_admin_quotation_rate_create(*, request:Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("parent_rate_id","int",0,None,None),("mode","str",1,["air","sea"],None),("movement","str",0,["export","import"],"export"),("origin","str",1,None,None),("destination","str",1,None,None),("carrier","str",1,None,None),("service","str",0,None,None),("currency","str",0,None,"USD"),("buy_rates","dict",1,None,None),("floor_rates","dict",1,None,None),("sell_rates_a","dict",1,None,None),("sell_rates_b","dict",1,None,None),("sell_rates_c","dict",1,None,None),("charges","dict",0,None,{}),("minimum_charge","float",0,None,None),("transit_time","str",0,None,None),("valid_from","str",1,None,None),("valid_to","str",1,None,None),("source_reference","str",1,None,None),("document_blob_ids","list:bigint",0,None,[])])
    try: valid_from, valid_to = datetime.strptime(ob["valid_from"], "%Y-%m-%d").date(), datetime.strptime(ob["valid_to"], "%Y-%m-%d").date()
    except Exception: raise Exception("valid from/to must use YYYY-MM-DD")
    async with app_state.client_postgres.acquire() as conn:
        access = await conn.fetchrow("SELECT pricing_category,allowed_origins,freight_status status FROM users WHERE id=$1", user_id)
        if not access or (request.state.user.get("role") != 1 and access["status"] != "active"): raise Exception("freight access disabled")
        if access and access["allowed_origins"] and ob["origin"].upper() not in access["allowed_origins"]: raise Exception("origin not permitted")
        rate_keys = set(ob["buy_rates"]) & set(ob["floor_rates"]) & set(ob["sell_rates_a"]) & set(ob["sell_rates_b"]) & set(ob["sell_rates_c"])
        if not rate_keys: raise Exception("at least one complete rate key is required")
        for key in rate_keys:
            try: values = [float(ob[x][key]) for x in ("buy_rates","floor_rates","sell_rates_a","sell_rates_b","sell_rates_c")]
            except Exception: raise Exception(f"invalid numeric rate for {key}")
            if min(values) < 0 or values[1] < values[0] or any(v < values[1] for v in values[2:]): raise Exception(f"invalid buy/floor/sell order for {key}")
        version = 1
        if ob["parent_rate_id"]:
            parent = await conn.fetchrow("SELECT id,parent_rate_id,version FROM freight_rate WHERE id=$1", ob["parent_rate_id"])
            if not parent: raise Exception("parent rate not found")
            version = int(parent["version"]) + 1
        row = await conn.fetchrow("INSERT INTO freight_rate (created_by_id,parent_rate_id,version,mode,movement,origin,destination,carrier,service,currency,buy_rates,floor_rates,sell_rates_a,sell_rates_b,sell_rates_c,charges,minimum_charge,transit_time,valid_from,valid_to,source_reference,document_blob_ids,status) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,'draft') RETURNING *", user_id, ob["parent_rate_id"], version, ob["mode"], ob["movement"], ob["origin"].upper(), ob["destination"].upper(), ob["carrier"].strip(), ob["service"] or None, ob["currency"].upper(), orjson.dumps(ob["buy_rates"]).decode(), orjson.dumps(ob["floor_rates"]).decode(), orjson.dumps(ob["sell_rates_a"]).decode(), orjson.dumps(ob["sell_rates_b"]).decode(), orjson.dumps(ob["sell_rates_c"]).decode(), orjson.dumps(ob["charges"]).decode(), ob["minimum_charge"], ob["transit_time"] or None, valid_from, valid_to, ob["source_reference"].strip(), ob["document_blob_ids"])
    return {"status":1,"message":{"id":row["id"],"status":row["status"],"version":row["version"]}}

@router.post("/admin/quotation-rate-decision")
async def func_api_admin_quotation_rate_decision(*, request:Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("rate_id","int",1,None,None),("action","str",1,["approved","rejected"],None),("remark","str",0,None,None)])
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            rate = await conn.fetchrow("SELECT * FROM freight_rate WHERE id=$1 FOR UPDATE", ob["rate_id"])
            if not rate: raise Exception("rate not found")
            if rate["status"] != "draft": raise Exception("rate is not pending")
            if rate["created_by_id"] == user_id: raise Exception("rate maker cannot approve own rate")
            status = ob["action"]
            await conn.execute("UPDATE freight_rate SET status=$1,decided_at=now(),decided_by_id=$2,decision_remark=$3,updated_by_id=$2 WHERE id=$4", status, user_id, ob["remark"] or None, ob["rate_id"])
            row = await conn.fetchrow("INSERT INTO freight_rate_approval (created_by_id,rate_id,action,remark) VALUES ($1,$2,$3,$4) RETURNING *", user_id, ob["rate_id"], ob["action"], ob["remark"] or None)
    return {"status":1,"message":dict(row)}

@router.get("/admin/quotation-rate-search")
async def func_api_admin_quotation_rate_search(*, request:Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("mode","str",1,["air","sea"],None),("origin","str",1,None,None),("destination","str",1,None,None),("shipment_date","str",0,None,None),("gross_kg","float",0,None,0),("cbm","float",0,None,0),("equipment","str",0,None,None),("quantity","float",0,None,1)])
    try: shipment_date = datetime.strptime(oq["shipment_date"], "%Y-%m-%d").date() if oq["shipment_date"] else datetime.now(timezone.utc).date()
    except Exception: raise Exception("shipment date must use YYYY-MM-DD")
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        access = await conn.fetchrow("SELECT pricing_category,allowed_origins,freight_status status FROM users WHERE id=$1", user_id)
        if not access or (request.state.user.get("role") != 1 and access["status"] != "active"): raise Exception("freight access disabled")
        if access and access["allowed_origins"] and oq["origin"].upper() not in access["allowed_origins"]: raise Exception("origin not permitted")
        category = access["pricing_category"] if access else "A"
        rows = [dict(r) for r in await conn.fetch("SELECT * FROM freight_rate WHERE status='approved' AND mode=$1 AND origin=$2 AND destination=$3 AND valid_from<=$4 AND valid_to>=$4 ORDER BY carrier,service,id DESC LIMIT 200", oq["mode"], oq["origin"].upper(), oq["destination"].upper(), shipment_date)]
    chargeable = max(float(oq["gross_kg"]), float(oq["cbm"]) * 167) if oq["mode"] == "air" else float(oq["quantity"])
    if chargeable <= 0: raise Exception("chargeable quantity must be positive")
    if oq["mode"] == "air":
        rate_key = "gt1000" if chargeable >= 1000 else "gt500" if chargeable >= 500 else "gt300" if chargeable >= 300 else "gt100" if chargeable >= 100 else "gt45" if chargeable >= 45 else "lt45"
    else: rate_key = (oq["equipment"] or "20GP").upper()
    output = []
    for row in rows:
        for key in ("sell_rates_a","sell_rates_b","sell_rates_c","charges"):
            if isinstance(row.get(key), str): row[key] = orjson.loads(row[key])
        sell_rates = row[{"A":"sell_rates_a","B":"sell_rates_b","C":"sell_rates_c"}[category]] or {}
        if rate_key not in sell_rates: continue
        sell_rate = float(sell_rates[rate_key]); total = max(sell_rate * chargeable, float(row["minimum_charge"] or 0))
        output.append({"rate_id":row["id"],"mode":row["mode"],"origin":row["origin"],"destination":row["destination"],"carrier":row["carrier"],"service":row["service"],"currency":row["currency"],"rate_key":rate_key,"chargeable_quantity":chargeable,"sell_rate":sell_rate,"estimated_total":round(total,2),"transit_time":row["transit_time"],"valid_to":row["valid_to"],"charges":row["charges"] or {}})
    return {"status":1,"message":{"pricing_category":category,"rate_key":rate_key,"chargeable_quantity":chargeable,"obj_list":output}}

@router.post("/admin/quotation-quote-create")
async def func_api_admin_quotation_quote_create(*, request:Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("customer_id","int",1,None,None),("rate_id","int",1,None,None),("shipment","dict",1,None,None),("requested_sell_rate","float",0,None,None),("exception_justification","str",0,None,None),("metadata","dict",0,None,{})])
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            access = await conn.fetchrow("SELECT pricing_category,allowed_origins,freight_status status FROM users WHERE id=$1", user_id)
            if not access or (request.state.user.get("role") != 1 and access["status"] != "active"): raise Exception("freight access disabled")
            category = access["pricing_category"] if access else "A"
            customer = await conn.fetchrow("SELECT * FROM freight_customer WHERE id=$1 AND status='active'", ob["customer_id"])
            if not customer: raise Exception("customer not found")
            rate = await conn.fetchrow("SELECT * FROM freight_rate WHERE id=$1 AND status='approved' AND valid_from<=CURRENT_DATE AND valid_to>=CURRENT_DATE FOR SHARE", ob["rate_id"])
            if not rate: raise Exception("approved valid rate not found")
            if access and access["allowed_origins"] and rate["origin"] not in access["allowed_origins"]: raise Exception("origin not permitted")
            shipment = ob["shipment"]
            if rate["mode"] == "air":
                chargeable = max(float(shipment.get("gross_kg") or 0), float(shipment.get("cbm") or 0) * 167)
                rate_key = "gt1000" if chargeable >= 1000 else "gt500" if chargeable >= 500 else "gt300" if chargeable >= 300 else "gt100" if chargeable >= 100 else "gt45" if chargeable >= 45 else "lt45"
            else:
                chargeable = float(shipment.get("quantity") or 1); rate_key = str(shipment.get("equipment") or "20GP").upper()
            if chargeable <= 0: raise Exception("chargeable quantity must be positive")
            data = {}
            for key in ("buy_rates","floor_rates","sell_rates_a","sell_rates_b","sell_rates_c","charges"):
                value = rate[key]
                data[key] = orjson.loads(value) if isinstance(value, str) else value or {}
            sell_map = data[{"A":"sell_rates_a","B":"sell_rates_b","C":"sell_rates_c"}[category]]
            if rate_key not in sell_map or rate_key not in data["floor_rates"] or rate_key not in data["buy_rates"]: raise Exception("rate unavailable for shipment")
            standard_sell = float(sell_map[rate_key]); floor_rate = float(data["floor_rates"][rate_key]); buy_rate = float(data["buy_rates"][rate_key])
            sell_rate = float(ob["requested_sell_rate"]) if ob["requested_sell_rate"] is not None else standard_sell
            is_exception = sell_rate < floor_rate
            if is_exception and not (ob["exception_justification"] or "").strip(): raise Exception("exception justification required below floor")
            total = max(sell_rate * chargeable, float(rate["minimum_charge"] or 0)); status = "exception_pending" if is_exception else "issued"
            quote = await conn.fetchrow("INSERT INTO freight_quote (created_by_id,customer_id,pricing_category,mode,origin,destination,shipment,chargeable_quantity,currency,total_sell,status,valid_to,kyc_status,credit_status,metadata) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15) RETURNING *", user_id, ob["customer_id"], category, rate["mode"], rate["origin"], rate["destination"], orjson.dumps(shipment).decode(), chargeable, rate["currency"], round(total,2), status, rate["valid_to"], customer["kyc_status"], customer["credit_status"], orjson.dumps(ob["metadata"]).decode())
            reference = f"MGH-{'A' if rate['mode']=='air' else 'S'}-{datetime.now(timezone.utc).strftime('%y%m')}-{quote['id']:06d}"
            await conn.execute("UPDATE freight_quote SET reference=$1 WHERE id=$2", reference, quote["id"])
            snapshot = {"rate_id":rate["id"],"version":rate["version"],"origin":rate["origin"],"destination":rate["destination"],"carrier":rate["carrier"],"service":rate["service"],"currency":rate["currency"],"rate_key":rate_key,"valid_to":str(rate["valid_to"]),"source_reference":rate["source_reference"]}
            await conn.execute("INSERT INTO freight_quote_line (created_by_id,quote_id,rate_id,carrier,service,rate_key,quantity,buy_rate,floor_rate,sell_rate,line_total,charges,rate_snapshot) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)", user_id, quote["id"], rate["id"], rate["carrier"], rate["service"], rate_key, chargeable, buy_rate, floor_rate, sell_rate, round(total,2), orjson.dumps(data["charges"]).decode(), orjson.dumps(snapshot).decode())
            if is_exception:
                await conn.execute("INSERT INTO freight_quote_exception (created_by_id,quote_id,requested_rate,floor_rate,estimated_impact,justification,status) VALUES ($1,$2,$3,$4,$5,$6,'pending')", user_id, quote["id"], sell_rate, floor_rate, round((floor_rate-sell_rate)*chargeable,2), ob["exception_justification"].strip())
    return {"status":1,"message":{"id":quote["id"],"reference":reference,"status":status,"exception_required":is_exception,"currency":rate["currency"],"sell_rate":sell_rate,"total_sell":round(total,2),"kyc_status":customer["kyc_status"],"credit_status":customer["credit_status"]}}

@router.post("/admin/quotation-exception-decision")
async def func_api_admin_quotation_exception_decision(*, request:Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("exception_id","int",1,None,None),("action","str",1,["approved","rejected"],None),("remark","str",0,None,None)])
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            exception = await conn.fetchrow("SELECT * FROM freight_quote_exception WHERE id=$1 FOR UPDATE", ob["exception_id"])
            if not exception: raise Exception("exception not found")
            if exception["status"] != "pending": raise Exception("exception is not pending")
            if exception["created_by_id"] == user_id: raise Exception("quote creator cannot approve own exception")
            status = ob["action"]; quote_status = "exception_approved" if status == "approved" else "rejected"
            await conn.execute("UPDATE freight_quote_exception SET status=$1,decided_at=now(),decided_by_id=$2,decision_remark=$3,updated_by_id=$2 WHERE id=$4", status, user_id, ob["remark"] or None, ob["exception_id"])
            quote = await conn.fetchrow("UPDATE freight_quote SET status=$1,updated_by_id=$2 WHERE id=$3 RETURNING id,reference,status", quote_status, user_id, exception["quote_id"])
    return {"status":1,"message":dict(quote)}

@router.get("/admin/quotation-dashboard")
async def func_api_admin_quotation_dashboard(*, request:Request):
    app_state, user_id = request.app.state, request.state.user["id"]
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        access = await conn.fetchrow("SELECT freight_status status FROM users WHERE id=$1", user_id)
        if not access or (request.state.user.get("role") != 1 and access["status"] != "active"): raise Exception("freight access disabled")
        role = await conn.fetchval("SELECT role FROM users WHERE id=$1", user_id)
        own = role == 2
        counts = dict(await conn.fetchrow("SELECT (SELECT COUNT(*) FROM freight_rate WHERE status='approved' AND valid_to>=CURRENT_DATE) approved_rates,(SELECT COUNT(*) FROM freight_rate WHERE status='draft') pending_rates,(SELECT COUNT(*) FROM freight_quote WHERE ($1::boolean=false OR created_by_id=$2)) quotes,(SELECT COUNT(*) FROM freight_quote_exception WHERE status='pending') pending_exceptions,(SELECT COUNT(*) FROM freight_customer WHERE status='active') customers", own, user_id))
        quotes = [dict(r) for r in await conn.fetch("SELECT q.id,q.reference,q.created_at,q.origin,q.destination,q.total_sell,q.currency,q.status,c.name customer_name FROM freight_quote q JOIN freight_customer c ON c.id=q.customer_id WHERE ($1::boolean=false OR q.created_by_id=$2) ORDER BY q.id DESC LIMIT 100", own, user_id)]
    return {"status":1,"message":{"counts":counts,"quotes":quotes}}
