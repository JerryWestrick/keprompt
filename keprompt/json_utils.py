"""Safe JSON parsing utilities for handling malformed LLM responses."""

import json
import sys


def safe_json_loads(raw: str, context: str = ""):
    """Parse JSON with recovery for common LLM malformations.

    Handles:
    - "Extra data" (model returns valid JSON followed by extra text)
    - Logs raw input to stderr on failure for debugging

    Args:
        raw: The JSON string to parse.
        context: Description of where this JSON came from (for error messages).

    Returns:
        The parsed JSON value.

    Raises:
        json.JSONDecodeError: If JSON cannot be recovered.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        repaired = _try_repair(raw)
        if repaired is not None:
            label = context or "unknown"
            display_raw = raw[:200] + "..." if len(raw) > 200 else raw
            print(f"[JSON Repaired] {label}: {display_raw!r}", file=sys.stderr)
            return repaired

        # Unrecoverable — log full details for debugging
        label = f"{context}: " if context else ""
        display_raw = raw[:1000] + "..." if len(raw) > 1000 else raw
        print(f"[JSON Error] {label}{e}", file=sys.stderr)
        print(f"[JSON Error] Raw data: {display_raw!r}", file=sys.stderr)
        raise


def _try_repair(raw: str):
    """Attempt to repair common LLM JSON malformations.

    Returns the parsed value on success, or None if unrecoverable.
    """
    stripped = raw.strip()

    # --- Brace/bracket repairs (try these first, they're more specific) ---

    # Missing opening brace: looks like object content without the leading {
    # e.g. ' "action": "search", "query": "foo"}'
    # or   'action": "search", ...'  (missing both { and opening ")
    if not stripped.startswith('{') and stripped.endswith('}'):
        for prefix in ['{', '{"']:
            try:
                return json.loads(prefix + stripped)
            except json.JSONDecodeError:
                pass
        # More aggressive: find first complete "key": and wrap from there
        result = _repair_truncated_object(stripped)
        if result is not None:
            return result

    # Missing closing brace
    if stripped.startswith('{') and not stripped.endswith('}'):
        try:
            return json.loads(stripped + '}')
        except json.JSONDecodeError:
            pass

    # Missing both braces: bare key-value pairs
    # e.g. '"action": "search", "query": "foo"'
    # or   'action": "search", "query": "foo"'
    if not stripped.startswith('{') and not stripped.endswith('}'):
        if ':' in stripped:
            for prefix in ['{', '{"']:
                try:
                    return json.loads(prefix + stripped + '}')
                except json.JSONDecodeError:
                    pass
            result = _repair_truncated_object(stripped + '}')
            if result is not None:
                return result

    # Missing opening bracket for arrays
    if not stripped.startswith('[') and stripped.endswith(']'):
        try:
            return json.loads('[' + stripped)
        except json.JSONDecodeError:
            pass

    # --- Fallback: extract first valid JSON value (handles trailing junk) ---
    try:
        decoder = json.JSONDecoder()
        result, _ = decoder.raw_decode(stripped)
        return result
    except json.JSONDecodeError:
        pass

    return None


import re

# Matches the start of a JSON key-value pair: "key":
_KEY_PATTERN = re.compile(r'"[^"]+"\s*:')


def _repair_truncated_object(s: str):
    """Repair a JSON object whose beginning was truncated.

    The model may chop off the leading '{"' or even part of the first key.
    e.g. 'action": "search", "query": "foo"}'
    We find the first complete "key": pattern and wrap everything from there.
    """
    m = _KEY_PATTERN.search(s)
    if m:
        # Take from the start of the matched key to the end
        candidate = '{' + s[m.start():]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None
