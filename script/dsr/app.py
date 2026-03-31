from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import Response
import re, io, mailparser, pandas as pd
from bs4 import BeautifulSoup

app = FastAPI()

def process_eml_bytes(eml_bytes: bytes) -> bytes:
    m = mailparser.parse_from_bytes(eml_bytes)
    s = m.subject
    # Extract HTML part specifically for BeautifulSoup
    h = m.text_html[0] if m.text_html else m.body
    a = m.attachments

    # Validation
    if not s or "loading approval" not in s.lower():
        raise ValueError("Invalid subject")
    if any(x in s.lower() for x in ["re:", "fw:", "fwd:"]):
        raise ValueError("Threaded mail not supported")

    date_m = re.search(r"\d{2}\.\d{2}\.\d{4}", s)
    cps_m = re.search(r"CPS ID\s*:\s*(\d+)", s)
    if not date_m or not cps_m:
        raise ValueError("Missing Date/CPS ID in subject")

    if not h:
        raise ValueError("MIME part 'text/html' missing")

    # Table Extraction
    soup = BeautifulSoup(h, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        raise ValueError("Required tables missing in HTML body")

    def tdf(t):
        rows = [[c.get_text(strip=True) for c in tr.find_all(["td","th"])] for tr in t.find_all("tr")]
        return pd.DataFrame(rows[1:], columns=rows[0])

    ddet = tdf(tables[1])
    ddet["Special Code 1"] = ddet["Special Code 1"].astype(str)

    # Attachment Processing
    matches = [x for x in a if x["filename"] and "packinglist" in x["filename"].lower()]
    if not matches:
        raise ValueError("PackingList attachment not found")

    f = sorted(matches, key=lambda x: x["filename"])[0]
    # Mailparser payloads are usually base64 decoded to bytes already
    dx = pd.read_excel(io.BytesIO(f["payload"]))

    # Transformation Logic
    dx.columns = dx.columns.str.strip()
    dx["SPECIAL CODE"] = dx["SPECIAL CODE"].astype(str)
    dx = dx.sort_values(by=list(dx.columns)).groupby("SPECIAL CODE").first().reset_index()

    if "QTY POLYBAG PER CTN" in dx.columns:
        dx["QTY POLYBAG PER CTN"] = dx.groupby("SPECIAL CODE")["QTY POLYBAG PER CTN"].transform("sum")

    def mseq(x): return "parcel" if x==1 else "bag" if x==2 else "mix" if x in [0,None] else x

    if "Warehouse address" in dx.columns and "Loading Sequence" in dx.columns:
        msk = dx["Warehouse address"] == "İthalat-Import"
        dx.loc[msk, "Loading Sequence"] = dx.loc[msk, "Loading Sequence"].apply(mseq)

    # Merge and Finalize
    df = dx.merge(ddet, left_on="SPECIAL CODE", right_on="Special Code 1", how="left")
    df["CPS_ID"], df["MAIL_DATE"], df["SOURCE"] = cps_m.group(1), date_m.group(), "manual"

    return df.to_csv(index=False).encode("utf-8")

@app.post("/process")
async def process(file: UploadFile):
    try:
        data = await file.read()
        out = process_eml_bytes(data)
        return Response(
            content=out, 
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=processed_{file.filename}.csv"}
        )
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Processing Error: {str(e)}")

@app.get("/")
def health():
    """Liveness probe for the API"""
    return {"status": "ok", "service": "email-processor"}