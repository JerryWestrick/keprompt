"""`.question` declares an LDM question set; `.evaluate` runs it.

Every case is a real prompt in `test/prompts/`. The live ones share one run of
`prompts/Ldm.prompt` and make real, billed calls to Jev; the declaration errors need no
network at all. Nothing is mocked -- the one defect the mocked in-process tests missed (a `score`
rubric must be a list, not a mapping: HTTP 422) lived exactly in the seam a mock replaced.
"""

import json
import sqlite3

import pytest

from conftest import chats_db, fails, run_prompt


@pytest.fixture(scope="module")
def run():
    """One real run of prompts/Ldm.prompt, shared by every live assertion below."""
    envelope, result = run_prompt("Ldm")
    assert envelope.get("success") is True, (
        f"run failed: {envelope.get('error')}\nstderr={result.stderr[-2000:]}")
    return envelope


def query(sql: str, *args):
    db = sqlite3.connect(chats_db())
    db.row_factory = sqlite3.Row
    out = [dict(r) for r in db.execute(sql, args)]
    db.close()
    return out


def ldm_parts(run):
    """The LDM messages of this run's chat, in order -- the call's content, as stored."""
    chat = query("SELECT messages_json FROM chats WHERE chat_id = ?", run["chat_id"])[0]
    messages = json.loads(chat["messages_json"])
    return [part for m in messages if m["role"] == "ldm" for part in m["content"]]


def part(run, set_name: str):
    return next(p for p in ldm_parts(run) if p["set"].endswith(set_name))


def costs(run):
    """This run's billed round trips -- LLM and LDM calls alike."""
    return query("SELECT * FROM cost_tracking WHERE chat_id = ? ORDER BY msg_no, round_trip",
                 run["chat_id"])


# --- what the user sees on stdout ----------------------------------------------------------

def test_answers_substitute_into_output(run):
    """`<<?.Intent.object.value>>` must resolve in an ordinary statement."""
    assert "object=Order" in run["stdout"]
    assert "action=create" in run["stdout"]


def test_answer_carries_the_primitive_that_answered(run):
    assert "intent_type=choice" in run["stdout"]
    assert "guard_type=noul" in run["stdout"]


def test_dispatch_line_builds_a_filename(run):
    """The feature's whole point: a path assembled from two answers."""
    assert "dispatch=create-Order.md" in run["stdout"]


# --- what the database keeps: the same records as an LLM call ------------------------------

def test_one_billed_round_trip_per_evaluate(run):
    """An LDM call is an execute: it is billed in cost_tracking like any other."""
    rows = costs(run)
    assert len(rows) == 2
    for r in rows:
        assert r["provider"] == "typesafe"
        assert r["success"] == 1
        assert r["error_message"] is None
        assert r["tokens_in"] > 0
        assert float(r["elapsed_time"]) > 0


def test_one_ldm_message_per_evaluate(run):
    assert [p["set"] for p in ldm_parts(run)] == ["_prompt.question.Intent", "_prompt.question.Guard"]


def test_message_holds_the_request_as_sent(run):
    """The yardstick: the stored call carries enough to rebuild it as a test case."""
    intent = part(run, "Intent")
    assert "3 boxes of lettuce" in intent["state"]
    assert set(intent["questions"]) == {"object", "action"}
    assert intent["questions"]["object"]["criteria"]["Order"].startswith("an order")
    assert intent["questions"]["object"]["instructions"]


def test_message_holds_the_answers(run):
    answers = part(run, "Intent")["answers"]
    assert answers["object"]["value"] == "Order"
    assert answers["object"]["type"] == "choice"
    assert 0.0 <= answers["object"]["confidence"] <= 1.0


def test_score_and_noul_come_back_in_their_own_shapes(run):
    """Live-only: a mocked boundary cannot catch a wrong request shape."""
    answers = part(run, "Guard")["answers"]

    # noul: the 0..1 value is the answer, and it carries no confidence.
    assert answers["injection"]["type"] == "noul"
    assert 0.0 <= answers["injection"]["value"] <= 1.0
    assert "confidence" not in answers["injection"]

    # score: an ordered rubric, answered as a position with a legend.
    assert answers["severity"]["type"] == "score"
    assert 0.0 <= answers["severity"]["value"] <= 1.0
    assert answers["severity"]["legend"]


def test_blatant_injection_scores_high(run):
    """Not a strict contract -- a check that the call is real and wired correctly."""
    assert part(run, "Guard")["answers"]["injection"]["value"] > 0.5


def test_message_records_which_model_answered(run):
    for p in ldm_parts(run):
        assert p["usage"]["input_tokens"] > 0
        # asked-for vs actually-answered: a floating alias resolves to a pinned version
        assert p["provider_selected_model"] and p["provider_selected_model"] != p["model"]


