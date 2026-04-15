import asyncio
import json
import logging
from datetime import UTC, date, datetime

import pytest
import structlog
from hypothesis import given
from hypothesis import strategies as st

from pylogkit import __version__
from pylogkit.main import (
    InitLoggers,
    InvalidLoggerNameError,
    Level,
    LoggerError,
    LoggerNotFoundError,
    LoggerReg,
    SetupLogger,
    _json_default,
    add_caller_details,
    bind,
    clear_context,
    context_scope,
    get_context,
    get_logger,
    make_json_safe,
)


@pytest.fixture(autouse=True)
def _reset_setup():
    """Reset SetupLogger state before each test to avoid flaky tests."""
    SetupLogger.reset()
    clear_context()
    yield
    SetupLogger.reset()
    clear_context()


def test_logger_error_inheritance():
    assert issubclass(LoggerNotFoundError, LoggerError)


@given(level=st.sampled_from(list(LoggerReg.Level)))
def test_logger_reg_levels(level):
    reg = LoggerReg(name="TEST", level=level)
    assert reg.name == "TEST"
    assert reg.level == level


def test_setup_logger_str_and_renderer(monkeypatch):
    reg = [LoggerReg(name="TEST", level=LoggerReg.Level.DEBUG)]

    s1 = SetupLogger(name_registration=reg, developer_mode=True)
    assert "registered" in str(s1)
    assert s1._renderer == s1.CONSOLE_HANDLER

    monkeypatch.setenv("MODE_DEV", "1")
    s2 = SetupLogger(name_registration=reg, developer_mode=False)
    assert s2._renderer == s2.CONSOLE_HANDLER

    monkeypatch.delenv("MODE_DEV", raising=False)
    s3 = SetupLogger(name_registration=reg, developer_mode=False)
    assert s3._renderer == s3.JSON_HANDLER


def test_timestamper_returns_callable():
    reg = [LoggerReg(name="TEST")]
    s = SetupLogger(name_registration=reg, developer_mode=True)
    ts = s._timestamper()
    assert callable(ts)


def test_preprocessors_extended_and_basic():
    reg = [LoggerReg(name="TEST")]
    s = SetupLogger(name_registration=reg, developer_mode=True)
    base = s._pre()
    ext = s._pre(extended=True)

    assert len(ext) > len(base)
    assert any(getattr(call, "__name__", "") == "merge_contextvars" for call in ext)


def test_init_loggers_no_loggers_defined():
    class Empty(InitLoggers):
        pass

    with pytest.raises(LoggerError):
        Empty()


def test_init_loggers_logger_not_found():
    class MyLoggers(InitLoggers):
        app = LoggerReg(name="APP")

    loggers = MyLoggers(developer_mode=True)
    with pytest.raises(LoggerNotFoundError):
        _ = loggers.not_exist


def test_logger_reg_empty_name_raises():
    with pytest.raises(InvalidLoggerNameError, match="must not be empty"):
        LoggerReg(name="")

    with pytest.raises(InvalidLoggerNameError, match="must not be empty"):
        LoggerReg(name="   ")


def test_logger_reg_strips_name():
    reg = LoggerReg(name="  APP  ")
    assert reg.name == "APP"


def test_add_caller_details():
    event_dict = {
        "filename": "test.py",
        "func_name": "test_func",
        "lineno": 42,
        "event": "test event",
    }
    result = add_caller_details(None, "", event_dict)
    assert result["logger"] == "test.py:test_func:42"
    assert "filename" not in result
    assert "func_name" not in result
    assert "lineno" not in result
    assert result["event"] == "test event"


def test_setup_logger_with_empty_list_uses_default():
    s = SetupLogger(name_registration=[], developer_mode=True)
    assert any(reg.name == "__root__" for reg in s._regs)
    assert len(s._regs) == 1  # only "__root__"


def test_bind_and_get_context():
    bind(test_key="test_value")
    ctx = get_context()
    assert ctx.get("test_key") == "test_value"
    clear_context()
    assert get_context() == {}


def test_context_scope():
    with context_scope(req_id="123"):
        assert get_context().get("req_id") == "123"
    assert get_context() == {}


def test_context_scope_cleans_on_exception():
    try:
        with context_scope(temp="value"):
            raise ValueError("test")
    except ValueError:
        pass
    assert get_context() == {}


def test_init_loggers_get_logger_method():
    class MyLoggers(InitLoggers):
        app = LoggerReg(name="APP_GET")

    loggers = MyLoggers(developer_mode=True)
    logger = loggers.get_logger("APP_GET")
    assert logger is not None
    assert loggers.get_logger("APP_GET") is loggers.get_logger("APP_GET")


def test_init_loggers_logger_names_method():
    class MyLoggers(InitLoggers):
        first = LoggerReg(name="FIRST")
        second = LoggerReg(name="SECOND")

    loggers = MyLoggers(developer_mode=True)
    names = loggers.logger_names()
    assert "FIRST" in names
    assert "SECOND" in names
    assert len(names) == 2


def test_init_loggers_get_logger_not_found():
    class MyLoggers(InitLoggers):
        app = LoggerReg(name="APP_MISS")

    loggers = MyLoggers(developer_mode=True)
    with pytest.raises(LoggerNotFoundError):
        loggers.get_logger("NONEXISTENT")


