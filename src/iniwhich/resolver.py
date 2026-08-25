"""Trace a section/key pair across a stack of INI files, in precedence order."""

from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass
class Source:
    file: str
    found: bool
    value: Optional[str]
    error: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"file": self.file, "found": self.found, "value": self.value}
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class TraceResult:
    section: str
    key: str
    sources: List[Source] = field(default_factory=list)

    @property
    def winner(self) -> Optional[Source]:
        # last file in precedence order that actually defines the key wins,
        # same rule most layered-config loaders use (later file overrides earlier)
        for source in reversed(self.sources):
            if source.found:
                return source
        return None

    def to_dict(self) -> dict:
        winner = self.winner
        return {
            "section": self.section,
            "key": self.key,
            "sources": [s.to_dict() for s in self.sources],
            "winner": {"file": winner.file, "value": winner.value} if winner else None,
        }

    def to_text(self) -> str:
        lines = []
        for source in self.sources:
            if source.error:
                lines.append(f"{source.file}: error - {source.error}")
            elif source.found:
                lines.append(f"{source.file}: {self.section}.{self.key} = {source.value}")
            else:
                lines.append(f"{source.file}: (not set)")

        winner = self.winner
        lines.append("")
        if winner:
            lines.append(f"winner: {winner.file} -> {self.section}.{self.key} = {winner.value}")
        else:
            lines.append(f"winner: none - {self.section}.{self.key} is not set in any file")
        return "\n".join(lines)


def read_file_list(path: str) -> List[str]:
    """Read a precedence-ordered list of INI file paths from a text file.

    One path per line, lowest priority first - same order as the positional
    FILES arguments on the command line. Blank lines and lines starting with
    '#' are skipped so the list can carry comments explaining why a file is
    where it is in the stack.
    """
    files = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            files.append(line)
    return files


def trace(section: str, key: str, filepaths: Sequence[str]) -> TraceResult:
    """Read each file in order and record what it says about section/key.

    Uses RawConfigParser so that values containing '%' don't blow up on
    interpolation syntax they were never meant to trigger - we only want
    to report what's on disk, not evaluate it.
    """
    sources = []
    for path in filepaths:
        parser = configparser.RawConfigParser()
        try:
            with open(path, encoding="utf-8") as fh:
                parser.read_file(fh)
        except (OSError, configparser.Error) as exc:
            sources.append(Source(file=path, found=False, value=None, error=str(exc)))
            continue

        if parser.has_option(section, key):
            sources.append(Source(file=path, found=True, value=parser.get(section, key)))
        else:
            sources.append(Source(file=path, found=False, value=None))

    return TraceResult(section=section, key=key, sources=sources)
