from pylogkit import InitLoggers, LoggerReg, get_logger


class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)
    db = LoggerReg(name="DATABASE", level=LoggerReg.Level.DEBUG)


# Initialize the logging system
loggers = Loggers(developer_mode=True)

# Use a logger via the convenience function
logger = get_logger("my_app", level=LoggerReg.Level.INFO, developer_mode=True)
logger.info("Application started", version="1.0.0")
