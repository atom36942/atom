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
import subprocess
import os

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

# done
print("\nFiles synced successfully!")
