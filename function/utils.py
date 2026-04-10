def func_password_hash(password: str) -> str:
    """Generate a SHA-256 hash for a given password."""
    import hashlib
    return hashlib.sha256(str(password).encode()).hexdigest()

def func_token_encode(payload: dict, secret_key: str, expiry_sec: int) -> str:
    """Generate a JWT token with a specified payload, secret key, and expiration time."""
    import jwt, datetime
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expiry_sec)
    payload["exp"] = exp
    return jwt.encode(payload, secret_key, algorithm="HS256")

def func_structure_create(directories_list: list, files_list: list) -> None:
    """Create directory and file structure if it doesn't exist."""
    import os
    for directory_path in directories_list:
        try:
            os.makedirs(directory_path, exist_ok=True)
        except OSError:
            pass
    for file_path in files_list:
        try:
            if not os.path.exists(file_path):
                open(file_path, "a").close()
        except OSError:
            pass

def func_structure_check(root_path: str, dirs: tuple = None, files: tuple = None) -> None:
    """Verify existence of required project directories and files."""
    from pathlib import Path
    dirs_list = dirs or ()
    files_list = files or ()
    try:
        root = Path(root_path)
        if not root.exists():
            return None
        missing_dirs = [directory_name for directory_name in dirs_list if not (root / directory_name).is_dir()]
        missing_files = [file_name for file_name in files_list if not (root / file_name).is_file()]
        if missing_dirs:
            print(f"Structure verification failed. Missing Dirs: {missing_dirs}")
        if missing_files:
            print(f"Structure verification failed. Missing Files: {missing_files}")
    except Exception:
        pass
    return None

def func_folder_reset(folder_path: str) -> str:
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

def func_validate_identifier(name: str) -> str:
    """Validate that a string is a safe SQL identifier (table/column name)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(name)):
        raise Exception(f"invalid identifier {name}")
    return name

def func_config_override_from_env(globals_dict: dict) -> None:
    """Override global configuration variables with values from environment variables using a 'CONFIG_' prefix."""
    import os, orjson
    for key, val in os.environ.items():
        if key.startswith("CONFIG_"):
            target_key = key.lower()
            if target_key in globals_dict:
                try:
                    globals_dict[target_key] = orjson.loads(val)
                except Exception:
                    globals_dict[target_key] = val

async def func_api_file_to_obj_list(upload_file: any) -> list[dict[str, any]]:
    """Convert an uploaded CSV file into a list of dictionaries (all at once)."""
    import csv, io, asyncio
    def _parse_csv(file):
        return [row for row in csv.DictReader(io.TextIOWrapper(file, encoding="utf-8"))]
    obj_list = await asyncio.to_thread(_parse_csv, upload_file.file)
    await upload_file.close()
    return obj_list

async def func_api_file_to_chunks(upload_file: any, chunk_size: int = None) -> any:
    """Yield chunks of dictionaries from an uploaded CSV file for memory efficiency."""
    if chunk_size is None:
        chunk_size = 5000
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
