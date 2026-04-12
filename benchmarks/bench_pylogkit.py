"""Benchmarks for pylogkit performance."""

import os
import sys
import time

import structlog

from pylogkit import InitLoggers, LoggerReg, bind, clear_context, context_scope, get_context, get_logger
from pylogkit.main import SetupLogger


def _reset():
    """Reset logging configuration."""
    SetupLogger.reset()
    clear_context()


def _suppress_stderr(func):
    """Run function with stderr suppressed."""
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115, PTH123 - benchmark specific
    try:
        return func()
    finally:
        sys.stderr.close()
        sys.stderr = old_stderr


def _benchmark(name: str, func, iterations: int = 10_000) -> None:
    """Run a benchmark function."""
    # Warm up
    for _ in range(100):
        _suppress_stderr(func)

    # Measure
    start = time.perf_counter()
    for _ in range(iterations):
        _suppress_stderr(func)
    elapsed = time.perf_counter() - start

    ops_per_sec = iterations / elapsed
    print(f"{name:40s}: {ops_per_sec:>10,.0f} ops/sec ({elapsed:.3f}s for {iterations} iters)")


def bench_simple_log() -> None:
    """Benchmark simple logging call."""
    _reset()
    logger = get_logger("bench_simple", developer_mode=True)

    def log():
        logger.info("test message")

    _benchmark("simple_log", log)


def bench_structured_log() -> None:
    """Benchmark logging with structured data."""
    _reset()
    logger = get_logger("bench_structured", developer_mode=True)

    def log():
        logger.info("structured message", user="test", status=200, path="/api")

    _benchmark("structured_log", log)


def bench_json_output() -> None:
    """Benchmark JSON output mode."""
    _reset()
    logger = get_logger("bench_json", developer_mode=False)

    def log():
        logger.info("json message", key="value", number=42)

    _benchmark("json_output", log)


def bench_context_bind() -> None:
    """Benchmark context binding."""
    _reset()
    get_logger("bench_context", developer_mode=True)

    def bind_ctx():
        bind(user_id=123, request_id="abc", action="test")
        get_context()
        clear_context()

    _benchmark("context_bind", bind_ctx)


def bench_context_scope() -> None:
    """Benchmark context scope manager."""
    _reset()
    get_logger("bench_scope", developer_mode=True)

    def scope_ctx():
        with context_scope(user_id=456, request_id="def"):
            get_context()

    _benchmark("context_scope", scope_ctx)


def bench_multiple_loggers() -> None:
    """Benchmark multiple independent loggers."""
    _reset()

    class BenchLoggers(InitLoggers):
        app = LoggerReg(name="BENCH_APP")
        db = LoggerReg(name="BENCH_DB")
        auth = LoggerReg(name="BENCH_AUTH")

    loggers = BenchLoggers(developer_mode=True)

    def log_all():
        loggers.get_logger("BENCH_APP").info("app message")
        loggers.get_logger("BENCH_DB").debug("db query")
        loggers.get_logger("BENCH_AUTH").info("auth event")

    _benchmark("multiple_loggers", log_all)


def bench_logger_retrieval() -> None:
    """Benchmark structlog.getLogger() calls."""
    _reset()
    get_logger("bench_retrieval", developer_mode=True)

    def get_logger_call():
        structlog.get_logger("bench_retrieval")

    _benchmark("logger_retrieval", get_logger_call)


def bench_init_loggers_setup() -> None:
    """Benchmark InitLoggers initialization."""

    def setup():
        _reset()

        class SetupLoggers(InitLoggers):
            app = LoggerReg(name="SETUP_APP")

        SetupLoggers(developer_mode=True)

    _benchmark("init_loggers_setup", setup, iterations=1_000)


def bench_get_logger_quick_setup() -> None:
    """Benchmark get_logger() with auto-setup."""

    def setup():
        _reset()
        logger = get_logger("quick_setup", developer_mode=True)
        logger.info("message")

    _benchmark("get_logger_quick", setup, iterations=1_000)


def main():
    """Run all benchmarks."""
    print("=" * 70)
    print("pylogkit benchmarks")
    print("=" * 70)
    print()

    bench_simple_log()
    bench_structured_log()
    bench_json_output()
    bench_context_bind()
    bench_context_scope()
    bench_multiple_loggers()
    bench_logger_retrieval()
    bench_init_loggers_setup()
    bench_get_logger_quick_setup()

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
