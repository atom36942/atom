"""Update Atom-owned files while preserving developer-only files.

Run from the project root with ``python sync.py``. The latest upstream updater
is installed and run first. Project updates are then prepared before writing
and rolled back from memory on write failure. No backup files are saved.
The Git index is never changed. See docs/extend.md for recovery instructions.
"""

import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

REPO_URL = "https://github.com/atom36942/atom.git"
files_to_sync = [
    # Individual root files.
    ".dockerignore",
    ".gitignore",
    "Dockerfile",
    "config.py",
    "main.py",
    "readme.md",
    "sync.py",

    # Selected files inside folders (other upstream files are not included).
    "static/api.html",
    "static/pgweb.html",
    "script/consumer_postgres_create.py",
    "script/consumer_postgres_update.py",
    "script/manual_postgres_cleaner.py",
    "script/manual_postgres_ingestion.py",
    "script/manual_postgres_secure.py",
    "script/worker_users_delete.py",
    # Whole folders: discover all their upstream files recursively.
    "docs",
    "function",
    "router",
]

# requirements.txt and config_extend.py are merged separately, not overwritten.
STATE_PATH = ".atom-sync/state.json"


def git(root, *args):
    """Never consume stale FETCH_HEAD or partial output after a failed command."""
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)
    return result.stdout


def safe_path(root, name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in (".", "..", ".git") for p in path.parts) or "\\" in name:
        raise ValueError(f"Unsafe sync path: {name}")
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError(f"Refusing to replace or follow symlink: {target}")
    if target.exists() and not target.is_file():
        raise ValueError(f"Expected a regular file: {name}")
    return target


def is_owned_path(name):
    return any(name == item or name.startswith(item + "/") for item in files_to_sync)


def get_pkg_name(line):
    line = line.strip()
    if not line or line.startswith(("#", "-", "//")):
        return None
    name = re.split(r"[=><~!;\[\s]", line)[0].strip()
    return re.sub(r"[-_.]+", "-", name).lower() if name else None


def merge_requirements(local, upstream):
    if local is None:
        return upstream if upstream.endswith("\n") else upstream + "\n"
    names = {get_pkg_name(line) for line in local.splitlines()}
    missing = []
    for line in upstream.splitlines():
        name = get_pkg_name(line)
        if name and name not in names:
            missing.append(line.strip())
            names.add(name)
    if not missing:
        return local
    return local + ("\n" if local and not local.endswith("\n") else "") + "\n".join(missing) + "\n"


def merge_config_extension(local, config):
    """Seed missing config maps without executing code or replacing overrides."""
    tree = ast.parse(local)
    assigned = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            assigned.update(n.id for target in node.targets for n in ast.walk(target) if isinstance(n, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            assigned.update(alias.asname or alias.name for alias in node.names)
    additions = []
    for node in ast.parse(config).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id in ("config_postgres", "config_api") and target.id not in assigned for target in targets):
                additions.append(ast.get_source_segment(config, node))
    return local + ("\n\n" + "\n\n".join(additions) + "\n" if additions else "")


def prepare_update(root, revision):
    entries = {}
    for record in git(root, "ls-tree", "-r", "-z", revision).split(b"\0"):
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_name.decode("utf-8")
        if is_owned_path(name) or name == "requirements.txt":
            if kind != "blob" or mode not in ("100644", "100755"):
                raise ValueError(f"Unsupported upstream file type: {name}")
            safe_path(root, name)
            entries[name] = (oid, 0o755 if mode == "100755" else 0o644)
    for item in [*files_to_sync, "requirements.txt", "function/__init__.py"]:
        if not any(name == item or name.startswith(item + "/") for name in entries):
            raise ValueError(f"Required upstream path is missing: {item}")

    plan = {}
    owned = {}
    for name, (oid, mode) in sorted(entries.items()):
        content = git(root, "cat-file", "blob", oid)
        if name.endswith(".py"):
            compile(content, name, "exec")
        plan[name] = (content, mode)
        if is_owned_path(name):
            owned[name] = hashlib.sha256(content).hexdigest()

    state_file = safe_path(root, STATE_PATH)
    if state_file.exists():
        state = json.loads(state_file.read_text())
        if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("files"), dict):
            raise ValueError("Unsupported or invalid sync ownership state")
        for name, digest in state["files"].items():
            if not is_owned_path(name):
                raise ValueError(f"Unexpected path in sync ownership state: {name}")
            if name not in owned:
                path = safe_path(root, name)
                if path.exists():
                    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                        raise ValueError(f"Retired Atom file has local edits: {name}. Move your code to a custom module before syncing.")
                    plan[name] = None

    requirements = safe_path(root, "requirements.txt")
    local_requirements = requirements.read_text() if requirements.exists() else None
    merged = merge_requirements(local_requirements, plan["requirements.txt"][0].decode())
    plan["requirements.txt"] = (merged.encode(), requirements.stat().st_mode & 0o777 if requirements.exists() else 0o644)

    extension = safe_path(root, "config_extend.py")
    local_extension = extension.read_text() if extension.exists() else "# config_extend.py\n"
    merged = merge_config_extension(local_extension, plan["config.py"][0].decode())
    plan["config_extend.py"] = (merged.encode(), extension.stat().st_mode & 0o777 if extension.exists() else 0o644)
    state = {"version": 1, "revision": revision, "files": owned}
    plan[STATE_PATH] = ((json.dumps(state, indent=2, sort_keys=True) + "\n").encode(), 0o600)
    return plan


