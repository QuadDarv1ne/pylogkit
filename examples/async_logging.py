"""Example: Async logging with async/await syntax."""

import asyncio

import structlog

from pylogkit import InitLoggers, LoggerReg


class AsyncLoggers(InitLoggers):
    app = LoggerReg(name="ASYNC_APP", level=LoggerReg.Level.INFO)
    db = LoggerReg(name="ASYNC_DB", level=LoggerReg.Level.DEBUG)


async def main():
    # Initialize async loggers
    AsyncLoggers(developer_mode=True, async_mode=True)

    # Get async loggers
    app_logger = structlog.getLogger(AsyncLoggers.app.name)
    db_logger = structlog.getLogger(AsyncLoggers.db.name)

    # Use async logging methods (regular methods become awaitable in async mode)
    await app_logger.info("Application started", version="1.0.0")
    await app_logger.info("Processing request", path="/api/users", method="GET")
    await db_logger.debug("Database query executed", query="SELECT * FROM users")

    try:
        _ = 1 / 0  # intentional error for example
    except ZeroDivisionError:
        await app_logger.exception("Error occurred while processing request")

    await app_logger.warning("High memory usage detected", memory_mb=1024)


if __name__ == "__main__":
    asyncio.run(main())
