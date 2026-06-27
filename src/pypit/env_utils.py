"""
pypit.env_utils
================
Standalone .env cascade reader — no third-party dependencies.

Inlined from abstract_security.envs; the dotenv/bcrypt/jwt surface of that
package is irrelevant here.  Search order:
  supplied path → cwd → home → ~/.envy_all → ~/envy_all
"""
import os
import sys

_DEFAULT_FILE = ".env"
_DEFAULT_KEY  = "MY_PASSWORD"


def _split_eq(line):
    """Split ``KEY=VALUE`` at the first '=' and strip whitespace."""
    if "=" in line:
        key, _, value = line.partition("=")
        return key.strip(), value.strip()
    return line.strip(), None


def _search_file(key, path, deep_scan=False):
    """Return the value of *key* in the env file at *path*, or None."""
    if not (path and os.path.isfile(path)):
        return None
    best_value, best_score = None, 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line_key, line_value = _split_eq(line)
            if line_key == key:
                return line_value
            if deep_scan and line_key and key:
                matched = sum(len(p) for p in key.split("_") if p and p in line_key)
                if matched / len(key) >= 0.5 and matched > best_score:
                    best_value, best_score = line_value, matched
    return best_value if deep_scan else None


def _candidate_dirs(start_path):
    """Return de-duplicated, existing directories to search."""
    home = os.path.expanduser("~")
    candidates = [
        start_path,
        os.getcwd(),
        home,
        os.path.join(home, ".envy_all"),
        os.path.join(home, "envy_all"),
    ]
    seen, result = set(), []
    for d in candidates:
        if d and d not in seen and os.path.isdir(d):
            seen.add(d)
            result.append(d)
    return result


def get_env_value(key=_DEFAULT_KEY, path=None, file_name=_DEFAULT_FILE,
                  deep_scan=False):
    """
    Read *key* from a .env-style file.

    If *path* points directly to a file, that file is tried first.
    Otherwise the cascade: supplied dir → cwd → home → ~/.envy_all.
    """
    key       = key       or _DEFAULT_KEY
    file_name = file_name or _DEFAULT_FILE

    if path and os.path.isfile(path):
        # direct file path given — search it first, then cascade from its dir
        value = _search_file(key, path, deep_scan)
        if value is not None:
            return value
        path = os.path.dirname(path)

    for directory in _candidate_dirs(path or os.getcwd()):
        value = _search_file(key, os.path.join(directory, file_name), deep_scan)
        if value is not None:
            return value
    return None


def get_env_path(key=_DEFAULT_KEY, path=None, file_name=_DEFAULT_FILE,
                 deep_scan=False):
    """Return the path of the first .env file that contains *key*, or None."""
    key       = key       or _DEFAULT_KEY
    file_name = file_name or _DEFAULT_FILE

    if path and os.path.isfile(path):
        if _search_file(key, path, deep_scan) is not None:
            return path
        path = os.path.dirname(path)

    for directory in _candidate_dirs(path or os.getcwd()):
        env_path = os.path.join(directory, file_name)
        if _search_file(key, env_path, deep_scan) is not None:
            return env_path
    return None


def get_initial_caller():
    """Return the path of the original entry-point script (sys.argv[0])."""
    entry = sys.argv[0] if sys.argv else None
    if entry:
        return os.path.realpath(entry)
    return None


def get_initial_caller_dir():
    """Return the directory of the original entry-point script."""
    caller = get_initial_caller()
    return os.path.dirname(caller) if caller else None


__all__ = [
    "get_env_value", "get_env_path",
    "get_initial_caller", "get_initial_caller_dir",
]
