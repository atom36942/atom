def func_password_hash(*, password_raw: any) -> str:
    """Generate SHA-256 hash of the provided password string."""
    import hashlib
    return hashlib.sha256(str(password_raw).encode()).hexdigest()

async def func_token_encode(*, user: dict, config_token_secret_key: str, config_token_expiry_sec: int, config_token_refresh_expiry_sec: int, config_token_key: list) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    import jwt, orjson, time
    if user is None:
        return None
    payload_dict = {k: user.get(k) for k in config_token_key} if config_token_key else dict(user) if isinstance(user, dict) else user
    serialized_payload = orjson.dumps(payload_dict, default=str).decode("utf-8")
    now_ts = int(time.time())
    access_token = jwt.encode({"exp": now_ts + config_token_expiry_sec, "data": serialized_payload, "type": "access"}, config_token_secret_key)
    refresh_token = jwt.encode({"exp": now_ts + config_token_refresh_expiry_sec, "data": serialized_payload, "type": "refresh"}, config_token_secret_key)
    return {"token": access_token, "token_refresh": refresh_token, "token_expiry_sec": config_token_expiry_sec, "token_refresh_expiry_sec": config_token_refresh_expiry_sec}

async def func_otp_generate(*, client_postgres_pool: any, email: str, mobile: str) -> int:
    """Generate a random 6-digit OTP and store it in PostgreSQL for a given email or mobile."""
    import random
    otp = random.randint(100000, 999999)
    query = "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3);"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, otp, email.strip().lower() if email else None, mobile.strip() if mobile else None)
    return otp

async def func_otp_verify(*, client_postgres_pool: any, otp: int, email: str, mobile: str, config_expiry_sec_otp: int) -> None:
    """Verify an OTP for email or mobile within its expiration window."""
    if not otp:
        raise Exception("otp code missing")
    if not email and not mobile:
        raise Exception("missing both email and mobile")
    if email and mobile:
        raise Exception("provide only one identifier")
    if email:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email.strip().lower()
    else:
        query = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile.strip()
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, identifier)
        if not records:
            raise Exception("otp not found")
        if records[0]["otp"] != otp:
            raise Exception("invalid otp code")
        if not records[0]["is_active"]:
            raise Exception("otp code expired")
    return None

async def func_request_param_read(*, request: any, mode: str, config: list, strict: int) -> dict:
    """Extract, validate, and type-cast request parameters from query, form, body or headers."""
    params_dict = {}
    header_params = {k.lower(): v for k, v in request.headers.items()}
    if mode == "query":
        params_dict = dict(request.query_params)
    elif mode == "form":
        form_data = await request.form()
        params_dict = {key: val for key, val in form_data.items() if isinstance(val, str)}
        for key in form_data.keys():
            files = [x for x in form_data.getlist(key) if getattr(x, "filename", None)]
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
    if config is None:
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
    output_dict = params_dict.copy() if not strict else {}
    for param in config:
        if not isinstance(param, (list, tuple)):
            raise Exception(f"invalid configuration format: expected list or tuple, got {type(param)}")
        param_len = len(param)
        if param_len < 5:
            param_key = param[0] if param_len > 0 else "unknown"
            raise Exception(f"invalid config tuple length {param_len} for '{param_key}': (key, dtype, is_mandatory, allowed_values, default_value) are required")
        key = param[0]
        dtype = param[1]
        is_mandatory = int(param[2])
        allowed_values = param[3]
        default_value = param[4]
        regex_info = param[5] if param_len > 5 else None
        regex_pattern = regex_info[0] if isinstance(regex_info, (list, tuple)) and len(regex_info) > 0 else None
        custom_error = regex_info[1] if isinstance(regex_info, (list, tuple)) and len(regex_info) > 1 else None
        description = param[6] if param_len > 6 else None
        if dtype not in TYPE_MAP and not dtype.startswith("list:"):
            raise Exception(f"parameter '{key}' has invalid dtype '{dtype}'")
        if is_mandatory == 1 and default_value is not None:
            raise Exception(f"parameter '{key}' is mandatory, default_value must be None")
        if default_value is not None and allowed_values and default_value not in allowed_values:
            raise Exception(f"parameter '{key}' default '{default_value}' violating allowed_values: {allowed_values}")
        if allowed_values is not None and not isinstance(allowed_values, (list, tuple)):
            raise Exception(f"parameter '{key}' allowed_values must be a list or tuple")
        val = params_dict.get(key)
        if val is None:
            val = header_params.get(key.lower())
        if val is None:
            val = default_value
        if isinstance(val, str) and val.lower() in ("null", "undefined"):
            val = default_value
        if is_mandatory == 1:
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
        if val is not None and allowed_values and val not in allowed_values:
            raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        if val is not None and regex_pattern:
            import re
            if not re.match(regex_pattern, str(val)):
                raise Exception(custom_error if custom_error else f"parameter '{key}' format invalid")
        output_dict[key] = val
    return output_dict