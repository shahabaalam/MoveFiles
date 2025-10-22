import argparse
from pathlib import Path


def parse_args(argv: list[str]):
    p = argparse.ArgumentParser(
        description="Copy a project while skipping venvs, __pycache__, and .pyc files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--source",
        "-s",
        type=Path,
        action="append",
        help="Source folder(s) to copy (repeat this flag to add multiple)",
    )
    p.add_argument(
        "--dest",
        "-d",
        type=Path,
        help="Destination parent folder (e.g., a drive or directory)",
    )
    p.add_argument("--name", type=str, default=None, help="Name of new folder at destination")
    p.add_argument(
        "--include-dotenv",
        action="store_true",
        help="Include .env files instead of excluding them",
    )
    p.add_argument(
        "--extra-ignore",
        action="append",
        default=None,
        help="Additional name globs to ignore (can repeat)",
    )
    return p.parse_args(argv)

