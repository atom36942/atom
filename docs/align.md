# Align

A procedure, not rules: how an AI agent brings one Atom-based project, or a folder of several, up to the latest Atom and in line with its rules. The rules themselves are only in [AGENTS.md](../AGENTS.md) and the docs it links; this page never repeats them. Start it from the project or workspace folder:

```text
Follow docs/align.md in each Atom-based repo of this folder; read ./CLAUDE.md first.
```

A repo on an older Atom may not have this page yet: the first time, ask the agent to run `python3 sync.py` (Windows `py sync.py`) in each Atom-based repo, then follow its `docs/align.md`.

1. **Pick the repos.** Read the workspace's `CLAUDE.md` (and any `CLAUDE.md` inside a repo): it says which repos may change and how (branches, commits, production databases), and it wins over this page. A repo is Atom-based when it has `sync.py`, `config_extend.py` and `*_extend` folders; the Atom framework repo itself is not a project. Show the list (repo, version from `python3 sync.py --status`, update yes or no and why) and wait for the OK. Then, one repo at a time, inside it:
2. **Update Atom.** With a clean `git status` (otherwise stop and ask) and the app stopped, run `python3 sync.py` from a terminal outside the venv ([sync.md](sync.md)); after a major version, follow each **Upgrade** entry in `CHANGELOG.md` since the old one; then `venv/bin/python -m script.check` (Windows `venv\Scripts\python -m script.check`) passes.
3. **Read the rules.** `AGENTS.md` in full and every doc it links for the areas the repo uses, then the repo's `docs_extend/*.md`.
4. **Audit.** Start from the `standard` lines the check printed (what the code misses of the measurable rules), then compare the repo with every rule in `AGENTS.md` and its docs, area by area, so one run covers the whole project; skip an area the repo doesn't have:
   - **Structure**: files in the right `*_extend` folder, one feature name across folders, no edited core file, nothing generated outside `tmp/`.
   - **Security**: secrets anywhere outside `.env` (code, `config_extend.py`, `files_extend/`, pages, docs, logs, and `git log -p` for keys committed before; a leaked key is reported for rotation), routes and their `config_api` access, routes returning more columns than their screen needs, SQL built from strings, values written into HTML unescaped, tokens or personal data in URLs or logs.
   - **Speed and scale**: a missing index for a filter, sort or search; one query per item instead of one statement; counts or totals computed in the browser; a table downloaded whole; exports or imports not streamed or batched; caches without a limit.
   - **Pages**: each page against the reference pages `AGENTS.md` names (read them before judging one), then the screens, words, colours and sizes in `frontend.md`; try each page on a phone width and in dark mode.
   - **Clean-up**: dead code, unused files, CSS and settings, duplicated helpers, docs in `docs_extend/` that no longer match the code, tests missing for a rule whose mistake gives wrong data silently.
5. **Propose.** A table: area, what the repo does now, what `AGENTS.md` says, Enforced/Rule/Default, the fix. Rules missed are fixed; Defaults are suggestions: one the repo keeps on purpose (another layout its users rely on, a page not built on Atom's flow) gets its reason written in `docs_extend/` instead of a fix, and a risky change to a working page is offered as optional. Wait for the OK.
6. **Refactor and verify.** Change only project files (never Atom's core, `.env` values or data); run the check again; start the app and click through every page; report what changed and what was skipped and why. Commit or push only when asked, or when `CLAUDE.md` allows it.

Run again later (after an Atom release, or as a check): steps that find nothing to do pass quickly, so only what drifted is proposed.
