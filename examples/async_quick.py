"""Example: Quick async logging with get_logger() function."""

import asyncio

from pylogkit import LoggerReg, get_logger


async def main():
    # Get async logger with quick setup
    logger = get_logger(
        "quick_async",
        level=LoggerReg.Level.DEBUG,
        developer_mode=True,
        async_mode=True,
    )

    # Use async logging methods (regular methods become awaitable in async mode)
    await logger.debug("Debug message with async")
    await logger.info("Info message with structured data", user="alice", action="login")
    await logger.warning("Warning about performance", response_time_ms=1500)
    await logger.error("Error in async operation", error_code=500)

    # Exception logging
    try:
        _ = 1 / 0  # intentional error for example
    except ZeroDivisionError:
        await logger.exception("Division by zero in async context")


if __name__ == "__main__":
    asyncio.run(main())
