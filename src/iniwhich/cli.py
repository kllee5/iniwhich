import argparse
import json
import sys
from typing import Optional, Sequence

from .resolver import trace


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
        nargs="+",
        help=(
            "config files in precedence order, lowest priority first "
            "(the last file that defines the key wins)"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of the human-readable report",
    )
    args = parser.parse_args(argv)

    result = trace(args.section, args.key, args.files)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.to_text())

    return 0 if result.winner is not None else 1


if __name__ == "__main__":
    sys.exit(main())
