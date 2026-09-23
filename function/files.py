"""Atom files functions."""

def func_structure_init(*, dir_list: tuple = ("tmp", "secret")) -> None:
    """Reset working tmp/ directory and ensure required application directories exist."""
    import os, shutil
    if os.path.isdir("tmp") and not os.path.islink("tmp"): shutil.rmtree("tmp")
    elif os.path.exists("tmp"): os.remove("tmp")
    for d in dir_list: os.makedirs(d, exist_ok=True)

async def func_api_file_to_chunks(*, upload_file: any, chunk_size: int):
    """Generator: reads an uploaded CSV file in chunks and yields lists of dictionaries."""
    import csv, io
    is_wrapped_upload = hasattr(upload_file, "file")
    if is_wrapped_upload:
        await upload_file.seek(0)
        f = io.TextIOWrapper(upload_file.file, encoding="utf-8", newline="")
    else:
        content = await upload_file.read()
        f = io.StringIO(content.decode("utf-8"))
    chunk = []
    try:
        reader = csv.DictReader(f)
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk: yield chunk
    finally:
        if is_wrapped_upload: f.detach()

def func_file_stream(*, output_path: str):
    """Stream a temporary file and remove it after the stream completes."""
    import os
    with open(output_path, mode="rb") as f:
        while chunk := f.read(1048576): yield chunk
    os.remove(output_path)
