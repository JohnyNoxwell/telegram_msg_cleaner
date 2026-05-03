# TG_CLEANER / TG_MSG_MNGR: архитектурный обзор проекта

Документ собран по текущему состоянию workspace на 2026-05-03.

Источник анализа:
- фактический код в `tg_msg_manager/`, `scripts/`, `tests/`
- текущие docs: `README.md`, `COMMANDS.md`, `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`
- локальная проверка тестов: `python3 -m unittest discover -s tests -q` -> `122 tests`, `OK`

Важно:
- документ описывает текущее рабочее дерево, а не только последнюю зафиксированную версию
- в репозитории есть незакоммиченные изменения, поэтому это описание относится к "живому" состоянию проекта

## 1. Что это за проект

Это консольное приложение для работы с историей Telegram на базе `Telethon`.

Основные задачи проекта:
- инкрементально синхронизировать сообщения цели из чатов Telegram
- вытягивать не только сообщения цели, но и окружающий контекст беседы
- хранить данные локально в `SQLite`
- экспортировать накопленные данные в TXT и AI-friendly JSONL
- удалять собственные сообщения пользователя из групп/каналов
- архивировать личные переписки с медиа-структурой
- поддерживать фоновое обновление через `launchd` на macOS

По сути это не просто "скрипт для удаления сообщений", а локальная data-pipeline/CLI-экосистема вокруг Telegram-истории.

## 2. Масштаб текущего codebase

Приблизительные метрики по текущему состоянию:
- `tg_msg_manager`: `40` Python-файлов, около `10 180` строк
- `tests`: `15` файлов, около `4 013` строк
- `scripts`: `4` файла, около `539` строк

Крупнейшие файлы:
- `tg_msg_manager/services/exporter.py` -> `1417` строк
- `tg_msg_manager/services/context_engine.py` -> `1198` строк
- `tg_msg_manager/services/db_exporter.py` -> `718` строк
- `tg_msg_manager/cli.py` -> `709` строк

Практический вывод: архитектура уже модульная, но часть hot-path логики все еще сосредоточена в нескольких очень крупных сервисах.

## 3. Технологии и стек

Ядро и инфраструктура:
- Python `3.9+`
- `Telethon` как Telegram API client
- `SQLite` как локальное хранилище
- `pydantic` и `pydantic-settings` для конфигурации
- стандартный `asyncio` для асинхронной оркестрации
- `unittest` как тестовый фреймворк
- `ruff` для lint/format

Что здесь сознательно не используется:
- нет ORM
- нет веб-сервера
- нет брокера очередей
- нет внешней БД
- нет dependency injection framework
- нет Click/Typer; CLI собран на стандартном `argparse`

Архитектурно проект опирается на "ручную", но достаточно дисциплинированную слоистую сборку.

## 4. Основные пользовательские сценарии

Проект поддерживает два режима работы:
- прямой CLI через `python3 -m tg_msg_manager.cli ...`
- интерактивное терминальное меню через `run.py` или алиас `tg`

Ключевой функционал:
- `export` -> синк сообщений пользователя из одного чата или из всех релевантных чатов
- `update` -> обновление всех зарегистрированных целей
- `db-export` -> выгрузка накопленной локальной истории в TXT/JSONL
- `export-pm` -> архив личной переписки с медиа-папками
- `clean` -> удаление собственных сообщений из доступных диалогов
- `delete` -> purge локальных данных цели из БД и файловой системы
- `schedule` -> создание `launchd`-задачи для регулярного `update`
- `setup` -> установка shell aliases

Важно различать:
- `delete` удаляет локальные данные, но не Telegram-сообщения
- `clean` удаляет Telegram-сообщения, а затем синхронно чистит локальную БД
- `export`/`update` читают Telegram и пополняют БД
- `db-export` не ходит в Telegram вообще

## 5. Слои архитектуры

Логически проект делится так:

```text
CLI / Terminal UX
    ->
Runtime bootstrap / process lifecycle
    ->
Application services
    ->
Telegram abstraction + Storage abstraction
    ->
Telethon + SQLite + filesystem
```

### 5.1 Presentation / CLI

Файлы:
- `tg_msg_manager/cli.py`
- `tg_msg_manager/cli_io.py`
- `tg_msg_manager/utils/ui.py`
- `tg_msg_manager/i18n.py`