def test_cost_rows_record_which_model_answered(run):
    answered = {p["provider_selected_model"] for p in ldm_parts(run)}
    assert {r["provider_selected_model"] for r in costs(run)} == answered


def test_the_set_holds_which_model_answered(run):
    chat = query("SELECT variables_json FROM chats WHERE chat_id = ?", run["chat_id"])[0]
    sets = json.loads(chat["variables_json"])["_prompt"]["question"]
    assert sets["Intent"]["_provider_selected_model"] == part(run, "Intent")["provider_selected_model"]


def test_inline_state_is_recorded_too(run):
    """`.evaluate ?.Set <text>` without a quote."""
    assert part(run, "Guard")["state"].startswith("IMPORTANT!!!")


def test_no_separate_ldm_table(run):
    tables = {r["name"] for r in query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert not {t for t in tables if "ldm" in t}


# --- which model .evaluate uses: the set's own (its line, or .question's), then $.ldm_model ---

def test_no_ldm_model_anywhere_is_an_error():
    assert "No LDM model" in json.dumps(fails("ldm-no-model"))


def test_evaluate_line_model_wins_over_question_line():
    """.question names a chat model; .evaluate's own line names another, which is the one used."""
    assert "nosuch/ldm-on-evaluate" in json.dumps(fails("ldm-line-beats-question"))


def test_evaluate_line_model_stays_in_its_set_only():
    """The line writes `?.Intent._model`; `$.ldm_model` and the other set are untouched."""
    envelope = fails("ldm-line-model-stays")
    chat = query("SELECT variables_json FROM chats WHERE chat_id = ?", envelope["chat_id"])[0]
    memory = json.loads(chat["variables_json"])["_prompt"]
    assert memory["question"]["Intent"]["_model"] == "nosuch/ldm-stays"
    assert "_model" not in memory["question"]["Other"]
    assert "ldm_model" not in memory


def test_line_params_work_with_an_inline_state():
    """The params object's closing brace ends it; the rest of the line is the state."""
    assert "nosuch/ldm-inline" in json.dumps(fails("ldm-line-params-inline"))


def test_line_params_take_only_ldm_model():
    assert "ldm_model" in json.dumps(fails("ldm-line-params-unknown"))


def test_question_line_model_wins_over_memory():
    """$.ldm_model holds a decision model, .question names a chat model: .question's is used."""
    text = json.dumps(fails("ldm-question-beats-memory"))
    assert "gpt-4o-mini" in text and "chat model" in text


def test_memory_is_the_fallback():
    text = json.dumps(fails("ldm-memory-fallback"))
    assert "nosuch/ldm-in-memory" in text


def test_ldm_model_can_come_from_the_command_line():
    text = json.dumps(fails("ldm-no-model", "--set", "$.ldm_model=nosuch/ldm-from-cli"))
    assert "nosuch/ldm-from-cli" in text


# --- declaration errors: offline, no key and no network ------------------------------------

def test_a_valid_declaration_needs_no_network():
    """Declaring a set makes no call -- only `.evaluate` does."""
    from conftest import ok
    assert "ok" in ok("q-valid")


def test_unknown_primitive_is_refused():
    text = json.dumps(fails("q-unknown-primitive"))
    assert "choice" in text and "noul" in text


def test_duplicate_question_is_refused():
    assert "twice" in json.dumps(fails("q-duplicate-question"))


def test_reserved_question_name_is_refused():
    assert "reserved" in json.dumps(fails("q-reserved-question-name"))


def test_reserved_set_name_is_refused():
    assert "reserved" in json.dumps(fails("q-reserved-set-name"))


def test_noul_takes_no_options():
    assert "no options" in json.dumps(fails("q-noul-with-options"))


def test_body_must_come_from_a_quote():
    assert "multi-line quote" in json.dumps(fails("q-body-not-quoted"))


def test_evaluate_with_empty_state_is_refused():
    assert "state" in json.dumps(fails("q-empty-state"))


def test_evaluating_an_undeclared_set_fails():
    assert "Missing" in json.dumps(fails("q-undeclared-set"))


# --- a statement refuses the wrong kind of model --------------------------------------------

def test_exec_refuses_a_decision_model():
    """An LDM selects from fixed options and never emits text; it cannot answer a conversation."""
    text = json.dumps(fails("mode-exec-with-ldm"))
    assert "decision model" in text and ".evaluate" in text


def test_evaluate_refuses_a_chat_model():
    text = json.dumps(fails("mode-evaluate-with-llm"))
    assert "chat model" in text and ".exec" in text


def test_evaluate_accepts_a_registry_declared_decision_model():
    """The positive case: a model the registry marks mode=ldm goes through."""
    from conftest import ok
    assert "object=Order" in ok("mode-evaluate-with-ldm", offline=False)
