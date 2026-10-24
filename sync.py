# command: python3 sync.py
# command (Windows): py sync.py --no-venv, then venv\Scripts\pip install -r requirements.txt

# info: Replaces Atom-owned files with upstream and deletes local-only files in Atom folders, keeping *_extend, config_extend.py and .env; resets the # atom section of requirements.txt and rebuilds venv/ to match requirements.txt exactly (skip with --no-venv). Run from the project root after committing: rolls back from memory on write failure, but saves no backups and never touches the Git index. See docs/sync.md.

# import
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

# config

# setting
REPO_URL = "https://github.com/atom36942/atom.git"
# 1. Files to sync: individual files replaced from upstream.
SYNC_FILES = [
    ".dockerignore",
    ".gitignore",
    "Dockerfile",
    "AGENTS.md",
    "config.py",
    "main.py",
    "readme.md",
    "ruff.toml",
    "sync.py",
]
# These folders belong entirely to Atom: sync mirrors them and removes any other file inside. Project files go in <folder>_extend/.
SYNC_FOLDERS = ["docs", "router", "function", "script", "static", "files"]
FILES_TO_SYNC = [*SYNC_FILES, *SYNC_FOLDERS]
# Project paths created locally only when missing, never modified afterwards.
EXTEND_FOLDERS = ["router_extend", "function_extend", "script_extend", "static_extend", "files_extend", "docs_extend", "tests_extend"]
# The starter config_extend.py sync creates when it is missing: # base (Atom's values), # atom (Atom's three dicts, each starting from its base; startup checks they keep Atom's entries), # misc (everything else).
CONFIG_EXTEND_STARTER = """# base
from config import config_column_int_mapping as base_config_column_int_mapping
from config import config_postgres as base_config_postgres
from config import config_api as base_config_api

# atom
config_column_int_mapping = {
**base_config_column_int_mapping,
# "task": {"status": {1: "To Do", 2: "Done"}},
}

config_postgres = {
**base_config_postgres,
"table": {
**base_config_postgres["table"],
# "task": [{"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True}],
},
}

config_api = {
**base_config_api,
# Add only after creating the matching router endpoint; choose an unused ID (200+):
# "/task/list": {"id": 200, "is_token": True},
}

# misc
# config_table_private_read_allowed = ["test", "task"]
"""
EXTEND_FILES = {
    "tests_extend/__init__.py": "",
    "config_extend.py": CONFIG_EXTEND_STARTER,
}
# requirements.txt has two sections: # atom is replaced with Atom's packages on every run, # extend (the project's packages) is kept; config_extend.py stays developer-managed.
REQUIREMENTS_ATOM_HEADER = "# atom: Atom's packages, replaced by sync.py on every run; add project packages under # extend"
REQUIREMENTS_EXTEND_HEADER = "# extend: this project's packages, pinned with ==; sync.py never changes them"
# venv/ is rebuilt to match requirements.txt exactly, on the Python version the Dockerfile names; its fingerprint skips rebuilds when nothing changed.
VENV_DIR = "venv"
VENV_OLD_DIR = "venv_old"
VENV_STATE = ".atom-venv.json"
STATE_PATH = ".atom-sync/state.json"
LOCK_TOKEN_ENV = "ATOM_SYNC_LOCK_TOKEN"  # noqa: S105 - name of the environment variable, not a secret

# logic
def git(*args, root):
    """Never consume stale FETCH_HEAD or partial output after a failed command."""
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)  # noqa: S603, S607 - fixed git command from PATH, arguments as a list, no shell
    return result.stdout

def safe_path(*, root, name):
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

def is_owned_path(*, name):
    return any(name == item or name.startswith(item + "/") for item in FILES_TO_SYNC)

def get_pkg_name(*, line):
    line = line.strip()
    if not line or line.startswith(("#", "-", "//")):
        return None
    name = re.split(r"[=><~!;\[\s]", line)[0].strip()
    return re.sub(r"[-_.]+", "-", name).lower() if name else None

def requirements_sections(*, text):
    """Split requirements text into (# atom lines, # extend lines, has_sections); lines outside the # atom section count as # extend."""
    atom, extend, current = [], [], "extend"
    has_sections = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# atom"):
            current, has_sections = "atom", True
            continue
        if stripped.startswith("# extend"):
            current, has_sections = "extend", True
            continue
        (atom if current == "atom" else extend).append(line)
    return atom, extend, has_sections

