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

def func_password_hash(password_raw: any) -> str:
    """Generate SHA-256 hash of the provided password string."""
    import hashlib
    return hashlib.sha256(str(password_raw).encode()).hexdigest()

def func_logic_data_validate(obj_list: list, api_role: str, config_column_blocked: list, immutable_fields: list = None) -> None:
    """Centralized validation for platform constraints, blocked columns, and immutable fields across one pass."""
    immutable_fields = immutable_fields or ["created_at"]
    for item in obj_list:
        if not isinstance(item, dict):
            continue
        for key in item:
            if key in immutable_fields:
                raise Exception(f"restricted update to immutable field: {key}")
            if api_role != "admin" and key in config_column_blocked:
                raise Exception(f"unauthorized update to restricted field: {key}")

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

def func_config_override_from_env(global_dict: dict) -> None:
    """Override configuration variables starting with 'config_' from environment variables and .env file."""
    import orjson, os, ast
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
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

async def func_client_download_file(file_path: str, is_delete_after: int = None, chunk_size: int = None) -> any:
    """Stream a file for client download with optional automatic cleanup after transmission."""
    if "tmp/" not in str(file_path):
        raise Exception("IO Boundary Violation: tmp/ path required")
    from fastapi import responses
    from starlette.background import BackgroundTask
    import os, mimetypes, aiofiles
    is_delete_after = is_delete_after if is_delete_after is not None else 1
    chunk_size = chunk_size or 1048576
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

async def func_request_param_read(request_obj: any, parsing_mode: str, param_config: list, is_strict: int = None) -> dict:
    """Extract, validate, and type-cast request parameters from query, form, body or headers."""
    is_strict = is_strict or 0
    params_dict = {}
    header_params = {k.lower(): v for k, v in request_obj.headers.items()}
    if parsing_mode == "query":
        params_dict = dict(request_obj.query_params)
    elif parsing_mode == "form":
        form_data = await request_obj.form()
        params_dict = {key: val for key, val in form_data.items() if isinstance(val, str)}
        for key in form_data.keys():
            files = [x for x in form_data.getlist(key) if getattr(x, "filename", None)]
            if files:
                params_dict[key] = files
    elif parsing_mode == "body":
        try:
            json_payload = await request_obj.json()
        except Exception:
            json_payload = None
        params_dict = json_payload if isinstance(json_payload, dict) else {"body": json_payload}
    elif parsing_mode == "header":
        params_dict = header_params
    else:
        raise Exception(f"invalid parsing mode: {parsing_mode}")
    if param_config is None:
        return params_dict
    import orjson
    def smart_dict(v):
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and v.strip():
            try:
                return orjson.loads(v)
            except Exception:
                pass
        return {}
    TYPE_MAP = {
        "int": int, "bigint": int, "smallint": int, "integer": int, "int4": int, "int8": int,
        "float": float, "number": float, "numeric": float,
        "str": str, "any": lambda v: v, 
        "bool": lambda v: 1 if str(v).strip().lower() in ("1", "true", "yes", "on", "ok") else 0, 
        "dict": smart_dict, "object": smart_dict,
        "file": lambda v: ([] if v is None else v if isinstance(v, list) else [v]),
        "list": lambda v: [] if v is None else v if isinstance(v, list) else [] if (isinstance(v, str) and not v.strip()) else [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else [v]
    }
    output_dict = params_dict.copy() if not is_strict else {}
    for param in param_config:
        key, data_type, is_mandatory, allowed_values, default_value = param[:5]
        regex_pattern = param[5] if len(param) > 5 else None
        custom_error = param[6] if len(param) > 6 else None
        if data_type not in TYPE_MAP and not data_type.startswith("list:"):
            raise Exception(f"parameter '{key}' has invalid data_type '{data_type}'")
        if is_mandatory == 1 and default_value is not None:
            raise Exception(f"parameter '{key}' is mandatory, default_value must be None")
        if default_value is not None and allowed_values and default_value not in allowed_values:
            raise Exception(f"parameter '{key}' default '{default_value}' violating allowed_values: {allowed_values}")
        if allowed_values is not None and not isinstance(allowed_values, (list, tuple)):
            raise Exception(f"parameter '{key}' allowed_values must be a list or tuple")
        if is_mandatory and key not in params_dict:
            raise Exception(f"parameter '{key}' missing")
        val = params_dict.get(key)
        if val is None:
            val = header_params.get(key.lower())
        if val is None:
            val = default_value
        if isinstance(val, str) and val.lower() in ("null", "undefined"):
            val = default_value
        if is_mandatory:
            if val is None:
                raise Exception(f"parameter '{key}' missing")
            if isinstance(val, str) and not val.strip():
                raise Exception(f"parameter '{key}' cannot be empty")
        if val is not None:
            try:
                if data_type.startswith("list:") and ":" in data_type:
                    inner_type = data_type.split(":")[1]
                    val_list = TYPE_MAP["list"](val)
                    val = [TYPE_MAP[inner_type](x) for x in val_list]
                else:
                    val = TYPE_MAP[data_type](val)
            except Exception:
                raise Exception(f"parameter '{key}' invalid type {data_type}")
        if val is not None and allowed_values and val not in allowed_values:
            raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        if val is not None and regex_pattern:
            import re
            if not re.match(regex_pattern, str(val)):
                raise Exception(custom_error if custom_error else f"parameter '{key}' format invalid")
        output_dict[key] = val
    return output_dict

def func_converter_number(data_type: str, process_mode: str, value: any) -> any:
    """Encode strings into specific-size integers or decode them back using a custom charset."""
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}
    charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"
    if data_type not in type_limits:
        raise ValueError(f"invalid data type: {data_type}, allowed: {list(type_limits.keys())}")
    base = len(charset)
    max_len = type_limits[data_type]
    if process_mode == "encode":
        val_str = str(value)
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
    if process_mode == "decode":
        try:
            num_val = int(value)
        except Exception:
            raise ValueError("invalid integer for decoding")
        decoded_chars = []
        while num_val > 0:
            num_val, reminder = divmod(num_val, base)
            decoded_chars.append(charset[reminder])
        return "".join(decoded_chars[::-1][1:]) if decoded_chars else ""
