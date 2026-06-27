"""
pypit.imports.utils
=====================
Command-runner helpers and repo-root detection.
"""
import os
import re
import subprocess

from .init_imports import *  # noqa: F401,F403


def getcmd(key, package_name=None, new_version=None):
    CMD_PRELOADS = {
        "upload":         ["python3", "-m", "twine", "upload", "dist/*", "--skip-existing"],
        "package_name":   ["python3", "setup.py", "--name"],
        "local_version":  ["pip", "show", f"{package_name}"],
        "build_package":  ["python3", "-m", "build", "--sdist", "--wheel"],
        "update_specific": ["bash", "-i", "-c", f"pipit {package_name}=={new_version}"],
        "update_package": ["pip", "install", f"{package_name}", "--upgrade", "--no-cache-dir"],
    }
    return CMD_PRELOADS.get(key)


def run_local_cmd(cmd, path=None):
    if path:
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            raise ValueError(f"Specified path does not exist or is not a directory: {path}")
    else:
        path = os.getcwd()
    try:
        result = subprocess.run(
            " ".join(cmd),
            shell=True,
            capture_output=True,
            text=True,
            cwd=path,
            check=True,
        )
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr
    except Exception as e:
        raise RuntimeError(f"Failed to execute command: {e}")


def run_local_command(cmd: str, path: str = None) -> str:
    path = path or os.getcwd()
    try:
        proc = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
        return (proc.stdout or ""), (proc.stderr or "")
    except Exception as e:
        return f"❌ run_local_cmd error: {e}\n", ""


def getCmdRunLocal(key, package_name=None, new_version=None, path=None):
    cmd = getcmd(key=key, package_name=package_name, new_version=new_version)
    return run_local_cmd(cmd=cmd, path=path)


def getCommandRunLocal(key, package_name=None, new_version=None, path=None):
    cmd = getcmd(key=key, package_name=package_name, new_version=new_version)
    return run_local_command(cmd=cmd, path=path)


def enforce_psycopg3_dependency():
    with open("setup.py", "r") as f:
        content = f.read()
    original = content
    content = re.sub(
        r"(psycopg2-binary|psycopg2)(\s*[<>=!~].*?)?(['\"])",
        r"psycopg[binary]\3",
        content,
    )
    content = content.replace("'psycopg2'", "'psycopg[binary]'")
    content = content.replace('"psycopg2"', '"psycopg[binary]"')
    content = content.replace("'psycopg2-binary'", "'psycopg[binary]'")
    content = content.replace('"psycopg2-binary"', '"psycopg[binary]"')
    if content != original:
        with open("setup.py", "w") as f:
            f.write(content)
        print("🔧 Enforced psycopg[binary] dependency in setup.py")
    else:
        print("ℹ️ No psycopg2 dependency found in setup.py")


def get_repo_root(start=None):
    import pathlib
    cur = (pathlib.Path(start) if start else pathlib.Path.cwd()).resolve()
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    raise RuntimeError(f"Not inside a git repository: {start or pathlib.Path.cwd()}")
