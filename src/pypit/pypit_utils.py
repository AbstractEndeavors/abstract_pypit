"""
pypit.pypit_utils
==================
Version management, build, upload, and gitignore helpers.
"""
import os
import re
import shutil
import subprocess

import requests

from .imports import *          # noqa: F401,F403
from .clean_the_repos import *  # noqa: F401,F403


def ensure_pyproject_toml():
    if not os.path.exists("pyproject.toml"):
        print("pyproject.toml not found. Creating pyproject.toml...")
        with open("pyproject.toml", "w") as f:
            f.write(
                "[build-system]\n"
                "requires = [\"setuptools>=42\", \"wheel\"]\n"
                "build-backend = \"setuptools.build_meta\"\n"
            )
        print("pyproject.toml created.")


GITIGNORE_ENTRIES = [
    "build/",
    "dist/",
    "logs/",
    "*.egg-info/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.whl",
    "*.tar.gz",
    "*.asc",
    ".env",
    ".venv/",
]


def ensure_gitignore(root="."):
    from pathlib import Path
    root = Path(root)
    gi = root / ".gitignore"
    existing = set()
    if gi.exists():
        existing = {l.strip() for l in gi.read_text().splitlines() if l.strip()}
    missing = [e for e in GITIGNORE_ENTRIES if e not in existing]
    if missing:
        with gi.open("a") as f:
            f.write("\n" + "\n".join(missing) + "\n")
        print(f"📝 Added {len(missing)} entries to .gitignore")
    result = subprocess.run(
        ["git", "ls-files", "--ignored", "--exclude-standard", "-z"],
        cwd=root, capture_output=True, text=True
    )
    tracked_noise = [f for f in result.stdout.split("\0") if f]
    if tracked_noise:
        subprocess.run(["git", "rm", "-r", "--cached", "--"] + tracked_noise, cwd=root)
        print(f"🗑️  Untracked {len(tracked_noise)} previously-committed artifact(s)")


def get_package_name(path=None):
    try:
        output, stderr = getCmdRunLocal(key="package_name", path=path)
        return output.strip()
    except subprocess.CalledProcessError:
        print("Error: Unable to determine package name from setup.py")


def get_current_version(package_name):
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        if response.status_code == 200:
            return response.json()["info"]["version"]
        else:
            print(f"Package {package_name} not found on PyPI. Using version 0.0.0.")
            return "0.0.0"
    except requests.RequestException as e:
        print(f"Error fetching current version from PyPI: {e}")
    return None


def get_local_version(package_name, path=None):
    try:
        output, stderr = getCmdRunLocal(key="local_version", package_name=package_name, path=path)
        for line in output.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        print(f"Package {package_name} is not installed locally. {output}")
        return output
    except Exception as e:
        print(f"Error checking local version for {package_name}: {e}")


def get_increment_version(version):
    if version:
        parts = version.split(".")
        if not all(part.isdigit() for part in parts):
            print(f"Invalid version format: {version}")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)


def get_local_increment_version(package_name):
    version = get_local_version(package_name)
    return get_increment_version(version)


def get_pypi_increment_version(package_name):
    version = get_current_version(package_name)
    return get_increment_version(version)


def get_local_file(basestring):
    curr_dir = os.getcwd()
    dir_list = os.listdir(curr_dir)
    return find_first(dir_list, lambda x: x.endswith(basestring))


def update_version_in_file(current_version, new_version, file_path):
    with open(file_path, "r") as f:
        content = f.read()
    updated_content = re.sub(
        f"['\"]{current_version}['\"]",
        f"'{new_version}'",
        content,
    )
    with open(file_path, "w") as f:
        f.write(updated_content)
    print(f"Updated {os.path.basename(file_path)} with new version: {new_version}")


def update_version_in_setup(new_version):
    setup_file_path = get_local_file("setup.py")
    if setup_file_path:
        update_setup_py_version(setup_file_path, new_version)


def update_pyproject_toml_version(toml_path="pyproject.toml", new_version="0.0.1"):
    from pathlib import Path
    p = Path(toml_path)
    txt = p.read_text(encoding="utf-8")
    new_txt, n = re.subn(
        r'(?m)^(version\s*=\s*)["\'][^"\']+["\']',
        lambda m: f'{m.group(1)}"{new_version}"',
        txt,
        count=1,
    )
    if n:
        p.write_text(new_txt, encoding="utf-8")
        print(f"Updated {os.path.basename(toml_path)} version -> {new_version}")
    else:
        print(f"⚠️ no top-level `version = ...` line in {os.path.basename(toml_path)}; left unchanged")


def update_version_in_toml(current_pypi_version, new_version):
    toml_file_path = get_local_file(".toml")
    if toml_file_path:
        update_pyproject_toml_version(toml_file_path, new_version)


def read_version_from_pyproject(path=None):
    from pathlib import Path
    toml_file = path or get_local_file(".toml")
    if not toml_file or not os.path.exists(toml_file):
        return None
    m = re.search(
        r'(?m)^version\s*=\s*["\']([^"\']+)["\']',
        Path(toml_file).read_text(encoding="utf-8"),
    )
    return m.group(1) if m else None


