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
- `config.py` and files listed in `sync_files` are replaced from upstream. Other paths are preserved.
- Root files in `sync_files` (`main.py`, `Dockerfile`, `readme.md`, `AGENTS.md`, `ruff.toml`, `.gitignore`, ...) are replaced on every sync and have no `_extend` version. Keep project notes and agent rules in `docs_extend/` (`docs_extend/AGENTS.md` is read by agents); a project that needs its own Dockerfile or root files is outside the sync model.
- Every `<name>_extend/` folder (`docs_extend/`, `router_extend/`, `function_extend/`, `script_extend/`, `static_extend/`, `files_extend/`, `tests_extend/`), `config_extend.py`, and `.env` are never overwritten or removed; a missing `_extend` folder (empty) or `config_extend.py` is created locally. They are outside the explicit sync file and folder lists, so upstream copies of these paths are also ignored.
- `requirements.txt` has two sections. `# atom` holds Atom's packages and is replaced with Atom's exact list on every sync; never edit it. `# extend` holds your project's packages (pinned with `==`), comments and option lines (`-e`, `--index-url`), and sync never changes it. A file from before the sections keeps every line Atom does not list as `# extend`. If `# extend` lists a package Atom also lists, sync removes your line (Atom's version is what gets installed) and says so; it also names any package Atom stopped listing, so you can add it under `# extend` if your code imports it. Names match the way pip does (`PyJWT` = `pyjwt`, `python_multipart` = `python-multipart`).
- `venv/` is made to match `requirements.txt` exactly (`# atom` plus `# extend`): no missing packages, no other versions, and nothing installed by hand. Sync rebuilds it from scratch, on the Python version the `Dockerfile` names (`FROM python:3.14-slim` → `python3.14`), whenever that version, `requirements.txt`, or the installed packages differ from the last build; otherwise it leaves it alone (about 0.1 s). A full rebuild takes about 20 s with pip's download cache. The old venv is kept as `venv_old/` until the new one installs and is put back if anything fails, so there is always a working venv. Stop the app before syncing. Run sync with your installed Python, not the venv's (`python3 sync.py`; on Windows `py sync.py`): the venv is built with the Dockerfile's Python either way, and Windows cannot replace a venv while anything runs from it. If the venv is in use (the app, `uvicorn --reload`, or on Windows VS Code's Python extension), sync still updates the files, leaves the venv as it was, and says what to close before running it again. Skip this step with `python3 sync.py --no-venv` (CI, Docker, or a venv elsewhere). When the `Dockerfile` moves to a new Python, the next sync rebuilds the venv on it; install that Python first (macOS: `brew install python@3.15`; Windows: the python.org installer, which adds the `py` launcher; Linux: your distribution's `python3.15` package). CI builds a real venv this way on Linux, macOS and Windows on every change (`tests/test_sync_venv_real.py`).
- `.atom-sync/state.json` records the synced revision and files; deletion inside Atom folders no longer depends on previous ownership records.
- Write failures trigger rollback using previous contents held in memory. No
  backup files are saved. No success message is printed on failure, and
  the command exits nonzero. A lock prevents overlapping updater runs.

Ownership state and the sync lock are excluded from Git and Docker builds. The state file records the last successful update. After a sync, restart the app.

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
