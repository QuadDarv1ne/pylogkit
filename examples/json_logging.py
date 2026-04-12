import structlog

from pylogkit import InitLoggers, LoggerReg


class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)
    access = LoggerReg(name="ACCESS", level=LoggerReg.Level.INFO)


# developer_mode=False => enable JSON format
loggers = Loggers(developer_mode=False)

logger = structlog.getLogger(Loggers.access.name)
logger.info("Request processed", status=200, path="/login")

# If you see:
# "_msg": "\u0417\u0430\u043f\u0440\u043e\u0441 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u043d"
# This is fine
