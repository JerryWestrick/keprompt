"""Each execution unit has its own model in memory: `$.llm_model` for `.exec`, `$.ldm_model` for
`.evaluate`. `model` is the deprecated spelling of `$.llm_model`: every use is redirected there,
with a warning. All offline -- every case fails or finishes before a call would be made.
"""

import json

from conftest import fails, ok, run_prompt


def test_llm_model_is_read_from_its_path():
    assert "nosuch/new-name" in json.dumps(fails("model-llm-path"))


def test_set_writes_the_llm_model_path():
    assert "nosuch/from-set" in json.dumps(fails("model-set-path"))


def test_command_line_writes_the_llm_model_path():
    text = json.dumps(fails("model-none", "--set", "$.llm_model=nosuch/from-cli"))
    assert "nosuch/from-cli" in text


def test_no_model_is_an_error():
    assert "No model specified" in json.dumps(fails("model-none"))


def test_deprecated_model_is_used_as_llm_model_with_a_warning():
    envelope, result = run_prompt("model-deprecated", offline=True)
    assert envelope["success"] is False
    assert "nosuch/old-name" in json.dumps(envelope)
    assert "'model' is deprecated" in result.stderr


def test_deprecated_model_on_the_command_line_warns_too():
    envelope, result = run_prompt("model-none", "--set", "model=nosuch/cli-old", offline=True)
    assert "nosuch/cli-old" in json.dumps(envelope)
    assert "'model' is deprecated" in result.stderr


def test_reading_deprecated_model_reads_llm_model_with_a_warning():
    envelope, result = run_prompt("model-read-deprecated", offline=True)
    assert envelope["success"] is True
    assert "m=some/model" in envelope["stdout"]
    assert "l=some/model" in envelope["stdout"]
    assert "'model' is deprecated" in result.stderr