def atomic_write(path, content, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".atom-sync-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def apply_update(root, plan):
    """Retain destination contents in memory for rollback during this run."""
    before = {}
    for name in plan:
        path = safe_path(root, name)
        before[name] = (path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else None
    touched = []
    try:
        for name, value in plan.items():
            path = safe_path(root, name)
            touched.append(name)
            if value is None:
                path.unlink(missing_ok=True)
                print(f" -> removed retired file {name}")
            else:
                atomic_write(path, *value)
                print(f" -> {name}")
    except BaseException:
        failures = []
        for name in reversed(touched):
            try:
                path = safe_path(root, name)
                if before[name] is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, *before[name])
            except Exception:
                failures.append(name)
        if failures:
            print(f"Rollback incomplete for {', '.join(failures)}. Recover affected files from your saved Git version", file=sys.stderr)
        else:
            print("Update failed; previous files restored.", file=sys.stderr)
        raise


@contextmanager
def sync_lock(root):
    directory = root / ".atom-sync"
    if directory.is_symlink():
        raise ValueError("Refusing symlinked .atom-sync directory")
    directory.mkdir(mode=0o700, exist_ok=True)
    lock = directory / "lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError("Another sync may be running. If a previous run was interrupted, review the working tree and confirm no updater is running before removing .atom-sync/lock.") from None
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def project_root(root):
    root = Path(root).resolve()
    git_root = Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if root != git_root:
        raise ValueError("Run the updater in the Atom project's Git root")
    return root


def fetch_revision(root, repo_url):
    print("Fetching Atom main...", flush=True)
    git(root, "fetch", "--no-tags", repo_url, "main")
    return git(root, "rev-parse", "--verify", "FETCH_HEAD^{commit}").decode().strip()


def apply_revision(root, revision):
    plan = prepare_update(root, revision)
    apply_update(root, plan)
    print("Files synced successfully! Restart the app; reinstall dependencies if requirements.txt changed.")


def sync(root, repo_url=REPO_URL):
    """Apply using this loaded implementation (also used by integration tests)."""
    root = project_root(root)
    with sync_lock(root):
        apply_revision(root, fetch_revision(root, repo_url))


def bootstrap_sync(root, repo_url=REPO_URL):
    """Install the fetched updater, then run it under the same parent-held lock."""
    root = project_root(root)
    with sync_lock(root):
        revision = fetch_revision(root, repo_url)
        record = git(root, "ls-tree", revision, "--", "sync.py").decode().strip()
        if not record:
            raise ValueError("Upstream sync.py is missing")
        metadata, name = record.split("\t", 1)
        mode, kind, oid = metadata.split()
        if name != "sync.py" or kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError("Upstream sync.py must be a regular Python file")
        source = git(root, "cat-file", "blob", oid)
        compile(source, "sync.py", "exec")
        script = safe_path(root, "sync.py")
        previous = (script.read_bytes(), script.stat().st_mode & 0o777) if script.exists() else None
        atomic_write(script, source, 0o755 if mode == "100755" else 0o644)
        print("Running the latest Atom updater...", flush=True)
        try:
            # The child applies this exact commit; it never re-fetches or bootstraps.
            result = subprocess.run([sys.executable, str(script), "--apply-revision", revision], cwd=root)
        except OSError:
            if previous is None:
                script.unlink(missing_ok=True)
            else:
                atomic_write(script, *previous)
            raise
        if result.returncode:
            raise ValueError(f"Latest Atom updater failed (exit {result.returncode}); review the working tree before retrying")


def apply_bootstrapped_revision(root, revision):
    """Internal child entry: validate the parent lock and pinned updater source."""
    root = project_root(root)
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        raise ValueError("Invalid sync revision")
    lock = safe_path(root, ".atom-sync/lock")
    if not lock.exists() or lock.read_text() != str(os.getppid()):
        raise ValueError("Internal sync mode requires the parent updater's lock")
    if safe_path(root, "sync.py").read_bytes() != git(root, "show", f"{revision}:sync.py"):
        raise ValueError("Updater source does not match the fetched revision")
    apply_revision(root, revision)


def main():
    try:
        root = Path(__file__).resolve().parent
        if len(sys.argv) == 3 and sys.argv[1] == "--apply-revision":
            apply_bootstrapped_revision(root, sys.argv[2])
        elif len(sys.argv) == 1:
            bootstrap_sync(root)
        else:
            raise ValueError("Usage: python sync.py")
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as error:
        # Avoid printing command arguments or fetched contents containing credentials.
        message = f"Git command failed (exit {error.returncode})" if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f"Sync failed: {message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Sync interrupted. Review the working tree if rollback could not complete.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
