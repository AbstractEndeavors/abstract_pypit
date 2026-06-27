"""
pypit.github_only
==================
Standalone GitHub-push step (no PyPI upload).
"""
import subprocess

from .imports import *       # noqa: F401,F403
from .github_auth import *   # noqa: F401,F403
from .pypit_utils import *   # noqa: F401,F403


def runGithubOnly(commit_message=None):
    ensure_clean_repo(where="github_only")
    git_env = ensure_git_ssh()
    package_name = get_package_name()
    print(f"Repo name: {package_name}")
    cfg = read_pypit_config()
    if not cfg["github_push"]:
        print("ℹ️ github-only: skipped (tool.pypit github_push=false — source handled externally).")
        return
    git_env = git_debug_repo_and_remote(package_name, owner=cfg["github_owner"], env=git_env)
    if not commit_message:
        commit_message = (
            f"Update {package_name} @ "
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
        print(f"❌ GitHub push failed: {e}")
