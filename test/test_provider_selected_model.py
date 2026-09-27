"""`provider_selected_model`: the model that answered -- the one asked for, unless the provider
identified another. `.exec` writes it to `$._provider_selected_model`, and every round trip stores
it in `cost_tracking`. (`.evaluate`'s side is in `test_ldm.py`.)

These are live, billed calls, one per provider. A provider the account cannot reach is skipped.
"""

import sqlite3

import pytest

from conftest import chats_db
from test_system_message import PROVIDERS, reply


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_exec_records_the_model_that_answered(provider):
    answer = reply(provider, "psm-exec")
    shown = answer.split("psm=", 1)[1].split()[0]
    assert shown, f"{provider}: $._provider_selected_model is empty"

    stored = sqlite3.connect(chats_db()).execute(
        "SELECT provider_selected_model FROM cost_tracking ORDER BY rowid DESC LIMIT 1").fetchone()
    assert stored == (shown,)
