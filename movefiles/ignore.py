from __future__ import annotations

import fnmatch
from pathlib import Path


EXCLUDED_DIR_NAMES = {
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".idea",
    ".vscode",
    "build",
    "dist",
    ".ruff_cache",
}

DEFAULT_EXCLUDED_FILE_GLOBS = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".DS_Store",
    "*.log",
    "*.egg",
    "*.egg-info",
    "*.so",
    ".coverage",
    ".env",
    ".env.*",
]


def make_ignore(extra_globs: list[str] | None, include_dotenv: bool):
    globs = list(DEFAULT_EXCLUDED_FILE_GLOBS)
    if include_dotenv:
        globs = [g for g in globs if not (g == ".env" or g.startswith(".env."))]
    if extra_globs:
        globs.extend(extra_globs)

    dir_names_lower = {d.lower() for d in EXCLUDED_DIR_NAMES}

    def ignore(cur_dir: str, names: list[str]):
        ignored: set[str] = set()
        for name in names:
            full = Path(cur_dir) / name
            name_lower = name.lower()
            if full.is_dir():
                if (
                    name_lower in dir_names_lower
                    or name_lower.startswith("venv")
                    or name_lower.endswith("venv")
                ):
                    ignored.add(name)
                    continue
            for pat in globs:
                if fnmatch.fnmatch(name, pat):
                    ignored.add(name)
                    break
        return ignored

    return ignore

