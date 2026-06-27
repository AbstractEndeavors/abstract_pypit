"""
pypit.imports.init_imports
============================
Base imports for all pypit modules.  Zero external dependencies except requests.
"""
import os
import re
import sys
import json
import shutil
import pathlib
import subprocess

import requests

from pathlib import Path
from subprocess import check_output

from ..env_utils import (
    get_env_value,
    get_env_path,
    get_initial_caller,
    get_initial_caller_dir,
)
from ..imports.paths import *  # noqa: F401,F403


def find_first(iterable, predicate, default=None):
    """Return the first item matching *predicate*, or *default*."""
    return next((item for item in iterable if predicate(item)), default)
