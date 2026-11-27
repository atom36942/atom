# Security

Please report vulnerabilities privately through GitHub: the repository's **Security** tab → **Report a vulnerability**. Do not open a public issue.

Include the affected route or file, steps to reproduce and the impact. Fixes go to `main`; projects get them with `python3 sync.py`.

## Supported versions

Only the latest release gets security fixes, as a new version on `main`; older versions are not patched. Check a project's version with `python3 sync.py --status` and upgrade with `python3 sync.py`, following the **Upgrade** steps in [CHANGELOG.md](CHANGELOG.md) when the major version changes.
