"""Live fallback: same delivery photo through analyze_delivery_photo, twice via keprompt.

Run with KEPROMPT_LIVE=1. Needs CEREBRAS_API_KEY and Epicure's model price file.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent / "analyze_delivery_photo"
JPG = FIXTURE_DIR / "REM26-1199.jpg"
PROMPT = FIXTURE_DIR / "analyze_delivery_photo.prompt"
EXPECTED = json.loads((FIXTURE_DIR / "expected.json").read_text(encoding="utf-8"))
EPICURE_PRICES = Path("/home/jerry/Epicure/prompts/functions/model_prices_and_context_window.json")

OCR_FIELDS = (
    "remision_number",
    "client",
    "payment_status",
    "payment_source",
    "signature_present",
    "original_total",
    "adjusted_total",
    "items_rejected",
)


def _cerebras_key():
    load_dotenv(Path.home() / ".env")
    return os.getenv("CEREBRAS_API_KEY") or os.getenv("CEREBRAS_KEY")


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("KEPROMPT_LIVE") != "1", reason="set KEPROMPT_LIVE=1 to run"),
    pytest.mark.skipif(not _cerebras_key(), reason="CEREBRAS_API_KEY not set"),
    pytest.mark.skipif(not EPICURE_PRICES.is_file(), reason="Epicure model price file not found"),
]


def _parse_ocr(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _run_keprompt(workspace: Path, extra_args: list[str]) -> dict:
    cmd = [
        sys.executable,
        "-m",
        "keprompt",
        "chat",
        "create",
        "--json",
        "--prompt",
        "analyze_delivery_photo",
        "--set",
        "image_path",
        str(JPG.resolve()),
        *extra_args,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    result = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        pytest.fail(f"keprompt failed ({result.returncode}): {result.stderr or result.stdout}")
    envelope = json.loads(result.stdout)
    if not envelope.get("success"):
        pytest.fail(f"keprompt unsuccessful: {envelope.get('error')}")
    return envelope


def _metrics(envelope: dict) -> dict:
    meta = envelope["data"]["metadata"]
    return {
        "tokens_in": meta["tokens_in"],
        "tokens_out": meta["tokens_out"],
        "total_cost": meta["total_cost"],
        "api_time": meta["api_time"],
        "elapsed_time": meta["elapsed_time"],
    }


def test_analyze_delivery_photo_fallback(tmp_path):
    prompts = tmp_path / "prompts"
    functions = prompts / "functions"
    functions.mkdir(parents=True)
    shutil.copy(PROMPT, prompts / "analyze_delivery_photo.prompt")
    shutil.copy(EPICURE_PRICES, functions / "model_prices_and_context_window.json")

    options = tmp_path / "llm_options.json"
    options.write_text(
        json.dumps({"llm_options": {"reasoning_effort": "none"}}),
        encoding="utf-8",
    )

    default_run = _run_keprompt(tmp_path, [])
    options_run = _run_keprompt(tmp_path, ["--set-from-json", str(options)])

    default_m = _metrics(default_run)
    options_m = _metrics(options_run)

    print()
    print(f"{'':20} {'no options':>14} {'reasoning none':>16}")
    for key in ("tokens_in", "tokens_out", "total_cost", "api_time", "elapsed_time"):
        print(f"{key:20} {default_m[key]!s:>14} {options_m[key]!s:>16}")

    for label, envelope in (("no options", default_run), ("reasoning none", options_run)):
        try:
            ocr = _parse_ocr(envelope["ai_response"])
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"OCR {label}: unreadable ({e})")
            continue
        diffs = []
        for key in OCR_FIELDS:
            got, want = ocr.get(key), EXPECTED[key]
            if key in ("original_total", "adjusted_total"):
                same = got is not None and float(got) == float(want)
            elif key == "client":
                same = str(got).upper() == str(want).upper()
            else:
                same = got == want
            if not same:
                diffs.append(f"{key}: {got!r} (expected {want!r})")
        print(f"OCR {label}: {'ok' if not diffs else '; '.join(diffs)}")
