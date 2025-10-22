from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

from .ignore import make_ignore


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _unique_dest(base_dir: Path, desired_name: str) -> Path:
    candidate = base_dir / desired_name
    if not candidate.exists():
        return candidate
    i = 1
    while True:
        candidate = base_dir / f"{desired_name}-copy-{i}"
        if not candidate.exists():
            return candidate
        i += 1


def _scan_total_bytes(source: Path, ignore) -> tuple[int, int]:
    total_bytes = 0
    total_files = 0
    for root, dirs, files in os.walk(source):
        names = list(dirs) + list(files)
        ignored = ignore(root, names)
        # prune dirs in-place
        dirs[:] = [d for d in dirs if d not in ignored]
        for f in files:
            if f in ignored:
                continue
            fp = Path(root) / f
            try:
                total_bytes += fp.stat().st_size
                total_files += 1
            except OSError:
                # Skip unreadable file
                continue
    return total_files, total_bytes


def _format_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for u in units:
        if size < 1024.0 or u == units[-1]:
            return f"{size:.1f} {u}"
        size /= 1024.0


def _format_eta(seconds: float) -> str:
    if seconds == float("inf") or seconds != seconds:  # NaN
        return "--:--"
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _copy_file_with_progress(src: Path, dst: Path, progress_cb, chunk_size: int = 1024 * 1024):
    size = src.stat().st_size
    with open(src, "rb") as rf, open(dst, "wb") as wf:
        while True:
            buf = rf.read(chunk_size)
            if not buf:
                break
            wf.write(buf)
            progress_cb(len(buf), size)
    try:
        shutil.copystat(src, dst, follow_symlinks=True)
    except OSError:
        pass


def run_copy_many(
    sources: list[Path],
    dest_parent: Path,
    name: str | None,
    include_dotenv: bool,
    extra_globs: list[str] | None,
):
    if not dest_parent.exists() or not dest_parent.is_dir():
        print(f"Destination parent not found or not a directory: {dest_parent}")
        sys.exit(3)

    for source in sources:
        if not source.exists() or not source.is_dir():
            print(f"Source not found or not a directory: {source}")
            sys.exit(2)

    if name and len(sources) != 1:
        print("Note: --name is ignored when copying multiple sources.")

    ignore = make_ignore(extra_globs=extra_globs, include_dotenv=include_dotenv)

    # Pre-scan to compute totals
    per_source_totals: dict[Path, tuple[int, int]] = {}
    total_files_all = 0
    total_bytes_all = 0
    for src in sources:
        files, bytes_ = _scan_total_bytes(src, ignore)
        per_source_totals[src] = (files, bytes_)
        total_files_all += files
        total_bytes_all += bytes_

    if total_bytes_all == 0:
        print("Nothing to copy after applying ignore rules.")
        return

    print(f"Sources: {len(sources)} | Files: {total_files_all} | Size: {_format_size(total_bytes_all)}")
    print("Skipping virtual environments, __pycache__, and Python bytecode.")

    start_time = time.time()
    total_copied_bytes = 0
    last_update = 0.0

    def print_progress(current_label: str):
        nonlocal last_update
        now = time.time()
        if now - last_update < 0.1:  # throttle updates
            return
        last_update = now
        elapsed = now - start_time
        speed = total_copied_bytes / elapsed if elapsed > 0 else 0.0
        remaining = total_bytes_all - total_copied_bytes
        eta = remaining / speed if speed > 0 else float("inf")
        pct = (total_copied_bytes / total_bytes_all) * 100.0
        line = (
            f"Overall {pct:6.2f}%  {_format_size(total_copied_bytes)} / {_format_size(total_bytes_all)}  "
            f"| { _format_size(int(speed)) }/s  | ETA {_format_eta(eta)}  | current: {current_label[:40]}"
        )
        print("\r" + line.ljust(120), end="", flush=True)

    try:
        for source in sources:
            desired_name = name or source.name if len(sources) == 1 else source.name
            final_dest = _unique_dest(dest_parent, desired_name)

            if source.resolve() == final_dest.resolve():
                print("\nDestination resolves to the same path as source; aborting.")
                sys.exit(4)
            if _is_relative_to(final_dest, source):
                print("\nDestination is inside source; choose a different location.")
                sys.exit(5)

            # Walk and copy with ignore rules
            for root, dirs, files in os.walk(source):
                names = list(dirs) + list(files)
                ignored = ignore(root, names)
                dirs[:] = [d for d in dirs if d not in ignored]

                # Ensure destination directory exists
                rel_root = os.path.relpath(root, start=source)
                dest_root = final_dest / rel_root if rel_root != "." else final_dest
                os.makedirs(dest_root, exist_ok=True)

                for f in files:
                    if f in ignored:
                        continue
                    src_file = Path(root) / f
                    dst_file = Path(dest_root) / f
                    # Ensure parent exists (already ensured, but safe)
                    os.makedirs(dst_file.parent, exist_ok=True)

                    def on_progress(inc_bytes: int, file_size: int):
                        nonlocal total_copied_bytes
                        total_copied_bytes += inc_bytes
                        label = f"{source.name}/" + str(src_file.relative_to(source))
                        print_progress(label)

                    _copy_file_with_progress(src_file, dst_file, on_progress)

        # final line
        print()
        print("Done.")
        print(f"Backups located under: {dest_parent}")
    except KeyboardInterrupt:
        print("\nAborted by user.")
        sys.exit(8)
    except Exception as e:
        print(f"\nCopy failed: {e}")
        sys.exit(7)

