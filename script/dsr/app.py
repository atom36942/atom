from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import Response
import re, io, mailparser, pandas as pd
from bs4 import BeautifulSoup

app = FastAPI()

def process_eml_bytes(eml_bytes: bytes) -> bytes:
    m = mailparser.parse_from_bytes(eml_bytes)
    s, h, a = m.subject, m.body, m.attachments

    if not s or "loading approval" not in s.lower():
        raise ValueError("Invalid subject")
    if any(x in s.lower() for x in ["re:", "fw:", "fwd:"]):
        raise ValueError("Threaded mail not supported")

    date_m = re.search(r"\d{2}\.\d{2}\.\d{4}", s)
    cps_m = re.search(r"CPS ID\s*:\s*(\d+)", s)
    if not date_m or not cps_m:
        raise ValueError("Invalid subject format")

    if not h:
        raise ValueError("Missing HTML body")

    soup = BeautifulSoup(h, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        raise ValueError("Tables missing")

    def tdf(t):
        rows = [[c.get_text(strip=True) for c in tr.find_all(["td","th"])] for tr in t.find_all("tr")]
        return pd.DataFrame(rows[1:], columns=rows[0])

    ddet = tdf(tables[1])

    matches = [x for x in a if x["filename"] and "packinglist" in x["filename"].lower()]
    if not matches:
        raise ValueError("PackingList not found")

    f = sorted(matches, key=lambda x: x["filename"])[0]
    dx = pd.read_excel(io.BytesIO(f["payload"]))

    dx.columns = dx.columns.str.strip()
    dx["SPECIAL CODE"] = dx["SPECIAL CODE"].astype(str)
    ddet["Special Code 1"] = ddet["Special Code 1"].astype(str)

    dx = dx.sort_values(by=list(dx.columns)).groupby("SPECIAL CODE").first().reset_index()

    if "QTY POLYBAG PER CTN" in dx.columns:
        dx["QTY POLYBAG PER CTN"] = dx.groupby("SPECIAL CODE")["QTY POLYBAG PER CTN"].transform("sum")

    def mseq(x): return "parcel" if x==1 else "bag" if x==2 else "mix" if x in [0,None] else x

    if "Warehouse address" in dx.columns and "Loading Sequence" in dx.columns:
        msk = dx["Warehouse address"]=="İthalat-Import"
        dx.loc[msk,"Loading Sequence"] = dx.loc[msk,"Loading Sequence"].apply(mseq)

    df = dx.merge(ddet, left_on="SPECIAL CODE", right_on="Special Code 1", how="left")
    df["CPS_ID"], df["MAIL_DATE"], df["SOURCE"] = cps_m.group(1), date_m.group(), "manual"

    return df.to_csv(index=False).encode()

@app.post("/process")
async def process(file: UploadFile):
    try:
        data = await file.read()
        out = process_eml_bytes(data)
        return Response(content=out, media_type="text/csv")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))