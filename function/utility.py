def func_structure_create(*, directories: list, files: list) -> None:
    """Create directory and file structure if it doesn't exist."""
    import os
    for directory_path in directories:
        try:
            os.makedirs(directory_path, exist_ok=True)
        except OSError:
            pass
    for file_path in files:
        try:
            if not os.path.exists(file_path):
                open(file_path, "a").close()
        except OSError:
            pass
        
async def func_api_file_to_obj_list(*, upload_file: any) -> list[dict[str, any]]:
    """Convert an uploaded CSV file into a list of dictionaries (all at once)."""
    import csv, io, asyncio
    def _parse_csv(file):
        return [row for row in csv.DictReader(io.TextIOWrapper(file, encoding="utf-8"))]
    obj_list = await asyncio.to_thread(_parse_csv, upload_file.file)
    await upload_file.close()
    return obj_list

async def func_api_file_to_chunks(*, upload_file: any, chunk_size: int) -> any:
    """Yield chunks of dictionaries from an uploaded CSV file for memory efficiency."""
    import csv, io, asyncio
    
    def _read_chunk(reader_iter, size):
        chunk = []
        try:
            for _ in range(size):
                chunk.append(next(reader_iter))
        except StopIteration:
            pass
        return chunk
    reader = csv.DictReader(io.TextIOWrapper(upload_file.file, encoding="utf-8"))
    reader_iter = iter(reader)
    while True:
        chunk = await asyncio.to_thread(_read_chunk, reader_iter, chunk_size)
        if not chunk:
            break
        yield chunk
    await upload_file.close()
    return

def func_config_override_from_env(*, global_dict: dict) -> None:
    """Override configuration variables starting with 'config_' from environment variables and .env file."""
    import orjson, os, ast
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
    for key, value in list(global_dict.items()):
        val_env = os.getenv(key)
        if key.startswith("config_") and val_env is not None:
            config_val = val_env
            if isinstance(global_dict[key], (list, tuple)):
                global_dict[key] = orjson.loads(config_val)
            elif isinstance(value, bool):
                global_dict[key] = 1 if config_val.lower() in ("true", "1", "yes", "on", "ok") else 0
            elif isinstance(value, int):
                global_dict[key] = int(config_val)
            elif isinstance(value, dict):
                try:
                    global_dict[key] = orjson.loads(config_val)
                except Exception:
                    pass
            else:
                try:
                    global_dict[key] = int(config_val)
                except Exception:
                    global_dict[key] = config_val
            if isinstance(global_dict[key], list):
                global_dict[key] = tuple(global_dict[key])
    try:
        with open("core/config.py", "r") as config_file:
            for node in ast.parse(config_file.read()).body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Name):
                    target_id = node.targets[0].id
                    value_id = node.value.id
                    if target_id.startswith("config_") and value_id.startswith("config_") and os.getenv(target_id) is None:
                        global_dict[target_id] = global_dict[value_id]
    except Exception:
        pass

def func_folder_reset(*, folder_path: str) -> str:
    """Purge all files and subdirectories within a specified directory."""
    import os, shutil
    absolute_path = folder_path if os.path.isabs(folder_path) else os.path.join(os.getcwd(), folder_path)
    if not os.path.isdir(absolute_path):
        return "folder not found"
    for item in os.listdir(absolute_path):
        item_path = os.path.join(absolute_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)
    return "folder reset done"

async def func_client_download_file(*, file_path: str, is_delete_after: int, chunk_size: int) -> any:
    """Stream a file for client download with optional automatic cleanup after transmission."""
    if "tmp/" not in str(file_path):
        raise Exception("IO Boundary Violation: tmp/ path required")
    from fastapi import responses
    from starlette.background import BackgroundTask
    import os, mimetypes, aiofiles
    file_name = os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    async def file_iterator():
        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    return responses.StreamingResponse(file_iterator(), media_type=content_type, headers={"Content-Disposition": f"attachment; filename=\"{file_name}\""}, background=BackgroundTask(os.remove, file_path) if is_delete_after == 1 else None)

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
