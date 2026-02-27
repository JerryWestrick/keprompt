"""keprompt.terminal_output

Rich-aware terminal output routing.

Problem
-------
KePrompt supports a machine-readable `--json` mode where **stdout must contain
only a single JSON document**. During recent refactors, some modules started
printing informational messages directly to stdout (sometimes at import time),
which corrupts JSON output when piping.

Solution
--------
Provide a single, formal API for "terminal output" that can:

* **Pretty mode**: print normally to real stdout using Rich
* **JSON mode**: capture all such output and attach it to the JSON envelope
  under the top-level `stdout` field (as a single concatenated string)

This module intentionally does *not* try to monkeypatch builtins.print().
Instead, KePrompt code should use `terminal_output.print()` / `.write()`.
"""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from rich.console import Console


OutputMode = Literal["buffer", "stdout", "capture"]


@dataclass(frozen=True)
class _BufferedPrint:
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]


class TerminalOutput:
    """Routes terminal output based on selected output format."""

    def __init__(self) -> None:
        # Default to buffering so import-time output doesn't hit stdout.
        self._mode: OutputMode = "buffer"
        self._buffer: List[_BufferedPrint] = []
        self._captured: List[str] = []

        # Rich console for real stdout printing
        self._stdout_console: Console = Console(file=sys.stdout)

    # --------------------------
    # Configuration
    # --------------------------
    @property
    def mode(self) -> OutputMode:
        return self._mode

    def configure(self, mode: Literal["stdout", "capture"]) -> None:
        """Set final output mode and flush any buffered output."""
        if mode not in ("stdout", "capture"):
            raise ValueError(f"Invalid terminal output mode: {mode}")

        # Configure before flushing so flush behaves correctly.
        self._mode = mode
        self._flush_buffer()

    def is_capture(self) -> bool:
        return self._mode == "capture"

    # --------------------------
    # Public API
    # --------------------------
    def write(self, text: str, end: str = "\n") -> None:
        """Write plain text via the unified terminal output channel."""
        self.print(text, end=end)

    def print(self, *objects: Any, **kwargs: Any) -> None:
        """Rich-aware print.

        Accepts strings with Rich markup or any Rich renderable.
        Supported kwargs are the same as `rich.console.Console.print`.

        Notes:
        - In "capture" mode, renderables are converted to plain text.
        - In "buffer" mode, the call is stored and replayed after configure().
        """
        if self._mode == "buffer":
            # Store the call to be replayed once main() decides output format.
            self._buffer.append(_BufferedPrint(args=objects, kwargs=dict(kwargs)))
            return

        if self._mode == "stdout":
            self._stdout_console.print(*objects, **kwargs)
            return

        # capture mode
        self._captured.append(self._render_to_text(objects, kwargs))

    def get_stdout(self) -> str:
        """Get captured stdout as a single concatenated string."""
        # Always include buffered output in capture if configure() was never called.
        # (should not happen in CLI, but keeps behavior sane in tests/imports)
        if self._mode == "buffer" and self._buffer:
            # Render buffered output to captured text without changing mode.
            parts: List[str] = []
            for item in self._buffer:
                parts.append(self._render_to_text(item.args, item.kwargs))
            return "".join(parts)
        return "".join(self._captured)

    # --------------------------
    # Internals
    # --------------------------
    def _flush_buffer(self) -> None:
        if not self._buffer:
            return

        pending = self._buffer
        self._buffer = []

        for item in pending:
            self.print(*item.args, **item.kwargs)

    @staticmethod
    def _render_to_text(objects: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
        """Render the given Rich print call to plain text (no ANSI)."""
        # We create a fresh recording console per call to avoid keeping a large
        # record buffer and to avoid needing to clear it.
        #
        # force_terminal=False and color_system=None ensures no ANSI colors.
        record_console = Console(
            file=io.StringIO(),
            record=True,
            force_terminal=False,
            color_system=None,
        )

        # If caller passes end="" it should be honored.
        record_console.print(*objects, **kwargs)
        return record_console.export_text()


# Global singleton used across the codebase.
terminal_output = TerminalOutput()
