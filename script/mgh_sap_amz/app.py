#import
import os
import json
import csv
import httpx
import asyncpg
import asyncssh
import uvicorn
import copy
from fastapi import FastAPI, Request
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from dotenv import load_dotenv

#config
load_dotenv()
config_amazon_client_id=os.getenv("config_amazon_client_id")
config_amazon_client_secret=os.getenv("config_amazon_client_secret")
config_sftp_host=os.getenv("config_sftp_host")
config_sftp_port=int(os.getenv("config_sftp_port") or 22)
config_sftp_username=os.getenv("config_sftp_username")
config_sftp_password=os.getenv("config_sftp_password")
config_postgres_url=os.getenv("config_postgres_url")
config_export_prefix="tmp/mgh_amazon_"
config_table_name="mgh_amazon_invoice"
config_token_url="https://sendstack-prod-token.auth.us-east-1.amazoncognito.com/oauth2/token"
config_api_url="https://prod.send.irisapi.iris.ctt.amazon.dev/sendInvoiceDocument"
config_cert_files=("secret/mgh_amazon_cert.txt","secret/mgh_amazon_key.key")
config_sftp_path="mgh/amazon"
config_payload_amazon_invoice={
    "invoiceDocument":{
        "invoiceId":"","accountId":"","invoiceDocumentOwner":{"supplierId":"MGHP","supplierIdType":"SCAC"},
        "invoiceHeader":{
            "invoiceNumber":"","purchaseOrderNumber":"","invoiceDate":"",
            "invoiceAmount":{"amount":0.0,"currencyCode":""},
            "invoiceAmountWithoutTaxes":{"amount":0.0,"currencyCode":""},
            "invoiceReferences":[{"invoiceId":"","invoiceNumber":""}],
            "buyer":{"legalEntity":{"addresses":[{"addressee":"Attend to : Transportation Finance","addressLine1":"300 Boren Ave N","addressLine2":"NA","addressLine3":"NA","municipalityName":"Seattle","cityName":"Seattle","stateName":"WA","countryName":"United States","countryCode":"US","postalCode":"98109"}],"taxIdentities":[{"taxIdentityNumber":"32-0765633","taxIdentityType":"VAT"}],"legalEntityName":"Amazon.com Services LLC","businessName":"Amazon Logistics"}},
            "supplier":{"legalEntity":{"addresses":[{"addressee":"MGH LOGISTICS PRIVATE LIMITED","addressLine1":"Unit No. 1107, 11th Floor, E-Wing, Times Square","addressLine2":"CTS No. 758/759, Marol, Mittal Industrial Estate","addressLine3":"Andheri East","municipalityName":"Mumbai","cityName":"Mumbai","stateName":"MH","countryName":"India","countryCode":"IN","postalCode":"400059"}],"taxIdentities":[{"taxIdentityNumber":"27AAECM2361B1ZW","taxIdentityType":"VAT"}],"legalEntityName":"MGH LOGISTICS PRIVATE LIMITED","businessName":"MGH LOGISTICS PRIVATE LIMITED"}},
            "billTo":{"legalEntity":{"addresses":[{"addressee":"Amazon Logistics, Inc.","addressLine1":"410 Terry Ave N","addressLine2":"Floor 5","addressLine3":"South Lake Union","municipalityName":"Seattle","cityName":"Seattle","stateName":"WA","countryName":"United States","countryCode":"US","postalCode":"98109"}],"taxIdentities":[{"taxIdentityNumber":"32-0765633","taxIdentityType":"VAT"}],"legalEntityName":"Amazon.com Services LLC","businessName":"Amazon AP"}},
            "billFrom":{"legalEntity":{"addresses":[{"addressee":"MGH LOGISTICS INC","addressLine1":"67 WALNUT AVE","addressLine2":"SUITE 301","addressLine3":"NA","municipalityName":"CLARK","cityName":"CLARK","stateName":"NJ","countryName":"United States","countryCode":"US","postalCode":"07066"}],"taxIdentities":[{"taxIdentityNumber":"32-0765633","taxIdentityType":"VAT"}],"legalEntityName":"MGH LOGISTICS INC","businessName":"MGH LOGISTICS"}},
            "documentTypeInfo":{"documentType":"INVOICE","requestForPayment":True}
        },
        "invoiceLineItems":[{
            "lineItemId":"1","description":"","lineItemRequisitionIdentifierInfo":{"primaryRefId":{"extensions":[{"trackingId":""}]}},
            "lineItemDetail":{
                "freightShipmentDetail":{
                    "shipmentIdentificationNumber":"","shipmentBillOfLadingNumber":"","proofOfDelivery":"",
                    "consigneeAddress":{"addressee":"Amazon Fulfillment Center","addressLine1":"2121 8th Ave","addressLine2":"Receiving Dock","addressLine3":"Building 7","municipalityName":"Seattle","cityName":"Seattle","stateName":"WA","countryName":"United States","countryCode":"US","postalCode":"98121"},
                    "transportationMethodType":"","shippedDate":"","deliveryDate":"",
                    "shipmentWeightDetail":{"grossWeight":{"weight":0.0,"unitOfMeasurement":"KG"},"netWeight":{"weight":0.0,"unitOfMeasurement":"KG"},"billedWeight":{"weight":0.0,"unitOfMeasurement":"KG"},"declaredWeight":{"weight":0.0,"unitOfMeasurement":"KG"}},
                    "shipmentVolumeDetail":{"billedVolume":{"length":0.0,"breadth":0.0,"height":0.0,"unitOfMeasurement":"GALLONS"},"declaredVolume":{"length":0.0,"breadth":0.0,"height":0.0,"unitOfMeasurement":"GALLONS"}},
                    "packageDetails":[{
                        "packageReferenceId":"",
                        "packageWeightDetail":{"grossWeight":{"weight":0.0,"unitOfMeasurement":"KG"},"netWeight":{"weight":0.0,"unitOfMeasurement":"KG"},"billedWeight":{"weight":0.0,"unitOfMeasurement":"KG"},"declaredWeight":{"weight":0.0,"unitOfMeasurement":"KG"}},
                        "packageVolumeDetail":{"billedVolume":{"length":0.0,"breadth":0.0,"height":0.0,"unitOfMeasurement":"GALLONS"},"declaredVolume":{"length":0.0,"breadth":0.0,"height":0.0,"unitOfMeasurement":"GALLONS"}}
                    }]
                }
            },
            "unitCharges":[{"chargeId":"","chargeCode":"","chargeAmount":{"amount":0.0,"currencyCode":""}}],
            "quantity":{"quantity":1.0,"quantityUnit":"COUNT"},
            "lineItemAmount":{"amount":0.0,"currencyCode":""},
            "lineItemAmountWithoutTaxes":{"amount":0.0,"currencyCode":""}
        }]
    }
}