def lines_trimmed(*, lines):
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines

def merge_requirements(*, local, upstream):
    """Build the project's requirements.txt: Atom's packages under # atom (replaced on every run), then the project's under # extend (kept).

    Returns (text, notes). A file without sections (written before them) keeps every line Atom does not list, as # extend.
    A # extend line for a package Atom lists is removed, since Atom's version is installed, and reported; so are packages Atom stopped listing.
    """
    upstream_atom, upstream_rest, upstream_sections = requirements_sections(text=upstream)
    atom_lines = lines_trimmed(lines=upstream_atom if upstream_sections else upstream_rest)
    atom_names = {name for line in atom_lines if (name := get_pkg_name(line=line))}
    local_atom, local_extend, local_sections = requirements_sections(text=local or "")
    notes, extend_lines = [], []
    for line in local_extend:
        name = get_pkg_name(line=line)
        if name in atom_names:
            if local_sections: notes.append(f"removed '{line.strip()}' from # extend: Atom lists {name}, and Atom's version is installed")
            continue
        extend_lines.append(line)
    dropped = sorted({name for line in local_atom if (name := get_pkg_name(line=line))} - atom_names)
    if dropped: notes.append(f"Atom no longer lists {', '.join(dropped)}; add any your project still imports under # extend")
    extend_lines = lines_trimmed(lines=extend_lines)
    text = "\n".join([REQUIREMENTS_ATOM_HEADER, *atom_lines, "", REQUIREMENTS_EXTEND_HEADER, *extend_lines]) + "\n"
    return text, notes

def prepare_update(*, root, revision):
    entries = {}
    for record in git("ls-tree", "-r", "-z", revision, root=root).split(b"\0"):
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_name.decode("utf-8")
        if is_owned_path(name=name) or name == "requirements.txt":
            if kind != "blob" or mode not in ("100644", "100755"):
                raise ValueError(f"Unsupported upstream file type: {name}")
            safe_path(root=root, name=name)
            entries[name] = (oid, 0o755 if mode == "100755" else 0o644)
    for item in [*FILES_TO_SYNC, "requirements.txt", "function/__init__.py"]:
        if not any(name == item or name.startswith(item + "/") for name in entries):
            raise ValueError(f"Required upstream path is missing: {item}")

    plan = {}
    owned = {}
    for name, (oid, mode) in sorted(entries.items()):
        content = git("cat-file", "blob", oid, root=root)
        if name.endswith(".py"):
            compile(content, name, "exec")
        plan[name] = (content, mode)
        if is_owned_path(name=name):
            owned[name] = hashlib.sha256(content).hexdigest()

    # Mirror complete Atom folders on every run, including the first sync.
    # Reject symlinks rather than following them while inventorying local files.
    for folder in SYNC_FOLDERS:
        if folder not in FILES_TO_SYNC:
            continue
        directory = root / folder
        if directory.is_symlink():
            raise ValueError(f"Refusing symlinked Atom folder: {folder}")
        if directory.exists() and not directory.is_dir():
            raise ValueError(f"Expected a directory: {folder}")
        for parent, directories, filenames in os.walk(directory, followlinks=False):
            for child in directories:
                if (Path(parent) / child).is_symlink():
                    raise ValueError(f"Refusing symlinked Atom folder: {Path(parent) / child}")
            for filename in filenames:
                name = (Path(parent) / filename).relative_to(root).as_posix()
                if is_owned_path(name=name):
                    safe_path(root=root, name=name)
                    if name not in owned:
                        plan[name] = None

    requirements = safe_path(root=root, name="requirements.txt")
    local_requirements = requirements.read_text() if requirements.exists() else None
    merged, notes = merge_requirements(local=local_requirements, upstream=plan["requirements.txt"][0].decode())
    for note in notes: print(f" ! requirements.txt: {note}")
    plan["requirements.txt"] = (merged.encode(), requirements.stat().st_mode & 0o777 if requirements.exists() else 0o644)

    state = {"version": 1, "revision": revision, "files": owned}
    plan[STATE_PATH] = ((json.dumps(state, indent=2, sort_keys=True) + "\n").encode(), 0o600)
    return plan

