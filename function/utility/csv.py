import os,csv,tempfile
def func_csv_header_update(file_path,replacements,encoding="utf-8-sig"):
    mapping=dict(replacements); d=os.path.dirname(file_path) or "."
    with open(file_path,"r",encoding=encoding,newline="") as f:
        sample=f.read(1024); f.seek(0); dialect=csv.Sniffer().sniff(sample); reader=csv.reader(f,dialect); header=next(reader); missing=[k for k in mapping if k not in header]
        if missing: raise ValueError(f"Missing columns: {missing}")
        new_header=[mapping.get(c,c) for c in header]
        with tempfile.NamedTemporaryFile("w",delete=False,dir=d,encoding=encoding,newline="") as tmp:
            writer=csv.writer(tmp,dialect); writer.writerow(new_header)
            for row in reader: writer.writerow(row)
            tmp_path=tmp.name
    os.replace(tmp_path,file_path)
    return {"updated":len(replacements),"columns":len(new_header),"file":file_path}
