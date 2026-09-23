"""Atom request functions."""

async def func_converter_number(*, datatype: str, mode: str, x: str) -> any:
    """Encodes a string to an integer or decodes an integer to a string based on base-39 charset mapping."""
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}
    charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"
    if datatype not in type_limits: raise ValueError(f"invalid type: {datatype}, allowed: {list(type_limits.keys())}")
    base = len(charset)
    max_len = type_limits[datatype]
    if mode == "encode":
        val_str = str(x)
        val_len = len(val_str)
        if val_len > max_len: raise ValueError(f"input too long {val_len} > {max_len}")
        result_num = val_len
        for char in val_str:
            char_idx = charset.find(char)
            if char_idx == -1: raise ValueError("invalid character in input")
            result_num = result_num * base + char_idx
        return result_num
    elif mode == "decode":
        try: num_val = int(x)
        except Exception: raise ValueError("invalid integer for decoding")
        decoded_chars = []
        while num_val > 0:
            num_val, reminder = divmod(num_val, base)
            decoded_chars.append(charset[reminder])
        return "".join(decoded_chars[::-1][1:]) if decoded_chars else ""
    else:
        raise ValueError(f"invalid mode: {mode}")

def func_query_bool_parse(value: any, default: bool = False) -> bool:
    """Parse a query-string boolean, retaining legacy 1/0 compatibility."""
    if value is None: return default
    if isinstance(value, bool): return value
    normalized = str(value).strip().lower()
    if normalized in ("true", "1"): return True
    if normalized in ("false", "0"): return False
    raise ValueError(f"invalid boolean query value: {value!r}; expected 'true' or 'false'")

async def func_request_param_read(*, request: any, mode: str, strict: bool, param_specs: list) -> dict:
    """Extract and validate request parameters; specs use bool ``required`` and optional ``allowed``/``default`` fields."""
    if not isinstance(strict, bool): raise Exception("strict must be bool")
    params_dict = {}
    header_params = {k.lower(): v for k, v in request.headers.items()}
    if mode == "query":
        params_dict = dict(request.query_params)
    elif mode == "form":
        form_data = await request.form()
        params_dict = {key: val for key, val in form_data.items() if isinstance(val, str)}
        for key in form_data.keys():
            files = [x for x in form_data.getlist(key) if not isinstance(x, str)]
            if files:
                params_dict[key] = files
    elif mode == "body":
        try:
            json_payload = await request.json()
        except Exception:
            json_payload = None
        params_dict = json_payload if isinstance(json_payload, dict) else {"body": json_payload}
    elif mode == "header":
        params_dict = header_params
    else:
        raise Exception(f"invalid mode: {mode}")
    if param_specs is None: return params_dict
    import orjson
    def smart_dict(v):
        if v is None: return {}
        if isinstance(v, dict): return v
        if isinstance(v, str):
            v = v.strip()
            if not v: return {}
            if v.startswith("{"): return orjson.loads(v)
        return {}
    def smart_list(v):
        if v is None: return []
        if isinstance(v, list): return v
        if isinstance(v, str):
            v = v.strip()
            if not v: return []
            if v.startswith("[") or v.startswith("{"):
                parsed = orjson.loads(v)
                return parsed if isinstance(parsed, list) else [parsed]
            return [x.strip() for x in v.split(",") if x.strip()]
        return [v]
    def smart_bool(v):
        if isinstance(v, bool): return v
        value = str(v).strip().lower()
        if value in ("true", "1", "yes", "on", "ok"): return True
        if value in ("false", "0", "no", "off"): return False
        raise ValueError(f"invalid boolean value: {v!r}")
    TYPE_MAP = {
        "int": int, "bigint": int, "smallint": int, "integer": int, "int4": int, "int8": int,
        "float": float, "number": float, "numeric": float,
        "str": str, "any": lambda v: v, 
        "bool": smart_bool,
        "dict": smart_dict, "object": smart_dict,
        "file": lambda v: [x for x in (v if isinstance(v, list) else [v] if v is not None else []) if hasattr(x, "file")],
        "list": smart_list
    }
    output_dict = params_dict.copy() if not strict else {}
    for param_spec in param_specs:
        if not isinstance(param_spec, dict): raise Exception(f"invalid parameter specification: expected dict, got {type(param_spec)}")
        if "name" not in param_spec or "type" not in param_spec: raise Exception("parameter specification requires 'name' and 'type'")
        key = param_spec["name"]
        dtype = param_spec["type"]
        is_required = param_spec.get("required", False)
        if not isinstance(is_required, bool): raise Exception(f"parameter '{key}' required must be bool")
        allowed_values = param_spec.get("allowed")
        default_value = param_spec.get("default")
        if dtype not in TYPE_MAP and not dtype.startswith("list:"): raise Exception(f"parameter '{key}' has invalid dtype '{dtype}'")
        if is_required and default_value is not None: raise Exception(f"parameter '{key}' is required, default must be None")
        if default_value is not None and allowed_values is not None and default_value not in allowed_values:
            raise Exception(f"parameter '{key}' default '{default_value}' violating allowed_values: {allowed_values}")
        if allowed_values is not None and not isinstance(allowed_values, (list, tuple)): raise Exception(f"parameter '{key}' allowed_values must be a list or tuple")
        val = params_dict.get(key)
        if val is None:
            val = header_params.get(key.lower())
        if val is None:
            val = default_value
        if isinstance(val, str) and val.lower() in ("null", "undefined"):
            val = default_value
        if dtype == "file" and isinstance(val, str):
            hint = f" received '{val}'" if val else ""
            raise Exception(f"parameter '{key}' expected file upload but received text field{hint}; use curl -F '{key}=@/path/to/file'")
        if is_required:
            if val is None:
                raise Exception(f"parameter '{key}' missing")
            if isinstance(val, str) and not val.strip():
                raise Exception(f"parameter '{key}' cannot be empty")
        if val is not None:
            try:
                if dtype.startswith("list:") and ":" in dtype:
                    inner_type = dtype.split(":")[1]
                    val_list = TYPE_MAP["list"](val)
                    val = [TYPE_MAP[inner_type](x) for x in val_list]
                else:
                    val = TYPE_MAP[dtype](val)
            except Exception:
                raise Exception(f"parameter '{key}' invalid type {dtype}")
        if is_required:
            if dtype == "file" and (not isinstance(val, list) or len(val) == 0):
                raise Exception(f"parameter '{key}' missing or invalid file upload")
            if dtype == "list" and (not isinstance(val, list) or len(val) == 0):
                 raise Exception(f"parameter '{key}' missing or empty list")
        if val is not None and allowed_values is not None and val not in allowed_values: raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        output_dict[key] = val
    return output_dict

def func_attach_user_audit_fields(*, request: any, obj_list: list, field: str = "created_by_id") -> list:
    """Inject current user ID into payload objects for audit field tracking."""
    user_id = getattr(getattr(request, "state", None), "user", {}).get("id")
    if user_id:
        return [dict(item, **{field: user_id}) for item in obj_list]
    return obj_list

async def func_extract_request_object_list(*, request: any) -> list:
    """Extract single or batch object payload list from request body."""
    app_state = request.app.state
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=False, param_specs=[])
    return ob.get("obj_list", [ob])
