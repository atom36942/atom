import subprocess

files_to_sync = [
    "main.py",
    "config.py",
    "function.py",
    "static/api.html",
    "readme.md",
    ".gitignore",
    "router/index.py",
    "router/auth.py",
    "router/my.py",
    "router/public.py",
    "router/private.py",
    "router/admin.py"
]

print("Fetching latest changes from remote...\n")
subprocess.run(["git", "fetch", "origin"])

print("\nSyncing the following files:")
for file in files_to_sync:
    print(f" -> {file}")

checkout_cmd = ["git", "checkout", "origin/main", "--"] + files_to_sync
subprocess.run(checkout_cmd)

print("\nFiles synced successfully!")