#pure func
async def func_sftp_read_files(host,port,username,password,remote_dir,local_prefix):
    os.makedirs(os.path.dirname(local_prefix),exist_ok=True)
    list_files=[]
    async with asyncssh.connect(host,port=port,username=username,password=password,known_hosts=None) as conn:
        async with conn.start_sftp_client() as sftp:
            files=await sftp.listdir(remote_dir)
            for f in files:
                if f not in ('.','..') and f.lower().endswith('.csv'):
                    local_path=f"{local_prefix}{f}"
                    await sftp.get(f"{remote_dir}/{f}",local_path)
                    list_files.append((f,local_path))
    return list_files

def func_csv_to_dict_list(local_path):
    with open(local_path,"r",encoding="utf-8") as file_csv:
        return list(csv.DictReader(file_csv))

def func_amazon_payload_build(row,invoice_id,today_utc):
    for k in ("INVOICEDATE","SHIPPEDDATE","DELIVERYDATE"):
        v=row.get(k)
        row[k]=datetime.strptime(v.strip(),"%Y%m%d").strftime("%Y-%m-%dT%H:%M:%SZ") if v and v!="00000000" else today_utc
    payload=copy.deepcopy(config_payload_amazon_invoice)
    payload["invoiceDocument"]["invoiceId"]=invoice_id
    payload["invoiceDocument"]["accountId"]=row["AccountID"]
    payload["invoiceDocument"]["invoiceHeader"]["invoiceNumber"]=invoice_id
    payload["invoiceDocument"]["invoiceHeader"]["purchaseOrderNumber"]=invoice_id
    payload["invoiceDocument"]["invoiceHeader"]["invoiceDate"]=row["INVOICEDATE"]
    payload["invoiceDocument"]["invoiceHeader"]["invoiceAmount"].update({"amount":float(row["INVOICEAMOUNT"]),"currencyCode":row["CURRENCY"]})
    payload["invoiceDocument"]["invoiceHeader"]["invoiceAmountWithoutTaxes"].update({"amount":float(row["INVOICEAMOUNT"]),"currencyCode":row["CURRENCY"]})
    payload["invoiceDocument"]["invoiceHeader"]["invoiceReferences"][0].update({"invoiceId":invoice_id,"invoiceNumber":invoice_id})
    iitem=payload["invoiceDocument"]["invoiceLineItems"][0]
    iitem["description"]=row["DESCRIPTION"]
    iitem["lineItemRequisitionIdentifierInfo"]["primaryRefId"]["extensions"][0]["trackingId"]=row["TRACKINGID"]
    ifdetail=iitem["lineItemDetail"]["freightShipmentDetail"]
    ifdetail["shipmentIdentificationNumber"]=row["FBANumber"]
    ifdetail["shipmentBillOfLadingNumber"]=row["SHIPMENTBILLOFLADINGNUMBER"]
    ifdetail["proofOfDelivery"]=row["PROOFOFDELIVERY"]
    ifdetail["transportationMethodType"]=row["TRANSPORTATIONMETHODTYPE"]
    ifdetail["shippedDate"]=row["SHIPPEDDATE"]
    ifdetail["deliveryDate"]=row["DELIVERYDATE"]
    for k in ("grossWeight","netWeight","billedWeight","declaredWeight"):
        ifdetail["shipmentWeightDetail"][k]["weight"]=float(row["GROSSWEIGHT"])
        ifdetail["packageDetails"][0]["packageWeightDetail"][k]["weight"]=float(row["GROSSWEIGHT"])
    for k in ("billedVolume","declaredVolume"):
        ifdetail["shipmentVolumeDetail"][k].update({"length":float(row["VOLUMELENGTH"]),"breadth":float(row["VOLUMEBREADTH"]),"height":float(row["VOLUMEHEIGHT"])})
        ifdetail["packageDetails"][0]["packageVolumeDetail"][k].update({"length":float(row["VOLUMELENGTH"]),"breadth":float(row["VOLUMEBREADTH"]),"height":float(row["VOLUMEHEIGHT"])})
    ifdetail["packageDetails"][0]["packageReferenceId"]=row["CHARGEID"]
    iitem["unitCharges"][0].update({"chargeId":row["CHARGEID"],"chargeCode":row["CHARGECODE"]})
    iitem["unitCharges"][0]["chargeAmount"].update({"amount":float(row["AMOUNT"]),"currencyCode":row["CURRENCYCODE"]})
    iitem["lineItemAmount"].update({"amount":float(row["INVOICEAMOUNT"]),"currencyCode":row["CURRENCYCODE"]})
    iitem["lineItemAmountWithoutTaxes"].update({"amount":float(row["INVOICEAMOUNT"]),"currencyCode":row["CURRENCYCODE"]} )
    return payload