def atomic_write(*, path, content, mode):
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

def apply_update(*, root, plan):
    """Retain destination contents in memory for rollback during this run."""
    before = {}
    for name in plan:
        path = safe_path(root=root, name=name)
        before[name] = (path.read_bytes(), path.stat().st_mode & 0o777) if path.exists() else None
    touched = []
    try:
        for name, value in plan.items():
            path = safe_path(root=root, name=name)
            touched.append(name)
            if value is None:
                path.unlink(missing_ok=True)
                print(f" -> removed retired file {name}")
            else:
                atomic_write(path=path, content=value[0], mode=value[1])
                print(f" -> {name}")
    except BaseException:
        failures = []
        for name in reversed(touched):
            try:
                path = safe_path(root=root, name=name)
                if before[name] is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path=path, content=before[name][0], mode=before[name][1])
            except Exception:
                failures.append(name)
        if failures:
            print(f"Rollback incomplete for {', '.join(failures)}. Recover affected files from your saved Git version", file=sys.stderr)
        else:
            print("Update failed; previous files restored.", file=sys.stderr)
        raise

    for folder in SYNC_FOLDERS:
        if folder not in FILES_TO_SYNC:
            continue
        for parent, directories, _filenames in os.walk(root / folder, topdown=False):
            for child in directories:
                path = Path(parent) / child
                if not any(path.iterdir()):
                    path.rmdir()

@contextmanager
def sync_lock(*, root):
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
        token = secrets.token_hex(32)
        with os.fdopen(fd, "w") as stream:
            stream.write(token)
        yield token
    finally:
        lock.unlink(missing_ok=True)

def project_root(*, root):
    root = Path(root).resolve()
    git_root = Path(git("rev-parse", "--show-toplevel", root=root).decode().strip()).resolve()
    if root != git_root:
        raise ValueError("Run the updater in the Atom project's Git root")
    return root

def fetch_revision(*, root, repo_url):
    print("Fetching Atom main...", flush=True)
    git("fetch", "--no-tags", repo_url, "main", root=root)
    return git("rev-parse", "--verify", "FETCH_HEAD^{commit}", root=root).decode().strip()

def create_extend_paths(*, root):
    for name, content in EXTEND_FILES.items():
        top = name.split("/")[0]
        if not (root / top).exists() and not (root / top).is_symlink():
            atomic_write(path=safe_path(root=root, name=name), content=content.encode(), mode=0o644)
            print(f" -> created {name}")
    for name in EXTEND_FOLDERS:
        path = root / name
        if not path.exists() and not path.is_symlink():
            path.mkdir()
            print(f" -> created {name}/")

def python_version_required(*, root):
    """The Python version the Dockerfile builds production on (FROM python:3.14-slim -> "3.14"); the venv uses the same."""
    dockerfile = safe_path(root=root, name="Dockerfile")
    match = re.search(r"^FROM python:(\d+\.\d+)", dockerfile.read_text() if dockerfile.exists() else "", re.MULTILINE)
    if not match: raise ValueError("Dockerfile must start with FROM python:<major>.<minor> so sync knows which Python the venv needs")
    return match.group(1)

def venv_python(*, venv):
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

def python_command(*, version):
    """A command that runs this Python version: this interpreter's base Python when it matches, else python3.X (or py -3.X on Windows)."""
    if f"{sys.version_info.major}.{sys.version_info.minor}" == version: return [getattr(sys, "_base_executable", sys.executable)]
    if sys.platform == "win32" and shutil.which("py"): return ["py", f"-{version}"]
    if path := shutil.which(f"python{version}"): return [path]
    hint = f"install it from python.org (includes the py launcher, so py -{version} works)" if sys.platform == "win32" else f"macOS: brew install python@{version}; Linux: your distribution's python{version} package"
    raise ValueError(f"Python {version} (named in the Dockerfile) is not installed: {hint}; then run sync again")

def run_command(*, args, cwd=None):
    """Run a venv or pip command; its output goes to the terminal so slow installs show progress."""
    try: subprocess.run(args, cwd=cwd, check=True)  # noqa: S603 - fixed Python and pip commands, arguments as a list, no shell
    except subprocess.CalledProcessError as error: raise ValueError(f"{' '.join(str(arg) for arg in args[1:3])} failed (exit {error.returncode})") from None

