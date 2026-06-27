# abstract_pypit

One-command PyPI publisher + GitHub pusher.

Finds the next free version above whatever is on PyPI, bumps `setup.py` and
`pyproject.toml`, builds sdist + wheel, uploads to PyPI via twine, commits and
pushes to GitHub, then syncs the local install — all in one call.

Zero dependencies outside the stdlib except `requests`.

## Install

```sh
pip install abstract_pypit
```

## Usage

```python
# from any package directory that has setup.py + pyproject.toml:
from pypit import runit
runit()
```

```sh
# or from the command line:
abstract-pypit
```

## Credentials

**PyPI:** twine reads `~/.pypirc` or `TWINE_USERNAME` / `TWINE_PASSWORD` env vars.

**GitHub:** create `pypit/src/envs/.env` on the machine running pypit:

```
GITHUB_OWNER_1=your-username
GITPASS_1=<your-github-pat>
GITHUB_OWNER_2=your-org
GITPASS_2=<org-github-pat>
```

SSH key at `~/.ssh/github/githubssh_nopass` must be registered with GitHub.

## Per-package config

Add to the package's own `pyproject.toml`:

```toml
[tool.pypit]
github_owner = "your-org-or-username"   # which org/user owns the repo
github_push  = true                      # set false to skip GitHub entirely
```

## License

MIT
