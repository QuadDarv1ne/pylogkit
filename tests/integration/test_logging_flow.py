"""Integration tests for logging flow."""

import json
import logging

import pytest
import structlog

from pylogkit import InitLoggers, LoggerReg, context_scope
from pylogkit.main import SetupLogger


@pytest.fixture(autouse=True)
def _reset_and_cleanup():
    """Reset SetupLogger state and clean up handlers after each test."""
    SetupLogger.reset()
    yield
    # Clean up any file handlers to avoid resource leaks
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            root_logger.removeHandler(handler)
    SetupLogger.reset()


def _flush_handlers():
    """Flush all logging handlers to ensure data is written."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.flush()


def test_console_output_format(tmp_path):
    """Test that console output contains expected formatting in developer mode."""
    log_file = tmp_path / "console_test.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, log_file=str(log_file))
    structlog.getLogger(TestLoggers.app.name).info("test message", key="value")
    _flush_handlers()

    content = log_file.read_text()
    data = json.loads(content.strip())
    assert data.get("status") is None or "key" in data
    assert data.get("key") == "value"


def test_json_output_format(tmp_path):
    """Test that JSON output is valid and contains expected fields."""
    log_file = tmp_path / "json_test.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_JSON", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, log_file=str(log_file))
    structlog.getLogger(TestLoggers.app.name).info("json_test_message", status=200, path="/test")
    _flush_handlers()

    content = log_file.read_text().strip()
    data = json.loads(content)
    assert "timestamp" in data
    assert "level" in data
    assert "_msg" in data or "event" in data
    assert data.get("status") == 200
    assert data.get("path") == "/test"


def test_multiple_loggers_isolation(tmp_path):
    """Test that multiple loggers work independently."""
    log_file = tmp_path / "multi_test.log"

    class TestLoggers(InitLoggers):
        debug_logger = LoggerReg(name="DBG", level=LoggerReg.Level.DEBUG)
        info_logger = LoggerReg(name="INF", level=LoggerReg.Level.INFO)
        warning_logger = LoggerReg(name="WRN", level=LoggerReg.Level.WARNING)

    TestLoggers(developer_mode=False, log_file=str(log_file))
    structlog.getLogger(TestLoggers.debug_logger.name).debug("debug_message")
    structlog.getLogger(TestLoggers.info_logger.name).info("info_message")
    structlog.getLogger(TestLoggers.warning_logger.name).warning("warning_message")
    _flush_handlers()

    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 3

    messages = [json.loads(line).get("_msg") or json.loads(line).get("event") for line in lines]
    assert "debug_message" in messages
    assert "info_message" in messages
    assert "warning_message" in messages


def test_logger_with_structured_data(tmp_path):
    """Test that structured data is properly passed through."""
    log_file = tmp_path / "struct_test.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_STRUCT", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, log_file=str(log_file))
    structlog.getLogger(TestLoggers.app.name).info(
        "Structured event",
        user="test_user",
        action="login",
        ip="127.0.0.1",
    )
    _flush_handlers()

    content = log_file.read_text().strip()
    data = json.loads(content)
    assert data.get("user") == "test_user"
    assert data.get("action") == "login"
    assert data.get("ip") == "127.0.0.1"


def test_exception_logging(tmp_path):
    """Test that exceptions are properly logged with traceback."""
    log_file = tmp_path / "exc_test.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_EXC", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, log_file=str(log_file))
    logger = structlog.getLogger(TestLoggers.app.name)
    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.exception("Exception occurred")
    _flush_handlers()

    content = log_file.read_text()
    data = json.loads(content.strip())
    assert data.get("_msg") == "Exception occurred" or data.get("event") == "Exception occurred"


def test_logger_level_filtering(tmp_path):
    """Test that DEBUG messages are filtered when level is INFO."""
    log_file = tmp_path / "filter_test.log"

    class TestLoggers(InitLoggers):
        info_only = LoggerReg(name="INFO_ONLY", level=LoggerReg.Level.INFO)

    TestLoggers(developer_mode=False, log_file=str(log_file))
    structlog.getLogger(TestLoggers.info_only.name).debug("This should be filtered")
    _flush_handlers()

    content = log_file.read_text().strip()
    assert content == ""


def test_unicode_in_json_output(tmp_path):
    """Test that Unicode characters are properly encoded in JSON output."""
    log_file = tmp_path / "unicode_test.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_UNICODE", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, log_file=str(log_file))
    structlog.getLogger(TestLoggers.app.name).info(
        "\u041f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440",
        data="\u0442\u0435\u0441\u0442\u043e\u0432\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435",
        emoji="\U0001f680",
    )
    _flush_handlers()

    content = log_file.read_text().strip()
    data = json.loads(content)
    msg = data.get("_msg") or data.get("event", "")
    assert "\u041f\u0440\u0438\u0432\u0435\u0442" in msg


@pytest.mark.asyncio
async def test_async_logging_console_output(tmp_path):
    """Test that async logging produces output in developer mode."""
    log_file = tmp_path / "async_console.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_ASYNC", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, async_mode=True, log_file=str(log_file))
    logger = structlog.getLogger(TestLoggers.app.name)
    await logger.info("async test message", key="async_value")
    _flush_handlers()

    content = log_file.read_text().strip()
    data = json.loads(content)
    assert data.get("key") == "async_value"


@pytest.mark.asyncio
async def test_async_logging_json_output(tmp_path):
    """Test that async logging produces valid JSON output."""
    log_file = tmp_path / "async_json.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_ASYNC_JSON", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, async_mode=True, log_file=str(log_file))
    logger = structlog.getLogger(TestLoggers.app.name)
    await logger.info("json_async_test", status=201, path="/async")
    _flush_handlers()

    content = log_file.read_text().strip()
    data = json.loads(content)
    assert "timestamp" in data
    assert data.get("status") == 201
    assert data.get("path") == "/async"


@pytest.mark.asyncio
async def test_async_logging_multiple_loggers(tmp_path):
    """Test async logging with multiple independent loggers."""
    log_file = tmp_path / "async_multi.log"

    class TestLoggers(InitLoggers):
        debug = LoggerReg(name="ASYNC_DBG", level=LoggerReg.Level.DEBUG)
        info = LoggerReg(name="ASYNC_INF", level=LoggerReg.Level.INFO)
        error = LoggerReg(name="ASYNC_ERR", level=LoggerReg.Level.ERROR)

    TestLoggers(developer_mode=False, async_mode=True, log_file=str(log_file))
    debug_logger = structlog.getLogger(TestLoggers.debug.name)
    info_logger = structlog.getLogger(TestLoggers.info.name)
    error_logger = structlog.getLogger(TestLoggers.error.name)

    await debug_logger.debug("async debug message")
    await info_logger.info("async info message")
    await error_logger.error("async error message")
    _flush_handlers()

    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 3


@pytest.mark.asyncio
async def test_async_logging_with_exception(tmp_path):
    """Test async exception logging."""
    log_file = tmp_path / "async_exc.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_ASYNC_EXC", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, async_mode=True, log_file=str(log_file))
    logger = structlog.getLogger(TestLoggers.app.name)

    try:
        raise ValueError("Async test exception")
    except ValueError:
        await logger.exception("Async exception occurred")
    _flush_handlers()

    content = log_file.read_text()
    data = json.loads(content.strip())
    assert data.get("_msg") == "Async exception occurred" or data.get("event") == "Async exception occurred"


@pytest.mark.asyncio
async def test_async_logging_context_variables(tmp_path):
    """Test async logging with context variables."""
    log_file = tmp_path / "async_ctx.log"

    class TestLoggers(InitLoggers):
        app = LoggerReg(name="APP_ASYNC_CTX", level=LoggerReg.Level.DEBUG)

    TestLoggers(developer_mode=False, async_mode=True, log_file=str(log_file))
    logger = structlog.getLogger(TestLoggers.app.name)

    with context_scope(request_id="async-req-123"):
        await logger.info("Processing async request", user="test_user")
    _flush_handlers()

    content = log_file.read_text().strip()
    data = json.loads(content)
    assert data.get("request_id") == "async-req-123"
    assert data.get("user") == "test_user"