async def func_amazon_token_get(state,config_token_url,now_utc):
    if not getattr(state,"cache_amazon_token",None) or not getattr(state,"cache_amazon_token_expires",None) or now_utc>=state.cache_amazon_token_expires:
        r_tk=await state.client_http.post(config_token_url,data={"grant_type":"client_credentials","client_id":config_amazon_client_id,"client_secret":config_amazon_client_secret},headers={"Content-Type":"application/x-www-form-urlencoded"})
        r_tk.raise_for_status()
        state.cache_amazon_token=r_tk.json()["access_token"]
        state.cache_amazon_token_expires=now_utc+timedelta(minutes=55)
    return state.cache_amazon_token

async def func_amazon_invoice_send(state,payload,config_api_url,config_cert_files):
    r=await state.client_http.post(config_api_url,json=payload,headers={"Authorization":f"Bearer {state.cache_amazon_token}","Content-Type":"application/json"},cert=config_cert_files,timeout=60)
    ok=r.status_code in (200,202)
    return ok,r

async def func_db_records_save(client_postgres_pool,table_name,db_records):
    query=f"INSERT INTO {table_name} (invoice_id,payload,filename,status,response) VALUES ($1,$2::jsonb,$3,$4,$5::jsonb)"
    async with client_postgres_pool.acquire() as conn:
        async with conn.transaction():
            await conn.executemany(query,[(r["invoice_id"],r["payload"],r["filename"],r["status"],r["response"]) for r in db_records])

#lifespan
@asynccontextmanager
async def func_lifespan(app:FastAPI):
    app.state.client_postgres_pool=await asyncpg.create_pool(config_postgres_url,min_size=1,max_size=10)
    async with app.state.client_postgres_pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {config_table_name} (
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ,
                invoice_id TEXT NOT NULL,
                payload JSONB NOT NULL,
                response JSONB NOT NULL,
                filename TEXT NOT NULL,
                status INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_{config_table_name}_status ON {config_table_name}(status);
        """)
    app.state.client_http=httpx.AsyncClient()
    app.state.cache_amazon_token=None
    app.state.cache_amazon_token_expires=None
    yield
    await app.state.client_http.aclose()
    await app.state.client_postgres_pool.close()

#fastapi app
app=FastAPI(lifespan=func_lifespan)

#api
@app.get("/mgh/amazon-invoice-send")
async def api_mgh_amazon_invoice_send(request:Request):
    state=request.app.state
    process_results=[]
    list_files=await func_sftp_read_files(config_sftp_host,config_sftp_port,config_sftp_username,config_sftp_password,config_sftp_path,config_export_prefix)
    now_utc=datetime.now(timezone.utc)
    today_utc=now_utc.strftime("%Y-%m-%dT00:00:00Z")
    await func_amazon_token_get(state,config_token_url,now_utc)
    for filename,local_path in list_files:
        db_records=[]
        rows=func_csv_to_dict_list(local_path)
        for row in rows:
            invoice_id=row.get("INVOICENUMBER")
            if not invoice_id or not invoice_id.strip(): continue
            payload=func_amazon_payload_build(row,invoice_id,today_utc)
            ok,r=await func_amazon_invoice_send(state,payload,config_api_url,config_cert_files)
            db_records.append({"invoice_id":invoice_id,"payload":json.dumps(payload),"filename":filename,"status":1 if ok else 0,"response":json.dumps(r.json() if r.content else {}) if ok else json.dumps({"error":r.text})})
        if db_records:
            await func_db_records_save(state.client_postgres_pool,config_table_name,db_records)
            process_results.append({"filename":filename,"records_processed":len(db_records)})
    return {"status":1,"message":process_results}

#app start
if __name__=="__main__":
    uvicorn.run("app:app",host="0.0.0.0",port=8001,reload=True)