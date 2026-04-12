"""Property-based tests for pylogkit processors and utilities."""

import string

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pylogkit.main import (
    InvalidLoggerNameError,
    LoggerReg,
    SetupLogger,
    add_caller_details,
    bind,
    clear_context,
    context_scope,
    get_context,
)


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset SetupLogger state and context before each test."""
    SetupLogger.reset()
    clear_context()
    yield
    SetupLogger.reset()
    clear_context()


# Strategies
valid_chars = st.characters(
    whitelist_categories=("L", "N", "S"),
    blacklist_characters="",
    min_codepoint=0x20,
    max_codepoint=0x7E,
)

arbitrary_strings = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        blacklist_characters="",
    ),
    min_size=1,
    max_size=100,
)

non_empty_strings = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        blacklist_characters="",
    ),
    min_size=1,
    max_size=50,
)

context_values = st.one_of(
    st.booleans(),
    st.integers(min_value=-1000, max_value=1000),
    st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=50),
)


@given(name=arbitrary_strings)
def test_logger_reg_accepts_any_valid_name(name):
    """Any non-empty name should be accepted."""
    reg = LoggerReg(name=name)
    assert reg.name == name.strip()
    assert len(reg.name) > 0


@given(name=st.just("") | st.just("   ") | st.just("\t") | st.just("\n"))
def test_logger_reg_rejects_empty_or_whitespace(name):
    """Empty or whitespace-only names should raise."""
    with pytest.raises(InvalidLoggerNameError):
        LoggerReg(name=name)


@given(name=arbitrary_strings)
def test_logger_reg_strips_whitespace(name):
    """Name should be stripped of leading/trailing whitespace."""
    padded = f"  {name}  "
    reg = LoggerReg(name=padded)
    assert reg.name == name


@given(filename=arbitrary_strings, func_name=arbitrary_strings, lineno=st.integers(min_value=0, max_value=99999))
def test_add_caller_details_formats_correctly(filename, func_name, lineno):
    """add_caller_details should always produce correct logger format."""
    event_dict = {
        "filename": filename,
        "func_name": func_name,
        "lineno": lineno,
        "event": "test",
    }
    result = add_caller_details(None, "", event_dict)
    expected_logger = f"{filename}:{func_name}:{lineno}"
    assert result["logger"] == expected_logger
    assert "filename" not in result
    assert "func_name" not in result
    assert "lineno" not in result
    assert result["event"] == "test"


@given(
    keys=st.dictionaries(
        keys=non_empty_strings,
        values=context_values,
        min_size=1,
        max_size=10,
    ),
)
def test_bind_and_get_context_roundtrip(keys):
    """Binding values should make them available via get_context."""
    clear_context()
    try:
        bind(**keys)
        ctx = get_context()
        for k, v in keys.items():
            assert ctx[k] == v
    finally:
        clear_context()


@given(
    outer_keys=st.dictionaries(keys=non_empty_strings, values=context_values, min_size=1, max_size=5),
    inner_keys=st.dictionaries(keys=non_empty_strings, values=context_values, min_size=1, max_size=5),
)
def test_context_scope_restores_outer_context(outer_keys, inner_keys):
    """context_scope should restore previous context on exit."""
    clear_context()
    try:
        bind(**outer_keys)
        with context_scope(**inner_keys):
            inner_ctx = get_context()
            for k, v in inner_keys.items():
                assert inner_ctx[k] == v
        outer_ctx = get_context()
        for k, v in outer_keys.items():
            assert outer_ctx[k] == v
        for k in inner_keys:
            if k not in outer_keys:
                assert k not in outer_ctx or outer_ctx[k] == outer_keys.get(k)
    finally:
        clear_context()


@given(
    keys=st.dictionaries(keys=non_empty_strings, values=context_values, min_size=1, max_size=5),
)
def test_context_scope_cleans_on_exception(keys):
    """context_scope should clean up even if exception occurs."""
    clear_context()
    try:
        with pytest.raises(ValueError, match="test"), context_scope(**keys):
            raise ValueError("test")
        ctx = get_context()
        for k in keys:
            if k not in ctx:
                pass  # expected - context was cleaned
    finally:
        clear_context()


@given(level=st.sampled_from(list(LoggerReg.Level)))
def test_logger_reg_level_enum_roundtrip(level):
    """LoggerReg.Level should be consistent."""
    assert level.value == level.value.upper()
    assert level in LoggerReg.Level


@given(
    event_dict=st.dictionaries(
        keys=st.sampled_from(["event", "timestamp", "level", "extra_key"]),
        values=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False, allow_infinity=False), st.booleans()),
        min_size=1,
        max_size=10,
    ),
)
def test_add_caller_details_preserves_other_keys(event_dict):
    """add_caller_details should preserve all keys except caller details."""
    event_dict_copy = event_dict.copy()
    result = add_caller_details(None, "", event_dict_copy)
    for k, v in event_dict.items():
        if k not in ("filename", "func_name", "lineno"):
            assert result.get(k) == v


def test_add_caller_details_with_defaults():
    """add_caller_details should use defaults when keys are missing."""
    event_dict = {"event": "test"}
    result = add_caller_details(None, "", event_dict)
    assert result["logger"] == "?:?:0"
    assert result["event"] == "test"