def test_init_loggers_getattr_private_underscore():
    """Test that accessing private attrs raises AttributeError during init."""

    class MyLoggers(InitLoggers):
        app = LoggerReg(name="APP_PRIV")

    loggers = MyLoggers(developer_mode=True)
    with pytest.raises(AttributeError):
        _ = loggers._nonexistent_private


def test_init_loggers_getattr_logger_not_found():
    """Test that __getattr__ raises LoggerNotFoundError for unknown names."""

    class MyLoggers(InitLoggers):
        app = LoggerReg(name="APP_NOTFOUND")

    loggers = MyLoggers(developer_mode=True)
    with pytest.raises(LoggerNotFoundError, match="not found"):
        _ = loggers.nonexistent_attr


def test_get_logger_returns_logger_instance():
    """Test that get_logger returns a usable logger."""
    logger = get_logger("test_quick", level=LoggerReg.Level.INFO, developer_mode=True)
    assert logger is not None
    # Should be able to call log methods without raising
    logger.info("test message", key="value")


def test_get_logger_uses_reused_setup():
    """Test that multiple get_logger calls don't reconfigure structlog."""
    SetupLogger.reset()
    logger1 = get_logger("test_reuse1", developer_mode=True)
    logger2 = get_logger("test_reuse2", developer_mode=True)
    # Both should be usable
    assert logger1 is not None
    assert logger2 is not None


def test_setup_logger_reset_method():
    """Test that SetupLogger.reset() allows re-configuration."""
    SetupLogger(name_registration=[], developer_mode=True)
    # After first init, _configured should be True
    # Reset should allow new init
    SetupLogger.reset()
    s2 = SetupLogger(name_registration=[], developer_mode=True)
    assert s2 is not None


def test_get_logger_with_all_levels():
    """Test get_logger() works with every log level."""
    SetupLogger.reset()
    for level in LoggerReg.Level:
        logger = get_logger(f"level_{level.value}", level=level, developer_mode=True)
        assert logger is not None
        # Each logger should be usable at its level
        getattr(logger, level.value.lower())(f"message at {level.value}")
    SetupLogger.reset()


def test_get_logger_default_level_is_debug():
    """Test that get_logger() defaults to DEBUG level."""
    SetupLogger.reset()
    logger = get_logger("default_level_test", developer_mode=True)
    # Should be able to log at DEBUG level
    logger.debug("debug message")
    SetupLogger.reset()


def test_get_logger_developer_mode_json():
    """Test get_logger() with developer_mode=False uses JSON renderer."""
    SetupLogger.reset()
    logger = get_logger("json_test", developer_mode=False)
    logger.info("json test message")
    SetupLogger.reset()


def test_unicode_symbols_in_json_mode():
    """Test that Unicode symbols are properly handled in JSON mode."""
    SetupLogger.reset()
    logger = get_logger("unicode_test", developer_mode=False)
    logger.info("Привет мир", data="тестовые данные", emoji="🚀")
    SetupLogger.reset()


def test_context_scope_with_multiple_kwargs():
    """Test that context_scope handles multiple kwargs."""
    with context_scope(user_id=123, request_id="abc", action="test"):
        ctx = get_context()
        assert ctx["user_id"] == 123
        assert ctx["request_id"] == "abc"
        assert ctx["action"] == "test"
    assert get_context() == {}


def test_bind_overwrites_previous_value():
    """Test that bind() overwrites previous context values."""
    bind(key="first")
    assert get_context()["key"] == "first"
    bind(key="second")
    assert get_context()["key"] == "second"
    clear_context()


def test_context_scope_restores_previous_context():
    """Test that context_scope restores the previous context on exit."""
    bind(persistent="value")
    with context_scope(temp="temp_value"):
        ctx = get_context()
        assert ctx["temp"] == "temp_value"
        assert ctx["persistent"] == "value"
    # Previous context should be restored, temp removed
    assert get_context() == {"persistent": "value"}
    clear_context()


def test_add_caller_details_with_missing_keys():
    """Test add_caller_details handles missing keys gracefully."""
    event_dict = {"event": "no caller info"}
    result = add_caller_details(None, "", event_dict)
    assert result["logger"] == "?:?:0"
    assert result["event"] == "no caller info"


def test_add_caller_details_with_partial_keys():
    """Test add_caller_details with only some caller keys present."""
    event_dict = {"filename": "app.py", "event": "partial"}
    result = add_caller_details(None, "", event_dict)
    assert result["logger"] == "app.py:?:0"
    assert "filename" not in result


def test_logger_reg_propagate_flag():
    """Test that LoggerReg propagate flag works correctly."""
    reg = LoggerReg(name="PROP_TEST", propagate=True)
    assert reg.propagate is True

    reg_no = LoggerReg(name="NO_PROP", propagate=False)
    assert reg_no.propagate is False


def test_setup_logger_str_representation():
    """Test SetupLogger.__str__ output format."""
    SetupLogger.reset()
    regs = [LoggerReg(name="A"), LoggerReg(name="B")]
    s = SetupLogger(name_registration=regs, developer_mode=True)
    result = str(s)
    assert "SetupLogger" in result
    assert "dev:True" in result
    assert "registered:" in result
    SetupLogger.reset()


