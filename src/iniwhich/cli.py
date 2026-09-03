import argparse
import itertools
import json
import sys
from typing import Optional, Sequence

from .resolver import discover_section_keys, read_file_list, trace


def main(argv: Optional[Sequence[str]] = None) -> int:
    # argparse's greedy matching of two optional positionals ("section",
    # "key") followed by a variadic one ("files") would eat the first two
    # file paths as section/key in --show-all-sections mode, so the shape of
    # the positionals has to be decided before the real parse.
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    show_all_sections = "--show-all-sections" in raw_argv

    parser = argparse.ArgumentParser(
        prog="iniwhich",
        description=(
            "Show which INI file actually sets a key's effective value, when the "
            "same section/key is spread across several layered config files."
        ),
    )
    if show_all_sections:
        parser.add_argument(
            "files",
            nargs="*",
            help=(
                "config files in precedence order, lowest priority first "
                "(the last file that defines each key wins). Omit if using "
                "--files-from"
            ),
        )
    else:
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
        "--show-all-sections",
        action="store_true",
        help=(
            "instead of tracing one section/key, report the winner for every "
            "section/key found anywhere in the file stack"
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

    if show_all_sections:
        pairs = discover_section_keys(files)
        results = [trace(section, key, files) for section, key in pairs]

        if args.json:
            print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            print(_all_sections_text(results))

        return 0 if results else 1

    result = trace(args.section, args.key, files)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.to_text())

    return 0 if result.winner is not None else 1


def _all_sections_text(results) -> str:
    if not results:
        return "no sections or keys found in any of the given files"

    lines = []
    for section, section_results in itertools.groupby(results, key=lambda r: r.section):
        lines.append(f"[{section}]")
        for result in section_results:
            winner = result.winner
            lines.append(f"  {result.key} -> {winner.file} = {winner.value}")
        lines.append("")
    return "\n".join(lines).rstrip("\n")


if __name__ == "__main__":
    sys.exit(main())
