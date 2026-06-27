"""
pypit (published as abstract_pypit)
=====================================
One-command PyPI publisher + GitHub pusher.

Usage as a library:
    from pypit import runit, runGithubOnly
    runit()

Usage from the command line (after pip install abstract_pypit):
    python -m pypit
"""

__version__ = "0.0.1"

from .main import runit, runPypit          # noqa: F401
from .github_only import runGithubOnly     # noqa: F401

__all__ = ["runit", "runPypit", "runGithubOnly", "__version__"]
