"""
pypit.main
===========
Full publish loop: version bump → clean → build → PyPI upload → GitHub push
→ local install sync.
"""
import os
import shutil
import subprocess
import time

from .imports import *       # noqa: F401,F403
from .pypit_utils import *   # noqa: F401,F403
from .github_auth import *   # noqa: F401,F403
from .clean_the_repos import ensure_clean_repo

ensure_clean_repo(where="main.py/import-guard")


_FATAL_PATTERNS = [
    "error: command",
    "getting requirements to build wheel: finished with status 'error'",
    "could not build wheels",
    "build backend returned an error",
    "no matching distribution found",
    "failed to build",
]


def update_package_until_synced(package_name, new_version=None):
    new_version = new_version or get_current_version(package_name)
    max_attempts = 5
    last_output, last_stderr = "", ""
    for attempt in range(max_attempts):
        output, stderr = update_package(package_name=package_name)
        last_output, last_stderr = str(output or ""), str(stderr or "")
        combined = (last_output + last_stderr).lower()
        local_version = get_local_version(package_name)
        print(f"Local version: {local_version}, PyPI version: {new_version}")
        if local_version == new_version:
            print(f"✅ {package_name} is up-to-date with PyPI.")
            return last_output, last_stderr
        fatal = next((p for p in _FATAL_PATTERNS if p in combined), None)
        if fatal:
            print(f"❌ Unrecoverable pip error ('{fatal}'). Fix the dependency then reinstall manually.")
            return last_output, last_stderr
        if attempt < max_attempts - 1:
            wait = 2 * (attempt + 1)
            print(f"Attempt {attempt + 1}/{max_attempts}: not yet synced, waiting {wait}s...")
            time.sleep(wait)
    print(f"⚠️ Could not sync to {new_version} after {max_attempts} attempts.")
    return last_output, last_stderr


def runPypit():
    ensure_gitignore()
    git_env = ensure_git_ssh()
    package_name = get_package_name()
    print(f"Package name: {package_name}")

    pypit_cfg = read_pypit_config()

    if pypit_cfg["github_push"]:
        try:
            git_env = git_debug_repo_and_remote(
                package_name, owner=pypit_cfg["github_owner"], env=git_env)
        except Exception as e:
            print(f"⚠️ git setup skipped (non-fatal): {e}")
            git_env = git_env or os.environ.copy()
    else:
        print("ℹ️ GitHub setup skipped (tool.pypit github_push=false — source handled externally).")
        git_env = git_env or os.environ.copy()

    local_version = get_local_version(package_name)
    print(f"Current local version: {local_version}")

    while True:
        try:
            ensure_clean_repo(where="runPypit/before-compute-version")
        except Exception as e:
            print(f"⚠️ repo not clean (non-fatal, continuing to PyPI): {e}")

        current_pypi_version = get_current_version(package_name)
        local_toml_version   = read_version_from_pyproject()
        pypi_increment_version = get_next_free_version(package_name, local_toml_version)
        print(
            f"PyPI version: {current_pypi_version} "
            f"(local toml: {local_toml_version}) → {pypi_increment_version}"
        )

        update_version_in_files(current_pypi_version, new_version=pypi_increment_version)

        # clean old artifacts
        directory = os.getcwd()
        src_dir   = os.path.join(directory, "src")
        remove_files = [
            os.path.join(directory, f) for f in os.listdir(directory)
            if f.endswith(".whl") or f.endswith(".tar.gz")
        ]
        remove_dirs = []
        if os.path.isdir(src_dir):
            remove_dirs += [
                os.path.join(src_dir, f) for f in os.listdir(src_dir)
                if f.endswith(".egg-info")
            ]
        remove_dirs += [
            os.path.join(directory, "build"),
            os.path.join(directory, "dist"),
        ]
        for d in remove_dirs:
            if os.path.isdir(d):
                shutil.rmtree(d)
        for f in remove_files:
            if os.path.exists(f):
                os.remove(f)

        print("🔧 Building package...")
        output, stderr = build_package()
        if output is None and stderr is None:
            raise RuntimeError("❌ Build failed — aborting.")
        print("✅ Build complete.")

        print("📤 Uploading to PyPI...")
        upload_package(package_name=package_name)
        print("✅ PyPI upload complete.")

        if not pypit_cfg["github_push"]:
            print("ℹ️ GitHub push skipped (tool.pypit github_push=false — source handled externally).")
        else:
            commit_message = (
                f"Release {package_name}=={pypi_increment_version} @ "
                f"{subprocess.check_output(['date', '-u', '+%Y-%m-%d %H:%M:%S UTC'], text=True).strip()}"
            )
            try:
                try_commit(commit_message, git_env)
                branch = current_branch(env=git_env)
                push_to_origin(branch, env=git_env)
                run_github(
                    ["git", "push", "--tags", "origin"],
                    cwd=str(get_repo_root()),
                    check=False,
                    env=git_env,
                )
                print("✅ GitHub push complete.")
            except Exception as e:
                print(f"⚠️ GitHub push failed (non-fatal): {e}")
                print("   PyPI upload already succeeded — continuing.")

        try:
            print("🔁 Updating local install...")
            update_package_until_synced(package_name, pypi_increment_version)
        except Exception as e:
            print(f"⚠️ Local update failed (non-fatal): {e}")

        print("✅ Run complete.")
        break


# Alias used by the original src/__init__.py → runit()
runit = runPypit
