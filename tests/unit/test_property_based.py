"""Property-based tests for pylogkit processors and utilities."""

import json
import string
from datetime import UTC, date, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pylogkit.main import (
    InvalidLoggerNameError,
    Level,
    LoggerReg,
    SetupLogger,
    _json_default,
    add_caller_details,
    bind,
    clear_context,
    context_scope,
    get_context,
    make_json_safe,
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
@settings(deadline=None)
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
            assert k not in ctx, f"Context key '{k}' was not cleaned up after exception"
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


# --- Property-based tests for make_json_safe and _json_default ---


def _json_safe_values(max_depth: int = 3) -> st.SearchStrategy:
    """Generate JSON-safe values of various types."""
    basic = st.one_of(
        st.none(),
        st.booleans(),
        st.integers(min_value=-10000, max_value=10000),
        st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False),
        st.text(max_size=100),
    )
    if max_depth <= 0:
        return basic

    nested = st.deferred(
        lambda: st.one_of(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(basic, nested),
                min_size=0,
                max_size=5,
            ),
            st.lists(
                st.one_of(basic, nested),
                min_size=0,
                max_size=5,
            ),
        )
    )
    return st.one_of(basic, nested)


@given(
    event_dict=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=_json_safe_values(max_depth=2),
        min_size=0,
        max_size=10,
    ),
)
def test_make_json_safe_preserves_json_safe_values(event_dict):
    """make_json_safe should not modify already JSON-safe values."""
    result = make_json_safe(None, "", event_dict.copy())
    # Result should be JSON serializable
    serialized = json.dumps(result)
    assert serialized is not None


@given(
    event_dict=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(
            st.just(datetime(2026, 1, 1, tzinfo=UTC)),
            st.just(date(2026, 1, 1)),
            st.just({1, 2, 3}),
            st.just(ValueError("test")),
        ),
        min_size=1,
        max_size=5,
    ),
)
def test_make_json_safe_converts_non_serializable(event_dict):
    """make_json_safe should convert non-serializable values to JSON-safe ones."""
    result = make_json_safe(None, "", event_dict.copy())
    # Result should be JSON serializable
    json_str = json.dumps(result)
    assert json_str is not None
    # Verify round-trip
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


@given(
    nested=st.one_of(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.lists(
                st.one_of(
                    st.just(datetime(2026, 4, 14, tzinfo=UTC)),
                    st.just(date(2026, 4, 14)),
                    st.integers(),
                ),
                min_size=0,
                max_size=5,
            ),
            min_size=1,
            max_size=3,
        ),
        st.lists(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=10),
                values=st.one_of(
                    st.just(datetime(2026, 4, 14, tzinfo=UTC)),
                    st.text(max_size=50),
                ),
                min_size=1,
                max_size=3,
            ),
            min_size=1,
            max_size=3,
        ),
    ),
)
def test_make_json_safe_handles_deeply_nested(nested):
    """make_json_safe should handle deeply nested structures with mixed types."""
    event_dict = {"data": nested}
    result = make_json_safe(None, "", event_dict)
    json_str = json.dumps(result)
    assert json_str is not None
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


@given(
    value=st.one_of(
        st.just(datetime.now(tz=UTC)),
        st.just(datetime.now(tz=UTC).date()),
        st.just(set(range(5))),
        st.just(Exception("test_error")),
        st.just(Level.INFO),
    ),
)
def test_json_default_always_returns_serializable(value):
    """_json_default should always return JSON-serializable values."""
    result = _json_default(value)
    # Should not raise
    json.dumps({"value": result})


def test_make_json_safe_with_empty_dict():
    """make_json_safe should handle empty event dicts."""
    result = make_json_safe(None, "", {})
    assert result == {}
    assert json.dumps(result) == "{}"


@given(
    key=st.text(min_size=1, max_size=50),
    value=st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(max_size=100),
    ),
)
def test_make_json_safe_identity_for_primitives(key, value):
    """make_json_safe should not modify primitive JSON-safe values."""
    event_dict = {key: value}
    result = make_json_safe(None, "", event_dict.copy())
    assert result[key] == value
