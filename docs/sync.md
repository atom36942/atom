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
- `.gitignore` commits only listed paths. It has two headers, like `requirements.txt`: sync resets the `# atom` part (everything above `# extend`) to Atom's and keeps the project's pattern lines under `# extend`: to commit a folder that is not `*_extend` (such as `infra/`), add `!infra/` and `!infra/**` under `# extend`.
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
| `python3 sync.py --ref <commit>` | `Pinned to 1d4f8a1 (--ref)`, then applies that commit instead of the latest |
| App startup | `Atom 1.3.0` |
| `GET /info` | `"atom_version": "1.3.0"` |

Versions follow semver: major (`2.0.0`) when projects must change their code, minor (`1.1.0`) for new features, patch (`1.0.1`) for fixes. Sync always takes the latest `main`; to mark a new version, raise `ATOM_VERSION` and the `Version` line at the top of `readme.md` (a test checks they match) and push to `main` (no tags or GitHub releases). Commits in between keep the last version. A project synced before versions existed shows `unknown` until its next sync. If a sync fails after installing the new `sync.py`, that file already shows the new version while the other files may be older; the error says so, and running sync again finishes it.

### Upgrading to 10.0.0

Per-user permissions are enforced: a route with `user_check_permission: {"mode": "token"}` admits only users whose `users.permissions` holds its `id` ([auth.md](auth.md#per-user-permissions)). Atom's samples: `/admin/postgres-query-runner-write` (6) needs role 1 and permission 6; `/admin/user-delete` (132) needs permission 132 only. Root (id 1) gets both at startup; root logs in again to use them, and other admins need a grant through `/admin/user-update`.

A project that sets `config_column_int_mapping["users"]` keeps Atom's labels (startup refuses a permission route without one):

```python
"users": {**base_config_column_int_mapping["users"], "role": {1: "Admin", 2: "General"}},
```

### Upgrading to 9.0.0

`config_sql` and `config_table` are removed: the startup queries are Atom's own code now, and a table's buffer size is a plain setting. A project that set either (startup stops, naming the new keys) sets plain values instead, in `config_extend.py` or `.env`:

| Before | 9.0.0 |
|---|---|
| `config_sql["config"]` (its `limit`) | `config_cache_row_limit_config` |
| `config_sql["users_role"]`, `["users_deactivated"]`, `["users_deleted"]` | `config_cache_row_limit_users_role`, `_users_deactivated`, `_users_deleted` (`0` = off) |
| `config_sql["profile_metadata"]` | `config_profile_metadata_sql` |
| `config_table["<table>"]["buffer_limit"]` | `config_buffer_limit_<table>` (Atom sets `config_buffer_limit_log_api = 1000`) |

`config_extend.py` sections are now `# base`, `# atom`, `# extend` (was `# misc`): move plain overrides of Atom's settings into `# atom`, keep only the project's own settings under `# extend` ([extend.md](extend.md)). Layout only; nothing checks it.

A script's schedule is `config_schedule_script_<script>` (was `config_schedule_<script>`), so it never clashes with the scheduler's own `config_schedule_timezone` and `config_schedule_check_sec`. Rename each one in `config_extend.py`, `.env` and the server's settings (`config_schedule_postgres_cleanup` → `config_schedule_script_postgres_cleanup`); an old name, even `off`, stops startup naming the new one.

### Upgrading to 8.0.0

- Two of Atom's scripts were renamed: `script/cleanup.py` → `script/postgres_cleanup.py` and `script/schema_plan.py` → `script/postgres_schema_plan.py` (run them as `venv/bin/python -m script.postgres_cleanup` and `script.postgres_schema_plan`). The setting `config_schedule_cleanup` is now `config_schedule_postgres_cleanup`: a project that sets the old name renames it (an old name that is not `off` stops startup: no script named cleanup).
- Every script starts with `# type: job` (runs once and exits) or `# type: continuous` (runs until stopped). Add it as the first line of each `script_extend/` script, then a blank line; a scheduled script without `# type: job` stops startup, and a `continuous` one is never scheduled ([schedule.md](schedule.md)).

### Upgrading to 7.0.0

Three settings were renamed; a project that sets one in `config_extend.py` or `.env` renames it (the old name stops startup, naming the new one):

| Before | 7.0.0 |
|---|---|
| `config_otp_retention_day` | `config_retention_day_otp` |
| `config_log_api_retention_day` | `config_retention_day_log_api` |
| `config_users_delete_retention_day` | `config_retention_day_users_delete` |

OTP and API-log cleanup now run as `script/cleanup.py` on `config_schedule_cleanup` ([schedule.md](schedule.md)); a new table, `script_run`, is created at startup.

### A fixed version: `--ref`

`python3 sync.py --ref <commit>` applies that Atom commit instead of main's latest: the same update on every machine and in CI, or going back to the Atom a project ran before. The commit must be on Atom's `main` (a short id such as `1d4f8a1` works; `git log --oneline` in an Atom clone, or the commit list on GitHub, shows each version's commit); anything else is refused before a file changes. It combines with `--no-venv` and `--no-outdated`. The pinned commit's own `sync.py` does the update, so a commit from before 3.24.0 installs an updater without `--ref`: run `python3 sync.py` (the latest) to get it back.

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
