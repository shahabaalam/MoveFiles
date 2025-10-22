import sys

from movefiles.cli import parse_args
from movefiles.pickers import _pick_directories, _pick_directory
from movefiles.copyops import run_copy_many


def main(argv: list[str] | None = None):
    args = parse_args(argv or sys.argv[1:])

    sources = args.source or _pick_directories()
    dest_parent = args.dest or _pick_directory(
        "Select the destination folder (parent)", "Enter destination parent folder path: "
    )

    run_copy_many(
        sources=sources,
        dest_parent=dest_parent,
        name=args.name,
        include_dotenv=bool(args.include_dotenv),
        extra_globs=args.extra_ignore,
    )


if __name__ == "__main__":
    main()
