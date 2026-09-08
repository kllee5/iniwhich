# Changelog

All notable changes to this project are documented here. Format is loosely
based on [Keep a Changelog](https://keepachangelog.com/), versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0]

Initial release.

- `iniwhich SECTION KEY FILE...` traces a section/key across a stack of INI
  files given in precedence order and reports the winner (last file to set
  it).
- `--json` emits the same trace as a machine-readable object instead of the
  text report.
- `--files-from PATH` reads the precedence-ordered file list from a text
  file, one path per line, so long-lived stacks don't need retyping.
- `--show-all-sections` skips the section/key arguments and reports the
  winner for every section/key found anywhere in the file stack.
- `[DEFAULT]` is handled the way `configparser` handles it: it fills in for
  a section that exists but doesn't set the key, and does not reach into a
  file that never has the section at all.
- Files that are missing or fail to parse are reported as errors on that
  source rather than crashing the whole trace, and don't block a later file
  in the stack from winning.