def test_init_loggers_multiple_loggers_with_levels():
    """Test InitLoggers with multiple loggers at different levels."""
    SetupLogger.reset()

    class MultiLoggers(InitLoggers):
        debug = LoggerReg(name="ML_DEBUG", level=LoggerReg.Level.DEBUG)
        info = LoggerReg(name="ML_INFO", level=LoggerReg.Level.INFO)
        error = LoggerReg(name="ML_ERROR", level=LoggerReg.Level.ERROR)

    loggers = MultiLoggers(developer_mode=True)
    names = loggers.logger_names()
    assert "ML_DEBUG" in names
    assert "ML_INFO" in names
    assert "ML_ERROR" in names
    assert len(names) == 3

    # All loggers should be accessible
    assert loggers.get_logger("ML_DEBUG") is not None
    assert loggers.get_logger("ML_INFO") is not None
    assert loggers.get_logger("ML_ERROR") is not None

    SetupLogger.reset()


def test_get_logger_with_special_characters_in_name():
    """Test get_logger() with special characters in name."""
    SetupLogger.reset()
    logger = get_logger("app.module.sub", developer_mode=True)
    assert logger is not None
    logger.debug("test with dotted name")
    SetupLogger.reset()


def test_setup_logger_with_log_file(tmp_path):
    """Test SetupLogger with file handler."""
    log_file = tmp_path / "test.log"
    SetupLogger.reset()
    regs = [LoggerReg(name="FILE_TEST")]
    SetupLogger(name_registration=regs, developer_mode=False, log_file=str(log_file))
    logger = structlog.get_logger("FILE_TEST")
    logger.info("test message", key="value")
    assert log_file.exists()
    content = log_file.read_text()
    assert "test message" in content
    SetupLogger.reset()


def test_setup_logger_with_rotating_file(tmp_path):
    """Test SetupLogger with rotating file handler."""
    log_file = tmp_path / "rotating.log"
    SetupLogger.reset()
    regs = [LoggerReg(name="ROTATING_TEST")]
    SetupLogger(
        name_registration=regs,
        developer_mode=False,
        log_file=str(log_file),
        max_bytes=1000,
        backup_count=2,
    )
    logger = structlog.get_logger("ROTATING_TEST")
    logger.info("rotating test message")
    assert log_file.exists()
    content = log_file.read_text()
    assert "rotating test message" in content
    SetupLogger.reset()


def test_get_logger_with_log_file(tmp_path):
    """Test get_logger() with file output."""
    log_file = tmp_path / "quick.log"
    SetupLogger.reset()
    logger = get_logger("quick_file_test", developer_mode=False, log_file=str(log_file))
    logger.info("quick file message", data="test")
    # Flush all handlers to ensure data is written
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.flush()
    assert log_file.exists()
    content = log_file.read_text()
    assert "quick file message" in content
    SetupLogger.reset()


def test_init_loggers_with_log_file(tmp_path):
    """Test InitLoggers with file output."""
    log_file = tmp_path / "app.log"
    SetupLogger.reset()

    class FileLoggers(InitLoggers):
        app = LoggerReg(name="APP_FILE")

    loggers = FileLoggers(developer_mode=False, log_file=str(log_file))
    logger = loggers.get_logger("APP_FILE")
    logger.info("app file message", version="1.0")
    assert log_file.exists()
    content = log_file.read_text()
    assert "app file message" in content
    SetupLogger.reset()


def test_file_handler_uses_json_format(tmp_path):
    """Test that file handler outputs JSON format."""
    log_file = tmp_path / "json_file.log"
    SetupLogger.reset()
    regs = [LoggerReg(name="JSON_FILE_TEST")]
    SetupLogger(name_registration=regs, developer_mode=False, log_file=str(log_file))
    logger = structlog.get_logger("JSON_FILE_TEST")
    logger.info("json file test", status=200)
    content = log_file.read_text().strip()
    data = json.loads(content)
    assert "timestamp" in data
    assert data.get("status") == 200
    SetupLogger.reset()


def test_renderer_returns_file_handler_when_log_file_set():
    """Test that _renderer returns FILE_HANDLER when log_file is set."""
    SetupLogger.reset()
    regs = [LoggerReg(name="RENDERER_TEST")]
    s = SetupLogger(name_registration=regs, developer_mode=True, log_file="test.log")
    assert s._renderer == s.FILE_HANDLER
    SetupLogger.reset()


def test_renderer_handles_isatty_error(monkeypatch):
    """Test that _renderer handles isatty() raising OSError (frozen apps)."""

    def raise_os_error():
        raise OSError("cannot do this on frozen application")

    monkeypatch.setattr("sys.stderr.isatty", raise_os_error)
    SetupLogger.reset()
    regs = [LoggerReg(name="ISATTY_TEST")]
    s = SetupLogger(name_registration=regs, developer_mode=False)
    # Should fall back to JSON handler when isatty fails
    assert s._renderer == s.JSON_HANDLER
    SetupLogger.reset()


def test_renderer_handles_isatty_attribute_error(monkeypatch):
    """Test that _renderer handles isatty() raising AttributeError."""

    def raise_attribute_error():
        raise AttributeError("no isatty")

    monkeypatch.setattr("sys.stderr.isatty", raise_attribute_error)
    SetupLogger.reset()
    regs = [LoggerReg(name="ISATTY_ATTR_TEST")]
    s = SetupLogger(name_registration=regs, developer_mode=False)
    # Should fall back to JSON handler when isatty fails
    assert s._renderer == s.JSON_HANDLER
    SetupLogger.reset()


