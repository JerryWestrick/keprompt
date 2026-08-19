#!/usr/bin/env python3
"""Compatibility entry point for the 2.15.0 -> 2.16.0 SQLite migration."""

import sys
from pathlib import Path

if __package__:
    from .migrate_sqlite import migrate
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from keprompt.migrations.migrate_sqlite import migrate


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    paths = [argument for argument in argv if not argument.startswith("-")]
    if len(paths) != 1:
        print(f"usage: {Path(sys.argv[0]).name} <path/to/chats.db> [--no-backup]")
        return 2
    changed = migrate(
        paths[0], target_version="2.16.0", backup="--no-backup" not in argv
    )
    print("migration complete" if changed else "database already current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())