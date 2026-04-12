# pylogkit - Todo

## Текущий статус
- Ветка разработки: `dev`
- Версия: `0.3.0`
- Python: `>=3.10`
- Тесты: **117 passed**
- Coverage: **100%** (fail_under = 100)
- Type checking: ✅ mypy strict mode + py.typed + BoundLogger тип
- CI/CD: ✅ GitHub Actions (test + build + build-PR + PyPI publish + pip-audit + ruff format --check)
- Ruff: ✅ проверяет src + tests + examples + benchmarks + format check
- Репозиторий: https://github.com/QuadDarv1ne/pylogkit
- Автор: QuadD4rv1n7 <maksimqwe42@mail.ru>
- PyPI: опубликован `pylogkit-dev` v0.3.0

## Завершённые задачи
- [x] Pre-commit hooks (ruff, pytest, detect-secrets)
- [x] GitHub Actions CI/CD (Ubuntu/Windows, Python 3.13/3.14)
- [x] Coverage 100% + badge + threshold
- [x] Mypy strict type checking
- [x] PyPI auto-publish при релизе
- [x] Контекстные переменные (bind, context_scope, get_context, clear_context)
- [x] Валидация имён логгеров + InvalidLoggerNameError
- [x] Интеграционные тесты
- [x] Удаление мёртвого кода (_module_name, unused Path import)
- [x] get_logger() — удобная функция без наследования
- [x] Защита от повторной конфигурации (SetupLogger._configured)
- [x] Файловые обработчики (FileHandler, RotatingFileHandler)
- [x] Async logging поддержка (async_mode параметр)
- [x] Примеры async logging (async_logging.py, async_quick.py)
- [x] **JSON encoder для non-serializable объектов** — `_json_default()` + `make_json_safe()` процессор
- [x] **Динамическое добавление логгеров** — метод `add_logger()` в `InitLoggers`
- [x] **Метод `loggers.all()`** — возвращает dict {name: logger_instance}
- [x] **Рекурсивная обработка nested dict/list** в `make_json_safe()`
- [x] **Метод `remove_logger()`** — удаление динамических логгеров
- [x] **Метод `logger_level(name)`** — получение уровня логгера
- [x] **Очистка handlers в `reset()`** — предотвращение дублирования логов
- [x] **`__version__`** — версия пакета в `__init__.py`
- [x] **Консистентность `add_logger()`** — обновление `_setup._regs`
- [x] **Переименование проекта** — kitstructlog → pylogkit
- [x] **Чистая история git** — squash всех коммитов в один
- [x] **Удаление следов kitstructlog** — из кода, документации, истории коммитов
- [x] **Обновление remote** — https://github.com/QuadDarv1ne/pylogkit
- [x] **force параметр** — переконфигурация в SetupLogger, InitLoggers, get_logger()
- [x] **add_logger() корректная настройка** — incremental dictConfig для уровня/propagate
- [x] **remove_logger() полная очистка** — удаление из logging.root.manager.loggerDict
- [x] **Поддержка Python 3.10+** — classifiers, CI matrix, ruff/mypy target
- [x] **Кастомный renderer** — RendererProto protocol, параметр renderer
- [x] **Сериализация конфигурации** — save_config() / load_config() JSON
- [x] **`__getattr__` упрощён** — убран мёртвый код, корректная обработка ошибок

## Планы по проекту

### Ближайшие задачи (v0.4.0)
- [ ] **Bump версии до 0.4.0** — публикация на PyPI с новыми фичами
- [ ] **Trusted Publishing** — настройка OIDC для автопублики без токена
- [ ] **Пример с кастомным renderer** — показать использование RendererProto
- [ ] **Пример save/load config** — демонстрация сериализации
- [ ] **CHANGELOG.md** — автоматическая генерация при релизе

### Среднесрочные улучшения (v0.5.x)
- [ ] **Tracing support** — интеграция с OpenTelemetry/trace_id, span_id
- [ ] **Фильтры по имени логгера** — возможность фильтровать сообщения по паттерну
- [ ] **Цветовая схема ConsoleRenderer** — кастомизация цветов в dev режиме
- [ ] **Асинхронные файловые обработчики** — для высокой нагрузки
- [ ] **Структурированные исключения** — стандартный формат error в JSON
- [ ] **Метрики логирования** — счётчики сообщений по уровням/логгерам

### Долгосрочные цели (v1.0.0)
- [ ] **Стабильный релиз 1.0.0** — полный API, документация, миграция
- [ ] **Сравнение с аналогами** — benchmark против loguru, structlog
- [ ] **Сниппеты для IDE** — автодополнение для LoggerReg
- [ ] **Плагины/расширения** — система плагинов для процессоров
- [ ] **Grafana/Loki интеграция** — готовый дашборд для мониторинга

## Потенциальные улучшения (в работе)
- [x] **Поддержка Python 3.10+** — реализовано ✅

## Потенциальные улучшения (не реализовано)
- [x] Property-based тестирование для процессоров (hypothesis)
- [x] Добавить benchmarks для оценки производительности
- [ ] Рассмотреть добавление pydantic для валидации конфигурации

## Результаты аудита (2026-04-12)

### Критические проблемы (исправлено)
- [x] **Хардкод `confhub`** — удалён из main.py, тест обновлён
- [x] **Несоответствие версий Python** — classifiers обновлены (3.13, 3.14), ruff target = py313
- [x] **Integration-тесты не в CI** — testpaths изменён на `["tests"]`, CI и pre-commit обновлены
- [x] **ruff exclude для тестов** — убран exclude, CI и pre-commit проверяют tests + examples

### Среднеприоритетные
- [x] Интеграционные тесты используют перехват `sys.stderr` — хрупкий подход → **исправлено: временные файлы**

### Низкоприоритетные
- [x] Рассмотреть убрать `ANN` и `ARG` из ignore ruff — **решено оставить**: mypy strict покрывает src, ANN в тестах избыточен

### Итоги исправлений
- **force параметр**: SetupLogger, InitLoggers, get_logger() принимают force=True
- **add_logger()**: использует incremental dictConfig для уровня/propagate
- **remove_logger()**: полностью очищает из logging.root.manager.loggerDict
- **Python 3.10+**: classifiers, CI matrix (3.10-3.14), ruff/mypy target
- **RendererProto protocol**: кастомные рендереры через renderer параметр
- **save_config/load_config**: сериализация конфигурации в JSON
- **__getattr__ упрощён**: убран мёртвый код, корректная обработка ошибок
- Coverage остался 100% (117 тестов)
- Git история: чистая, никаких следов kitstructlog
- PyPI: опубликован `pylogkit-dev` v0.3.0

## Правила проекта
- Не создавать документацию без запроса
- Дело не в количестве, а в качестве
- Разрабатывать в `dev`, проверять и мержить в `main`
- Всегда синхронизировать изменения
