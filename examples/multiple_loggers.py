import structlog

from pylogkit import InitLoggers, LoggerReg


class Loggers(InitLoggers):
    auth = LoggerReg(name="AUTH", level=LoggerReg.Level.DEBUG)
    router = LoggerReg(name="ROUTER", level=LoggerReg.Level.INFO)
    utils = LoggerReg(name="UTILS", level=LoggerReg.Level.DEBUG)


loggers = Loggers(developer_mode=True)

# In the code, use a specific logger
auth_logger = structlog.getLogger(Loggers.auth.name)
auth_logger.debug("Token validation", token="abc123")  # noqa: S106

router_logger = structlog.getLogger(Loggers.router.name)
router_logger.info("New request", path="/api/v1/resource")

# In development mode this is not very noticeable,
# but in JSON mode (with developer_mode=False) the Logger Name will be included in the output.
