import os
def function_render_html(name: str):
    if ".." in name: 
        raise Exception("invalid name")
    match = None
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "venv"]
        if f"{name}.html" in files:
            match = os.path.join(root, f"{name}.html")
            break
    if not match: 
        raise Exception("file not found")
    with open(match, "r", encoding="utf-8") as file:
        return file.read()
    
async def function_param_read(request, mode, config):
    if mode == "query":
        param = dict(request.query_params)
    elif mode == "form":
        form_data = await request.form()
        param = {k: v for k, v in form_data.items() if isinstance(v, str)}
        param.update({
            k: [f for f in form_data.getlist(k) if getattr(f, "filename", None)]
            for k in form_data.keys()
            if any(getattr(f, "filename", None) for f in form_data.getlist(k))
        })
    elif mode == "body":
        param = await request.json()
    else:
        raise Exception(f"Invalid mode: {mode}")
    def cast(value, dtype):
        if dtype == "int":
            return int(value)
        if dtype == "float":
            return float(value)
        if dtype == "bool":
            return str(value).lower() in ("1", "true", "yes", "on")
        if dtype == "list":
            if isinstance(value, str):
                return [v.strip() for v in value.split(",")]
            if isinstance(value, list):
                return value
            return [value]
        if dtype == "file":
            return value if isinstance(value, list) else [value]
        return value
    for key, dtype, mandatory, default in config:
        if mandatory and key not in param:
            raise Exception(f"{key} missing from {mode} param")
        value = param.get(key, default)
        if dtype and value is not None:
            try:
                value = cast(value, dtype)
            except Exception:
                raise Exception(f"{key} must be of type {dtype}")
        param[key] = value
    return param
 
