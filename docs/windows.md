# 🪟 Windows

The readme's steps in PowerShell. Paths use `venv\Scripts\` instead of `venv/bin/`, and the `py` launcher instead of `python3`.

## Installation
```powershell
# 1. Python 3.14, once per machine: install it from python.org (adds the py launcher)
py -3.14 --version                           # must print 3.14.x

# 2. new project with sync.py
mkdir <project>
cd <project>
git init
Invoke-WebRequest https://raw.githubusercontent.com/atom36942/atom/main/sync.py -OutFile sync.py
py sync.py

# 3. run, then open http://localhost:8000
venv\Scripts\python main.py
venv\Scripts\uvicorn main:app --reload
```

## Sync
Run it from a new PowerShell window, outside the venv (`deactivate` first): Windows cannot replace a venv while anything runs from it.
```powershell
py sync.py                                   # everyday: update files, rebuild venv\, list newer # extend packages
py sync.py --no-outdated                     # same, without the PyPI lookup
py sync.py --no-venv                         # files only: you install requirements.txt yourself (own venv, Docker)
py sync.py --no-venv --no-outdated           # CI: files only, no PyPI lookup
```
If sync says the venv is in use, close the app, `uvicorn --reload` and VS Code's Python extension (or the VS Code window), then run it again.

## Test
```powershell
venv\Scripts\ruff check .
venv\Scripts\python -m unittest discover -s tests_extend -t .
```

## Contributing
To work on Atom itself:
```powershell
git clone https://github.com/atom36942/atom.git
cd atom
py -3.14 -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\pip install -r requirements.txt
venv\Scripts\ruff check .
venv\Scripts\python -m unittest discover -s tests -t .
```

## Notes
- Keep the project out of OneDrive or Dropbox; their file syncing locks files in `venv\`.
- When the `Dockerfile` moves to a new Python, install it from python.org before the next sync.
- More on sync and recovery: [sync.md](sync.md).
