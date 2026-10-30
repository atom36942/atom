# command: python3 sync.py    (everyday: update files, rebuild venv/, list newer # extend packages)
# command: python3 sync.py --no-outdated    (same, without the PyPI lookup)
# command: python3 sync.py --no-venv    (files only: venv managed yourself, Docker)
# command: python3 sync.py --no-venv --no-outdated    (CI: files only, no PyPI lookup)
# command: python3 sync.py --status    (which Atom version this project has and the latest; changes nothing)
# command (Windows): py sync.py    (same flags; from a new PowerShell window, outside the venv)

# info: Updates a project to the latest Atom, or starts one in an empty Git folder. Steps:
# - fetch Atom's main branch, print the version change (ATOM_VERSION below) and hand over to its latest sync.py
# - replace Atom's files and folders; delete other files inside Atom folders
# - keep *_extend, config_extend.py and .env; create each one only if missing:
#   - folders router_extend/, function_extend/, files_extend/, static_extend/, script_extend/, tests_extend/, docs_extend/, each with a readme.md
#   - tests_extend/__init__.py
#   - config_extend.py (starter: # base, # atom, # misc)
#   - .env (sample settings, commented out)
# - requirements.txt: reset # atom to Atom's list (dropping packages Atom no longer uses), tidy # extend
# - .gitignore: reset everything above # extend to Atom's, keep the project's lines under # extend
# - rebuild venv/ to match requirements.txt (skip: --no-venv)
# - list newer # extend packages on PyPI (skip: --no-outdated)
# - roll back on a write failure; never touches the Git index. Details: docs/sync.md

# import
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# config

# setting
# Atom's version: raised by hand when a change is worth a new number (no tags); a project's sync.py shows the version it has
ATOM_VERSION = "2.0.0"
REPO_URL = "https://github.com/atom36942/atom.git"
# Single files replaced from upstream on every sync.
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
}

config_postgres = {
**base_config_postgres,
"table": {
**base_config_postgres["table"],
},
}

config_api = {
**base_config_api,
}

