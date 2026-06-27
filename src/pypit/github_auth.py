"""
pypit.github_auth
==================
GitHub SSH setup, API repo management, and git commit/push helpers.
"""
import os
import json
import subprocess

import requests

from .imports import *  # noqa: F401,F403


# ------------------------------------------------------------------------------
# Subprocess helpers
# ------------------------------------------------------------------------------

def run_github(cmd, cwd=None, check=True, env=None):
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return (p.stdout or "").strip(), (p.stderr or "").strip()


def _git(cmd, check=True, env=None):
    return run_github(["git", *cmd], cwd=str(get_repo_root()), check=check, env=env)


# ------------------------------------------------------------------------------
# SSH helpers
# ------------------------------------------------------------------------------

def ensure_ssh_key(key_path=None):
    key_path = os.path.expanduser(key_path or get_git_key_path())
    subprocess.run(["ssh-agent", "-s"], check=False, stdout=subprocess.PIPE, text=True)
    p = subprocess.run(["ssh-add", key_path], text=True, capture_output=True)
    if p.returncode != 0 and "already" not in (p.stderr or ""):
        print(f"⚠️ ssh-add failed: {p.stderr.strip()}")
    else:
        print(f"✅ SSH key {key_path} loaded into agent")


def ensure_ssh_config_for_github(key_path=None):
    key_path = os.path.expanduser(key_path or get_git_key_path())
    cfg_path = os.path.expanduser(get_ssh_config_path())
    ssh_dir = os.path.dirname(cfg_path)
    os.makedirs(ssh_dir, exist_ok=True)
    try:
        os.chmod(ssh_dir, 0o700)
    except OSError:
        pass
    block = (
        "Host github.com\n"
        "  User git\n"
        f"  IdentityFile {key_path}\n"
        "  IdentitiesOnly yes\n"
    )
    try:
        txt = ""
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        if "Host github.com" not in txt:
            with open(cfg_path, "a", encoding="utf-8") as f:
                f.write("\n" + block)
            print("🛠️ wrote github.com SSH stanza to ~/.ssh/config")
        if os.path.exists(cfg_path):
            os.chmod(cfg_path, 0o600)   # ssh rejects group/other-writable config
    except Exception as e:
        print(f"⚠️ couldn't edit ~/.ssh/config: {e}")


def git_env_with_key(key_path=None):
    key_path = os.path.expanduser(key_path or get_git_key_path())
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes"
    return env


def ensure_git_ssh():
    ensure_ssh_config_for_github(get_git_key_path())
    ensure_ssh_key(get_git_key_path())
    return git_env_with_key(get_git_key_path())


# ------------------------------------------------------------------------------
# GitHub API helpers
# ------------------------------------------------------------------------------

def github_api_headers(i):
    tok = get_owner_tok(i)
    if not tok:
        raise RuntimeError("GITHUB_TOKEN not set; cannot create GitHub repo automatically.")
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
    }


