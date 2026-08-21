# iniwhich

Most real deployments don't have one config file, they have a stack of them:
a system default, a per-environment override, a per-host override, maybe a
file dropped in by whatever deploy tooling you're using. All of them are INI
files, all of them might touch the same `[section] key = value`, and the
actual value your program uses is whichever file loaded last set it.

When something is misconfigured, the question you actually have is: "which
of these files is setting `db.host`, and what would it be without that one?"
Answering that by hand means opening every file and grepping. `iniwhich`
answers it directly.

## usage

Say you have three files, applied in this order (later overrides earlier):

`base.ini`:

```ini
[db]
host = localhost
port = 5432
```

`prod.ini`:

```ini
[db]
host = db.internal.example
```

`hotfix.ini`:

```ini
[db]
```

Run:

```
$ iniwhich db host base.ini prod.ini hotfix.ini
base.ini: db.host = localhost
prod.ini: db.host = db.internal.example
hotfix.ini: (not set)

winner: prod.ini -> db.host = db.internal.example
```

`hotfix.ini` has a `[db]` section but never touches `host`, so it's not the
one to blame - `prod.ini` is, even though it's not the last file in the
stack.

With `--json`:

```
$ iniwhich db host base.ini prod.ini hotfix.ini --json
{
  "section": "db",
  "key": "host",
  "sources": [
    {"file": "base.ini", "found": true, "value": "localhost"},
    {"file": "prod.ini", "found": true, "value": "db.internal.example"},
    {"file": "hotfix.ini", "found": false, "value": null}
  ],
  "winner": {"file": "prod.ini", "value": "db.internal.example"}
}
```

The JSON shape is stable and meant to be piped into `jq` or another script -
`.winner.file` tells you which file to edit, `.sources` gives you the full
override chain.

Exit code is `0` if the key resolves to a value anywhere in the stack, `1`
if no file in the stack sets it.

## installing

No dependencies beyond the standard library. From a checkout:

```
pip install -e .
```

which puts an `iniwhich` command on your PATH.

## why not just grep

`grep -n host base.ini prod.ini hotfix.ini` gets you the raw matches, but
it doesn't know INI structure - it can't tell a `[db] host` from a
`[cache] host` in another section, and it won't tell you which match is the
one that actually wins. `iniwhich` parses each file properly and applies the
same last-one-wins rule your config loader does.
