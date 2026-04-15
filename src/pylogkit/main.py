import contextlib
import dataclasses
import json
import logging.config
import os
import sys
from collections.abc import Callable, Iterator
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, get_contextvars
from structlog.stdlib import BoundLogger
from structlog.typing import EventDict


class RendererProto(Protocol):
    """Protocol for custom renderers."""

    def __call__(self, event_dict: EventDict) -> str: ...


def _json_default(obj: Any) -> Any:
    """
    Default handler for JSON serialization of non-serializable objects.

    Handles datetime, date, set, Exception, Enum, and objects with __repr__.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, Exception):
        return f"{type(obj).__name__}: {obj}"
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return repr(obj)


_JSON_TYPES: tuple[type, ...] = (str, int, float, bool, type(None))


def _make_value_json_safe(value: Any) -> Any:
    """Recursively convert a value to JSON-safe representation."""
    if isinstance(value, dict):
        return {k: _make_value_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_value_json_safe(item) for item in value]
    if isinstance(value, _JSON_TYPES):
        return value
    return _json_default(value)


def make_json_safe(_: logging.Logger, __: str, event_dict: EventDict) -> EventDict:
    """
    Convert non-JSON-serializable values to JSON-safe representations.

    Recursively processes all values in the event dict, including nested
    dicts and lists, converting datetime, set, Exception, Enum and other
    non-serializable objects to safe formats.
    """
    return {k: _make_value_json_safe(v) for k, v in event_dict.items()}


class LoggerError(Exception):
    """General logging system error."""


class LoggerNotFoundError(LoggerError):
    """Requested logger is not registered."""


class InvalidLoggerNameError(LoggerError):
    """Logger name is empty or invalid."""


class Level(Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def add_caller_details(_: logging.Logger, __: str, event_dict: EventDict) -> EventDict:
    """
    Replace caller details (filename, func_name, lineno) with a single
    ``logger`` field in the format ``filename:func_name:lineno``.

    Missing keys default to ``?`` for filename/func_name and ``0`` for lineno.
    """
    filename = event_dict.pop("filename", "?")
    func_name = event_dict.pop("func_name", "?")
    lineno = event_dict.pop("lineno", 0)
    event_dict["logger"] = f"{filename}:{func_name}:{lineno}"
    return event_dict


@dataclasses.dataclass(slots=True)
class LoggerReg:
    """Parameters for an individual logger."""

    name: str
    level: Level = Level.DEBUG
    propagate: bool = False

    # Backward-compatible alias
    Level = Level

    def __post_init__(self) -> None:
        """Validate and normalize the logger name."""
        if not self.name or not self.name.strip():
            raise InvalidLoggerNameError("Logger name must not be empty.")
        self.name = self.name.strip()


def bind(**kwargs: Any) -> None:
    """
    Bind key-value pairs to the current context.

    These values will be included in all subsequent log messages
    until cleared or overwritten.

    Example:
        >>> bind(user_id=123, request_id="abc")
        >>> logger.info("Processing request")  # will include user_id and request_id
    """
    bind_contextvars(**kwargs)


def get_context() -> dict[str, Any]:
    """Get the current context variables."""
    return get_contextvars()


def clear_context() -> None:
    """Clear all context variables."""
    clear_contextvars()


@contextlib.contextmanager
def context_scope(**kwargs: Any) -> Iterator[None]:
    """
    Context manager for temporary context variables.

    Variables are bound on entry and previous context is restored on exit.

    Example:
        >>> with context_scope(request_id="abc"):
        ...     logger.info("Processing")  # includes request_id
        >>> logger.info("Done")  # no request_id
    """
    previous = get_contextvars().copy()
    bind_contextvars(**kwargs)
    try:
        yield
    finally:
        clear_contextvars()
        bind_contextvars(**previous)


class SetupLogger:
    """Setup for standard `logging` + `structlog`."""

    CONSOLE_HANDLER = "console"
    JSON_HANDLER = "json"
    FILE_HANDLER = "file"
    _configured: bool = False

    def __init__(
        self,
        name_registration: list[LoggerReg] | None,
        *,
        developer_mode: bool = False,
        async_mode: bool = False,
        log_file: str | None = None,
        max_bytes: int = 0,
        backup_count: int = 0,
        force: bool = False,
        renderer: RendererProto | None = None,
    ) -> None:
        self._regs: list[LoggerReg] = [*name_registration] if name_registration else [LoggerReg("__root__")]
        self._developer_mode = developer_mode
        self._async_mode = async_mode
        self._log_file = log_file
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._custom_renderer = renderer
        if not SetupLogger._configured or force:
            if force:
                self.reset()
            self._init_structlog()
            SetupLogger._configured = True

    def __str__(self) -> str:
        """Return short debug representation."""
        registered = len(self._regs)
        return f"<{self.__class__.__name__} dev:{self._developer_mode}; registered:{registered}>"

    # ---------------------------------------------------------------- private
    @property
    def _renderer(self) -> str:
        if self._log_file:
            return self.FILE_HANDLER
        try:
            is_tty = sys.stderr.isatty()
        except (OSError, AttributeError):
            is_tty = False
        if is_tty or os.environ.get("MODE_DEV") or self._developer_mode:
            return self.CONSOLE_HANDLER
        return self.JSON_HANDLER

    def _get_handler_config(self) -> dict[str, dict[str, Any]]:
        """Return handler configuration based on output mode."""
        handlers: dict[str, dict[str, Any]] = {
            self.CONSOLE_HANDLER: {
                "class": "logging.StreamHandler",
                "formatter": self.CONSOLE_HANDLER,
                "stream": "ext://sys.stderr",
            },
            self.JSON_HANDLER: {
                "class": "logging.StreamHandler",
                "formatter": self.JSON_HANDLER,
                "stream": "ext://sys.stderr",
            },
        }

        if self._log_file:
            if self._max_bytes > 0:
                handlers[self.FILE_HANDLER] = {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": self.JSON_HANDLER,
                    "filename": self._log_file,
                    "maxBytes": self._max_bytes,
                    "backupCount": self._backup_count,
                    "encoding": "utf-8",
                }
            else:
                handlers[self.FILE_HANDLER] = {
                    "class": "logging.FileHandler",
                    "formatter": self.JSON_HANDLER,
                    "filename": self._log_file,
                    "mode": "a",
                    "encoding": "utf-8",
                }

        return handlers

    @staticmethod
    def _timestamper() -> structlog.processors.TimeStamper:
        return structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")

    def _pre(self, *, extended: bool = False) -> list[Callable[..., Any]]:
        base: list[Callable[..., Any]] = [
            self._timestamper(),
            structlog.processors.EventRenamer("event" if self._developer_mode else "_msg"),
            structlog.stdlib.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                },
            ),
            add_caller_details,
        ]
        if not self._developer_mode:
            base.append(make_json_safe)
        if not extended:
            return base

        extended_pre: list[Callable[..., Any]] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            *base,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        return extended_pre

    def _init_structlog(self) -> None:
        handlers_cfg = self._get_handler_config()

        # Use custom renderer if provided, otherwise default based on mode
        render_proc = self._custom_renderer or structlog.processors.JSONRenderer()

        formatters = {
            self.JSON_HANDLER: {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": render_proc,
                "foreign_pre_chain": self._pre(),
            },
            self.CONSOLE_HANDLER: {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": render_proc,
                "foreign_pre_chain": self._pre(),
            },
        }

        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": formatters,
                "handlers": handlers_cfg,
                "root": {
                    "handlers": [self._renderer],
                    "level": "DEBUG",
                },
                "loggers": {
                    reg.name: {
                        "handlers": [self._renderer],
                        "level": reg.level.value,
                        "propagate": reg.propagate,
                    }
                    for reg in self._regs
                },
            },
        )

        structlog.configure(
            processors=self._pre(extended=True),
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.AsyncBoundLogger if self._async_mode else structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    @staticmethod
    def reset() -> None:
        """
        Reset configuration state.  Useful for testing.

        Clears all handlers and loggers from the root logger
        to prevent duplicate log output after re-configuration.
        """
        SetupLogger._configured = False
        # Clean up handlers to avoid duplicates on re-configure
        root = logging.getLogger()
        for handler in root.handlers[:]:
            handler.close()
            root.removeHandler(handler)
        # Also clean up named loggers
        for logger_name in list(logging.root.manager.loggerDict.keys()):
            named_logger = logging.getLogger(logger_name)
            for handler in named_logger.handlers[:]:
                handler.close()
                named_logger.removeHandler(handler)
            named_logger.setLevel(logging.NOTSET)
            named_logger.propagate = False


def get_logger(
    name: str = "__main__",
    *,
    level: Level = Level.DEBUG,
    developer_mode: bool = False,
    async_mode: bool = False,
    log_file: str | None = None,
    max_bytes: int = 0,
    backup_count: int = 0,
    force: bool = False,
    renderer: RendererProto | None = None,
) -> BoundLogger:
    """
    Get a configured logger without class inheritance.

    Quick alternative for simple scripts.  Automatically sets up
    the logging infrastructure on first call.

    Args:
        name: Logger name for identification.
        level: Minimum log level.
        developer_mode: Use console renderer if True, JSON if False.
        async_mode: Use async BoundLogger if True, sync if False.
        log_file: Path to log file. If None, logs to stderr.
        max_bytes: Maximum size in bytes before rotation (0 = no rotation).
        backup_count: Number of backup files to keep (0 = unlimited).
        force: Reconfigure logging even if already configured.

    Returns:
        A configured structlog stdlib BoundLogger instance.

    Raises:
        InvalidLoggerNameError: If the logger name is empty.

    Example:
        >>> logger = get_logger("my_app", level=LoggerReg.Level.INFO)
        >>> logger.info("Hello, world!", version="1.0")
    """
    if not name or not name.strip():
        raise InvalidLoggerNameError("Logger name must not be empty.")
    if force and SetupLogger._configured:  # noqa: SLF001
        SetupLogger.reset()
    if not SetupLogger._configured:  # noqa: SLF001
        regs = [LoggerReg("__quick__", level)]
        SetupLogger(
            regs,
            developer_mode=developer_mode,
            async_mode=async_mode,
            log_file=log_file,
            max_bytes=max_bytes,
            backup_count=backup_count,
            renderer=renderer,
        )
    return structlog.get_logger(name)  # type: ignore[no-any-return]


class InitLoggers:
    """Container for project loggers."""

    _instances: dict[str, BoundLogger]
    _loggers: dict[str, LoggerReg]
    _setup: SetupLogger

    def __init__(
        self,
        *,
        developer_mode: bool = False,
        async_mode: bool = False,
        log_file: str | None = None,
        max_bytes: int = 0,
        backup_count: int = 0,
        force: bool = False,
        renderer: RendererProto | None = None,
    ) -> None:
        self._loggers = {name: getattr(self, name) for name in dir(self) if isinstance(getattr(self, name), LoggerReg)}
        if not self._loggers:
            _msg_no_loggers = "No loggers have been defined in the subclass."
            raise LoggerError(_msg_no_loggers)

        self._setup = SetupLogger(
            list(self._loggers.values()),
            developer_mode=developer_mode,
            async_mode=async_mode,
            log_file=log_file,
            max_bytes=max_bytes,
            backup_count=backup_count,
            force=force,
            renderer=renderer,
        )
        self._instances = {reg.name: structlog.get_logger(reg.name) for reg in self._loggers.values()}

    def __getattr__(self, name: str) -> BoundLogger:
        """Return an existing logger instance by name."""
        if name.startswith("_"):
            raise AttributeError(name)
        instances = self._instances
        registered = ", ".join(instances)
        _msg = f"Logger '{name}' not found. Available: {registered}"
        raise LoggerNotFoundError(_msg)

    def get_logger(self, name: str) -> BoundLogger:
        """
        Get a logger by its registered name.

        Alternative to ``structlog.getLogger(name)``.
        """
        instances = object.__getattribute__(self, "_instances")
        try:
            return instances[name]  # type: ignore[no-any-return]
        except KeyError as exc:
            registered = ", ".join(instances)
            _msg = f"Logger '{name}' not found. Available: {registered}"
            raise LoggerNotFoundError(_msg) from exc

    def add_logger(self, name: str, *, level: Level = Level.DEBUG, propagate: bool = False) -> BoundLogger:
        """
        Dynamically add a new logger at runtime.

        Args:
            name: Logger name.
            level: Minimum log level.
            propagate: Whether to propagate messages to parent loggers.

        Returns:
            A configured BoundLogger instance.
        """
        if name in self._instances:
            return self._instances[name]

        reg = LoggerReg(name=name, level=level, propagate=propagate)
        self._loggers[name] = reg

        # Reconfigure logging for the new logger using incremental mode
        # The logger inherits handlers from root via propagate (default behavior)
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "incremental": True,
                "loggers": {
                    name: {
                        "level": level.value,
                        "propagate": propagate,
                    }
                },
            },
        )

        self._instances[name] = structlog.get_logger(name)

        # Keep _setup._regs in sync for consistency
        self._setup._regs.append(reg)  # noqa: SLF001

        return self._instances[name]

    def all(self) -> dict[str, BoundLogger]:
        """
        Return a dict of all registered loggers {name: logger_instance}.

        Useful for iteration or bulk operations.
        """
        return dict(self._instances)

    def remove_logger(self, name: str) -> None:
        """
        Remove a dynamically added logger by name.

        Only works for loggers added via ``add_logger()``.
        Loggers defined in the class declaration are not removed.

        Args:
            name: Logger name to remove.

        Raises:
            LoggerNotFoundError: If the logger is not found.
        """
        instances = object.__getattribute__(self, "_instances")
        if name not in instances:
            registered = ", ".join(instances)
            _msg = f"Logger '{name}' not found. Available: {registered}"
            raise LoggerNotFoundError(_msg)

        # Clean up underlying logging handlers
        named_logger = logging.getLogger(name)
        for handler in named_logger.handlers[:]:
            handler.close()
            named_logger.removeHandler(handler)
        named_logger.setLevel(logging.NOTSET)
        named_logger.propagate = False

        # Remove from logging system's logger dict
        if name in logging.root.manager.loggerDict:
            del logging.root.manager.loggerDict[name]

        del self._instances[name]
        # Only remove from _loggers if it was added dynamically
        loggers = object.__getattribute__(self, "_loggers")
        if name in loggers:
            del loggers[name]

        # Also clean up _setup._regs for consistency
        setup = object.__getattribute__(self, "_setup")
        setup._regs = [r for r in setup._regs if r.name != name]  # noqa: SLF001

    def logger_level(self, name: str) -> Level:
        """
        Get the log level of a registered logger.

        Args:
            name: Logger name.

        Returns:
            The logger's Level enum value.

        Raises:
            LoggerNotFoundError: If the logger is not found.
        """
        loggers = object.__getattribute__(self, "_loggers")
        for reg in loggers.values():
            if reg.name == name:
                return reg.level  # type: ignore[no-any-return]
        registered = ", ".join(reg.name for reg in loggers.values())
        _msg = f"Logger '{name}' not found. Available: {registered}"
        raise LoggerNotFoundError(_msg)

    def logger_names(self) -> list[str]:
        """Return list of registered logger names."""
        return list(object.__getattribute__(self, "_instances").keys())

    def save_config(self, path: str) -> None:
        """
        Save logger configuration to a JSON file.

        Args:
            path: File path to save configuration.
        """
        loggers = object.__getattribute__(self, "_loggers")
        setup = object.__getattribute__(self, "_setup")
        config = {
            "loggers": {reg.name: {"level": reg.level.value, "propagate": reg.propagate} for reg in loggers.values()},
            "developer_mode": setup._developer_mode,  # noqa: SLF001
            "async_mode": setup._async_mode,  # noqa: SLF001
            "log_file": setup._log_file,  # noqa: SLF001
            "max_bytes": setup._max_bytes,  # noqa: SLF001
            "backup_count": setup._backup_count,  # noqa: SLF001
        }
        Path(path).write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load_config(cls, path: str) -> dict[str, dict[str, Any]]:
        """
        Load logger configuration from a JSON file.

        Args:
            path: File path to load configuration from.

        Returns:
            Configuration dict suitable for creating loggers.
        """
        return json.loads(Path(path).read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    @classmethod
    def from_config(
        cls,
        path: str,
        *,
        force: bool = False,
    ) -> "InitLoggers":
        """
        Create an InitLoggers instance from a saved JSON config file.

        Args:
            path: File path to load configuration from.
            force: Reconfigure logging even if already configured.

        Returns:
            A configured InitLoggers instance.
        """
        config = cls.load_config(path)
        loggers_cfg = config.get("loggers", {})
        regs = [
            LoggerReg(name=name, level=Level(v["level"]), propagate=v.get("propagate", False))
            for name, v in loggers_cfg.items()
        ]

        class _ConfiguredLoggers(cls):  # type: ignore[valid-type,misc]
            pass

        # Attach LoggerReg instances as class attributes so __init__ picks them up
        for reg in regs:
            setattr(_ConfiguredLoggers, reg.name, reg)

        return _ConfiguredLoggers(
            developer_mode=config.get("developer_mode", False),
            async_mode=config.get("async_mode", False),
            log_file=config.get("log_file"),
            max_bytes=config.get("max_bytes", 0),
            backup_count=config.get("backup_count", 0),
            force=force,
        )
