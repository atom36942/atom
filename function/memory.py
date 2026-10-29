# import
import asyncio
import gc
import platform
import sys
import time
import tracemalloc
from collections import Counter
import psutil
from starlette.datastructures import State
try: import resource
except ImportError: resource = None    # Windows has no resource module

# function
async def func_memory_deep_size(*, obj, max_objects: int = 1_000_000, yield_every: int = 5000) -> tuple:
    """Bytes held by obj and everything it contains (dicts, lists, tuples, sets, object attributes), each object counted once.

    Returns (bytes, is_partial): the walk stops after max_objects objects. Every yield_every objects it lets other requests run;
    children are copied onto the walk's own stack in one step, so a dict changing meanwhile cannot break the walk (sizes are then approximate).
    """
    seen, stack, total = set(), [obj], 0
    while stack:
        item = stack.pop()
        if id(item) in seen: continue
        if len(seen) >= max_objects: return total, True
        seen.add(id(item))
        if len(seen) % yield_every == 0: await asyncio.sleep(0)
        total += sys.getsizeof(item, 0)
        if isinstance(item, (str, bytes, bytearray, int, float, bool, type(None))): continue
        if isinstance(item, dict): stack.extend(item.keys()); stack.extend(item.values())
        elif isinstance(item, (list, tuple, set, frozenset)): stack.extend(item)
        if hasattr(item, "__dict__") and not isinstance(item, type): stack.append(vars(item))
    return total, False

async def func_memory_report(*, app_state: State, top_types: int = 20, yield_every: int = 5000) -> dict:
    """RAM of this worker process, the size of each in-memory item Atom keeps on app_state, the most common Python object types, and allocation tracing.

    Sizes and counts only, never values. Clients (database pools, SDKs) are skipped, since walking them measures their libraries, not the app's data; the monitor's app view lists them.
    Runs on the event loop but yields every yield_every objects, so requests keep being served while a large report is built.
    """
    process = psutil.Process()
    with process.oneshot():
        memory, cpu = process.memory_info(), process.cpu_times()
        info = {"pid": process.pid, "threads": process.num_threads(), "uptime_sec": round(time.time() - process.create_time())}
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None
    system = psutil.virtual_memory()
    state = vars(app_state)["_state"]
    items = []
    for name, value in list(state.items()):    # a copy: the state may gain entries while this yields
        if name.startswith(("func_", "config_", "runtime_memory_trace_")) or callable(value) and not isinstance(value, (dict, list)): continue
        if name.startswith("client_"): continue
        size, is_partial = await func_memory_deep_size(obj=value, yield_every=yield_every)
        kind = next((prefix for prefix in ("cache", "buffer", "runtime") if name.startswith(prefix + "_")), "extend" if name == "extend" else "other")    # what losing it means: cache is rebuilt, buffer loses rows
        items.append({"name": name, "kind": kind, "type": type(value).__name__, "entries": len(value) if hasattr(value, "__len__") else None, "bytes": size, "is_partial": is_partial})
    config_names = [name for name in state if name.startswith("config_")]
    config_size, config_partial = await func_memory_deep_size(obj=[state[name] for name in config_names], yield_every=yield_every)
    items.append({"name": "config_* (all settings)", "kind": "config", "type": "settings", "entries": len(config_names), "bytes": config_size, "is_partial": config_partial})
    counts, sizes = Counter(), Counter()
    for i, obj in enumerate(gc.get_objects()):    # containers only: str and int are not tracked by the garbage collector
        if i % yield_every == 0: await asyncio.sleep(0)
        name = type(obj).__name__
        counts[name] += 1
        sizes[name] += sys.getsizeof(obj, 0)
    return {
        "process": {**info, "rss_bytes": memory.rss, "vms_bytes": memory.vms, "peak_rss_bytes": peak if peak is None or sys.platform == "darwin" else peak * 1024,    # ru_maxrss is bytes on macOS, KB on Linux
                    "cpu_user_sec": round(cpu.user, 2), "cpu_system_sec": round(cpu.system, 2), "python": platform.python_version(), "workers": getattr(app_state, "config_uvicorn_workers", 1)},
        "system": {"total_bytes": system.total, "available_bytes": system.available, "used_percent": system.percent},
        "app_state": sorted(items, key=lambda item: item["bytes"], reverse=True),
        "objects": {"tracked": sum(counts.values()), "top": [{"type": name, "count": count, "bytes": sizes[name]} for name, count in counts.most_common(top_types)], "gc": [{"generation": i, **stat} for i, stat in enumerate(gc.get_stats())]},
        "trace": func_memory_trace_report(app_state=app_state),
    }

def func_memory_trace_report(*, app_state: State, top_lines: int = 20) -> dict:
    """While tracing, the source lines that allocated the most memory still in use."""
    if not tracemalloc.is_tracing(): return {"is_tracing": False}
    current, peak = tracemalloc.get_traced_memory()
    stats = tracemalloc.take_snapshot().filter_traces((tracemalloc.Filter(False, tracemalloc.__file__), tracemalloc.Filter(False, "<frozen importlib._bootstrap>"))).statistics("lineno")[:top_lines]
    return {"is_tracing": True, "started_at": getattr(app_state, "runtime_memory_trace_started_at", None), "stops_at": getattr(app_state, "runtime_memory_trace_stops_at", None), "traced_bytes": current, "traced_peak_bytes": peak,
            "top": [{"file": stat.traceback[0].filename, "line": stat.traceback[0].lineno, "bytes": stat.size, "count": stat.count} for stat in stats]}

def func_memory_trace(*, app_state: State, action: str, duration_sec: int = 300) -> dict:
    """Start or stop tracemalloc in this worker. It slows every allocation, so it stops by itself after duration_sec."""
    if action == "start":
        if not tracemalloc.is_tracing(): tracemalloc.start(1)
        app_state.runtime_memory_trace_started_at = int(time.time())
        app_state.runtime_memory_trace_stops_at = int(time.time()) + duration_sec
        handle = getattr(app_state, "runtime_memory_trace_timer", None)
        if handle: handle.cancel()
        app_state.runtime_memory_trace_timer = asyncio.get_running_loop().call_later(duration_sec, tracemalloc.stop)
    elif action == "stop":
        handle = getattr(app_state, "runtime_memory_trace_timer", None)
        if handle: handle.cancel()
        app_state.runtime_memory_trace_timer = None
        tracemalloc.stop()
    else: raise Exception(f"invalid action: {action}")
    return {"is_tracing": tracemalloc.is_tracing(), "stops_at": app_state.runtime_memory_trace_stops_at if tracemalloc.is_tracing() else None}