Ответственность слоя:
- парсинг CLI-команд
- запуск интерактивного меню
- ввод пользователя
- рендер прогресса и финальных summary
- переключение языка

Ключевой момент: сервисы больше не печатают прогресс напрямую в терминал. Они эмитят service events, а CLI-слой уже рендерит их.

### 5.2 Runtime / bootstrap

Файлы:
- `tg_msg_manager/core/runtime.py`
- `tg_msg_manager/core/config.py`
- `tg_msg_manager/core/process.py`
- `tg_msg_manager/core/logging.py`
- `tg_msg_manager/core/telemetry.py`
- `tg_msg_manager/core/context.py`

Ответственность:
- сбор runtime-путей и конфигурации
- process lock
- signal handling
- логирование и telemetry
- контекстные переменные для логов и языка

### 5.3 Domain / models

Файлы:
- `tg_msg_manager/core/models/message.py`
- `tg_msg_manager/core/models/sync_report.py`
- `tg_msg_manager/core/models/service_payloads.py`
- `tg_msg_manager/core/models/setup.py`
- `tg_msg_manager/infrastructure/storage/records.py`

Ответственность:
- нормализованная модель сообщения
- typed DTO для payload'ов сервисных событий
- typed DTO для результатов setup/scheduler
- typed read-side records из storage

### 5.4 Telegram adapter

Файлы:
- `tg_msg_manager/core/telegram/interface.py`
- `tg_msg_manager/core/telegram/client.py`
- `tg_msg_manager/core/telegram/throttler.py`

Ответственность:
- изоляция Telethon за абстрактным интерфейсом
- throttling
- `FloodWait` handling
- нормализация Telegram Message -> `MessageData`

### 5.5 Application services

Файлы:
- `tg_msg_manager/services/exporter.py`
- `tg_msg_manager/services/context_engine.py`
- `tg_msg_manager/services/db_exporter.py`
- `tg_msg_manager/services/cleaner.py`
- `tg_msg_manager/services/private_archive.py`
- `tg_msg_manager/services/file_writer.py`
- `tg_msg_manager/services/scheduler.py`
- `tg_msg_manager/services/alias_manager.py`

Это главный "бизнес-слой" проекта.

### 5.6 Storage / infrastructure

Файлы:
- `tg_msg_manager/infrastructure/storage/interface.py`
- `tg_msg_manager/infrastructure/storage/sqlite.py`
- `tg_msg_manager/infrastructure/storage/_sqlite_schema.py`
- `tg_msg_manager/infrastructure/storage/_sqlite_write_path.py`
- `tg_msg_manager/infrastructure/storage/_sqlite_read_path.py`
- `tg_msg_manager/infrastructure/storage/_sqlite_sync_state.py`

Ответственность:
- схема БД
- write path
- read path
- sync state
- миграции
- typed storage contracts

## 6. Runtime-композиция и жизненный цикл процесса

Центральная точка сборки приложения:
- `build_app_runtime()` формирует `AppRuntime`
- `AppRuntime` содержит `Settings`, `AppPaths`, путь к Python-интерпретатору

`AppPaths` вычисляет:
- `config.json`
- `messages.db`
- `.tg_msg_manager.lock`
- `LOGS/`
- `DB_EXPORTS/`
- `PRIVAT_DIALOGS/`
- `PUBLIC_GROUPS/`

Нюанс:
- `PRIVAT_DIALOGS` написано с исторической опечаткой и используется в коде как реальное имя директории

`CLIContext` является composition root для runtime-ресурсов:
- поднимает `ProcessManager`
- открывает `SQLiteStorage`
- по необходимости поднимает `TelethonClientWrapper`
- создает `ExportService`, `CleanerService`, `DBExportService`, `PrivateArchiveService`
- умеет корректно завершать все ресурсы

Поведение по сигналам:
- проект использует file lock, чтобы не запускать несколько копий одновременно
- первый `SIGINT`/`Ctrl+C` инициирует graceful shutdown
- второй сигнал форсирует жесткий выход
- во время прерывания export-потока `CLIContext.emergency_callback()` пытается сделать аварийный JSON-export активной цели

Это важный operational design: приложение ориентировано на длинные прерываемые batch-задачи.

## 7. Конфигурация

Конфиг загружается через `Settings` в `core/config.py`.

Поддерживаются источники:
- init args
- env vars с префиксом `TG_`
- `config.json`
- `.env`

