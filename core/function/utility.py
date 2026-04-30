async def func_api_file_to_chunks(*, upload_file: any, chunk_size: int):
    """Generator: reads an uploaded CSV file in chunks and yields lists of dictionaries."""
    import csv, io
    content = await upload_file.read()
    f = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(f)
    chunk = []
    for row in reader:
        chunk.append(row)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

def func_file_size_read(*, file_path: str) -> str:
    """Read and format the size of a file in a human-readable string."""
    import os
    if not os.path.exists(file_path):
        return "0 B"
    size = os.path.getsize(file_path)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def func_file_extension_read(*, filename: str) -> str:
    """Extract the file extension from a filename."""
    import os
    return os.path.splitext(filename)[1].lower()

def func_file_mime_read(*, filename: str) -> str:
    """Identify the MIME type of a file based on its extension."""
    import mimetypes
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"

def func_converter_number(*, type: str, mode: str, x: any) -> any:
    """Encode strings into specific-size integers or decode them back using a custom charset."""
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}
    charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"
    if type not in type_limits:
        raise ValueError(f"invalid type: {type}, allowed: {list(type_limits.keys())}")
    base = len(charset)
    max_len = type_limits[type]
    if mode == "encode":
        val_str = str(x)
        val_len = len(val_str)
        if val_len > max_len:
            raise ValueError(f"input too long {val_len} > {max_len}")
        result_num = val_len
        for char in val_str:
            char_idx = charset.find(char)
            if char_idx == -1:
                raise ValueError("invalid character in input")
            result_num = result_num * base + char_idx
        return result_num
    if mode == "decode":
        try:
            num_val = int(x)
        except Exception:
            raise ValueError("invalid integer for decoding")
        decoded_chars = []
        while num_val > 0:
            num_val, reminder = divmod(num_val, base)
            decoded_chars.append(charset[reminder])
        return "".join(decoded_chars[::-1][1:]) if decoded_chars else ""

async def func_regex_check(*, config_regex: dict, obj_list: list):
    """Validate fields in a list of objects against regex patterns defined in config."""
    import re
    if not config_regex:
        return
    for obj in obj_list:
        for key, regex_info in config_regex.items():
            val = obj.get(key)
            if val is not None:
                pattern = regex_info[0]
                error_msg = regex_info[1]
                if not re.match(pattern, str(val)):
                    raise Exception(error_msg)