def test_get_handler_config_returns_file_handler(tmp_path):
    """Test _get_handler_config includes file handler when log_file is set."""
    log_file = tmp_path / "config.log"
    SetupLogger.reset()
    regs = [LoggerReg(name="CONFIG_TEST")]
    s = SetupLogger(name_registration=regs, developer_mode=False, log_file=str(log_file))
    config = s._get_handler_config()
    assert s.FILE_HANDLER in config
    assert config[s.FILE_HANDLER]["filename"] == str(log_file)
    SetupLogger.reset()


def test_get_handler_config_rotating(tmp_path):
    """Test _get_handler_config creates rotating handler when max_bytes > 0."""
    log_file = tmp_path / "rotating_config.log"
    SetupLogger.reset()
    regs = [LoggerReg(name="ROT_CONFIG_TEST")]
    s = SetupLogger(
        name_registration=regs,
        developer_mode=False,
        log_file=str(log_file),
        max_bytes=5000,
        backup_count=3,
    )
    config = s._get_handler_config()
    assert s.FILE_HANDLER in config
    assert config[s.FILE_HANDLER]["class"] == "logging.handlers.RotatingFileHandler"
    assert config[s.FILE_HANDLER]["maxBytes"] == 5000
    assert config[s.FILE_HANDLER]["backupCount"] == 3
    SetupLogger.reset()


def test_get_handler_config_regular_file(tmp_path):
    """Test _get_handler_config creates regular file handler when max_bytes = 0."""
    log_file = tmp_path / "regular.log"
    SetupLogger.reset()
    regs = [LoggerReg(name="REG_FILE_TEST")]
    s = SetupLogger(name_registration=regs, developer_mode=False, log_file=str(log_file))
    config = s._get_handler_config()
    assert s.FILE_HANDLER in config
    assert config[s.FILE_HANDLER]["class"] == "logging.FileHandler"
    assert "maxBytes" not in config[s.FILE_HANDLER]
    SetupLogger.reset()


def test_setup_logger_async_mode():
    """Test SetupLogger with async mode enabled."""
    SetupLogger.reset()
    regs = [LoggerReg(name="ASYNC_TEST")]
    s = SetupLogger(name_registration=regs, developer_mode=True, async_mode=True)
    assert s._async_mode is True
    SetupLogger.reset()


def test_setup_logger_async_mode_default_false():
    """Test SetupLogger async_mode defaults to False."""
    SetupLogger.reset()
    regs = [LoggerReg(name="ASYNC_DEFAULT")]
    s = SetupLogger(name_registration=regs, developer_mode=True)
    assert s._async_mode is False
    SetupLogger.reset()


def test_get_logger_async_mode_parameter():
    """Test get_logger() accepts async_mode parameter."""
    SetupLogger.reset()

    async def check_async():
        logger = get_logger("async_quick_test", async_mode=True)
        assert logger is not None
        # In async mode, regular methods should be awaitable
        await logger.info("test async mode")
        SetupLogger.reset()

    asyncio.run(check_async())


@pytest.mark.asyncio
async def test_async_logging_basic():
    """Test basic async logging functionality."""
    SetupLogger.reset()
    logger = get_logger("async_basic", developer_mode=True, async_mode=True)
    # Should not raise - async methods should be callable
    await logger.info("async test message", key="value")
    SetupLogger.reset()


@pytest.mark.asyncio
async def test_async_logging_all_levels():
    """Test all async log levels."""
    SetupLogger.reset()
    logger = get_logger("async_levels", developer_mode=True, async_mode=True)
    await logger.debug("debug message")
    await logger.info("info message")
    await logger.warning("warning message")
    await logger.error("error message")
    SetupLogger.reset()


@pytest.mark.asyncio
async def test_async_logging_with_structured_data():
    """Test async logging with structured data."""
    SetupLogger.reset()
    logger = get_logger("async_structured", developer_mode=True, async_mode=True)
    await logger.info("request processed", status=200, path="/api/test", method="GET")
    SetupLogger.reset()


def test_init_loggers_async_mode():
    """Test InitLoggers with async_mode enabled."""
    SetupLogger.reset()

    class AsyncLoggers(InitLoggers):
        app = LoggerReg(name="ASYNC_APP")

    async def check_async():
        loggers = AsyncLoggers(developer_mode=True, async_mode=True)
        logger = loggers.get_logger("ASYNC_APP")
        # In async mode, regular methods should be awaitable
        await logger.info("test async init")
        SetupLogger.reset()

    asyncio.run(check_async())


@pytest.mark.asyncio
async def test_init_loggers_async_logging():
    """Test actual async logging with InitLoggers."""
    SetupLogger.reset()

    class AsyncLoggers(InitLoggers):
        app = LoggerReg(name="ASYNC_APP_LOG")

    loggers = AsyncLoggers(developer_mode=True, async_mode=True)
    logger = loggers.get_logger("ASYNC_APP_LOG")
    await logger.info("async app message", version="1.0")
    SetupLogger.reset()


def test_async_mode_with_file_logging(tmp_path):
    """Test async mode combined with file logging."""
    log_file = tmp_path / "async_file.log"
    SetupLogger.reset()

    async def check_async_file():
        logger = get_logger(
            "async_file_test",
            developer_mode=False,
            async_mode=True,
            log_file=str(log_file),
        )
        await logger.info("async file test message")
        # Flush to ensure data is written
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            handler.flush()
        assert log_file.exists()
        SetupLogger.reset()

    asyncio.run(check_async_file())


