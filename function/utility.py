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
    return None

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