# misc
"""
# The readme.md sync writes into each *_extend folder whenever it is missing (rules in full: AGENTS.md "Where code goes").
EXTEND_README = {
    "router_extend": "# router_extend\nAPI routes: one `<feature>.py` with `router = APIRouter()`. A route with params reads them with `app_state.func_request_param_read`, calls a `func_*` and returns `{\"status\": 1, \"message\": result}`; no business logic. Every route needs a `config_api` entry (id 200+) in `config_extend.py`. See AGENTS.md (Routes, config_api).\n",
    "function_extend": "# function_extend\nBusiness logic: `<feature>.py` (a big feature may split into `<feature>_<part>.py`) with keyword-only `func_*` functions, available as `app_state.func_*`; names are unique across Atom and the project. Optional `func_extend(*, app_state)` runs at startup and `func_extend_shutdown(*, app_state)` at shutdown. Reuse Atom's clients (`app_state.client_*`) and `func_*` helpers before writing your own. See AGENTS.md (Functions, Reuse Atom).\n",
    "files_extend": "# files_extend\nShared constants and `param_specs` (`import files_extend.<module>`), plus JSON, prompts and templates read by path from the project root. Never written at runtime: generated files go in `tmp/<feature>/`, data in the database. See AGENTS.md (Where code goes).\n",
    "static_extend": "# static_extend\nWeb pages, served at `/static/<name>` and opened at `/page/<app>`: one file `<app>.html` or a folder `<app>/index.html` with its assets linked absolutely (`/static/<app>/js/app.js`). Lowercase names keep URLs clean; state such as a tab goes in the query (`/page/<app>?tab=x`). See AGENTS.md (Where code goes).\n",
    "script_extend": "# script_extend\nProject scripts and jobs: one `.py` per job with sections `# command`, `# info`, `# import`, `# config` (values from `config.py` or the environment only), `# setting`, `# logic`, `# main`. Imports stdlib, packages, `config`, `function` and the project's `function_extend`/`files_extend` (move helpers there when a script grows); runtime data in `tmp/<script>/`, deleted on success. See AGENTS.md (Style).\n",
    "tests_extend": "# tests_extend\nProject tests (`unittest`), one `test_<feature>.py` each; keep `__init__.py`. Run: `venv/bin/python -m unittest discover -s tests_extend -t .`\n",
    "docs_extend": "# docs_extend\nShort project docs, one `<feature>.md` each: what it does and how to use it, no SQL or code dumps. Rules live only in the root `AGENTS.md` (Atom's, synced).\n",
}
# The starter .env sync creates when it is missing: sample values, commented out.
ENV_STARTER = """# config_postgres_url_master=postgresql://postgres:postgres@localhost:5432/postgres
# config_root_user_password=your-strong-root-password
# config_token_secret_key=your-secret-key-at-least-32-chars
# config_signup_allowed_roles=[2]
# config_is_prod=false
# config_is_pgweb_enabled=true
# config_redis_url_api_response=redis://localhost:6379/0
"""
EXTEND_FILES = {
    "tests_extend/__init__.py": "",
    "config_extend.py": CONFIG_EXTEND_STARTER,
    ".env": ENV_STARTER,
}
# requirements.txt has two sections: # atom is replaced with Atom's packages on every run, # extend (the project's packages) is kept; config_extend.py stays developer-managed.
REQUIREMENTS_ATOM_HEADER = "# atom"
REQUIREMENTS_EXTEND_HEADER = "# extend"
# .gitignore: Atom's allow-list above # extend is replaced on every run; the project's lines under # extend (folders it commits) are kept.
GITIGNORE_EXTEND_HEADER = "# extend"
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
    """Build the project's requirements.txt, comparing it line by line with Atom's # atom list.

    Returns (text, notes). # atom becomes exactly Atom's list. Every other package line ends up in # extend, sorted by name with option
    lines (-e, --index-url) first: a package under # atom that Atom no longer lists is removed (Atom dropped it), a # extend line for a package
    Atom lists is removed (Atom's version is installed), a repeated package keeps its last line, and comment lines are dropped so the
    section stays a flat list. Version pins are never changed; lines not pinned with == are reported.
    """
    upstream_atom, upstream_rest, upstream_sections = requirements_sections(text=upstream)
    atom_lines = lines_trimmed(lines=upstream_atom if upstream_sections else upstream_rest)
    atom_versions = {name: line.strip() for line in atom_lines if (name := get_pkg_name(line=line))}
    local_atom, local_extend, local_sections = requirements_sections(text=local or "")
    local_extend_names = {get_pkg_name(line=line) for line in local_extend}
    notes, options, extend = [], [], {}
    for line in local_atom:
        name = get_pkg_name(line=line)
        if name and name not in atom_versions and name not in local_extend_names: notes.append(f"removed '{line.strip()}': Atom no longer uses it; add it to # extend if your project does")
    for line in local_extend:
        stripped, name = line.strip(), get_pkg_name(line=line)
        if not stripped: continue
        if stripped.startswith("-"):
            if stripped not in options: options.append(stripped)
            continue
        if not name:
            notes.append(f"removed '{stripped}' from # extend: the section holds package lines only")
            continue
        if name in atom_versions:
            notes.append(f"removed '{stripped}' from # extend: Atom installs {atom_versions[name]}")
            continue
        if name in extend: notes.append(f"{name} was listed twice in # extend; kept '{stripped}'")
        extend[name] = stripped
    notes += [f"'{line}' in # extend is not pinned with ==" for line in extend.values() if "==" not in line.split(";")[0]]
    extend_lines = [*options, *(extend[name] for name in sorted(extend))]
    text = "\n".join([REQUIREMENTS_ATOM_HEADER, *atom_lines, "", REQUIREMENTS_EXTEND_HEADER, *extend_lines]) + "\n"
    return text, notes

def merge_gitignore(*, local, upstream):
    """Atom's .gitignore up to its # extend header, then the project's pattern lines under its own # extend header (comments dropped); a file without one gets Atom's as is."""
    upstream_lines = upstream.splitlines()
    head = upstream_lines[:upstream_lines.index(GITIGNORE_EXTEND_HEADER) + 1] if GITIGNORE_EXTEND_HEADER in upstream_lines else [*upstream_lines, "", GITIGNORE_EXTEND_HEADER]
    local_lines = (local or "").splitlines()
    extend = [line for line in local_lines[local_lines.index(GITIGNORE_EXTEND_HEADER) + 1:] if line.strip() and not line.startswith("#")] if GITIGNORE_EXTEND_HEADER in local_lines else []
    return "\n".join([*head, *extend]) + "\n"

def pypi_latest(*, name):
    """The newest release on PyPI, or None when PyPI can't be reached."""
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json", timeout=5) as response:  # noqa: S310 - fixed https host, quoted package name
            return json.load(response)["info"]["version"]
    except (OSError, ValueError, KeyError):
        return None

def version_parts(*, version):
    """Leading release numbers for comparing versions: "2.10.1rc1" -> (2, 10, 1)."""
    return tuple(int(part) for part in re.findall(r"\d+", re.match(r"[\d.]*", version)[0]))

def extend_outdated_report(*, root):
    """Print # extend packages pinned below their newest PyPI release; never changes anything, and stays silent when offline."""
    requirements = root / "requirements.txt"
    if not requirements.exists(): return
    _, extend, _ = requirements_sections(text=requirements.read_text())
    pins = {}
    for line in extend:
        match = re.match(r"^\s*([A-Za-z0-9._-]+)(?:\[[^\]]*\])?==([^\s;#]+)", line)
        if match: pins[match[1]] = match[2]
    if not pins: return
    with ThreadPoolExecutor(max_workers=8) as pool:
        latest = dict(zip(pins, pool.map(lambda name: pypi_latest(name=name), pins), strict=True))
    outdated = [f"   {name} {version} -> {latest[name]}{' (major: check its release notes)' if version_parts(version=latest[name])[:1] != version_parts(version=version)[:1] else ''}" for name, version in pins.items() if latest[name] and version_parts(version=latest[name]) > version_parts(version=version)]
    if outdated: print("Newer versions of your # extend packages (sync never changes them; update the == pin to upgrade):", *outdated, sep="\n")

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
    gitignore = safe_path(root=root, name=".gitignore")
    plan[".gitignore"] = (merge_gitignore(local=gitignore.read_text() if gitignore.exists() else None, upstream=plan[".gitignore"][0].decode()).encode(), plan[".gitignore"][1])

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

def atom_version(*, source):
    """The ATOM_VERSION in a sync.py's source (bytes), or None for a sync.py from before versions."""
    match = re.search(rb'^ATOM_VERSION = "([^"]+)"$', source, re.MULTILINE)
    return match[1].decode() if match else None

def synced_revision(*, root):
    """The Atom commit this project was last synced to, or None."""
    try: return json.loads((root / STATE_PATH).read_text()).get("revision")
    except (OSError, ValueError): return None

def version_change(*, old, new, is_same_revision):
    """One line for the version change: "Atom 1.2.0 -> 1.3.0", "Already on Atom 1.3.0", or the same version with newer commits."""
    if old != new: return f"Atom {old or 'unknown (synced before versions)'} -> {new or 'unknown'}"
    if is_same_revision: return f"Already on Atom {new}"
    return f"Atom {new} (newer commits on main)"

def status(*, root, repo_url=REPO_URL):
    """Print this project's Atom version and the latest on main; changes nothing."""
    root = project_root(root=root)
    script = root / "sync.py"
    old = atom_version(source=script.read_bytes()) if script.exists() else None
    revision = fetch_revision(root=root, repo_url=repo_url)
    new = atom_version(source=git("show", f"{revision}:sync.py", root=root))
    is_same = synced_revision(root=root) == revision
    print(f"This project: Atom {old or 'unknown (synced before versions)'}{'' if is_same or old != new else ' (main has newer commits)'}")
    print(f"Latest on main: Atom {new or 'unknown'} ({revision[:7]})")
    print("Up to date." if is_same else "Run python3 sync.py to update.")

def fetch_revision(*, root, repo_url):
    print("Fetching Atom main...", flush=True)
    git("fetch", "--no-tags", repo_url, "main", root=root)
    return git("rev-parse", "--verify", "FETCH_HEAD^{commit}", root=root).decode().strip()

def create_extend_paths(*, root):
    for name in EXTEND_FOLDERS:
        path = root / name
        if not path.exists() and not path.is_symlink():
            path.mkdir()
            print(f" -> created {name}/")
    # every starter file is created whenever it is missing (its folder must be a real one); existing files are never touched
    for name, content in {**EXTEND_FILES, **{f"{folder}/readme.md": text for folder, text in EXTEND_README.items()}}.items():
        path = root / name
        if path.parent.is_dir() and not path.parent.is_symlink() and not path.exists() and not path.is_symlink():
            atomic_write(path=safe_path(root=root, name=name), content=content.encode(), mode=0o600 if name == ".env" else 0o644)
            print(f" -> created {name}")

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
    if sys.platform == "win32" and shutil.which("py") and subprocess.run(["py", f"-{version}", "-c", "pass"], capture_output=True).returncode == 0: return ["py", f"-{version}"]  # noqa: S603, S607 - the py launcher, fixed arguments; it exits non-zero (103) when that version is not installed
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
    # Cloud-synced folders lock each new file while uploading it, so a venv rebuild there crawls or hangs.
    if cloud := next((part for part in root.resolve().parts if part.lower().startswith(("onedrive", "dropbox"))), None): raise ValueError(f"the project is inside {cloud}, which locks the thousands of files a venv rebuild writes; files are synced, the venv is unchanged: move the project to a local folder outside it (Windows: C:\\projects\\<name>), then run sync again")
    print(f"Rebuilding venv on Python {version} to match requirements.txt exactly; stop the app first. This can take a few minutes...", flush=True)
    if venv.exists():
        try: venv.rename(venv_old)
        except OSError as error: raise ValueError(f"{VENV_DIR} is in use, so it cannot be replaced ({error}); files are synced, the venv is unchanged: {in_use}") from None
    try:
        run_command(args=[*command, "-m", "venv", str(venv)])
        run_command(args=[str(venv_python(venv=venv)), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
        run_command(args=[str(venv_python(venv=venv)), "-m", "pip", "install", "-r", "requirements.txt"], cwd=root)
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

def apply_revision(*, root, revision, is_venv_sync=False, is_outdated_check=True):
    plan = prepare_update(root=root, revision=revision)
    apply_update(root=root, plan=plan)
    create_extend_paths(root=root)
    print("Files synced successfully!")
    if is_venv_sync: sync_venv(root=root)
    else: print("venv not checked (--no-venv); to match requirements.txt: venv/bin/pip install -r requirements.txt")
    if is_outdated_check: extend_outdated_report(root=root)
    print("Restart the app.")

def sync(*, root, repo_url=REPO_URL, is_venv_sync=False):
    """Apply using this loaded implementation (also used by integration tests)."""
    root = project_root(root=root)
    with sync_lock(root=root):
        apply_revision(root=root, revision=fetch_revision(root=root, repo_url=repo_url), is_venv_sync=is_venv_sync)

def bootstrap_sync(*, root, repo_url=REPO_URL, is_venv_sync=True, is_outdated_check=True):
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
        print(version_change(old=atom_version(source=previous[0]) if previous else None, new=atom_version(source=source), is_same_revision=synced_revision(root=root) == revision), flush=True)
        atomic_write(path=script, content=source, mode=0o755 if mode == "100755" else 0o644)
        print("Running the latest Atom updater...", flush=True)
        try:
            # The child applies this exact commit; it never re-fetches or bootstraps.
            # Windows venv launchers may insert another process between us and Python.
            child_env = os.environ.copy()
            child_env[LOCK_TOKEN_ENV] = lock_token
            result = subprocess.run([sys.executable, str(script), "--apply-revision", revision, *([] if is_venv_sync else ["--no-venv"]), *([] if is_outdated_check else ["--no-outdated"])], cwd=root, env=child_env)  # noqa: S603 - runs the validated sync.py with this interpreter, no shell
        except OSError:
            if previous is None:
                script.unlink(missing_ok=True)
            else:
                atomic_write(path=script, content=previous[0], mode=previous[1])
            raise
        if result.returncode:
            raise ValueError(f"Latest Atom updater failed (exit {result.returncode}). sync.py now shows Atom {atom_version(source=source) or 'unknown'}, but the other files may not be updated: review the working tree, then run python3 sync.py again")

def apply_bootstrapped_revision(*, root, revision, is_venv_sync=True, is_outdated_check=True):
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
    apply_revision(root=root, revision=revision, is_venv_sync=is_venv_sync, is_outdated_check=is_outdated_check)

def main():
    try:
        root = Path(__file__).resolve().parent
        cli_args = sys.argv[1:]    # flags from users; --apply-revision <revision> plus the same flags from the parent updater
        is_venv_sync = "--no-venv" not in cli_args    # --no-venv: update files only, leave venv/ as it is
        is_outdated_check = "--no-outdated" not in cli_args    # --no-outdated: skip the PyPI lookup of # extend packages (offline, CI)
        args = [arg for arg in cli_args if arg not in ("--no-venv", "--no-outdated")]
        if len(args) == 2 and args[0] == "--apply-revision":
            apply_bootstrapped_revision(root=root, revision=args[1], is_venv_sync=is_venv_sync, is_outdated_check=is_outdated_check)
        elif args == ["--status"]:
            status(root=root)
        elif not args:
            bootstrap_sync(root=root, is_venv_sync=is_venv_sync, is_outdated_check=is_outdated_check)
        else:
            raise ValueError("Usage: python3 sync.py [--no-venv] [--no-outdated] | python3 sync.py --status")
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
