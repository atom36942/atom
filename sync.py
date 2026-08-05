"""
Atom framework updater.

Pulls the latest core framework files (and the docs/ folder) from the upstream
Atom repo and overwrites the local copies — so you can update without a full
re-clone. Only the files in `files_to_sync` are touched; your extension files
(config_extend.py, function_extend.py, custom routers), .env, and other project
files are left untouched.

Usage:  venv/bin/python sync.py   (run from the repo root; re-install deps if
requirements.txt changed). See docs/extend.md for the extend-without-forking model.
"""

# packages
import ast
import os
import subprocess

# config
REPO_URL = "https://github.com/atom36942/atom.git"
files_to_sync = [
    "main.py",
    "function.py",
    "config.py",
    "router/index.py",
    "router/auth.py",
    "router/my.py",
    "router/public.py",
    "router/private.py",
    "router/admin.py",
    "static/api.html",
    "readme.md",
    "Dockerfile",
    ".gitignore",
    "docs",
    "script/consumer_postgres_create.py",
    "script/consumer_postgres_update.py",
    "script/manual_postgres_cleaner.py",
    "script/manual_postgres_ingestion.py",
    "script/manual_postgres_secure.py",
    "script/worker_resume_parser.py",
    "script/worker_users_delete.py",
    "sync.py",
]
if not os.path.exists("requirements.txt"):
    files_to_sync.append("requirements.txt")

# fetch upstream
print(f"Fetching latest changes from {REPO_URL}...\n")
subprocess.run(["git", "fetch", REPO_URL, "main"])

# overwrite listed files
print("\nSyncing the following files:")
for file in files_to_sync:
    print(f" -> {file}")
checkout_cmd = ["git", "checkout", "FETCH_HEAD", "--"] + files_to_sync
subprocess.run(checkout_cmd)

# check extension files
def check_var_in_file(file_path: str, var_name: str) -> bool:
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        return True
    except Exception:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if f"{var_name} =" in content or f"{var_name}=" in content:
            return True
    return False

def extract_var_from_config(var_name: str) -> str | None:
    if not os.path.exists("config.py"):
        return None
    try:
        with open("config.py", "r", encoding="utf-8") as f:
            code = f.read()
        tree = ast.parse(code)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        return ast.get_source_segment(code, node)
    except Exception:
        pass
    return None

if not os.path.exists("function_extend.py"):
    print("\nCreating function_extend.py...")
    with open("function_extend.py", "w", encoding="utf-8") as f:
        f.write("# function_extend.py\n")

if not os.path.exists("config_extend.py"):
    print("\nCreating config_extend.py...")
    with open("config_extend.py", "w", encoding="utf-8") as f:
        f.write("# config_extend.py\n")

for var in ["config_postgres", "config_api"]:
    if not check_var_in_file("config_extend.py", var):
        segment = extract_var_from_config(var)
        if segment:
            print(f"Copying {var} into config_extend.py...")
            with open("config_extend.py", "a", encoding="utf-8") as f:
                if os.path.getsize("config_extend.py") > 0:
                    f.write("\n\n")
                f.write(segment + "\n")

# done
print("\nFiles synced successfully!")

