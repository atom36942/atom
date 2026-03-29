import os, sys, json, uuid, time, random, string, re, subprocess

# config
input_path = "curl.txt"
out_path = "tmp/curl_output.txt"
fail_path = "tmp/curl_fail.log"
baseurl = "http://127.0.0.1:8000"
token_root = ""
username = uuid.uuid4().hex
username_bigint = str(random.randint(10**15, 10**18))
token = ""

# init
os.makedirs("tmp", exist_ok=True)
with open(out_path, "w") as f: f.write("")

# parse
with open(input_path, "r") as f: lines = f.read().splitlines()
all_cmds, cur = [], ""
for line in lines:
    cur += line.strip() + " " if line.endswith("\\") else line
    if not line.endswith("\\"):
        if cur.strip() and not cur.strip().startswith("#"): all_cmds.append(cur.strip())
        cur = ""

# run
count, success, fail, total_ms = 0, 0, 0, 0
for cmd in all_cmds:
    if cmd.startswith("0"): continue
    replacements = {"$baseurl": baseurl, "$token_root": token_root, "$username_bigint": username_bigint, "$username": username, "$token": token}
    cmd = re.sub(r'\$[a-zA-Z0-9_]+', lambda m: replacements.get(m.group(0), m.group(0)), cmd)
    url = re.search(r'https?://[^\s"\']+', cmd).group(0) if "http" in cmd else "url"
    print(f"🚀 {url}")
    with open(out_path, "a") as f: f.write(cmd + "\n\n")
    start = time.time()
    res = subprocess.run(f"{cmd} --silent --show-error --write-out '\n%{{http_code}}'", shell=True, capture_output=True, text=True)
    ms = int((time.time() - start) * 1000)
    out = res.stdout.strip().split("\n")
    status, body = out[-1] if out else "000", "\n".join(out[:-1])
    total_ms += ms; count += 1
    if status == "200":
        print(f"✅ Success ({ms}ms)"); success += 1
        if url.split("?")[0].rstrip("/").endswith("/auth/login-password-username"):
            try:
                is_root_login = '"username":"atom"' in cmd.replace(" ", "").replace("'", '"')
                data = json.loads(body).get("message", {})
                if isinstance(data, dict) and (tok_obj := data.get("token")):
                    token_str = tok_obj.get("token") if isinstance(tok_obj, dict) else str(tok_obj)
                    if token_str: 
                        token = token_str
                        if is_root_login: token_root = token_str
            except: pass
    else:
        print(f"❌ {body or res.stderr}"); fail += 1
        with open(fail_path, "a" if fail > 1 else "w") as f: f.write(f"{cmd}\n{body or res.stderr}\n\n")

# summary
avg_ms = total_ms // count if count else 0
print("-" * 38)
print("📊 Curl Execution Summary")
print(f"🚀 Total: {count}")
print(f"✅ Success: {success}")
print(f"❌ Fail: {fail}")
print(f"⏳ Avg Response Time: {avg_ms}ms")
print(f"📄 Report : {out_path}")
if fail > 0: print(f"📄 Failed responses saved in: {fail_path}")
print("-" * 38)
