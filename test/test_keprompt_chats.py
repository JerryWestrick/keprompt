from pathlib import Path

import pytest

from keprompt.keprompt_chats import sqlite_path


def test_sqlite_path_is_the_workspace_database():
    assert sqlite_path("sqlite:///prompts/chats.db") == Path("prompts/chats.db")


def test_sqlite_path_keeps_an_absolute_database():
    assert sqlite_path("sqlite:////home/jerry/Epicure/prompts/chats.db") == Path(
        "/home/jerry/Epicure/prompts/chats.db"
    )


def test_sqlite_path_refuses_a_non_sqlite_url():
    with pytest.raises(SystemExit):
        sqlite_path("postgresql://localhost/keprompt")