def get_github_login(i):
    r = requests.get("https://api.github.com/user",
                     headers=github_api_headers(i), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Could not determine GitHub user: {r.status_code} {r.text}")
    return r.json()["login"]


def repo_exists(i, name: str) -> bool:
    owner = get_owner_name(i)
    r = requests.get(f"https://api.github.com/repos/{owner}/{name}",
                     headers=github_api_headers(i), timeout=20)
    return r.status_code == 200


def create_repo(i, name: str, *, private=False, is_org=True):
    if is_org:
        owner = get_owner_name(i)
        url = f"https://api.github.com/orgs/{owner}/repos"
        body = {"name": name, "private": private, "auto_init": False,
                "has_issues": True, "has_projects": False, "has_wiki": False}
    else:
        url = "https://api.github.com/user/repos"
        body = {"name": name, "private": private, "auto_init": False}
    r = requests.post(url, headers=github_api_headers(i),
                      data=json.dumps(body), timeout=20)
    if r.status_code not in (201, 202):
        raise RuntimeError(f"GitHub repo create failed ({r.status_code}): {r.text}")


def _slot_for_owner(owner_name, max_slots=8):
    for i in range(1, max_slots + 1):
        try:
            if get_owner_name(i) == owner_name:
                return i
        except Exception:
            continue
    return None


def ensure_remote_repo(package_name: str, owner: str = None,
                       prefer_org_owner: int = 2, private=False, env=None) -> str:
    if owner:
        slot = _slot_for_owner(owner)
        if slot is not None:
            try:
                if not repo_exists(slot, package_name):
                    create_repo(slot, package_name, private=private, is_org=True)
            except Exception as e:
                print(f"⚠️ API repo ensure for {owner}/{package_name} skipped: {e}")
        else:
            print(f"ℹ️ no .env token slot for owner '{owner}' — relying on SSH key for push")
        return f"git@github.com:{owner}/{package_name}.git"


# ------------------------------------------------------------------------------
# Forgejo (canonical source-of-truth git host). GitHub is a downstream push-mirror
# configured INSIDE Forgejo, so pypit pushes releases to Forgejo and lets the mirror
# propagate to GitHub. Host/port/org are env-overridable.
# ------------------------------------------------------------------------------
import os as _fj_os
FORGEJO_HOST = _fj_os.environ.get("PYPIT_FORGEJO_HOST", "git.abstractendeavors.com")
FORGEJO_PORT = _fj_os.environ.get("PYPIT_FORGEJO_PORT", "2222")
FORGEJO_ORG  = _fj_os.environ.get("PYPIT_FORGEJO_ORG", "AbstractEndeavors")

def is_forgejo_url(url: str) -> bool:
    return bool(url) and FORGEJO_HOST in url

def forgejo_ssh_url(package_name: str, owner: str = None) -> str:
    return f"ssh://git@{FORGEJO_HOST}:{FORGEJO_PORT}/{owner or FORGEJO_ORG}/{package_name}.git"
    owner = get_owner_name(prefer_org_owner)
    try:
        if not repo_exists(prefer_org_owner, package_name):
            create_repo(prefer_org_owner, package_name, private=private, is_org=True)
        return f"git@github.com:{owner}/{package_name}.git"
    except Exception:
        i = prefer_org_owner - 1
        user = get_github_login(i)
        if not repo_exists(i, package_name):
            create_repo(i, package_name, private=private, is_org=False)
        return f"git@github.com:{user}/{package_name}.git"


def default_ssh_url(package_name: str, owner: str = None) -> str:
    if not owner:
        raise RuntimeError(
            f"Cannot build SSH URL for '{package_name}': no github_owner configured. "
            "Add [tool.pypit] github_owner = \"<your-org-or-user>\" to your pyproject.toml."
        )
    return f"git@github.com:{owner}/{package_name}.git"


# ------------------------------------------------------------------------------
# Git repo setup
# ------------------------------------------------------------------------------

def current_branch(env=None):
    out, _ = _git(["symbolic-ref", "--short", "HEAD"], check=False, env=env)
    return out.strip() or "main"


def _ensure_on_main(env=None):
    branch_out, _ = _git(["symbolic-ref", "--short", "HEAD"], check=False, env=env)
    current = branch_out.strip()
    if current == "main":
        return "main"
    if current == "master":
        print("⚠️ Branch is 'master' — renaming to 'main'")
        _git(["branch", "-m", "master", "main"], env=env)
        return "main"
    if not current:
        print("⚠️ Detached HEAD — checking out 'main'")
        _git(["checkout", "-B", "main"], check=False, env=env)
        branch_out, _ = _git(["symbolic-ref", "--short", "HEAD"], check=False, env=env)
        current = branch_out.strip()
        if not current:
            raise RuntimeError(
                f"Still detached HEAD in {get_repo_root()}. Run `git checkout -B main` manually."
            )
        return current
    print(f"ℹ️ On branch '{current}' — leaving as-is")
    return current


def _ensure_origin(package_name: str, owner: str = None, env=None) -> str:
    remotes_out, _ = _git(["remote", "-v"], check=False, env=env)
    has_origin = any(line.startswith("origin\t") for line in remotes_out.splitlines())
    if has_origin:
        url_out, _ = _git(["remote", "get-url", "origin"], check=False, env=env)
        # Forgejo is canonical: never clobber a Forgejo origin back to GitHub.
        if is_forgejo_url(url_out):
            print(f"\u2705 Forgejo origin (canonical) kept as-is: {url_out}")
            return url_out
        if owner and f":{owner}/" not in url_out:
            new_url = default_ssh_url(package_name, owner=owner)
            _git(["remote", "set-url", "origin", new_url], env=env)
            print(f"✅ Repointed origin {url_out} → {new_url}")
            return new_url
        print(f"✅ Remote origin already configured: {url_out}")
        return url_out
    try:
        ssh_url = ensure_remote_repo(package_name, owner=owner, env=env)
        print(f"✅ Remote repo ensured via API: {ssh_url}")
    except Exception as e:
        ssh_url = default_ssh_url(package_name, owner=owner)
        print(f"⚠️ API unavailable ({e}) — using default URL: {ssh_url}")
    _git(["remote", "add", "origin", ssh_url], env=env)
    print(f"✅ Added remote origin → {ssh_url}")
    return ssh_url


def bootstrap_repo(package_name: str, owner: str = None, env=None):
    from pathlib import Path
    cwd = Path.cwd()
    if not (cwd / ".git").exists():
        subprocess.run(["git", "init"], cwd=str(cwd), check=True)
        print(f"✅ Initialized git repo in {cwd}")
    _ensure_on_main(env=env)
    ssh_url = _ensure_origin(package_name, owner=owner, env=env)
    _git(["add", "-A"], env=env)
    status_out, _ = _git(["status", "--porcelain"], check=False, env=env)
    if status_out.strip():
        _git(["commit", "-m", f"Clean init {package_name}"], env=env)
    run_github(["git", "push", "--force", "-u", "origin", "main"],
               cwd=str(get_repo_root()), check=False, env=env)
    print("✅ Force-pushed clean state to origin/main")


def ensure_git_repo_and_remote(package_name: str, owner: str = None, env=None):
    from pathlib import Path
    cwd = Path.cwd()
    if not (cwd / ".git").exists():
        print(f"⚠️ No .git found in {cwd} — bootstrapping...")
        bootstrap_repo(package_name, owner=owner, env=env)
        return
    branch = _ensure_on_main(env=env)
    ssh_url = _ensure_origin(package_name, owner=owner, env=env)
    remote_branches, _ = run_github(["git", "branch", "-r"],
                                    cwd=str(get_repo_root()), check=False, env=env)
    if "origin/main" not in remote_branches:
        print("⚠️ origin/main doesn't exist yet — pushing now...")
        run_github(["git", "push", "-u", "origin", "main"],
                   cwd=str(get_repo_root()), check=False, env=env)
        print("✅ Pushed 'main' branch to remote")


def git_debug_dump(env=None):
    root = str(get_repo_root())
    for label, cmd in [
        ("git remote -v",         ["git", "remote", "-v"]),
        ("branch",                ["git", "symbolic-ref", "--short", "HEAD"]),
        ("status",                ["git", "status", "--porcelain"]),
        ("ssh -T git@github.com", ["ssh", "-T", "git@github.com"]),
    ]:
        r = subprocess.run(cmd, cwd=root, text=True, capture_output=True, env=env)
        print(f"== {label} ==\n{r.stdout or r.stderr}")


def git_debug_repo_and_remote(package_name, owner=None, env=None):
    git_env = env or ensure_git_ssh()
    ensure_git_repo_and_remote(package_name, owner=owner, env=git_env)
    git_debug_dump(env=git_env)
    return git_env


# ------------------------------------------------------------------------------
# Commit / push
# ------------------------------------------------------------------------------

def stage_and_commit_if_changes(message: str, env=None):
    _git(["add", "-A"], env=env)
    status_out, _ = _git(["status", "--porcelain"], check=False, env=env)
    if not status_out.strip():
        return False
    try:
        _git(["commit", "-m", message], env=env)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ git commit failed (exit {e.returncode}):\n{e.stderr}")
        raise


def push_to_origin(branch: str, env=None):
    root = str(get_repo_root())
    run_github(["git", "fetch", "origin"], cwd=root, check=False, env=env)
    remote_branches, _ = run_github(["git", "branch", "-r"], cwd=root, check=False, env=env)
    remote_has_branch = f"origin/{branch}" in remote_branches
    if remote_has_branch:
        run_github(["git", "pull", "--rebase", "origin", branch],
                   cwd=root, check=False, env=env)
    cmd = (["git", "push", "-u", "origin", branch] if not remote_has_branch
           else ["git", "push", "origin", branch])
    out, err = run_github(cmd, cwd=root, check=False, env=env)
    combined = (out or "") + "\n" + (err or "")
    if "Permission denied (publickey)" in combined:
        raise RuntimeError("SSH key not accepted. Check `ssh -T git@github.com`.")
    if "repository not found" in combined.lower():
        url_out, _ = run_github(["git", "remote", "get-url", "origin"],
                                cwd=root, check=False, env=env)
        raise RuntimeError(f"Remote repo not found. URL: {url_out}")
    if "fatal:" in combined.lower() or "error:" in combined.lower():
        raise RuntimeError(f"git push failed:\n{combined}")
    if "up-to-date" in combined or "up to date" in combined:
        print("ℹ️ git push: remote already up-to-date")
        return False
    print(f"✅ Pushed '{branch}' to origin")
    return True


def _try_stage_commit_push(commit_message: str, git_env: dict):
    did_commit = False
    push_ok = False
    push_err = None
    try:
        did_commit = stage_and_commit_if_changes(commit_message, env=git_env)
    except Exception as e:
        print(f"⚠️ stage_and_commit_if_changes failed: {e}")
    try:
        branch = current_branch(env=git_env)
        push_to_origin(branch, env=git_env)
        push_ok = True
    except Exception as e:
        push_err = str(e)
        print(f"⚠️ git push failed: {push_err}")
    return did_commit, push_ok, push_err


def try_commit(commit_message, git_env):
    try:
        did_commit, pushed, push_err = _try_stage_commit_push(commit_message, git_env)
        print(f"Did commit locally: {did_commit}, Push succeeded: {pushed}")
        if push_err:
            print(f"Push error (non-fatal): {push_err}")
    except Exception as e:
        print(f"⚠️ Unexpected error during commit/push: {e}")
