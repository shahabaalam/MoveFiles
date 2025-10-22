# MoveFiles Backup Tool

The idea for this app came from my need to back up all my projects to an external device. Since each project contained a virtual environment folder, copying them would have taken up unnecessary time and space. To solve this problem, I decided to create a Python-based solution.

The app Copies one or more project folders to a destination parent directory while skipping virtual environments, caches, and common build artifacts. Shows overall progress with percentage, throughput, and ETA.

## Overview
- Entry point: `app.py`
- Core modules in the `movefiles/` package:
  - `movefiles/cli.py` – argument parsing
  - `movefiles/pickers.py` – GUI/CLI folder selection (Windows native multi-select when available)
  - `movefiles/ignore.py` – ignore rules and patterns
  - `movefiles/copyops.py` – scanning, copying, progress and safety checks

This structure keeps `app.py` small and makes future changes easier by isolating responsibilities.

## Requirements
- Python 3.10+ (uses modern type hints like `Path | None`).
- Windows for native multi-select dialog (COM). macOS/Linux use Tk GUI or CLI prompts.
- Optional: `tkinter` for GUI prompts on non-Windows or when COM selection isn’t available.

## Installation
No external packages are required. Clone or copy this repository and run with Python.

## Usage
Run with prompts and GUI:

```
python app.py
```

You’ll be asked to:
- Select one or more source folders (Windows native multi-select when available; otherwise a Tk dialog).
- Select a destination parent folder.

Skip prompts with CLI flags:

```
python app.py --source C:\path\to\proj --dest D:\Backups
python app.py -s C:\p1 -s C:\p2 -d D:\Backups
```

Optional flags:
- `--name MyProjectBackup` (used only when exactly one source is provided)
- `--include-dotenv` (include `.env` and `.env.*`)
- `--extra-ignore PATTERN` (repeatable; e.g., `--extra-ignore *.sqlite3`)

## Arguments
- `--source, -s PATH` (repeatable): One or more source directories. If omitted, the tool prompts to select.
- `--dest, -d PATH`: Destination parent directory. If omitted, the tool prompts to select.
- `--name NAME`: Name of the new folder at destination (used only when copying a single source).
- `--include-dotenv`: Include `.env` files (excluded by default).
- `--extra-ignore GLOB` (repeatable): Add more ignore patterns (fnmatch-style).

## Ignore Rules
Excluded directories:
```
__pycache__, venv, .venv, env, .env, .git, .hg, .svn,
.mypy_cache, .pytest_cache, .tox, .idea, .vscode, build, dist, .ruff_cache
```

Excluded files:
```
*.pyc, *.pyo, *.pyd, .DS_Store, *.log, *.egg, *.egg-info, *.so, .coverage, .env, .env.*
```

Add your own patterns with `--extra-ignore`.

## Progress Display
Shows overall percentage, copied size vs total, current throughput, ETA, and the current file label.

## Safety
- Creates a unique destination folder to avoid overwrites (e.g., `name-copy-1`).
- Refuses to copy when the destination resolves to the same path as the source, or when the destination is inside the source.
- Preserves timestamps/metadata where possible via `copystat`.

## Examples
- Copy a single project and name the backup folder:
  - `python app.py -s C:\Dev\MyApp -d E:\Backups --name MyApp-2025-01-01`
- Copy multiple projects at once:
  - `python app.py -s C:\Dev\App1 -s C:\Dev\App2 -d E:\Backups`
- Include dotenv and ignore SQLite files:
  - `python app.py -s . -d D:\Backups --include-dotenv --extra-ignore *.sqlite3`

## Notes
- On Windows, a native multi-select folder picker is used when available.
- On other platforms, the tool tries a Tk dialog first; if GUI isn’t available, it falls back to CLI prompts.

