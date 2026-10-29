# command: venv/bin/python -m script.load_test --concurrency 50 --duration 20

# info: Load tests a running Atom server: many concurrent virtual users per route, reporting requests/sec, p50/p95/p99 latency and error rate. Never point it at production.

# import
import argparse
import asyncio
import os
import time
import urllib.parse
import orjson
try: import uvloop
except ImportError: uvloop = None

# config
token = os.getenv("ATOM_LOAD_TOKEN")    # a test user's access token, for routes that need one

# setting
ROUTE_LIST = [
    ("info", "GET", "/info", None, False, False),
    ("public-read-cached", "GET", "/public/object-read?table=test&limit=20", None, False, False),
    ("public-read-db", "GET", "/public/object-read?table=test&limit=20&is_disable_cache=true", None, False, False),
    ("my-read", "GET", "/my/object-read?table=test&limit=20", None, True, False),
    ("my-create", "POST", "/my/object-create?table=test", {"title": "load test"}, True, True),
]
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")

# logic
def args_read():
    parser = argparse.ArgumentParser(description="Load test a running Atom server.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=50, help="virtual users per route")
    parser.add_argument("--duration", type=float, default=20, help="seconds per route")
    parser.add_argument("--route", action="append", help="route name to run; repeat for several (default: all that apply)")
    parser.add_argument("--write", action="store_true", help="include routes that create rows")
    parser.add_argument("--allow-remote", action="store_true", help="allow a non-localhost url")
    return parser.parse_args()

def percentile(*, sorted_list: list, pct: float) -> float:
    if not sorted_list: return 0.0
    return sorted_list[min(len(sorted_list) - 1, int(len(sorted_list) * pct / 100))]

async def response_read(*, reader: asyncio.StreamReader) -> tuple:
    """Read one HTTP/1.1 response; returns (status, body, keep_alive)."""
    head = await reader.readuntil(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split(" ", 2)[1])
    headers = {k.strip().lower(): v.strip() for k, _, v in (line.partition(":") for line in lines[1:] if line)}
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body = b""
        while (size := int((await reader.readuntil(b"\r\n")).split(b";")[0], 16)):
            body += (await reader.readexactly(size + 2))[:-2]
        await reader.readuntil(b"\r\n")
    else:
        body = await reader.readexactly(int(headers.get("content-length", 0)))
    return status, body, headers.get("connection", "").lower() != "close"

async def route_run(*, host: str, port: int, request: bytes, concurrency: int, duration: float) -> dict:
    """Each virtual user keeps one connection open and sends requests back to back until the deadline."""
    latency_list, error_count, error_sample = [], 0, None
    deadline = time.perf_counter() + duration
    async def user():
        nonlocal error_count, error_sample
        reader = writer = None
        while time.perf_counter() < deadline:
            start = time.perf_counter()
            try:
                if writer is None: reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), 10)
                writer.write(request)
                status, body, keep_alive = await asyncio.wait_for(response_read(reader=reader), 30)
                if status >= 400:
                    error_count += 1
                    error_sample = error_sample or f"HTTP {status}: {body[:120].decode(errors='replace')}"
                if not keep_alive: writer.close(); writer = None
            except Exception as e:
                error_count += 1
                error_sample = error_sample or f"{type(e).__name__}: {e}"
                if writer: writer.close()
                writer = None
            latency_list.append((time.perf_counter() - start) * 1000)
        if writer: writer.close()
    started = time.perf_counter()
    await asyncio.gather(*(user() for _ in range(concurrency)))
    elapsed = time.perf_counter() - started
    latency_list.sort()
    total = len(latency_list)
    return {"req_sec": total / elapsed if elapsed else 0, "p50": percentile(sorted_list=latency_list, pct=50), "p95": percentile(sorted_list=latency_list, pct=95), "p99": percentile(sorted_list=latency_list, pct=99), "error_pct": 100 * error_count / total if total else 0, "total": total, "error_sample": error_sample}

def request_build(*, method: str, host: str, port: int, path: str, body: dict | None, token: str | None) -> bytes:
    data = orjson.dumps(body) if body is not None else b""
    head = [f"{method} {path} HTTP/1.1", f"Host: {host}:{port}", "Connection: keep-alive", f"Content-Length: {len(data)}"]
    if body is not None: head.append("Content-Type: application/json")
    if token: head.append(f"Authorization: Bearer {token}")
    return ("\r\n".join(head) + "\r\n\r\n").encode() + data

def url_parse(*, url: str, allow_remote: bool) -> tuple:
    """(host, port) of a plain-http url; refuses a non-local host unless allowed."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if not allow_remote and host not in LOCAL_HOSTS and not host.endswith((".localhost", ".test")): raise SystemExit(f"refusing non-local url {url}; pass --allow-remote for a test server, never production")
    if parsed.scheme != "http": raise SystemExit("only http:// urls are supported; test the app directly, not through a TLS proxy")
    return host, parsed.port or 80

def route_select(*, route_names: list | None, token: str | None, write: bool) -> list:
    """(name, method, path, body) of the routes to run; skips ones that need a token or --write."""
    if route_names and (unknown := set(route_names) - {name for name, *_ in ROUTE_LIST}): raise SystemExit(f"unknown route: {', '.join(sorted(unknown))}; choose from {', '.join(name for name, *_ in ROUTE_LIST)}")
    selected = []
    for name, method, path, body, needs_token, writes in ROUTE_LIST:
        if route_names and name not in route_names: continue
        if needs_token and not token: print(f"skip {name}: set ATOM_LOAD_TOKEN to a test user's access token"); continue
        if writes and not write: print(f"skip {name}: pass --write to include routes that create rows"); continue
        selected.append((name, method, path, body))
    if not selected: raise SystemExit("no routes to run")
    return selected

async def routes_measure(*, args, host, port, selected, token):
    print(f"\n{args.url} | {args.concurrency} users | {args.duration:g}s per route\n")
    print(f"{'route':<22}{'req/s':>9}{'p50 ms':>9}{'p95 ms':>9}{'p99 ms':>9}{'errors':>9}{'requests':>10}")
    for name, method, path, body in selected:
        request = request_build(method=method, host=host, port=port, path=path, body=body, token=token)
        await route_run(host=host, port=port, request=request, concurrency=1, duration=0.5)    # warm-up: fills caches and pools before timing
        r = await route_run(host=host, port=port, request=request, concurrency=args.concurrency, duration=args.duration)
        print(f"{name:<22}{r['req_sec']:>9.0f}{r['p50']:>9.1f}{r['p95']:>9.1f}{r['p99']:>9.1f}{r['error_pct']:>8.1f}%{r['total']:>10}")
        if r["error_sample"]: print(f"{'':<22}first error: {r['error_sample']}")
    print("\nThe client shares this machine's CPU with the server; compare runs on the same setup only.")

def main():
    args = args_read()
    if args.concurrency < 1 or args.duration <= 0: raise SystemExit("concurrency must be >= 1 and duration > 0")
    host, port = url_parse(url=args.url, allow_remote=args.allow_remote)
    selected = route_select(route_names=args.route, token=token, write=args.write)
    (uvloop.run if uvloop else asyncio.run)(routes_measure(args=args, host=host, port=port, selected=selected, token=token))

# main
if __name__ == "__main__":
    main()
