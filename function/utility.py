import sys
def function_check_required_env(config, required_keys):
    missing = [key for key in required_keys if not config.get(key)]
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return None

import os
def function_delete_files(folder_path=".", extension_list=None, file_prefix_list=None):
    if extension_list is None:
        extension_list = []
    if file_prefix_list is None:
        file_prefix_list = []
    skip_dirs = ('venv', 'env', '__pycache__', 'node_modules')
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if not (d.startswith('.') or d.lower() in skip_dirs)]
        for filename in files:
            if any(filename.endswith(ext) for ext in extension_list) or any(filename.startswith(prefix) for prefix in file_prefix_list):
                file_path = os.path.join(root, filename)
                os.remove(file_path)
    return None