# --- Tests for _json_default and make_json_safe ---


def test_json_default_datetime():
    """Test _json_default handles datetime."""
    dt = datetime(2026, 4, 12, 10, 30, 0, tzinfo=UTC)
    result = _json_default(dt)
    assert result == "2026-04-12T10:30:00+00:00"


def test_json_default_date():
    """Test _json_default handles date."""
    d = date(2026, 4, 12)
    result = _json_default(d)
    assert result == "2026-04-12"


def test_json_default_set():
    """Test _json_default handles set."""
    s = {1, 2, 3}
    result = _json_default(s)
    assert isinstance(result, list)
    assert set(result) == {1, 2, 3}


def test_json_default_exception():
    """Test _json_default handles Exception."""
    exc = ValueError("test error")
    result = _json_default(exc)
    assert result == "ValueError: test error"


def test_json_default_enum():
    """Test _json_default handles Enum."""
    result = _json_default(LoggerReg.Level.INFO)
    assert result == "INFO"


def test_json_default_bytes():
    """Test _json_default handles bytes."""
    result = _json_default(b"hello")
    assert result == "hello"


def test_json_default_bytes_invalid_utf8():
    """Test _json_default handles invalid UTF-8 bytes."""
    result = _json_default(b"\xff\xfe")
    assert isinstance(result, str)


def test_json_default_object_with_dict():
    """Test _json_default handles objects with __dict__."""

    class CustomObj:
        def __init__(self):
            self.foo = "bar"

    obj = CustomObj()
    result = _json_default(obj)
    assert result == {"foo": "bar"}


def test_json_default_fallback_to_repr():
    """Test _json_default falls back to repr()."""

    class NoDictObj:
        __slots__ = ()

    obj = NoDictObj()
    result = _json_default(obj)
    assert repr(obj) in result


def test_make_json_safe_converts_datetime():
    """Test make_json_safe converts datetime values."""
    dt = datetime(2026, 4, 12, 10, 30, 0, tzinfo=UTC)
    event_dict = {"event": "test", "timestamp": dt}
    result = make_json_safe(None, "", event_dict)
    assert result["timestamp"] == "2026-04-12T10:30:00+00:00"
    assert result["event"] == "test"


def test_make_json_safe_converts_set():
    """Test make_json_safe converts set values."""
    event_dict = {"event": "test", "tags": {"a", "b", "c"}}
    result = make_json_safe(None, "", event_dict)
    assert isinstance(result["tags"], list)
    assert set(result["tags"]) == {"a", "b", "c"}


def test_make_json_safe_preserves_json_safe_values():
    """Test make_json_safe preserves values that are already JSON serializable."""
    event_dict = {"event": "test", "status": 200, "path": "/api"}
    result = make_json_safe(None, "", event_dict)
    assert result["status"] == 200
    assert result["path"] == "/api"


def test_make_json_safe_handles_exception_in_value():
    """Test make_json_safe handles Exception values."""
    event_dict = {"event": "error occurred", "error": ValueError("bad value")}
    result = make_json_safe(None, "", event_dict)
    assert result["error"] == "ValueError: bad value"


# --- Tests for add_logger and all() ---


def test_add_logger_dynamically(tmp_path):
    """Test adding a logger dynamically."""
    log_file = tmp_path / "add_logger.log"
    SetupLogger.reset()

    class DynamicLoggers(InitLoggers):
        app = LoggerReg(name="DYN_APP")

    loggers = DynamicLoggers(developer_mode=False, log_file=str(log_file))
    new_logger = loggers.add_logger("DYN_NEW", level=LoggerReg.Level.WARNING)
    assert new_logger is not None

    # Dynamic logger inherits root handlers, so it logs to stderr by default
    # Use the existing app logger's handler by propagating
    new_logger.warning("dynamic logger message")
    for handler in logging.getLogger().handlers:
        handler.flush()

    # The message goes to stderr (root handler), verify logger is usable
    assert "DYN_NEW" in loggers.logger_names()
    SetupLogger.reset()


def test_add_logger_returns_existing_if_present(tmp_path):
    """Test add_logger returns the same logger if already registered."""
    log_file = tmp_path / "add_existing.log"
    SetupLogger.reset()

    class ExistingLoggers(InitLoggers):
        app = LoggerReg(name="EXIST_APP")

    loggers = ExistingLoggers(developer_mode=False, log_file=str(log_file))
    logger1 = loggers.add_logger("EXIST_APP")
    logger2 = loggers.add_logger("EXIST_APP")
    assert logger1 is logger2
    SetupLogger.reset()


def test_all_returns_all_loggers(tmp_path):
    """Test all() returns dict of all registered loggers."""
    log_file = tmp_path / "all_test.log"
    SetupLogger.reset()

    class AllLoggers(InitLoggers):
        first = LoggerReg(name="ALL_FIRST")
        second = LoggerReg(name="ALL_SECOND")
        third = LoggerReg(name="ALL_THIRD")

    loggers = AllLoggers(developer_mode=False, log_file=str(log_file))
    all_loggers = loggers.all()
    assert "ALL_FIRST" in all_loggers
    assert "ALL_SECOND" in all_loggers
    assert "ALL_THIRD" in all_loggers
    assert len(all_loggers) == 3
    SetupLogger.reset()