Ключевые поля:
- `api_id`
- `api_hash`
- `session_name`
- `db_path`
- `account_name`
- `whitelist_chats`
- `include_chats`
- `chats_to_search_user_msgs`
- `max_rps`
- `log_level`
- `lang`

Подходы:
- Pydantic-валидация
- нормализация ID-значений в `int` или `str`
- поддержка legacy aliases для полей (`exclude_chats` -> `whitelist_chats`, `language`/`ui_language` -> `lang`)

Нюанс:
- `config.example.json` устарел и не соответствует текущей модели `Settings`
- в example-конфиге есть поля вроде `dry_run`, `delete_media`, `batch_size`, `default_export_chats`, которых в актуальном `Settings` нет
- это важно для внешнего анализа: docs по конфигу частично исторические, а не строго отражающие runtime

## 8. Модель данных

Базовая доменная сущность: `MessageData`.

Поля:
- `message_id`
- `chat_id`
- `user_id`
- `author_name`
- `timestamp`
- `text`
- `media_type`
- `reply_to_id`
- `fwd_from_id`
- `context_group_id`
- `raw_payload`
- `is_service`
- `media_ref`

Инварианты:
- уникальность сообщения определяется парой `(chat_id, message_id)`
- `payload_hash` вычисляется детерминированно по полезной нагрузке
- `raw_payload` хранится как нормализованный Telethon-слепок

Это очень важное архитектурное решение:
- проект хранит и "плоские" поля, и сырой payload
- при этом для AI-export по умолчанию не тащит весь raw наружу, а отдает компактный профиль

## 9. Схема SQLite

Таблицы:

| Таблица | Назначение |
| --- | --- |
| `messages` | основное хранилище сообщений |
| `users` | справочник пользователей |
| `chats` | справочник чатов |
| `message_context_links` | таблица связей контекста |
| `message_target_links` | ключевая таблица атрибуции сообщений конкретным целям |
| `sync_state` | head-состояние чата |
| `retry_queue` | заготовка под retry-механику |
| `sync_targets` | зарегистрированные цели синка и их персональные чекпоинты |

Ключевая архитектурная идея: target attribution

Проект разделяет:
- физическое сообщение в `messages`
- логическую принадлежность сообщения конкретной цели через `message_target_links`

Это позволяет:
- нескольким целям ссылаться на один и тот же context message
- не дублировать сообщения в БД
- удалять orphan-сообщения только когда на них больше никто не ссылается

Именно эта схема делает возможным "smart purge" и нормальный контекстный экспорт.

### 9.1 Что хранится в `sync_targets`

Для каждой пары `(user_id, chat_id)` хранятся:
- `last_msg_id` -> head-checkpoint
- `tail_msg_id` -> tail-checkpoint
- `is_complete` -> история чата для этой цели полностью пройдена или нет
- `deep_mode`
- `recursive_depth`
- `added_at`
- `last_sync_at`
- `author_name`

Нюанс:
- whole-chat targets кодируются как `user_id == chat_id`
- это не отдельный тип сущности, а специальная интерпретация той же схемы

### 9.2 Индексы

Есть индексы на:
- `(user_id, chat_id, timestamp)`
- `message_id`
- `(chat_id, reply_to_id)`
- `target_user_id`
- `(chat_id, target_user_id, message_id)`
- `context_group_id`

То есть storage оптимизирован под:
- поиск истории по цели
- связь reply-chain
- выборки по target attribution
- контекстные cluster/group операции

## 10. Storage-подход

`SQLiteStorage` разбит mixin-архитектурой:
- schema
- write path
- read path
- sync state

Это один из главных рефакторингов проекта.

Write discipline:
- один shared write-connection
- `threading.Lock` вокруг транзакции записи
- WAL mode
- фоновой writer через `asyncio.Queue`

Read discipline:
- отдельные read-connections на запрос

Практический смысл:
- запись максимально централизована и детерминирована
- чтение не блокирует event loop тяжелыми транзакциями записи так сильно, как при одном соединении на все

Нюансы:
- это все еще single-process local SQLite system, а не распределенное хранилище
- write path остается потенциальным bottleneck для очень тяжелых deep-export проходов

## 11. Ключевые сервисы

### 11.1 `ExportService`

Это самый важный сервис проекта.

Что делает:
- синхронизирует один чат/цель
- сканирует несколько диалогов для одного пользователя
- обновляет все tracked targets
- управляет checkpoint'ами и прогрессом

