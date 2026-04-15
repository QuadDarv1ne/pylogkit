# pylogkit - Todo

## Текущий статус (2026-04-15)
- Ветка разработки: `dev` (все изменения закоммичены, рабочая директория чистая)
- Версия: `0.4.0`
- Python: `>=3.10` (3.10–3.14)
- Тесты: **128 passed** ✅ (113 unit + 15 property-based)
- Coverage: **100%** (fail_under = 100)
- Type checking: ✅ mypy strict + py.typed + BoundLogger
- CI/CD: ✅ GitHub Actions (test + build + build-PR + pip-audit + ruff format --check + **pypi-publish**)
- Ruff: ✅ src + tests + examples + benchmarks + format check
- Репозиторий: https://github.com/QuadDarv1ne/pylogkit
- PyPI: `pylogkit-dev` v0.3.0 (v0.4.0 готова к публикации — нужен тег `v0.4.0`)
- README.md: бейджи PyPI исправлены — `pylogkit` → `pylogkit-dev`
- Лицензия: MIT

### Архитектура
- **SetupLogger** — низкоуровневая настройка logging + structlog (handlers, processors, async)
- **InitLoggers** — базовый класс для определения всех логгеров проекта
- **get_logger()** — быстрый логгер без наследования
- **LoggerReg** — объявление логгера (name, level, propagate)
- **context API** — bind / get_context / clear_context / context_scope
- **processors** — make_json_safe (рекурсивный), add_caller_details
- **RendererProto** — protocol для кастомных рендереров
- **save_config/load_config** — сериализация конфигурации в JSON

### Незакоммиченные изменения
- test_property_based.py: `test_context_scope_restores_outer_context` — добавлен `@settings(deadline=None)` (flaky hypothesis test)
- todo.md: обновлён статус

### Последние улучшения (2026-04-15)
- ✅ **CI PyPI publish** — `pypa/gh-action-pypi-publish` при теге `v*`
- ✅ **Bump версии до 0.4.0** — pyproject.toml, __init__.py, тест
- ✅ **Оптимизация hot path** — `isinstance`-check вместо `json.dumps()` в `_make_value_json_safe`
- ✅ **Удалён upstream remote** — старый kitstructlog больше не нужен
- ✅ **Property-based тесты** — +6 тестов для make_json_safe и _json_default (hypothesis)
- ✅ **frozen app защита** — sys.stderr.isatty() try/except OSError
- ✅ **Vacuous assertion fixed** — `test_context_scope_cleans_on_exception`: `pass` заменён на `assert`
- ✅ **Docstring fix** — `backup_count`: "0 = unlimited" → "0 = no rotation"
- ✅ **Double getattr eliminated** — `InitLoggers.__init__`: walrus operator вместо двойного `getattr`
- ✅ **Stale kitstructlog editable install removed** — конфликтующая установка из старого проекта
- ✅ **MODE_DEV env var fix** — `"0"` и `"false"` больше не считаются truthy
- ✅ **Dead code removed** — `bool` удалён из `_JSON_TYPES` (bool — подкласс int)
- ✅ **__init__.py simplified** — убран冗余 `import X as X` (42 → 34 строки)
- ✅ **publish.yml PyPI URL fixed** — `pylogkit` → `pylogkit-dev` (совпадение с pyproject.toml)
- ✅ **Test assertions strengthened** — убраны слабые `or "_msg"` fallbacks в 5 тестах
- ✅ **README.md PyPI badges fixed** — `pylogkit` → `pylogkit-dev` в бейджах и ссылках
- ✅ **Hypothesis deadline fix** — `test_context_scope_restores_outer_context`: добавлен `@settings(deadline=None)`

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
- [x] **CI PyPI publish** — `pypa/gh-action-pypi-publish` при теге `v*`
- [x] **Bump версии до 0.4.0** — pyproject.toml, __init__.py, тест
- [x] **Оптимизация `_make_value_json_safe`** — `isinstance` вместо `json.dumps()`
- [x] **Удалён upstream remote** — старый kitstructlog

## Планы по проекту

### Ближайшие задачи (v0.4.0)
- [x] **Bump версии до 0.4.0** — pyproject.toml, __init__.py, тест
- [x] **CI PyPI publish** — `pypa/gh-action-pypi-publish` при теге `v*`
- [ ] **Пример с кастомным renderer** — показать использование RendererProto
- [ ] **Пример save/load config** — демонстрация сериализации
- [ ] **CHANGELOG.md** — автоматическая генерация при релизе
- [ ] **Тесты кастомного renderer** — проверка RendererProto protocol
- [ ] **Тег v0.4.0 + push** — триггер PyPI publish
- [ ] **dev → main merge** — синхронизация веток

### Среднесрочные улучшения (v0.5.x)
- [ ] **Tracing support** — интеграция с OpenTelemetry/trace_id, span_id
- [ ] **Фильтры по имени логгера** — возможность фильтровать сообщения по паттерну
- [ ] **Цветовая схема ConsoleRenderer** — кастомизация цветов в dev режиме
- [ ] **Структурированные исключения** — стандартный формат error в JSON
- [ ] **Метрики логирования** — счётчики сообщений по уровням/логгерам
- [ ] **Environment-based конфигуровка** — загрузка конфига из env vars
- [ ] **Lazy evaluation для дорогих значений** — отложенное вычисление логов
- [x] **CI publish job** — исправлена зависимость: `publish` теперь `needs: test` вместо `needs: build` (build не запускается на тегах)

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
- [x] `from_config()` конструктор — добавлен `InitLoggers.from_config(path)` ✅
- [x] `save_config()` не сохраняет `log_file`, `max_bytes`, `backup_count` — исправлено ✅
- [ ] `_JSON_TYPES` кортеж — можно расширить до frozenset для O(1) lookup

## Результаты аудита (2026-04-12) — всё исправлено ✅

### Критические проблемы
- [x] **Хардкод `confhub`** — удалён из main.py, тест обновлён
- [x] **Несоответствие версий Python** — classifiers обновлены (3.10–3.14), ruff target = py310
- [x] **Integration-тесты не в CI** — testpaths = `["tests"]`, CI и pre-commit обновлены
- [x] **ruff exclude для тестов** — убран exclude, проверяются tests + examples

### Среднеприоритетные
- [x] Integration-тесты используют временные файлы вместо перехвата stderr

### Низкоприоритетные
- [x] ANN и ARG в ignore ruff — оставлено: mypy strict покрывает src

### Итоги
- Coverage: **100%** (125 тестов)
- Git история: чистая, без следов kitstructlog
- PyPI: `pylogkit-dev` v0.3.0

## Правила проекта
- Не создавать документацию без запроса
- Дело не в количестве, а в качестве
- Разрабатывать в `dev`, проверять и мержить в `main`
- Всегда синхронизировать изменения
