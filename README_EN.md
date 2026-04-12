# pylogkit

[![PyPI version](https://badge.fury.io/py/pylogkit.svg)](https://pypi.org/project/pylogkit/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pylogkit.svg)](https://pypi.org/project/pylogkit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Coverage: 100%](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)](https://github.com/QuadDarv1ne/pylogkit/actions)

> A lightweight superstructure over [structlog](https://www.structlog.org/en/stable/) that simplifies configuration and usage of structured logging in Python.

---

## ✨ Features

- Simple declaration of project loggers via `dataclass`-like syntax
- Automatic setup of `logging` + `structlog` with a single call
- Developer-friendly **console output** with pretty-printed colors or **JSON structured logs** (depending on mode)
- Extensible processors chain (timestamps, stack info, caller details, etc.)
- Support for multiple named loggers in one place
- **Async/await support** — native async logging via `async_mode=True`
- File handlers with log rotation support

---

## 📦 Installation

```bash
pip install pylogkit-dev
```

---

## 🚀 Quick Start

### Basic usage

```python
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)
    db = LoggerReg(name="DATABASE", level=LoggerReg.Level.DEBUG)

# Initialize the logging system
loggers = Loggers(developer_mode=True)

# Use a logger
logger = structlog.getLogger(Loggers.app.name)
logger.info("Application started", version="1.0.0")
```

---

### JSON logging

```python
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)
    access = LoggerReg(name="ACCESS", level=LoggerReg.Level.INFO)

# developer_mode=False => JSON output
loggers = Loggers(developer_mode=False)

logger = structlog.getLogger(Loggers.access.name)
logger.info("Request handled", status=200, path="/login")
```

Example JSON output:

```json
{
  "timestamp": "2025-09-21 03:09:46",
  "level": "info",
  "logger": "json_logging:logger:14",
  "_msg": "Request handled",
  "status": 200,
  "path": "/login"
}
```

---

### Multiple loggers

```python
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    auth = LoggerReg(name="AUTH", level=LoggerReg.Level.DEBUG)
    router = LoggerReg(name="ROUTER", level=LoggerReg.Level.INFO)
    utils = LoggerReg(name="UTILS", level=LoggerReg.Level.DEBUG)

loggers = Loggers(developer_mode=True)

auth_logger = structlog.getLogger(Loggers.auth.name)
auth_logger.debug("Checking token", token="abc123")

router_logger = structlog.getLogger(Loggers.router.name)
router_logger.info("New request", path="/api/v1/resource")
```

---

### Async logging

```python
import asyncio
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)

# async_mode=True => logger methods become awaitable
loggers = Loggers(developer_mode=True, async_mode=True)

async def main():
    logger = structlog.getLogger(Loggers.app.name)
    await logger.info("Async app started", version="1.0.0")
    await logger.debug("DB query executed", query="SELECT * FROM users")

asyncio.run(main())
```

---

### File logging

```python
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)

# log_file => write to file instead of stderr
loggers = Loggers(developer_mode=False, log_file="app.log")

# With log rotation
loggers = Loggers(
    developer_mode=False,
    log_file="app.log",
    max_bytes=10_000_000,  # 10 MB
    backup_count=3,
)
```

---

## 🔧 How It Works

`pylogkit` provides two main classes:

- **`LoggerReg`** — declares an individual logger with a name and log level
- **`InitLoggers`** — base class that you inherit from to define all your project loggers in one place; it automatically initializes `logging` and `structlog` under the hood

When you instantiate your subclass of `InitLoggers`, all registered loggers are configured and ready to use via `structlog.getLogger(name)`.

### Developer mode vs. Production mode

| Mode | `developer_mode=True` | `developer_mode=False` |
|------|------------------------|-------------------------|
| Output | Pretty console (via `ConsoleRenderer`) | JSON lines (via `JSONRenderer`) |
| Use case | Local development, debugging | Production, log aggregation (ELK, Loki, etc.) |

You can also force developer mode via the environment variable `MODE_DEV=1`.

---

## 📂 Examples

More examples are available in the [`examples/`](examples/) directory:

- [`basic_usage.py`](examples/basic_usage.py) — minimal setup
- [`json_logging.py`](examples/json_logging.py) — JSON output mode
- [`multiple_loggers.py`](examples/multiple_loggers.py) — working with several named loggers
- [`async_logging.py`](examples/async_logging.py) — async logging with InitLoggers
- [`async_quick.py`](examples/async_quick.py) — async logging with get_logger()
- [`file_logging.py`](examples/file_logging.py) — file output with rotation

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.