Ключевые методы:
- `sync_chat()`
- `sync_all_dialogs_for_user()`
- `sync_all_outdated()`
- `sync_all_tracked()`

Архитектурная роль:
- orchestration layer между Telegram client, storage и DeepModeEngine

### 11.2 `DeepModeEngine`

Это под-сервис контекстного экспорта.

Что делает:
- строит context clusters вокруг target messages
- предпочитает структурные связи Telegram вместо наивного "окна по message_id"
- умеет использовать локально уже сохраненные сообщения перед live-запросами

По факту это отдельный graph/context engine поверх Telegram-хронологии.

### 11.3 `DBExportService`

Что делает:
- выгружает накопленную историю из SQLite
- пишет TXT или JSONL
- умеет пропускать повторный экспорт, если fingerprint не изменился
- умеет потоково писать AI-friendly JSONL без полной материализации всей истории в память

### 11.4 `CleanerService`

Что делает:
- ищет собственные сообщения пользователя
- удаляет их из Telegram
- синхронно убирает локальные записи из БД
- поддерживает whitelist/include logic
- умеет purge локальных данных конкретной цели

### 11.5 `PrivateArchiveService`

Что делает:
- архивирует личный диалог
- сохраняет текстовый лог
- скачивает медиа в структуру папок
- привязывает сообщения к target attribution

### 11.6 `FileRotateWriter`

Что делает:
- пишет большие экспорты по частям
- поддерживает stateful resume
- переносит файловый I/O в `asyncio.to_thread()`

### 11.7 `Scheduler` и `AliasManager`

Роль:
- не domain-логика, а эксплуатационная обвязка
- планировщик создает `launchd` plist под команду `update`
- alias manager ставит shell aliases для удобного запуска

## 12. Главные алгоритмы и подходы

### 12.1 Инкрементальный sync по схеме HEAD/TAIL

Это центральный алгоритм проекта.

Идея:
- `HEAD` отвечает за новые сообщения сверху истории
- `TAIL` отвечает за старую непройденную историю снизу

Преимущества:
- можно быстро догружать новые сообщения без полного перескана
- можно возобновлять старый прерванный проход
- можно отделить "оперативное обновление" от "докачки хвоста"

Для каждой цели отдельно отслеживаются:
- верхний checkpoint
- нижний checkpoint
- флаг полноты истории

### 12.2 Разбиение истории на диапазоны

`ExportService` умеет делить историю на `_ScanRange`.

Поведение:
- при первом полном проходе история режется на несколько descending tail-ranges
- при update может быть только HEAD-range
- при resume добавляется HEAD-range плюс один или несколько TAIL-range

Нюанс:
- логика tail-checkpoint намеренно продвигается только по верхнему непрерывному префиксу пройденных диапазонов
- это защищает от "ложного завершения", когда нижние куски уже обработаны, а середина еще пропущена

### 12.3 Deep Mode: структурный контекст вместо тупого окна

Deep mode работает многоступенчато:
- сначала берутся target messages
- затем ищутся parent messages по `reply_to_id`
- затем ищутся сообщения, отвечающие на target и на уже найденные структурные сообщения
- затем учитывается `topic/thread`-семантика
- только на глубине 3 подключается time-based fallback

Почему это важно:
- проект осознанно старается не собирать шумный контекст просто по соседним ID
- приоритет у reply-chain, thread/topic и контекстных связей

### 12.4 Локальный cache-first подход для контекста

Перед live-fetch:
- parent messages сначала ищутся в SQLite
- диапазоны сообщений сначала собираются из локальной БД
- потом live-запросами дозаполняются только missing pieces

Есть несколько стратегий дозагрузки:
- selective fill по отдельным `message_id`
- compact fill по небольшим поддиапазонам
- full scan по диапазону

То есть контекстный движок адаптивно выбирает наименее дорогую стратегию.

### 12.5 Shared head prefetch для bulk update

При `update` сервис умеет:
- сгруппировать несколько целей в одном чате
- один раз вытащить общий верхний срез истории чата
- переиспользовать его для нескольких target users

Это уменьшает число однотипных Telegram-запросов.

Это одна из самых сильных оптимизаций проекта на уровне orchestration.

### 12.6 Deduplication

Используются два уровня дедупликации:
- PK `(chat_id, message_id)` -> не допускает дубль одного и того же Telegram message
- `payload_hash` -> позволяет понять, изменилась ли полезная нагрузка сообщения

