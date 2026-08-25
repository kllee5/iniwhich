import argparse
import json
import sys
from typing import Optional, Sequence

from .resolver import read_file_list, trace


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="iniwhich",
        description=(
            "Show which INI file actually sets a key's effective value, when the "
            "same section/key is spread across several layered config files."
        ),
    )
    parser.add_argument("section", help="INI section name, e.g. 'db'")
    parser.add_argument("key", help="key within that section, e.g. 'host'")
    parser.add_argument(
        "files",
        nargs="*",
        help=(
            "config files in precedence order, lowest priority first "
            "(the last file that defines the key wins). Omit if using "
            "--files-from"
        ),
    )
    parser.add_argument(
        "--files-from",
        metavar="PATH",
        help=(
            "read the precedence-ordered file list from PATH instead of "
            "argv, one path per line (blank lines and '#' comments ignored)"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of the human-readable report",
    )
    args = parser.parse_args(argv)

    if args.files_from:
        if args.files:
            parser.error("pass FILES as arguments or use --files-from, not both")
        try:
            files = read_file_list(args.files_from)
        except OSError as exc:
            parser.error(f"could not read --files-from file: {exc}")
        if not files:
            parser.error(f"--files-from file '{args.files_from}' lists no files")
    else:
        if not args.files:
            parser.error("no files given: pass FILES as arguments or use --files-from")
        files = args.files

    result = trace(args.section, args.key, files)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.to_text())

    return 0 if result.winner is not None else 1


if __name__ == "__main__":
    sys.exit(main())
