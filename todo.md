# pylogkit - Todo

## Текущий статус
- Ветка разработки: `dev`
- Версия: `0.2.0`
- Python: `>=3.13`
- Тесты: **109 passed**
- Coverage: **100%** (fail_under = 100)
- Type checking: ✅ mypy strict mode + py.typed + BoundLogger тип
- CI/CD: ✅ GitHub Actions (test + build + build-PR + PyPI publish + pip-audit + ruff format --check)
- Ruff: ✅ проверяет src + tests + examples + benchmarks + format check
- Репозиторий: https://github.com/QuadDarv1ne/pylogkit
- Автор: QuadD4rv1n7 <maksimqwe42@mail.ru>
- PyPI: опубликован `pylogkit-dev` v0.2.0

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

## Потенциальные улучшения (в работе)
- [ ] **Поддержка Python 3.10+** — расширить аудиторию (сейчас только 3.13+)

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
- Переименование: kitstructlog → pylogkit (код, тесты, примеры, CI/CD, документация)
- Удалён скрытый логгер `confhub` (main.py)
- Версии Python согласованы: 3.13+ везде (classifiers, ruff target)
- Integration-тесты запускаются в CI (106 тестов)
- Ruff проверяет src + tests + examples + benchmarks + format check
- CI: ruff check всех файлов, pytest tests, mypy без флагов, pip-audit, ruff format --check
- Pre-commit: запускает все тесты
- Добавлен `py.typed` marker для mypy
- Type hints: `Any` → `BoundLogger` для get_logger() и InitLoggers методов
- Удалён пустой `src/__init__.py`
- Codecov `fail_ci_if_error: true`
- Добавлен build-pr job для проверки сборки в PR
- `context_scope` теперь сохраняет и восстанавливает контекст (не очищает всё)
- Добавлен docstring к `add_caller_details`
- Убран мёртвый путь в ruff per-file-ignores
- Обновлена версия pytest-asyncio
- Исправлен test_logger_level_filtering: реальная проверка фильтрации
- Integration тесты переписаны без лишних noqa
- Coverage остался 100%
- Git история: 1 чистый коммит, никаких следов kitstructlog
- PyPI токен сохранён в ~/.pypirc (QuadD4rv1n7)

## Правила проекта
- Не создавать документацию без запроса
- Дело не в количестве, а в качестве
- Разрабатывать в `dev`, проверять и мержить в `main`
- Всегда синхронизировать изменения