Если hash не менялся:
- запись сообщения можно не перезаписывать
- но target link при этом все равно может быть добавлен отдельно

### 12.7 Target attribution как reference model

Контекстные сообщения могут быть общими для нескольких целей.

Поэтому:
- `messages` хранит физическую сущность
- `message_target_links` хранит "кому это сообщение нужно"

Это делает экспорт и очистку гораздо точнее, чем модель "у каждой цели свой отдельный JSONL".

### 12.8 Background write queue

Запись в SQLite построена через:
- `asyncio.Queue`
- background writer
- пакетные коммиты до `500` items

Идея:
- не флашить БД после каждого сообщения
- дать sync-пайплайну работать батчами
- снизить write amplification

### 12.9 FloodWait и throttling

Telegram adapter реализует:
- token bucket throttler (`RateThrottler`)
- adaptive rate slow-down после `FloodWait`
- retry после sleep

Плюс:
- `iter_messages()` умеет fallback на локальную фильтрацию по `sender_id`, если Telethon не смог резолвить `from_user`

### 12.10 Streaming DB export

AI JSON export умеет:
- использовать summary + iterator-path
- не загружать все строки пользователя в память, если storage поддерживает streaming

Это уже не просто "собрать список и написать в файл", а вполне зрелый streaming export path.

### 12.11 Fingerprint-based export skip

`DBExportService` хранит manifest в `.export_state/`.

Fingerprint включает:
- user id
- count сообщений
- first/last message id
- first/last timestamp
- формат
- профиль JSON

Если fingerprint не изменился и все части экспорта на месте:
- новый export не пересобирается

### 12.12 Stateful file rotation

`FileRotateWriter`:
- режет большие экспорты на `part2`, `part3`, ...
- хранит state отдельно в `.writer_state/`
- умеет продолжить запись без потери нумерации частей

Это особенно важно для длинных TXT/JSONL выгрузок.

## 13. Разделение по пакетам и фактическая ответственность

### `core/`

Содержит то, что можно считать системным каркасом:
- runtime
- config
- logging
- process/signal
- telemetry
- telegram adapter abstraction
- typed payloads/models

### `services/`

Содержит application use cases:
- экспорт
- контекстный движок
- экспорт из БД
- очистка
- архив лички
- файловый writer
- scheduler
- alias setup

### `infrastructure/storage/`

Содержит реальную persistence implementation и ее contracts.

### `cli.py` + `cli_io.py`

Содержат composition root + presentation glue.

Это хороший признак зрелости: orchestration и rendering уже разведены.

## 14. Наблюдаемость и операционная диагностика

В проекте есть два контура observability:

Логи:
- human formatter в консоль
- JSON formatter в `LOGS/app_YYYYMMDD.log`

Telemetry:
- counters
- duration metrics
- flood-wait accumulation
- write/flush/export/sync stage timings
- финальный dump в `LOGS/telemetry_latest.json`

Дополнительно используются `ContextVar` для:
- `chat_id`
- `trace_id`
- языка интерфейса

Это значит, что проект уже мыслит себя как долгоживущий batch-tool, а не одноразовый скрипт.

## 15. CLI, UX и i18n

Особенности интерфейса:
- градиентный ANSI banner
- raw terminal input
- `ESC` как back/cancel
- интерактивное меню
- event-driven progress rendering
- локализация `ru/en`

Нюанс:
- язык хранится не в module-global переменной, а в `ContextVar`
- это защищает от гонок при параллельных задачах и делает CLI более корректным в async-сценариях

Еще один важный UX-факт:
- если CLI запускается без subcommand вне TTY, он не пытается открыть меню, а просто печатает help

## 16. Экспортные форматы

### TXT

TXT-экспорт:
- ориентирован на чтение человеком
- группирует сообщения по датам и авторам
- умеет вставлять короткий reply-context

### JSONL

JSONL-экспорт по умолчанию ориентирован на AI/анализ:
- компактный профиль
- нет полного `raw_payload`
- сохраняются `reply_to_id`, `reply_to_top_id`, `forum_topic`, `context_group_id`, `edit_date`, реакции и другие graph-relevant поля

Нюанс:
- в коде есть внутренний `json_profile="full"`, но стандартный CLI путь использует compact AI profile

## 17. PM archive

`export-pm` устроен отдельно от group export.

