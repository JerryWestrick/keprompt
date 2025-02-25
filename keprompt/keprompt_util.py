import argparse
import os
import re
from typing import Optional

from rich.console import Console

console = Console()

"""Box drawing characters for ASCII-style borders."""
TOP_LEFT = '╭'
TOP_RIGHT = '╮'
BOTTOM_LEFT = '╰'
BOTTOM_RIGHT = '╯'
VERTICAL = '│'
HORIZONTAL = '─'
RIGHT_TRIANGLE = u"\u25B6"
LEFT_TRIANGLE = u"\u25C0"
CIRCLE = "⬤"
CHAR_SEND_REQUEST = RIGHT_TRIANGLE
HORIZONTAL_LINE = u"\u2500"



def backup_file(filepath: str, backup_dir: Optional[str] = None, extension: Optional[str] = None) -> str:
    """Version files with numbered backups.

    Args:
        filepath: Path to the file to version
        backup_dir: Directory for backups (defaults to file's directory)
        extension: Override extension for backup files (defaults to original extension)
    """
    base_dir = os.path.dirname(filepath)
    filename, file_ext = os.path.splitext(os.path.basename(filepath))

    backup_dir = backup_dir or base_dir
    backup_ext = extension or file_ext

    if backup_dir == '':
        backup_dir = '.'

    # console.print(f"{backup_dir=}, {base_dir=}, {filename=}, {backup_ext=}")
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)

    backup_pattern = re.compile(f'{filename}\\.~(\\d+)~{backup_ext}')
    versions = [
        int(match.group(1))
        for match in (backup_pattern.match(f) for f in os.listdir(backup_dir))
        if match
    ]

    for version in sorted(versions, reverse=True):
        old_file = f'{backup_dir}/{filename}.~{version:02d}~{backup_ext}'
        new_file = f'{backup_dir}/{filename}.~{version + 1:02d}~{backup_ext}'
        os.rename(old_file, new_file)

    target_file = f'{backup_dir}/{filename}{backup_ext}'
    if os.path.exists(target_file):
        os.rename(target_file, f'{backup_dir}/{filename}.~01~{backup_ext}')

    return target_file


def get_cmd_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keprompt util test command line tool.")
    parser.add_argument('-v', '--versioned_file', action='store_true', help='test the versioned_file() routine..')
    parser.add_argument('-l', '--list', nargs='?', const='*', help='List Prompt file')

    return parser.parse_args()



if __name__ == "__main__":
    # Test The routine...
    args: argparse.Namespace = get_cmd_args()

    if args.list:
        console.print(f"[bold white]{TOP_LEFT}{HORIZONTAL * 5}[/][bold green] Testable Routines [/][bold white]{HORIZONTAL * 61}{TOP_RIGHT}[/]")
        console.print(f"[bold white]{VERTICAL}{'':<85}{VERTICAL}[/]")
        console.print(f"[bold white]{BOTTOM_LEFT}{HORIZONTAL * 85}{BOTTOM_RIGHT}[/]")

    if args.versioned_file:
        console.print(f"[bold white]{TOP_LEFT}{HORIZONTAL * 5}[/][bold green] Versioned_File [/][bold white]{HORIZONTAL * 61}{TOP_RIGHT}[/]")
        for i in range(10):
            filename = backup_file('logs/test.log')
            console.print(f"[bold white]{VERTICAL}[/]{i:02} {filename:<82}[bold white]{VERTICAL}[/]")
            with open(filename, 'w') as file:
                pass
        console.print(f"[bold white]{BOTTOM_LEFT}{HORIZONTAL * 85}{BOTTOM_RIGHT}[/]")



