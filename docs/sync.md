# 🔄 Syncing Atom

Move existing custom files into the matching `*_extend/` folders before syncing, and save your work in Git. Files left in Atom folders will be replaced or removed. See [migration instructions](extend.md#migrating-existing-custom-files).

When new Atom versions ship, pull the latest core files with `sync.py`:

```bash
python3 sync.py
```

The updater first fetches upstream `main`, pins that commit, validates its
`sync.py`, and replaces the local updater. It then starts that latest version in a
fresh process using the same Python interpreter. The latest version applies its
sync rules immediately, in this same invocation; there is no second manual run.
The child uses the pinned commit without re-fetching or restarting again, while
the parent holds the sync lock. A per-run token passed to the child validates
the handoff without depending on parent process IDs, which Windows virtual
environment launchers can change.

The latest updater prepares and validates the selected project files before
replacing them. Missing required files, invalid Python, failed Git commands, or
symlinked destinations stop the update. Files are written to the working tree;
the Git index is left unchanged. If the project sync fails, the newly installed
`sync.py` remains in place, while project write failures use in-memory rollback.
If the new process cannot be launched, the old updater is restored from memory.

- `docs/`, `router/`, `function/`, `script/`, `static/`, and `files/` belong entirely to Atom. Sync mirrors all upstream files and removes every local file absent upstream, including edited files, local-only modules, and caches, on every run including the first.
- Project scripts, web assets, and extra files go in `script_extend/`, `static_extend/`, and `files_extend/`; anything left in an Atom folder is removed on the next sync.
- `config.py` and files listed in `SYNC_FILES` are replaced from upstream. Other paths are preserved.
- Root files in `SYNC_FILES` (`main.py`, `Dockerfile`, `readme.md`, `AGENTS.md`, `ruff.toml`, `.gitignore`, ...) are replaced on every sync and have no `_extend` version. Keep project notes in `docs_extend/<feature>.md`; agent rules live only in Atom's `AGENTS.md`; a project that needs its own Dockerfile or root files is outside the sync model.
- `.gitignore` commits only listed paths. Sync resets everything above its `# extend` line to Atom's and keeps the project's pattern lines below it: to commit a folder that is not `*_extend` (such as `infra/`), add `!infra/` and `!infra/**` under `# extend`.
- Every `<name>_extend/` folder (`docs_extend/`, `router_extend/`, `function_extend/`, `script_extend/`, `static_extend/`, `files_extend/`, `tests_extend/`), `config_extend.py`, and `.env` are never overwritten or removed; a missing `_extend` folder, `config_extend.py` or `.env` (a commented starter: uncomment the lines you need and put your values) is created locally, and each `_extend` folder gets a short `readme.md` (what goes there); every one of these starter files (`readme.md`, `tests_extend/__init__.py`, `config_extend.py`, `.env`) is created again whenever it is missing, and an existing one is never changed. They are outside the explicit sync file and folder lists, so upstream copies of these paths are also ignored.
- `requirements.txt` has two sections, and sync checks every line against Atom's list. Names match the way pip does (`PyJWT` = `pyjwt`).
  - `# atom` becomes exactly Atom's list on every sync; never edit it. A package there that Atom no longer lists is dropped, so packages Atom stops using leave your project too; sync names each one, and a project that still imports one adds it to `# extend`.
  - `# extend` holds your project's packages, pinned with `==`, plus option lines (`-e`, `--index-url`). Sync keeps your versions, sorts the list by name and drops comment lines. A line for a package Atom also lists is removed (Atom's version is installed), and a repeated package keeps its last line.
  - Every change is printed, along with lines not pinned with `==`.
  - After syncing, sync looks up your `# extend` packages on PyPI and lists newer versions; it never upgrades them, and it stays silent when offline. `python3 sync.py --no-outdated` skips the lookup.
- `venv/` is made to match `requirements.txt` exactly (`# atom` plus `# extend`): no missing packages, no other versions, and nothing installed by hand. Sync rebuilds it from scratch, on the Python version the `Dockerfile` names (`FROM python:3.14-slim` → `python3.14`), whenever that version, `requirements.txt`, or the installed packages differ from the last build; otherwise it leaves it alone (about 0.1 s). A full rebuild takes about 20 s with pip's download cache. The old venv is kept as `venv_old/` until the new one installs and is put back if anything fails, so there is always a working venv. Stop the app before syncing. Run sync with your installed Python, not the venv's (`python3 sync.py`; on Windows `py sync.py`): the venv is built with the Dockerfile's Python either way, and Windows cannot replace a venv while anything runs from it. If the venv is in use (the app, `uvicorn --reload`, or on Windows VS Code's Python extension), sync still updates the files, leaves the venv as it was, and says what to close before running it again. Skip this step with `python3 sync.py --no-venv` (CI, Docker, or a venv elsewhere). When the `Dockerfile` moves to a new Python, the next sync rebuilds the venv on it; install that Python first (macOS: `brew install python@3.15`; Windows: the python.org installer, which adds the `py` launcher; Linux: your distribution's `python3.15` package). CI builds a real venv this way on Linux, macOS and Windows on every change.
- `.atom-sync/state.json` records the synced revision and files; deletion inside Atom folders no longer depends on previous ownership records.
- Write failures trigger rollback using previous contents held in memory. No
  backup files are saved. No success message is printed on failure, and
  the command exits nonzero. A lock prevents overlapping updater runs.

Ownership state and the sync lock are excluded from Git and Docker builds. The state file records the last successful update. After a sync, restart the app.

## Versions

Atom's version is `ATOM_VERSION` in `sync.py` (for example `ATOM_VERSION = "1.2.0"`). Sync replaces `sync.py`, so a project's own `sync.py` always shows the Atom version it has, and its commit diff shows a version change.

| Where | Shows |
|---|---|
| `sync.py` | `ATOM_VERSION = "1.2.0"` |
| `python3 sync.py` | `Atom 1.2.0 -> 1.3.0` before it applies, `Already on Atom 1.3.0`, or `Atom 1.3.0 (newer commits on main)` |
| `python3 sync.py --status` | This project's version and the latest on main; changes nothing |
| App startup | `Atom 1.3.0` |
| `GET /info` | `"atom_version": "1.3.0"` |

Versions follow semver: major (`2.0.0`) when projects must change their code, minor (`1.1.0`) for new features, patch (`1.0.1`) for fixes. Sync always takes the latest `main`; to mark a new version, raise `ATOM_VERSION` and push to `main` (no tags or GitHub releases). Commits in between keep the last version. A project synced before versions existed shows `unknown` until its next sync. If a sync fails after installing the new `sync.py`, that file already shows the new version while the other files may be older; the error says so, and running sync again finishes it.

## Recovering an interrupted update

Rollback is available only while the updater process is running. If rollback
cannot finish, or the process is forcibly killed, review the working tree and
recover affected files from your saved Git version. Uncommitted changes have no
persistent recovery copy. Remove `.atom-sync/lock` only after confirming no updater
is running. Review the diff and run your application tests before deploying;
syntax validation does not verify runtime compatibility.

See the [extension guide](extend.md) for keeping custom configuration, routers, and functions separate from framework files.

---

📚 [Back to README](../readme.md)