def read_pypit_config(path=None):
    from pathlib import Path
    cfg = {"github_owner": None, "github_push": True}
    try:
        toml_file = path or get_local_file(".toml")
        if not toml_file or not os.path.exists(toml_file):
            return cfg
        txt = Path(toml_file).read_text(encoding="utf-8")
        m = re.search(r"(?ms)^\[tool\.pypit\]\s*(.*?)(?=^\[|\Z)", txt)
        if not m:
            return cfg
        body = m.group(1)
        owner = re.search(r'(?m)^\s*github_owner\s*=\s*["\']([^"\']+)["\']', body)
        if owner:
            cfg["github_owner"] = owner.group(1)
        push = re.search(r'(?m)^\s*github_push\s*=\s*(true|false)', body, re.I)
        if push:
            cfg["github_push"] = (push.group(1).lower() == "true")
    except Exception as e:
        print(f"⚠️ read_pypit_config: {e}; using defaults")
    return cfg


def _version_tuple(v):
    try:
        return [int(x) for x in str(v).split(".")]
    except (TypeError, ValueError):
        return [0]


def get_pypi_release_set(package_name):
    try:
        r = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=15)
        if r.status_code == 200:
            return set(r.json().get("releases", {}).keys())
    except requests.RequestException:
        pass
    return set()


def _fetch_pypi_state(package_name):
    """(latest_version, releases_set) from PyPI. FAIL LOUD on a transient failure
    (network error / non-404 status) so we never re-publish an existing release by
    guessing. A 404 means the package is new -> ("0.0.0", empty set)."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        r = requests.get(url, timeout=15)
    except requests.RequestException as e:
        raise RuntimeError(
            f"PyPI unreachable for {package_name} ({e}); refusing to guess a version "
            f"(would risk re-publishing an existing release)."
        ) from e
    if r.status_code == 404:
        return "0.0.0", set()
    if r.status_code != 200:
        raise RuntimeError(
            f"PyPI returned HTTP {r.status_code} for {package_name}; refusing to guess a version."
        )
    data = r.json()
    return data["info"]["version"], set(data.get("releases", {}).keys())


def get_next_free_version(package_name, local_version=None):
    pypi, releases = _fetch_pypi_state(package_name)
    if local_version and _version_tuple(local_version) > _version_tuple(pypi):
        if local_version not in releases:
            return local_version
        parts = _version_tuple(local_version)
    else:
        parts = _version_tuple(pypi)
    while True:
        parts[-1] += 1
        cand = ".".join(map(str, parts))
        if cand not in releases:
            return cand


def update_version_in_files(current_pypi_version, new_version):
    update_version_in_setup(new_version)
    update_version_in_toml(current_pypi_version, new_version)


def build_package(package_name=None, path=None):
    try:
        output, stderr = getCmdRunLocal(key="build_package", package_name=package_name, path=path)
        print(f"Package built successfully: {output}")
        for file in os.listdir("dist"):
            if file.endswith((".whl", ".tar.gz")):
                result = subprocess.run(
                    ["gpg", "--detach-sign", "--armor", f"dist/{file}"],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    print(f"⚠️ GPG signing skipped for {file}: {result.stderr.strip()}")
        return output, stderr
    except Exception as e:
        print(f"Error during building the package: {e}")
    return None, None


def upload_package(package_name=None, path=None):
    try:
        subprocess.run(
            [
                "python3", "-m", "twine", "upload",
                "--repository", "pypi",
                "--non-interactive",
                "--skip-existing",
                "dist/*",
            ],
            check=True,
        )
        print("✅ Package uploaded to PyPI.")
    except subprocess.CalledProcessError:
        print("❌ PyPI upload failed.")
        exit(1)


def update_setup_py_version(setup_path="setup.py", new_version="0.0.10"):
    from pathlib import Path
    p = Path(setup_path)
    txt = p.read_text(encoding="utf-8")
    for line in txt.split("\n"):
        cleanline = line.replace(" ", "")
        if "version=" in cleanline:
            txt = txt.replace(
                f"version{line.split('version')[1].split(',')[0]},",
                f"version='{new_version}',",
            )
            p.write_text(txt, encoding="utf-8")
            return


def update_package(package_name=None, path=None):
    try:
        output, stderr = getCmdRunLocal(key="update_package", package_name=package_name, path=path)
        print(f"Package updated successfully: {output}")
        return str(output), str(stderr)
    except Exception as e:
        print(f"Error during update: {e}")
    return None, None


def update_to_specific(package_name, new_version, path=None):
    cmd = ["python3", "-m", "pip", "install", "--no-cache-dir", f"{package_name}=={new_version}"]
    proc = subprocess.run(cmd, cwd=path or os.getcwd(), capture_output=True, text=True)
    print(proc.stdout)
    print(proc.stderr)
    return proc.stdout, proc.stderr


def update_package_until_synced(package_name, new_version=None):
    import time
    new_version = new_version or get_current_version(package_name)
    max_attempts = 5
    for attempt in range(max_attempts):
        output, stderr = update_package(package_name=package_name)
        local_version = get_local_version(package_name)
        print(f"Local version: {local_version}, PyPI version: {new_version}")
        if local_version == new_version:
            print(f"{package_name} is up-to-date with PyPI.")
            return output, stderr
        print(f"Attempt {attempt + 1}/{max_attempts}: version not yet synced, waiting...")
        time.sleep(2)
    print(f"⚠️ Could not sync to {new_version} after {max_attempts} attempts.")
    return output, stderr
