# 🔄 Syncing Atom

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

- If a file or folder is removed from the updater's sync selection, its local
  files are preserved and its old ownership records are dropped on successful sync.
- All upstream files in `docs/` and `function/` are discovered automatically, except excluded paths.
- Only six router files are synced: `index.py`, `auth.py`, `my.py`, `public.py`,
  `private.py`, and `admin.py`. Other router files are preserved, even if upstream
  contains a file with the same name.
- Developer-only function files and `.env` are preserved. Selected upstream paths belong to Atom.
- Existing requirement entries are preserved; missing packages are appended.
- `config_extend.py` is developer-managed: sync does not create, read, or modify it.
  Create it manually when you need configuration overrides.
- `.atom-sync/state.json` records the last synced Atom files. On later updates,
  unchanged Atom files removed upstream are also removed locally. If such a file
  has local edits, sync stops so you can move those edits to a custom module.
  On the first run, unknown files are preserved.
- Write failures trigger rollback using previous contents held in memory. No
  backup files are saved. No success message is printed on failure, and
  the command exits nonzero. A lock prevents overlapping updater runs.

Ownership state and the sync lock are excluded from Git and Docker builds. Keep the
state file for future ownership tracking. Re-run the dependency install if
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
