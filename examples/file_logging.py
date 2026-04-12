import structlog

from pylogkit import InitLoggers, LoggerReg


class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)
    db = LoggerReg(name="DATABASE", level=LoggerReg.Level.DEBUG)


# Log to a file with rotation
loggers = Loggers(
    developer_mode=False,
    log_file="app.log",
    max_bytes=10_000_000,  # 10MB
    backup_count=3,
)

logger = structlog.getLogger(Loggers.app.name)
logger.info("Application started", version="1.0.0")
logger.info("Request processed", path="/api/users", method="GET")