def venv_fingerprint(*, root, venv, version):
    """What the venv must keep matching: the Python version, requirements.txt, and the exact installed packages."""
    try: packages = subprocess.run([str(venv_python(venv=venv)), "-m", "pip", "freeze"], capture_output=True, check=True).stdout  # noqa: S603 - the venv's own pip, no shell
    except (OSError, subprocess.CalledProcessError): return None
    return {"python": version, "requirements": hashlib.sha256((root / "requirements.txt").read_bytes()).hexdigest(), "packages": hashlib.sha256(packages).hexdigest()}

def sync_venv(*, root):
    """Make venv/ match requirements.txt exactly: rebuild it from scratch when the Python version, requirements.txt or the installed packages changed.

    The previous venv is kept as venv_old until the new one installs, and restored if anything fails, so there is always a working venv.
    """
    version = python_version_required(root=root)
    venv, venv_old = root / VENV_DIR, root / VENV_OLD_DIR
    for path in (venv, venv_old):
        if path.is_symlink() or (path.exists() and not path.is_dir()): raise ValueError(f"Refusing to rebuild: {path.name} is not a plain directory")
    in_use = f"stop the app and anything else using {VENV_DIR} (on Windows also VS Code's Python extension), then run sync again with your installed Python, not the venv's: py sync.py on Windows, python3 sync.py elsewhere"
    if sys.platform == "win32" and venv.exists() and Path(sys.prefix).resolve() == venv.resolve(): raise ValueError(f"sync is running from {VENV_DIR}, which Windows cannot replace while it runs; files are synced, the venv is unchanged: {in_use}")
    if venv_old.exists():
        # left by an interrupted rebuild
        if venv.exists(): shutil.rmtree(venv_old, ignore_errors=True)
        else: venv_old.rename(venv)
        if venv_old.exists(): raise ValueError(f"{VENV_OLD_DIR} from an earlier rebuild is still in use; files are synced, the venv is unchanged: {in_use}")
    state = venv / VENV_STATE
    if state.exists():
        try:
            if json.loads(state.read_text()) == venv_fingerprint(root=root, venv=venv, version=version):
                print("venv already matches requirements.txt.")
                return
        except (OSError, ValueError): pass
    command = python_command(version=version)
    print(f"Rebuilding venv on Python {version} to match requirements.txt exactly; stop the app first. This can take a few minutes...", flush=True)
    if venv.exists():
        try: venv.rename(venv_old)
        except OSError as error: raise ValueError(f"{VENV_DIR} is in use, so it cannot be replaced ({error}); files are synced, the venv is unchanged: {in_use}") from None
    try:
        run_command(args=[*command, "-m", "venv", str(venv)])
        run_command(args=[str(venv_python(venv=venv)), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
        run_command(args=[str(venv_python(venv=venv)), "-m", "pip", "install", "--quiet", "-r", "requirements.txt"], cwd=root)
        fingerprint = venv_fingerprint(root=root, venv=venv, version=version)
        if fingerprint is None: raise ValueError("pip freeze failed in the new venv")
        state.write_text(json.dumps(fingerprint, indent=2) + "\n")
    except BaseException:
        shutil.rmtree(venv, ignore_errors=True)
        if venv_old.exists(): venv_old.rename(venv)
        print("venv rebuild failed; the previous venv is back in place.", file=sys.stderr)
        raise
    shutil.rmtree(venv_old, ignore_errors=True)
    print("venv rebuilt: it matches requirements.txt exactly.")

def apply_revision(*, root, revision, is_venv_sync=False):
    plan = prepare_update(root=root, revision=revision)
    apply_update(root=root, plan=plan)
    create_extend_paths(root=root)
    print("Files synced successfully!")
    if is_venv_sync: sync_venv(root=root)
    else: print("venv not checked (--no-venv); to match requirements.txt: venv/bin/pip install -r requirements.txt")
    print("Restart the app.")

def sync(*, root, repo_url=REPO_URL, is_venv_sync=False):
    """Apply using this loaded implementation (also used by integration tests)."""
    root = project_root(root=root)
    with sync_lock(root=root):
        apply_revision(root=root, revision=fetch_revision(root=root, repo_url=repo_url), is_venv_sync=is_venv_sync)

def bootstrap_sync(*, root, repo_url=REPO_URL, is_venv_sync=True):
    """Install the fetched updater, then run it under the same parent-held lock."""
    root = project_root(root=root)
    with sync_lock(root=root) as lock_token:
        revision = fetch_revision(root=root, repo_url=repo_url)
        record = git("ls-tree", revision, "--", "sync.py", root=root).decode().strip()
        if not record:
            raise ValueError("Upstream sync.py is missing")
        metadata, name = record.split("\t", 1)
        mode, kind, oid = metadata.split()
        if name != "sync.py" or kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError("Upstream sync.py must be a regular Python file")
        source = git("cat-file", "blob", oid, root=root)
        compile(source, "sync.py", "exec")
        script = safe_path(root=root, name="sync.py")
        previous = (script.read_bytes(), script.stat().st_mode & 0o777) if script.exists() else None
        atomic_write(path=script, content=source, mode=0o755 if mode == "100755" else 0o644)
        print("Running the latest Atom updater...", flush=True)
        try:
            # The child applies this exact commit; it never re-fetches or bootstraps.
            # Windows venv launchers may insert another process between us and Python.
            child_env = os.environ.copy()
            child_env[LOCK_TOKEN_ENV] = lock_token
            result = subprocess.run([sys.executable, str(script), "--apply-revision", revision, *([] if is_venv_sync else ["--no-venv"])], cwd=root, env=child_env)  # noqa: S603 - runs the validated sync.py with this interpreter, no shell
        except OSError:
            if previous is None:
                script.unlink(missing_ok=True)
            else:
                atomic_write(path=script, content=previous[0], mode=previous[1])
            raise
        if result.returncode:
            raise ValueError(f"Latest Atom updater failed (exit {result.returncode}); review the working tree before retrying")

def apply_bootstrapped_revision(*, root, revision, is_venv_sync=True):
    """Internal child entry: validate the parent lock and pinned updater source."""
    root = project_root(root=root)
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision):
        raise ValueError("Invalid sync revision")
    lock = safe_path(root=root, name=".atom-sync/lock")
    token = os.environ.pop(LOCK_TOKEN_ENV, "")
    if not token:
        raise ValueError("Internal sync mode requires the parent updater's lock: no handoff token was received. If you ran python3 sync.py, the previous updater may have just installed this version; run python3 sync.py again.")
    if not lock.exists():
        raise ValueError("Internal sync mode requires the parent updater's lock: .atom-sync/lock is missing")
    if not secrets.compare_digest(lock.read_bytes(), token.encode()):
        raise ValueError("Internal sync mode requires the parent updater's lock: the handoff token does not match .atom-sync/lock")
    if safe_path(root=root, name="sync.py").read_bytes() != git("show", f"{revision}:sync.py", root=root):
        raise ValueError("Updater source does not match the fetched revision")
    apply_revision(root=root, revision=revision, is_venv_sync=is_venv_sync)

def main():
    try:
        root = Path(__file__).resolve().parent
        cli_args = sys.argv[1:]    # [--no-venv] from users; --apply-revision <revision> [--no-venv] from the parent updater
        is_venv_sync = "--no-venv" not in cli_args
        args = [arg for arg in cli_args if arg != "--no-venv"]
        if len(args) == 2 and args[0] == "--apply-revision":
            apply_bootstrapped_revision(root=root, revision=args[1], is_venv_sync=is_venv_sync)
        elif not args:
            bootstrap_sync(root=root, is_venv_sync=is_venv_sync)
        else:
            raise ValueError("Usage: python3 sync.py [--no-venv]")
    except (OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as error:
        # Avoid printing command arguments or fetched contents containing credentials.
        message = f"Git command failed (exit {error.returncode})" if isinstance(error, subprocess.CalledProcessError) else str(error)
        print(f"Sync failed: {message}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Sync interrupted. Review the working tree if rollback could not complete.", file=sys.stderr)
        return 130
    return 0

# main
if __name__ == "__main__":
    sys.exit(main())
