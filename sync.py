import subprocess
import os

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

]

if not os.path.exists("requirements.txt"):
    files_to_sync.append("requirements.txt")

print(f"Fetching latest changes from {REPO_URL}...\n")
subprocess.run(["git", "fetch", REPO_URL, "main"])

print("\nSyncing the following files:")
for file in files_to_sync:
    print(f" -> {file}")

checkout_cmd = ["git", "checkout", "FETCH_HEAD", "--"] + files_to_sync
subprocess.run(checkout_cmd)

print("\nFiles synced successfully!")
