"""
Tests for module-qualified function specs in .functions directive.

Covers: bare names, module.*, module.func, and error cases.
"""

import pytest
from pathlib import Path
from keprompt.keprompt_function_space import FunctionSpace


@pytest.fixture
def fs():
    """Create a FunctionSpace with fake function_array for testing."""
    space = object.__new__(FunctionSpace)
    space.function_array = [
        {"name": "get_clients", "_executable": "prompts/functions/epicure_tools"},
        {"name": "get_orders", "_executable": "prompts/functions/epicure_tools"},
        {"name": "new_order", "_executable": "prompts/functions/epicure_tools"},
        {"name": "cancel_order", "_executable": "prompts/functions/epicure_tools"},
        {"name": "readfile", "_executable": "prompts/functions/keprompt_builtins"},
        {"name": "writefile", "_executable": "prompts/functions/keprompt_builtins"},
        {"name": "execcmd", "_executable": "prompts/functions/keprompt_builtins"},
    ]
    return space


# --- bare names (backward compat) ---

def test_bare_names(fs):
    result = fs.resolve_function_names(["get_clients", "readfile"])
    assert result == ["get_clients", "readfile"]


def test_bare_name_unknown(fs):
    with pytest.raises(ValueError, match="unknown function 'nope'"):
        fs.resolve_function_names(["nope"])


# --- module.* wildcard ---

def test_wildcard(fs):
    result = fs.resolve_function_names(["epicure_tools.*"])
    assert set(result) == {"get_clients", "get_orders", "new_order", "cancel_order"}


def test_wildcard_unknown_module(fs):
    with pytest.raises(ValueError, match="unknown module 'nope'"):
        fs.resolve_function_names(["nope.*"])


# --- module.func qualified ---

def test_qualified_name(fs):
    result = fs.resolve_function_names(["keprompt_builtins.readfile"])
    assert result == ["readfile"]


def test_qualified_name_wrong_module(fs):
    with pytest.raises(ValueError, match="unknown function 'readfile' in module 'epicure_tools'"):
        fs.resolve_function_names(["epicure_tools.readfile"])


# --- mixed specs ---

def test_mixed_specs(fs):
    result = fs.resolve_function_names(["epicure_tools.*", "keprompt_builtins.readfile"])
    assert "get_clients" in result
    assert "readfile" in result
    assert "writefile" not in result  # only readfile from builtins


def test_wildcard_plus_bare(fs):
    result = fs.resolve_function_names(["epicure_tools.*", "readfile"])
    assert "get_clients" in result
    assert "readfile" in result


# --- deduplication ---

def test_no_duplicates(fs):
    result = fs.resolve_function_names(["get_clients", "epicure_tools.*"])
    assert result.count("get_clients") == 1