Что делает:
- создает папку вида `Name_ID`
- пишет `chat_log.txt`
- складывает медиа в поддиректории:
  - `photos`
  - `videos`
  - `voices`
  - `documents`

Нюансы:
- архив лички не является replayable Telegram-backup
- он ближе к "исследовательскому/читаемому" архиву
- в storage такой архив тоже регистрируется как target и обновляет sync timestamp

## 18. Cleaner / удаление сообщений

`CleanerService` делает live-cleanup через Telegram API.

Подходы безопасности:
- whitelist
- include list
- dry-run по умолчанию
- пропуск service messages
- удаление из локальной БД только после live-delete

Нюансы:
- whitelist умеет сопоставлять разные числовые варианты chat id, включая `-100...`
- CLI-команда `clean` не имеет отдельного флага для PM-cleanup
- включение PM-cleanup доступно из интерактивного меню, а не из стандартного subcommand surface

## 19. Scheduler и shell integration

### Scheduler

`schedule`:
- пишет `~/Library/LaunchAgents/com.tg-msg-manager.update.plist`
- регистрирует `launchctl load`
- запускает именно `python -m tg_msg_manager.cli update`

То есть scheduler заточен под регулярный `update`, а не под `clean`.

### Aliases

AliasManager ставит:
- `tg`
- `tgr`
- `tgd`
- `tge`
- `tgu`
- `tgpm`

Unix-путь:
- редактирует `.zshrc` или `.bashrc`

Windows-путь:
- генерирует `.bat` wrappers

## 20. Скрипты вокруг основного приложения

Полезные и актуальные:
- `scripts/reset_and_seed_targets.py` -> очистка локального состояния и seed `sync_targets`
- `scripts/export_user_context_from_db.py` -> отдельная ad-hoc выгрузка контекстных сообщений из БД
- `scripts/cleanup_exports.py` -> утилита для чистки legacy export-артефактов

Нюанс:
- `scripts/migrate_to_db.py` выглядит legacy-скриптом и, судя по импортам, не соответствует текущей структуре пакета
- для внешнего анализа его лучше считать историческим артефактом, а не надежным рабочим инструментом

## 21. Тесты и качество

Покрытые области:
- storage CRUD и typed records
- sync-system и tracked update
- exporter/context behavior
- file writer
- config
- CLI wiring
- process lock и signals
- observability
- telegram adapter/throttler
- scheduler
- alias manager
- i18n

Фактический статус на момент анализа:
- `122` теста проходят

Но важно понимать характер покрытия:
- это в основном unit и mock-heavy tests
- реальных end-to-end прогонов против Telegram немного
- проект хорошо покрыт на уровне контрактов и orchestration semantics, но не как full integration system

## 22. Ключевые сильные стороны архитектуры

- Хорошо выраженная слоистость: CLI, core, services, infrastructure.
- Четкая нормализация данных в SQLite.
- Продуманная target-attribution модель вместо дублирования контекста.
- Реальный incremental sync, а не "каждый раз полный экспорт".
- Контекстный deep mode опирается на структуру Telegram, а не только на соседние ID.
- Event-driven граница между сервисами и UI.
- Streaming DB export path.
- Telemetry и structured logging уже встроены.
- Runtime bootstrap и path injection уже централизованы.

## 23. Ограничения, нюансы и потенциальные узкие места

### 23.1 Крупные hot-path файлы

Главные зоны сложности:
- `services/exporter.py`
- `services/context_engine.py`
- `services/db_exporter.py`
- `cli.py`

Хотя они уже декомпозированы лучше, чем раньше, это все равно самые вероятные кандидаты на дальнейшее дробление.

### 23.2 SQLite write path остается центральным bottleneck

Сейчас все упирается в:
- один процесс
- один shared write connection
- один background writer
- локальный WAL SQLite

Для локального single-user инструмента это нормально.
Для очень больших deep-export сценариев это будет масштабный предел.

### 23.3 `retry_queue` пока больше заготовка, чем активная подсистема

Схема и storage API для retry есть:
- `enqueue_retry_task`
- `get_retry_tasks`
- `remove_retry_task`

Но в основном рабочем приложении активного orchestration-цикла поверх этой очереди сейчас нет.

То есть механизм повторов скорее недостроен, чем полноценно эксплуатируется.

### 23.4 `message_context_links` выглядит недоиспользованной сущностью

Таблица создается и пополняется, но основной deep/context hot path в реальности опирается прежде всего на:
- `reply_to_id` в `messages`
- `context_group_id`
- `message_target_links`

