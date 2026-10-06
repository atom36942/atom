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

- `docs/`, `router/`, and `function/` belong entirely to Atom. Sync mirrors all upstream files and removes every local file absent upstream, including edited files, local-only modules, and caches, on every run including the first.
- Only `script/consumer_postgres_create.py` and `script/consumer_postgres_update.py` are synced inside `script/`, like the selected files in `static/`. All other scripts are preserved, even if upstream has matching paths. The whole `script/` folder is not replaced.
- `config.py` and files listed in `sync_files` are replaced from upstream. Other paths are preserved.
- `docs_extend/`, `router_extend/`, `function_extend/`, `script_extend/`, `config_extend.py`, and `.env` are never touched. They are outside the explicit sync file and folder lists, so upstream copies of these paths are also ignored.
- Existing requirement entries are preserved; missing packages are appended.
- `.atom-sync/state.json` records the synced revision and files; deletion inside Atom folders no longer depends on previous ownership records.
- Write failures trigger rollback using previous contents held in memory. No
  backup files are saved. No success message is printed on failure, and
  the command exits nonzero. A lock prevents overlapping updater runs.

Ownership state and the sync lock are excluded from Git and Docker builds. The state file records the last successful update. Re-run the dependency install if
`requirements.txt` changed, then restart the app:

```bash
venv/bin/pip install -r requirements.txt
```

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
