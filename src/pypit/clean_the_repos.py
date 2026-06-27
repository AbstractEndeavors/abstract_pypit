"""
pypit.clean_the_repos
======================
Conflict-marker guard using git-tracked file list (not filesystem walk).
"""
import os
import re
import subprocess

from .imports import *  # noqa: F401,F403

# ------------------------------------------------------------------------------
# A real git conflict block is anchored lines in order:
#   <<<<<<< <label>
#   [||||||| <label>]   (diff3 style, optional)
#   =======
#   >>>>>>> <label>
# Anchoring at line start + exact 7 chars kills Cython comments and string
# literals that are not conflict markers.
# ------------------------------------------------------------------------------
_RE_OURS   = re.compile(r"^<{7}(?: |$)")
_RE_BASE   = re.compile(r"^\|{7}(?: |$)")
_RE_SPLIT  = re.compile(r"^={7}$")
_RE_THEIRS = re.compile(r"^>{7}(?: |$)")

_SKIP_SUFFIXES = {
    ".whl", ".gz", ".zip", ".tar", ".png", ".jpg", ".jpeg", ".pdf", ".so",
    ".pyc", ".pyo", ".c", ".cpp", ".cc", ".h", ".hpp", ".pyx", ".pxd",
}
_MAX_BYTES = 5_000_000


def _git_root(start="."):
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=os.path.abspath(start), capture_output=True, text=True,
    )
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _repo_files(root):
    found = []
    for args in (
        ["git", "ls-files", "-z"],
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
    ):
        out = subprocess.run(args, cwd=root, capture_output=True, text=True)
        found += [f for f in out.stdout.split("\0") if f]
    return list(dict.fromkeys(found))


def _looks_text(path):
    try:
        if os.path.isdir(path):
            return False
        if os.path.splitext(path)[1].lower() in _SKIP_SUFFIXES:
            return False
        if os.path.getsize(path) > _MAX_BYTES:
            return False
        with open(path, "rb") as f:
            return b"\x00" not in f.read(2048)
    except OSError:
        return False


def _scan_for_conflicts(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    if "<<<<<<<" not in text or ">>>>>>>" not in text:
        return []
    hits, block, state = [], [], "clean"
    for ln, line in enumerate(text.splitlines(), 1):
        if _RE_OURS.match(line):
            block = [(ln, line.rstrip())]
            state = "ours"
        elif state == "ours" and _RE_BASE.match(line):
            block.append((ln, line.rstrip()))
            state = "base"
        elif state in ("ours", "base") and _RE_SPLIT.match(line):
            block.append((ln, line.rstrip()))
            state = "split"
        elif state == "split" and _RE_THEIRS.match(line):
            block.append((ln, line.rstrip()))
            hits.extend(block)
            block, state = [], "clean"
    return hits[:10]


def ensure_clean_repo(where="(unspecified)", *, require_clean_git=False, root="."):
    git_root = _git_root(root)
    if git_root is None:
        print(f"ℹ️ ensure_clean_repo[{where}]: {os.path.abspath(root)} is not a git "
              f"repo — skipping conflict scan")
        return
    offenders = {}
    for rel in _repo_files(git_root):
        p = os.path.join(git_root, rel)
        if not _looks_text(p):
            continue
        hits = _scan_for_conflicts(p)
        if hits:
            offenders[p] = hits
    if offenders:
        lines = [f"\n🚫 Merge conflict markers detected {where}. Resolve before continuing:"]
        for path, hits in offenders.items():
            lines.append(f"  - {path}")
            for ln, t in hits:
                lines.append(f"      L{ln:>4}: {t}")
            if len(hits) == 10:
                lines.append("      ... (more lines truncated)")
        raise RuntimeError("\n".join(lines))
    if require_clean_git:
        for args, err_msg in (
            (["git", "diff", "--quiet"], "Unstaged changes in working tree."),
            (["git", "diff", "--cached", "--quiet"], "Staged but uncommitted changes in index."),
        ):
            rc = subprocess.call(args, cwd=git_root,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if rc != 0:
                raise RuntimeError(err_msg)