def test_all_returns_copy_not_reference(tmp_path):
    """Test all() returns a copy, not the internal dict."""
    log_file = tmp_path / "all_copy.log"
    SetupLogger.reset()

    class CopyLoggers(InitLoggers):
        app = LoggerReg(name="COPY_APP")

    loggers = CopyLoggers(developer_mode=False, log_file=str(log_file))
    all1 = loggers.all()
    all2 = loggers.all()
    assert all1 is not all2
    assert all1 == all2
    SetupLogger.reset()


def test_add_logger_with_propagate(tmp_path):
    """Test add_logger with propagate=True."""
    log_file = tmp_path / "propagate.log"
    SetupLogger.reset()

    class PropLoggers(InitLoggers):
        app = LoggerReg(name="PROP_APP")

    loggers = PropLoggers(developer_mode=False, log_file=str(log_file))
    logger = loggers.add_logger("PROP_NEW", propagate=True, level=LoggerReg.Level.INFO)
    assert logger is not None
    logger.info("propagate test")
    for handler in logging.getLogger().handlers:
        handler.flush()

    content = log_file.read_text()
    assert "propagate test" in content
    SetupLogger.reset()


def test_make_json_safe_with_nested_structures(tmp_path):
    """Test make_json_safe handles nested structures with non-serializable values."""
    log_file = tmp_path / "nested_json.log"
    SetupLogger.reset()

    class NestedLoggers(InitLoggers):
        app = LoggerReg(name="NEST_APP")

    loggers = NestedLoggers(developer_mode=False, log_file=str(log_file))
    logger = loggers.get_logger("NEST_APP")
    dt = datetime(2026, 4, 12, 10, 30, 0, tzinfo=UTC)
    tags = {"tag1", "tag2"}
    logger.info("nested event", created_at=dt, tags=tags)
    for handler in logging.getLogger().handlers:
        handler.flush()

    content = log_file.read_text().strip()
    data = json.loads(content)
    assert data["created_at"] == "2026-04-12T10:30:00+00:00"
    assert isinstance(data["tags"], list)
    SetupLogger.reset()


def test_make_json_safe_nested_dict():
    """Test make_json_safe handles nested dicts."""
    dt = datetime(2026, 4, 12, 10, 30, 0, tzinfo=UTC)
    event_dict = {"event": "test", "meta": {"created": dt, "count": 5}}
    result = make_json_safe(None, "", event_dict)
    assert result["meta"]["created"] == "2026-04-12T10:30:00+00:00"
    assert result["meta"]["count"] == 5


def test_make_json_safe_nested_list():
    """Test make_json_safe handles nested lists."""
    dt = datetime(2026, 4, 12, 10, 30, 0, tzinfo=UTC)
    event_dict = {"event": "test", "items": [dt, {1, 2}, "ok"]}
    result = make_json_safe(None, "", event_dict)
    assert result["items"][0] == "2026-04-12T10:30:00+00:00"
    assert set(result["items"][1]) == {1, 2}
    assert result["items"][2] == "ok"


def test_make_json_safe_deeply_nested():
    """Test make_json_safe handles deeply nested structures."""
    dt = datetime(2026, 4, 12, 10, 30, 0, tzinfo=UTC)
    event_dict = {"event": "test", "data": {"a": {"b": [dt, {"c": {1, 2}}]}}}
    result = make_json_safe(None, "", event_dict)
    assert result["data"]["a"]["b"][0] == "2026-04-12T10:30:00+00:00"
    assert set(result["data"]["a"]["b"][1]["c"]) == {1, 2}


def test_make_json_safe_tuple():
    """Test make_json_safe handles tuples."""
    dt = datetime(2026, 4, 12, 10, 30, 0, tzinfo=UTC)
    event_dict = {"event": "test", "pair": (dt, "value")}
    result = make_json_safe(None, "", event_dict)
    assert result["pair"] == ["2026-04-12T10:30:00+00:00", "value"]


# --- Tests for remove_logger and logger_level ---


def test_remove_logger_dynamically():
    """Test removing a dynamically added logger."""
    SetupLogger.reset()

    class RemoveLoggers(InitLoggers):
        app = LoggerReg(name="RM_APP")

    loggers = RemoveLoggers(developer_mode=True)
    loggers.add_logger("RM_TEMP", level=LoggerReg.Level.DEBUG)
    assert "RM_TEMP" in loggers.logger_names()

    loggers.remove_logger("RM_TEMP")
    assert "RM_TEMP" not in loggers.logger_names()
    assert "RM_APP" in loggers.logger_names()
    SetupLogger.reset()


def test_remove_logger_not_found():
    """Test remove_logger raises for nonexistent logger."""
    SetupLogger.reset()

    class RemoveLoggers(InitLoggers):
        app = LoggerReg(name="RM_APP")

    loggers = RemoveLoggers(developer_mode=True)
    with pytest.raises(LoggerNotFoundError):
        loggers.remove_logger("NONEXISTENT")
    SetupLogger.reset()