Это похоже на исторический слой нормализации, который сейчас не является центральным источником истины для контекстного движка.

### 23.5 Конфиг и часть текстов исторически дрейфовали

Самый явный пример:
- `config.example.json` не соответствует актуальному `Settings`
- некоторые i18n-строки все еще ссылаются на поле `dry_run` в `config.json`, которого в текущей модели настроек нет

Для внешнего аналитика это важно: часть operational docs уже выровнена, но некоторые конфигурационные артефакты все еще legacy.

### 23.6 Scheduler привязан к macOS

`schedule` в текущем виде:
- ориентирован на `launchd`
- не является кроссплатформенным orchestration layer

### 23.7 Single-account design

Система строится вокруг одной активной Telegram-сессии.

Мультиаккаунтность:
- упоминается в roadmap
- в текущем runtime не является встроенным first-class capability

### 23.8 `clean` и `export-pm` функционально отдельны от общего sync-пайплайна

Они хорошо интегрированы в runtime и storage, но:
- логика удаления живет отдельно
- PM archive имеет собственный жизненный цикл и собственный формат результата

Это нормально, но это не "единый универсальный pipeline".

### 23.9 Типовая аккуратность выше, чем абсолютная типовая строгость

В проекте много typed DTO и record-моделей, но встречается type drift.
Пример:
- `UserExportRow.context_group_id` типизирован как `Optional[int]`, хотя реально cluster ids могут быть строковыми UUID-подобными значениями

Это не ломает рантайм, но для дальнейшей эволюции типовой дисциплины это зона внимания.

## 24. Что особенно важно знать другой модели перед анализом развития

Если внешняя модель будет оценивать дальнейшую эволюцию проекта, ей важно понимать:

1. Это не CRUD-приложение, а локальный асинхронный pipeline вокруг Telegram history.
2. Самая важная бизнес-идея проекта не cleanup, а target-attributed context-aware sync.
3. Главный актив архитектуры — модель `messages` + `message_target_links` + `sync_targets`.
4. Главные ограничения роста — сложность `ExportService`/`DeepModeEngine` и single-node SQLite write path.
5. Проект уже довольно зрелый в части операционной дисциплины: lock, graceful shutdown, telemetry, manifest-based exports, resume.
6. Некоторые legacy-артефакты еще присутствуют: устаревший `config.example.json`, старые scripts, недоиспользуемые таблицы/queue hooks.

## 25. Рекомендуемый порядок чтения кода для внешнего анализа

Если другая модель будет читать исходники, лучший маршрут такой:

1. `README.md`
2. `tg_msg_manager/cli.py`
3. `tg_msg_manager/core/runtime.py`
4. `tg_msg_manager/core/config.py`
5. `tg_msg_manager/services/exporter.py`
6. `tg_msg_manager/services/context_engine.py`
7. `tg_msg_manager/infrastructure/storage/sqlite.py`
8. `tg_msg_manager/infrastructure/storage/_sqlite_schema.py`
9. `tg_msg_manager/infrastructure/storage/_sqlite_write_path.py`
10. `tg_msg_manager/infrastructure/storage/_sqlite_read_path.py`
11. `tg_msg_manager/services/db_exporter.py`
12. `tg_msg_manager/services/cleaner.py`
13. `tg_msg_manager/services/private_archive.py`
14. `tests/test_sync_system.py`
15. `tests/test_storage_sqlite.py`
16. `CHANGELOG.md`
17. `TODO.md`

Такой порядок даст:
- сначала картину продукта
- потом composition root
- затем основной sync-движок
- потом persistence и side-flows
- в конце operational history и рефакторинговый контекст

## 26. Короткий итог

Текущая версия проекта — это локальная асинхронная Telegram data platform в миниатюре:
- со своим runtime bootstrap
- со слоистой архитектурой
- с нормализованным SQLite storage
- с target-aware incremental sync
- с отдельным deep context engine
- с AI-friendly export-пайплайном
- с observability и эксплуатационной дисциплиной выше среднего для CLI-утилиты

Главная архитектурная ценность проекта:
- не в UI
- не в alias/scheduler
- даже не в одном только cleanup

А в том, что он уже умеет аккуратно и инкрементально собирать Telegram-историю как локальный граф сообщений с переиспользуемым контекстом и персональными sync-checkpoint'ами.
