#import
from fastapi import FastAPI, UploadFile, HTTPException, Request
from fastapi.responses import Response, JSONResponse
import re, io, mailparser, pandas as pd
from bs4 import BeautifulSoup
import uvicorn, os
from contextlib import asynccontextmanager

#config
# Ensure 'pip install openpyxl' is run for Excel processing
PORT = int(os.getenv("PORT", 8002))

#pure func
def process_eml_bytes(eml_bytes: bytes) -> bytes:
    m = mailparser.parse_from_bytes(eml_bytes)
    subj = m.subject
    
    # 1. Subject Validation & Date Extraction
    if not subj or "loading approval" not in subj.lower():
        raise ValueError("Subject must contain 'Loading Approval'")
    
    date_match = re.search(r"\d{2}\.\d{2}\.\d{4}", subj)
    mail_subject_date = date_match.group() if date_match else ""
    
    # 2. Attachment Extraction (mail_excel)
    matches = [x for x in m.attachments if x["filename"] and "packinglist" in x["filename"].lower()]
    if not matches:
        raise ValueError("PackingList Excel attachment not found")
        
    dx = pd.read_excel(io.BytesIO(matches[0]["payload"]))
    dx.columns = dx.columns.str.strip()
    
    if "SPECIAL CODE" not in dx.columns:
        raise ValueError("Column 'SPECIAL CODE' missing in Excel")
        
    dx["SPECIAL CODE"] = dx["SPECIAL CODE"].astype(str).str.strip()

    # 3. Aggregation (mail_excel_sum)
    sum_cols = ["CARTONS", "QTY", "WEIGHT", "CBM", "Lot Type as per qualitity", "QTY POLYBAG PER CTN"]
    existing_sum_cols = [c for c in sum_cols if c in dx.columns]
    
    dx_sum = dx.groupby("SPECIAL CODE")[existing_sum_cols].sum().reset_index()
    dx_first = dx.groupby("SPECIAL CODE").first().reset_index().drop(columns=existing_sum_cols)
    dx_final = pd.merge(dx_sum, dx_first, on="SPECIAL CODE")

    # 4. Body Table Extraction (mail_body_table)
    html_body = m.text_html[0] if m.text_html else m.body
    soup = BeautifulSoup(html_body, "html.parser")
    tables = soup.find_all("table")
    
    ddet = pd.DataFrame()
    join_key = None
    
    for t in tables:
        rows = [[c.get_text(strip=True) for c in tr.find_all(["td","th"])] for tr in t.find_all("tr")]
        if len(rows) < 2: continue
        temp_df = pd.DataFrame(rows[1:], columns=rows[0])
        
        for key in ["Special Code", "Special Code 1"]:
            if key in temp_df.columns:
                ddet = temp_df
                join_key = key
                break
        if join_key: break
        
    if ddet.empty:
        raise ValueError("Email body table with 'Special Code' or 'Special Code 1' not found")
        
    ddet[join_key] = ddet[join_key].astype(str).str.strip()

    # 5. Relational Join
    df = pd.merge(dx_final, ddet, left_on="SPECIAL CODE", right_on=join_key, how="left")

    # 6. Sequence Logic (İthalat-Import Mapping)
    def map_sequence(row):
        if str(row.get("Warehouse address")) == "İthalat-Import":
            val = row.get("Loading Sequence")
            if val in [1, "1"]: return "parcel"
            if val in [2, "2"]: return "bag"
            if val in [0, "0", None, "null", "nan"]: return "mix"
        return row.get("Loading Sequence")
    
    df["Loading Sequence"] = df.apply(map_sequence, axis=1)

    # 7. Final Schema Construction
    final_headers = [
        "REF", "SHIPPER", "SHIPMENT TYPE", "Warehouse address", "TALEP ID", "ORDER", 
        "SPECIAL CODE", "Loading Sequence", "Merch Group", "MODEL ADI", 
        "Lot Type as per qualitity", "CARTONS", "QTY", "WEIGHT", "CBM", "POL", "POD", 
        "Retail Depo Tarih", "SHIPMENT APPROVAL DATE", "S/O DATE", 
        "CARTED DATE TO NHAVA SHEVA CFS", "HAND OVER", "CFS CUT OFF", "PLANNED ETD", 
        "UPDATED ETD", "PLANNED ETA", "UPDATED ETA", "CARRIER", "FEEDER VESSEL", 
        "MAIN VESSEL", "CONTAINER NUMBER", "CONTAINER TYPE", "BOOKING", "DOCUMENT", 
        "STUFFING", "HS CODE", "HBL", "MBL", "Remarks", "QTY POLYBAG PER CTN"
    ]

    # Injection: Constants & Subject Date
    df["REF"] = "manual"
    df["SHIPMENT APPROVAL DATE"] = mail_subject_date
    df["S/O DATE"] = mail_subject_date
    
    manual_placeholders = [
        "CARTED DATE TO NHAVA SHEVA CFS", "HAND OVER", "CFS CUT OFF", "PLANNED ETD", 
        "UPDATED ETD", "PLANNED ETA", "UPDATED ETA", "CARRIER", "FEEDER VESSEL", 
        "MAIN VESSEL", "CONTAINER NUMBER", "CONTAINER TYPE", "BOOKING", "DOCUMENT", 
        "STUFFING", "HBL", "MBL", "Remarks"
    ]
    for col in manual_placeholders:
        df[col] = "manual"

    # Fill missing headers to maintain 40-column count
    for col in final_headers:
        if col not in df.columns:
            df[col] = ""

    return df[final_headers].to_csv(index=False).encode("utf-8")

#lifespan
@asynccontextmanager
async def func_lifespan(app: FastAPI):
    yield

#app
app = FastAPI(lifespan=func_lifespan)

#middleware
@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": 0, "message": str(exc)}
    )

#api
@app.get("/")
async def api_health(request: Request):
    return {"status": 1, "message": "dsr_email_processor_active"}

@app.post("/process")
async def process_endpoint(file: UploadFile):
    content = await file.read()
    try:
        csv_bytes = process_eml_bytes(content)
        return Response(
            content=csv_bytes, 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename=processed_{file.filename}.csv"}
        )
    except ValueError as ve:
        return JSONResponse(status_code=422, content={"status": 0, "message": str(ve)})

#app start
if __name__ == "__main__":
    # Ensure this filename is named 'app.py' or update the string below
    uvicorn.run("app:app", host="0.0.0.0", port=PORT)