def test_logger_level_returns_level():
    """Test logger_level returns correct level."""
    SetupLogger.reset()

    class LevelLoggers(InitLoggers):
        debug = LoggerReg(name="LV_DEBUG", level=LoggerReg.Level.DEBUG)
        info = LoggerReg(name="LV_INFO", level=LoggerReg.Level.INFO)
        error = LoggerReg(name="LV_ERROR", level=LoggerReg.Level.ERROR)

    loggers = LevelLoggers(developer_mode=True)
    assert loggers.logger_level("LV_DEBUG") == LoggerReg.Level.DEBUG
    assert loggers.logger_level("LV_INFO") == LoggerReg.Level.INFO
    assert loggers.logger_level("LV_ERROR") == LoggerReg.Level.ERROR
    SetupLogger.reset()


def test_logger_level_not_found():
    """Test logger_level raises for nonexistent logger."""
    SetupLogger.reset()

    class LevelLoggers(InitLoggers):
        app = LoggerReg(name="LV_APP")

    loggers = LevelLoggers(developer_mode=True)
    with pytest.raises(LoggerNotFoundError):
        loggers.logger_level("NONEXISTENT")
    SetupLogger.reset()


def test_remove_logger_then_add_again():
    """Test that a logger can be removed and added again."""
    SetupLogger.reset()

    class ReAddLoggers(InitLoggers):
        app = LoggerReg(name="RA_APP")

    loggers = ReAddLoggers(developer_mode=True)
    loggers.add_logger("RA_TEMP")
    assert "RA_TEMP" in loggers.logger_names()

    loggers.remove_logger("RA_TEMP")
    assert "RA_TEMP" not in loggers.logger_names()

    loggers.add_logger("RA_TEMP", level=LoggerReg.Level.WARNING)
    assert "RA_TEMP" in loggers.logger_names()
    assert loggers.logger_level("RA_TEMP") == LoggerReg.Level.WARNING
    SetupLogger.reset()


# --- Tests for reset handler cleanup and __version__ ---


def test_setup_logger_reset_clears_handlers():
    """Test that SetupLogger.reset() removes all handlers."""
    SetupLogger.reset()
    get_logger("handler_test", developer_mode=True)
    root = logging.getLogger()
    assert len(root.handlers) > 0

    SetupLogger.reset()
    assert len(root.handlers) == 0


def test_setup_logger_reset_clears_named_loggers():
    """Test that reset cleans up named loggers."""
    SetupLogger.reset()

    class ResetLoggers(InitLoggers):
        app = LoggerReg(name="RESET_APP")

    ResetLoggers(developer_mode=True)
    named_logger = logging.getLogger("RESET_APP")
    assert len(named_logger.handlers) > 0

    SetupLogger.reset()
    # After reset, the named logger should have no handlers
    named_logger = logging.getLogger("RESET_APP")
    assert len(named_logger.handlers) == 0


def test_version_exists():
    """Test that __version__ is defined."""
    assert __version__ == "0.4.0"


def test_version_is_string():
    """Test that __version__ is a string."""
    assert isinstance(__version__, str)


def test_add_logger_updates_setup_regs():
    """Test that add_logger() appends to _setup._regs for consistency."""
    SetupLogger.reset()

    class SyncLoggers(InitLoggers):
        app = LoggerReg(name="SYNC_APP")

    loggers = SyncLoggers(developer_mode=True)
    initial_count = len(loggers._setup._regs)
    loggers.add_logger("SYNC_NEW")
    assert len(loggers._setup._regs) == initial_count + 1
    SetupLogger.reset()


def test_level_class_exported():
    """Test that Level enum is properly exported."""
    assert Level.DEBUG == LoggerReg.Level.DEBUG
    assert Level.INFO == LoggerReg.Level.INFO
    assert Level.WARNING == LoggerReg.Level.WARNING
    assert Level.ERROR == LoggerReg.Level.ERROR
    assert Level.CRITICAL == LoggerReg.Level.CRITICAL


def test_get_logger_empty_name_raises():
    """Test that get_logger() validates empty name."""
    SetupLogger.reset()
    with pytest.raises(InvalidLoggerNameError, match="must not be empty"):
        get_logger("")
    with pytest.raises(InvalidLoggerNameError, match="must not be empty"):
        get_logger("   ")
    SetupLogger.reset()


def test_remove_logger_cleans_handlers():
    """Test that remove_logger() properly cleans up logging handlers."""
    SetupLogger.reset()

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="CLEAN_APP")

    loggers = TestLoggers(developer_mode=True)
    loggers.add_logger("temp_logger")

    # Add a real handler to the underlying logger to test cleanup
    named = logging.getLogger("temp_logger")
    test_handler = logging.StreamHandler()
    named.addHandler(test_handler)
    assert len(named.handlers) > 0

    loggers.remove_logger("temp_logger")

    # Verify logger is removed from internal state
    assert "temp_logger" not in loggers.logger_names()
    assert "temp_logger" not in loggers.all()

    # Verify underlying logging.Logger is cleaned
    assert len(named.handlers) == 0
    assert named.level == logging.NOTSET
    assert named.propagate is False
    SetupLogger.reset()


def test_remove_logger_updates_setup_regs():
    """Test that remove_logger() updates _setup._regs list."""
    SetupLogger.reset()

    class RegLoggers(InitLoggers):
        app = LoggerReg(name="REG_APP")

    loggers = RegLoggers(developer_mode=True)
    loggers.add_logger("remove_me")
    assert any(r.name == "remove_me" for r in loggers._setup._regs)

    loggers.remove_logger("remove_me")
    assert not any(r.name == "remove_me" for r in loggers._setup._regs)
    SetupLogger.reset()


