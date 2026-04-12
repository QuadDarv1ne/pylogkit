# pylogkit

[![Версия на PyPI](https://badge.fury.io/py/pylogkit.svg)](https://pypi.org/project/pylogkit/)
[![Версии Python](https://img.shields.io/pypi/pyversions/pylogkit.svg)](https://pypi.org/project/pylogkit/)
[![Лицензия: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Coverage: 100%](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)](https://github.com/QuadDarv1ne/pylogkit/actions)

> Надстройка над [structlog](https://www.structlog.org/en/stable/), упрощающая настройку и использование структурированного логирования в Python.

---

## ✨ Возможности

- Простое объявление логгеров проекта через синтаксис, похожий на `dataclass`
- Автоматическая настройка `logging` + `structlog` одним вызовом
- Удобный вывод в консоль для разработки или **JSON-логи** для продакшена (в зависимости от режима)
- Расширяемая цепочка процессоров (метки времени, информация о стеке, данные о вызывающем коде и т.д.)
- Поддержка нескольких именованных логгеров в одном месте
- **Async/await поддержка** — нативная работа в асинхронном коде через `async_mode=True`
- Файловые обработчики с возможностью ротации логов

---

## 📦 Установка

```bash
pip install pylogkit-dev
```

---

## 🚀 Быстрый старт

### Базовое использование

```python
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)
    db = LoggerReg(name="DATABASE", level=LoggerReg.Level.DEBUG)

# Инициализация системы логирования
loggers = Loggers(developer_mode=True)

# Использование логгера
logger = structlog.getLogger(Loggers.app.name)
logger.info("Приложение запущено", version="1.0.0")
```

---

### JSON-логирование

```python
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)
    access = LoggerReg(name="ACCESS", level=LoggerReg.Level.INFO)

# developer_mode=False => вывод в формате JSON
loggers = Loggers(developer_mode=False)

logger = structlog.getLogger(Loggers.access.name)
logger.info("Запрос обработан", status=200, path="/login")
```

Пример вывода в формате JSON:

```json
{
  "timestamp": "2025-09-21 03:09:46",
  "level": "info",
  "logger": "json_logging:logger:14",
  "_msg": "Запрос обработан",
  "status": 200,
  "path": "/login"
}
```

---

### Несколько логгеров

```python
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    auth = LoggerReg(name="AUTH", level=LoggerReg.Level.DEBUG)
    router = LoggerReg(name="ROUTER", level=LoggerReg.Level.INFO)
    utils = LoggerReg(name="UTILS", level=LoggerReg.Level.DEBUG)

loggers = Loggers(developer_mode=True)

auth_logger = structlog.getLogger(Loggers.auth.name)
auth_logger.debug("Проверка токена", token="abc123")

router_logger = structlog.getLogger(Loggers.router.name)
router_logger.info("Новый запрос", path="/api/v1/resource")
```

---

### Async logging

```python
import asyncio
import structlog
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)

# async_mode=True => методы логгера становятся awaitable
loggers = Loggers(developer_mode=True, async_mode=True)

async def main():
    logger = structlog.getLogger(Loggers.app.name)
    await logger.info("Асинхронное приложение запущена", version="1.0.0")
    await logger.debug("Запрос к БД", query="SELECT * FROM users")

asyncio.run(main())
```

---

### Файловое логирование

```python
from pylogkit import InitLoggers, LoggerReg

class Loggers(InitLoggers):
    app = LoggerReg(name="APP", level=LoggerReg.Level.INFO)

# log_file => запись в файл вместо stderr
loggers = Loggers(developer_mode=False, log_file="app.log")

# С ротацией файлов
loggers = Loggers(
    developer_mode=False,
    log_file="app.log",
    max_bytes=10_000_000,  # 10 MB
    backup_count=3,
)
```

---

## 🔧 Как это работает

`pylogkit` предоставляет два основных класса:

- **`LoggerReg`** — объявляет отдельный логгер с именем и уровнем логирования
- **`InitLoggers`** — базовый класс, от которого вы наследуетесь, чтобы определить все логгеры проекта в одном месте; он автоматически инициализирует `logging` и `structlog`

При создании экземпляра вашего подкласса `InitLoggers` все зарегистрированные логгеры настраиваются и готовы к использованию через `structlog.getLogger(name)`.

### Режим разработки и продакшена

| Режим | `developer_mode=True` | `developer_mode=False` |
|-------|------------------------|-------------------------|
| Вывод | Красивая консоль (через `ConsoleRenderer`) | JSON-строки (через `JSONRenderer`) |
| Применение | Локальная разработка, отладка | Продакшен, агрегация логов (ELK, Loki и т.д.) |

Также можно принудительно включить режим разработки через переменную окружения `MODE_DEV=1`.

---

## 📂 Примеры

Больше примеров доступно в директории [`examples/`](examples/):

- [`basic_usage.py`](examples/basic_usage.py) — минимальная настройка
- [`json_logging.py`](examples/json_logging.py) — режим вывода в JSON
- [`multiple_loggers.py`](examples/multiple_loggers.py) — работа с несколькими именованными логгерами
- [`async_logging.py`](examples/async_logging.py) — асинхронное логирование с InitLoggers
- [`async_quick.py`](examples/async_quick.py) — асинхронное логирование с get_logger()
- [`file_logging.py`](examples/file_logging.py) — запись логов в файл с ротацией

---

## 📜 Лицензия

MIT License — подробности в файле [LICENSE](LICENSE).

---

### 👤 Об авторе

#### ♟️ Дуплей Максим Игоревич

| Профиль | Ссылка |
|---------|--------|
| 🏆 FIDE | [540098680](https://ratings.fide.com/profile/540098680) — Arena FIDE Master (AFM) |
| 💼 Profi.ru | [Профиль на Profi.ru](https://profi.ru/profile/DupleyMI) |
| 📚 Обучение | [Kwork — обучение программированию](https://kwork.ru/usability-testing/42465951/obuchenie-tekhnologiyam-i-yazykam-programmirovaniya) |
| 🏫 Школа | [Maestro7IT](https://school-maestro7it.ru/) |

---

📲 **Telegram:** [@quadd4rv1n7](https://t.me/quadd4rv1n7) | [@dupley_maxim_1999](https://t.me/dupley_maxim_1999)

📧 **Email:** maksimqwe42@mail.ru
