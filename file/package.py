import json
import subprocess
import sys

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

# upgrade pip first
subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

# get outdated packages
out = subprocess.check_output(
    [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"]
)
packages = [p["name"] for p in json.loads(out)]

failed = []
upgraded = []

for pkg in packages:
    print(f"\nUpgrading {pkg} ...")
    res = run([
        sys.executable, "-m", "pip", "install",
        "--upgrade",
        "--upgrade-strategy", "only-if-needed",
        pkg
    ])

    if res.returncode == 0:
        upgraded.append(pkg)
        print(f"✓ {pkg}")
    else:
        failed.append(pkg)
        print(f"✗ {pkg} (skipped due to conflict)")

print("\nSummary")
print("Upgraded:", upgraded)
print("Skipped :", failed)