def test_remove_logger_cleans_logger_dict():
    """Test that remove_logger() removes logger from logging.root.manager.loggerDict."""
    SetupLogger.reset()

    class CleanLoggers(InitLoggers):
        app = LoggerReg(name="CLEAN_BASE")

    loggers = CleanLoggers(developer_mode=True)
    loggers.add_logger("to_remove")
    assert "to_remove" in logging.root.manager.loggerDict

    loggers.remove_logger("to_remove")
    assert "to_remove" not in logging.root.manager.loggerDict
    SetupLogger.reset()


def test_setup_logger_force_reconfigures():
    """Test that force=True reconfigures even if already configured."""
    SetupLogger.reset()

    class FirstLoggers(InitLoggers):
        app = LoggerReg(name="FIRST", level=LoggerReg.Level.INFO)

    first = FirstLoggers(developer_mode=True)
    assert SetupLogger._configured

    # Second instance should not reconfigure by default
    class SecondLoggers(InitLoggers):
        db = LoggerReg(name="SECOND")

    second = SecondLoggers(developer_mode=True)
    assert len(first._setup._regs) == 1
    assert len(second._setup._regs) == 1

    # force=True should reconfigure
    third = SecondLoggers(developer_mode=True, force=True)
    assert third._setup._configured
    assert len(third._setup._regs) == 1
    SetupLogger.reset()


def test_get_logger_force_reconfigures():
    """Test that force=True in get_logger() resets configuration."""
    SetupLogger.reset()

    logger1 = get_logger("test1", level=Level.INFO)
    assert SetupLogger._configured

    logger2 = get_logger("test2", force=True)
    assert SetupLogger._configured
    assert logger1 is not None
    assert logger2 is not None
    SetupLogger.reset()


def test_add_logger_assigns_handlers():
    """Test that add_logger() configures the logger with proper level and propagation."""
    SetupLogger.reset()

    class BaseLoggers(InitLoggers):
        app = LoggerReg(name="BASE_APP")

    loggers = BaseLoggers(developer_mode=True)
    loggers.add_logger("dynamic_logger", level=Level.WARNING)

    # Verify the logger is configured
    dynamic = logging.getLogger("dynamic_logger")
    assert dynamic.level <= logging.WARNING or dynamic.propagate

    # Verify it works
    assert "dynamic_logger" in loggers.logger_names()
    SetupLogger.reset()


def test_custom_renderer():
    """Test that custom renderer is used when provided."""
    SetupLogger.reset()

    def my_renderer(event_dict: dict) -> str:
        return f"CUSTOM: {event_dict.get('event', '')}"

    class RenderLoggers(InitLoggers):
        app = LoggerReg(name="RENDER_APP")

    loggers = RenderLoggers(developer_mode=True, renderer=my_renderer)
    assert loggers._setup._custom_renderer is my_renderer
    SetupLogger.reset()


def test_get_logger_custom_renderer():
    """Test that get_logger() accepts custom renderer."""
    SetupLogger.reset()

    def my_renderer(event_dict: dict) -> str:
        return f"QUICK: {event_dict.get('event', '')}"

    logger = get_logger("quick_render", renderer=my_renderer)
    assert logger is not None
    SetupLogger.reset()


def test_save_and_load_config(tmp_path):
    """Test saving and loading configuration."""
    SetupLogger.reset()

    class ConfigLoggers(InitLoggers):
        app = LoggerReg(name="CFG_APP", level=LoggerReg.Level.WARNING)
        db = LoggerReg(name="CFG_DB", level=LoggerReg.Level.DEBUG, propagate=True)

    loggers = ConfigLoggers(developer_mode=True)
    config_file = tmp_path / "config.json"
    loggers.save_config(str(config_file))

    # Load and verify
    loaded = InitLoggers.load_config(str(config_file))
    assert "CFG_APP" in loaded["loggers"]
    assert loaded["loggers"]["CFG_APP"]["level"] == "WARNING"
    assert loaded["loggers"]["CFG_DB"]["level"] == "DEBUG"
    assert loaded["loggers"]["CFG_DB"]["propagate"] is True
    assert loaded["developer_mode"] is True
    assert loaded["log_file"] is None
    assert loaded["max_bytes"] == 0
    assert loaded["backup_count"] == 0
    SetupLogger.reset()


def test_from_config_creates_loggers(tmp_path):
    """Test creating InitLoggers from a saved config file."""
    SetupLogger.reset()

    class ConfigLoggers(InitLoggers):
        app = LoggerReg(name="FC_APP", level=LoggerReg.Level.WARNING)
        db = LoggerReg(name="FC_DB", level=LoggerReg.Level.DEBUG, propagate=True)

    loggers = ConfigLoggers(developer_mode=True, log_file=str(tmp_path / "fc.log"))
    config_file = tmp_path / "fc_config.json"
    loggers.save_config(str(config_file))
    SetupLogger.reset()

    restored = InitLoggers.from_config(str(config_file))
    assert "FC_APP" in restored.logger_names()
    assert "FC_DB" in restored.logger_names()
    assert restored.logger_level("FC_APP") == LoggerReg.Level.WARNING
    assert restored.logger_level("FC_DB") == LoggerReg.Level.DEBUG
    assert restored._setup._developer_mode is True
    SetupLogger.reset()
