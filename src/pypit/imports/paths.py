"""
pypit.imports.paths
=====================
Path helpers for locating the pypit-local .env and resolving GitHub credentials.
All env reading goes through pypit.env_utils (stdlib-only, zero deps).
"""
import os
from ..env_utils import get_env_value, get_initial_caller_dir


def get_abs_path():
    return os.path.abspath(__file__)


def get_abs_dir():
    return os.path.dirname(get_abs_path())


def get_src_dir():
    return os.path.dirname(get_abs_dir())


def get_env_dir():
    return os.path.join(get_src_dir(), "envs")


def get_local_env():
    return os.path.join(get_env_dir(), ".env")


# ---------------------------------------------------------------------------
# indirection chain (ENV_PATH / ENV_KEY)
# ---------------------------------------------------------------------------

def get_pre_path():
    return get_env_value(path=get_local_env(), key="ENV_PATH")


def get_pre_key():
    return get_env_value(path=get_local_env(), key="ENV_KEY")


def get_init_env_path():
    return get_env_value(path=get_local_env(), key=get_pre_key())


def get_init_owner_env_value(key):
    return get_env_value(path=get_local_env(), key=key)


# ---------------------------------------------------------------------------
# GitHub owner / token slots
# ---------------------------------------------------------------------------

def get_owner_name_key(i):
    return get_env_value(path=get_local_env(), key=f"GITHUB_OWNER_{i}")


def get_owner_tok_key(i):
    return get_env_value(path=get_local_env(), key=f"GITPASS_{i}")


def get_owner_env_value(key):
    return get_env_value(path=get_local_env(), key=key)


def get_owner_name_value(i):
    return get_env_value(path=get_local_env(), key=get_owner_name_key(i))


def get_owner_tok_value(i):
    return get_env_value(path=get_local_env(), key=get_owner_tok_key(i))


def get_owner_name(i):
    return get_owner_name_value(i)


def get_owner_tok(i):
    return get_owner_tok_value(i)


# ---------------------------------------------------------------------------
# SSH / git config paths (hardcoded, matching original)
# ---------------------------------------------------------------------------

def get_git_key_path():
    return "~/.ssh/github/githubssh_nopass"


def get_ssh_config_path():
    return "~/.ssh/config"


__all__ = [
    "get_abs_path", "get_abs_dir", "get_src_dir", "get_env_dir", "get_local_env",
    "get_pre_path", "get_pre_key", "get_init_env_path",
    "get_init_owner_env_value", "get_owner_env_value",
    "get_owner_name_key", "get_owner_tok_key",
    "get_owner_name_value", "get_owner_tok_value",
    "get_owner_name", "get_owner_tok",
    "get_git_key_path", "get_ssh_config_path",
]
