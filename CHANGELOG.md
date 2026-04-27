All notable changes to this project will be documented in this file in both English and Russian.
Все значимые изменения проекта фиксируются в этом файле на английском и русском языках.

## [4.2.5] - 2026-04-27

### Changed (EN)
- **Docs/CLI Alignment**: Synchronized `README.md`, `COMMANDS.md`, and in-app copy with the current menu layout, alias set, scheduler scope, export format semantics, and neutral sample IDs.
- **Service Rendering Boundary**: Moved user-facing progress/status rendering for export, cleanup, and PM archive flows behind a lightweight service-event sink so `services/` no longer own direct terminal output.
- **Storage Contracts**: Split the monolithic storage typing into narrower service-oriented protocols while preserving `SQLiteStorage` as the compatible umbrella backend.
- **Shared Quality Gates**: Added repo-level `make lint`, `make format-check`, `make test`, and `make verify` workflows backed by `ruff`, and wired CI to the same `make verify` entrypoint.

### Fixed (EN)
- Fixed CLI `db-export` semantics so `db-export --user-id <ID>` writes TXT again, while `--json` explicitly opts into the compact JSONL export.
- Fixed CLI `export --json` semantics so the final post-sync export format now matches the flag: plain `export` produces TXT, `export --json` produces JSONL.
- Fixed no-subcommand CLI usage outside an interactive TTY to print parser help instead of crashing on raw terminal input handling.
- Removed dead public flags that did not affect runtime behavior (`update --force-resync`, `clean --user-id`) so the documented CLI surface matches the real one.

### Изменения (RU)
- **Выравнивание docs и CLI**: `README.md`, `COMMANDS.md` и in-app тексты синхронизированы с текущей структурой меню, набором алиасов, реальным scope планировщика, семантикой форматов экспорта и нейтральными sample ID.
- **Граница рендеринга сервисов**: Пользовательский вывод прогресса/статуса для export, cleanup и PM archive переведён на лёгкий service-event sink, так что слой `services/` больше не рисует терминал напрямую.
- **Контракты storage**: Монолитная типизация storage разделена на более узкие service-oriented протоколы, при этом `SQLiteStorage` сохранён как совместимый umbrella backend.
- **Общие quality gates**: Добавлены единые `make lint`, `make format-check`, `make test` и `make verify` на базе `ruff`, а CI переведён на тот же entrypoint `make verify`.

### Исправления (RU)
- Исправлена семантика CLI `db-export`: `db-export --user-id <ID>` снова пишет TXT, а `--json` теперь явно включает компактный JSONL-экспорт.
- Исправлена семантика CLI `export --json`: итоговый post-sync export теперь реально зависит от флага — обычный `export` пишет TXT, `export --json` пишет JSONL.
- Исправлен запуск CLI без subcommand вне интерактивного TTY: теперь выводится parser help, а не происходит падение на raw-input обработке.
- Убраны мёртвые публичные флаги, не влияющие на runtime (`update --force-resync`, `clean --user-id`), чтобы документированный CLI surface совпадал с реальным.

## [4.2.4] - 2026-04-26

### Changed (EN)
- **Update UX Notes**: Documented that `update/tgu` can spend time in a shared head prefetch phase before visible per-target progress appears, especially after a large interrupted export.
- **Target Status Visibility**: Primary target listings now show explicit `Done` / `Incomplete` state instead of relying only on message counters.

### Fixed (EN)
- Fixed sync freshness semantics so `register_target()`, `update_last_msg_id()`, and `update_sync_tail()` no longer refresh `last_sync_at` during partial progress or startup bookkeeping.
- Fixed interrupted multi-range history resume so tail checkpoints only advance across the highest contiguous completed prefix, preventing broken `tail_msg_id = 0` / `is_complete = 0` states after `Ctrl+C`.
- Fixed terminal history resume so targets that legitimately reach the bottom (`tail_msg_id <= 1`) can be finalized on the next pass instead of hanging forever as incomplete.
- Fixed emergency AI JSON export after `SIGINT` when the fast row-export path skipped an unchanged file via manifest reuse.

### Изменения (RU)
- **Примечание по UX обновления**: Задокументировано, что `update/tgu` может тратить заметное время на фазу shared head prefetch до появления видимого прогресса по целям, особенно после большого прерванного экспорта.
- **Видимость статуса целей**: В списках primary targets теперь явно показывается состояние `Готово` / `Не докачано`, а не только счётчики сообщений.

### Исправления (RU)
- Исправлена семантика freshness: `register_target()`, `update_last_msg_id()` и `update_sync_tail()` больше не обновляют `last_sync_at` во время частичного прогресса или стартового bookkeeping.
- Исправлена докачка многодиапазонной истории после прерывания: tail-checkpoint теперь двигается только по верхнему непрерывному префиксу реально пройденных диапазонов, что убирает битые состояния вида `tail_msg_id = 0` при `is_complete = 0` после `Ctrl+C`.
- Исправлена финализация терминального хвоста истории: цели, которые реально дошли до дна (`tail_msg_id <= 1`), теперь могут закрываться на следующем проходе, а не висеть бесконечно в incomplete-state.
- Исправлен emergency AI JSON export после `SIGINT`, когда fast row-export path переиспользовал manifest и падал на unchanged-файле.

## [4.2.3] - 2026-04-25

### Changed (EN)
- **Default Deep Depth**: Deep exports now default to depth `2`, which keeps structural reply/topic context while avoiding the noisier time-based fallback unless depth `3` is requested explicitly.
- **Safe Sync/Export Acceleration**: Optimized the local hot path without increasing Telegram request pressure: deferred SQLite flushes out of per-batch sync loops, replaced per-message target-link checks with batched lookups, batched parent fetches from storage in Deep Mode, and buffered DB export file writes.
- **Runtime Telemetry**: Added stage-level timings and counters for Telegram I/O, Deep Mode expansion, SQLite queue/flush/commit work, and DB export writing. The latest summary is now written to `LOGS/telemetry_latest.json` and emitted as structured log events during bulk updates.

### Fixed (EN)
- Fixed mixed timestamp handling between live Telegram messages and SQLite-loaded messages by normalizing deserialization to UTC-aware datetimes, preventing `offset-naive` vs `offset-aware` comparison errors during deep scans.
- Fixed AI JSONL key ordering so `edit_date` is emitted first when present, improving manual inspection of edited messages.

### Added (EN)
- Added `scripts/reset_and_seed_targets.py` to wipe local DB/export artifacts and reseed `sync_targets` from `DB_TARGETS.txt` before a full fresh `update`.

### Изменения (RU)
- **Глубина Deep Mode по умолчанию**: Глубокий экспорт теперь по умолчанию использует глубину `2`, сохраняя структурный контекст по reply/topic без лишнего time-fallback, если явно не запрошена глубина `3`.
- **Безопасное ускорение sync/export**: Локальный hot path ускорен без роста давления на Telegram API: `flush` вынесен из каждого batch-цикла, проверка target-link переведена на пакетные запросы, parent lookup в Deep Mode стал пакетным, а запись DB-export файлов буферизована.
- **Runtime-метрики**: Добавлены тайминги и счётчики по стадиям Telegram I/O, расширения Deep Mode, SQLite queue/flush/commit и записи DB export. Последняя сводка теперь сохраняется в `LOGS/telemetry_latest.json` и логируется как structured events во время массового `update`.

### Исправления (RU)
- Исправлена обработка смешанных timestamp между live-сообщениями Telegram и сообщениями, загруженными из SQLite: десериализация нормализована в UTC-aware `datetime`, что убирает ошибку сравнения `offset-naive` и `offset-aware` дат в deep scan.
- Исправлен порядок ключей в AI JSONL: при наличии `edit_date` теперь выводится первым, чтобы edited messages было проще читать глазами.

### Добавлено (RU)
- Добавлен `scripts/reset_and_seed_targets.py` для полной очистки локальной БД/экспортов и повторного заполнения `sync_targets` из `DB_TARGETS.txt` перед полным новым `update`.

## [4.2.2] - 2026-04-25

### Changed (EN)
- **Deep Mode Context Selection**: Reworked Deep Mode to prefer structural Telegram links (`reply_to_id`, reply chains, topic metadata) over loose message-id proximity, which sharply reduces unrelated context noise.
- **AI-Optimized DB Export**: `db-export --json` now emits a compact AI-oriented JSONL profile by default. The export keeps graph-relevant fields such as reply links, topic/thread metadata, edit timestamps, and cluster identifiers while dropping bulky raw Telethon payloads.
- **Writer State Location**: Export rotation state files are now stored under `DB_EXPORTS/.writer_state/` instead of cluttering the export directory root, with legacy state files migrated lazily.

### Fixed (EN)
- Fixed DB export naming so the filename prefix falls back to the target's real `author_name` from messages when the normalized `users` record is empty, instead of defaulting to raw numeric IDs.

### Изменения (RU)
- **Выбор контекста в Deep Mode**: Deep Mode переработан так, чтобы опираться на структурные Telegram-связи (`reply_to_id`, reply-chain, metadata topic/thread), а не на рыхлую близость по `message_id`, что заметно уменьшает шум в контексте.
- **AI-оптимизированный DB Export**: `db-export --json` теперь по умолчанию пишет компактный AI-ориентированный JSONL-профиль. Экспорт сохраняет поля, важные для графового анализа: reply-связи, metadata topic/thread, `edit_date` и cluster identifiers, но убирает тяжёлый raw Telethon payload.
- **Новый путь для writer state**: Состояние ротации экспорта теперь хранится в `DB_EXPORTS/.writer_state/`, а не засоряет корень каталога выгрузки; старые state-файлы лениво мигрируются.

### Исправления (RU)
- Исправлен нейминг DB-export файлов: если нормализованная запись в `users` пуста, префикс имени файла теперь берётся из реального `author_name` в сообщениях, а не скатывается к числовому ID.

## [4.2.1] - 2026-04-25

### Fixed (EN)
- Fixed `update` so it synchronizes every tracked primary target instead of only the currently outdated subset.
- Fixed whole-chat target handling during bulk update runs: targets with `user_id == chat_id` are now synchronized as full-chat targets instead of being misrouted as sender-filtered exports.

### Исправления (RU)
- Исправлена команда `update`: теперь она проходит по всем tracked primary targets, а не только по текущему устаревшему подмножеству.
- Исправлена обработка full-chat targets при массовом обновлении: цели с `user_id == chat_id` теперь синхронизируются как целый чат, а не ошибочно как экспорт с фильтром по отправителю.

## [4.2.0] - 2026-04-25

### Changed (EN)
- **SQLite Storage Refactor**: Split the storage layer into schema, write-path, read-path, and sync-state modules while preserving the public `SQLiteStorage` API.
- **Connection Discipline**: Centralized writes behind a locked shared transaction and moved read queries to dedicated read connections for more predictable SQLite usage.
- **Deep Mode Write Path**: Batched clustered/context message persistence to reduce write amplification during deep exports.
- **Export Semantics**: Clarified `--limit` behavior so it caps work inside a single `sync_chat` instead of multiplying across parallel workers.
- **TXT Rotation Resume**: Added sidecar writer state so text exports resume cleanly across runs without losing part counters.
- **Project Operations**: Added a minimal GitHub Actions CI workflow, local verification commands, and explicit known limitations in the docs.

### Fixed (EN)
- Fixed sync target freshness detection so old targets are not re-scanned forever after successful sync.
- Fixed target checkpoint corruption where context messages could advance another user's `last_msg_id`.
- Fixed cross-chat Deep Mode collisions by scoping processed message tracking to `(chat_id, message_id)`.
- Fixed `get_messages` FloodWait retries to preserve `limit`.
- Fixed PM archive persistence so archived PM messages are attributed to the target and refresh sync timestamps.
- Fixed CLI `delete` initialization so purge flows work even without a live Telegram client.
- Fixed orphan `message_target_links` cleanup when deleting messages from storage.
- Fixed signal handling tests so the full test suite no longer kills itself with a real `SIGINT`.

### Изменения (RU)
- **Рефактор SQLite Storage**: Хранилище разделено на модули schema, write-path, read-path и sync-state без изменения публичного API `SQLiteStorage`.
- **Дисциплина соединений**: Все записи централизованы через общий lock и shared transaction, а чтение переведено на отдельные read connections.
- **Deep Mode Write Path**: Сохранение кластеров и контекста переведено на пакетные записи, чтобы уменьшить write amplification при глубоких экспортах.
- **Семантика экспорта**: Поведение `--limit` уточнено: теперь ограничение действует в рамках одного `sync_chat`, а не умножается на число параллельных воркеров.
- **Resume для TXT-ротации**: Добавлено sidecar-состояние writer'а, чтобы текстовый экспорт корректно продолжался между запусками.
- **Операционная часть проекта**: Добавлены минимальный GitHub Actions CI, команды локальной проверки и раздел с known limitations в документации.

### Исправления (RU)
- Исправлено определение устаревших целей: старые targets больше не пересканируются бесконечно после успешной синхронизации.
- Исправлена порча checkpoint'ов, при которой контекстные сообщения могли продвигать `last_msg_id` другого пользователя.
- Исправлены cross-chat коллизии в Deep Mode: tracking обработанных сообщений теперь использует пару `(chat_id, message_id)`.
- Исправлены ретраи `get_messages` после FloodWait: теперь сохраняется `limit`.
- Исправлена запись `export-pm`: сообщения лички теперь корректно атрибутируются цели и обновляют sync timestamp.
- Исправлена инициализация CLI-команды `delete`, чтобы purge-сценарии работали без live Telegram client.
- Исправлена очистка orphan `message_target_links` при удалении сообщений из storage.
- Исправлены signal tests: полный test suite больше не убивает сам себя реальным `SIGINT`.

## [4.1.0] - 2026-04-21

### Changed (EN)
- **Enhanced CLI UX**: Redesigned user selection lists with better formatting: `author_name (ID) | Group Name`.
- **Interactive Sync Controls**: Added real-time prompts for Deep Mode and Recursive Depth in the main export menu.
- **Improved Progress Reporting**: Implemented a live counter showing the number of messages exported and the current Message ID being scanned.
- **Chat-like TXT Export**: Completely redesigned the plain text output with message grouping, date headers, and reply quotes for better readability.
- **Metadata Integrity**: Added explicit chat metadata tracking (`upsert_chat`) and fixed name mix-ups in the storage layer.
- **Infrastructure**: Optimized `.gitignore` for better protection of session and database artifacts.
- **Reliability & Performance**: 
  - Fixed a critical issue where emergency JSON exports were bypassed on Ctrl+C by switching to async-native signal handling.
  - Implemented 'Cached Skip' optimization: synchronized scans now skip context extraction for already-processed messages, drastically improving resume speed.
  - Resolved `TypeError` in the global update service and missing type imports.

### Изменения (RU)
- **Улучшенный интерфейс CLI**: Переработаны списки выбора пользователей: теперь отображается `Имя автора (ID) | Название группы`.
- **Интерактивное управление синхронизацией**: Добавлен запрос параметров Deep Mode и глубины рекурсии при запуске экспорта.
- **Улучшенная индикация прогресса**: Добавлен живой счетчик выгруженных сообщений и текущего ID сканируемого сообщения.
- **TXT-экспорт в стиле чата**: Полностью изменен формат текстовых файлов — теперь сообщения группируются по автору, добавлены заголовки дат и цитаты ответов.
- **Целостность данных**: Добавлено отслеживание метаданных групп и исправлена путаница имен пользователей и чатов.
- **Инфраструктура**: Оптимизирован `.gitignore` для надежного исключения файлов сессий и баз данных.
- **Надежность и Скорость**: 
  - Исправлена критическая проблема с игнорированием Ctrl+C и сбоем аварийного экспорта.
  - Внедрена оптимизация «Пропуск кеша», ускоряющая повторную синхронизацию в десятки раз.
  - Исправлен `TypeError` в режиме общего обновления и ошибки импортов.

### Fixed
- Resolved `AttributeError` in `DBExportService` related to wrong message ID attribute.
- Fixed `SyntaxError` (indentation) in `ExporterService` after UI updates.
- Corrected logic in `sync_chat` to prioritize user name for sync target registration.

## [4.0.0] - 2026-04-20
### Added
- **Target Attribution System**: Implemented a reference-counting mechanism using `message_target_links`. Every message and its surrounding context is now explicitly linked to a primary sync target.
- **Smart Purge (Garbage Collection)**: Redesigned the data removal logic. Context messages are now only deleted from the database if they are no longer referenced by any active sync target, preventing data orphans and preserving shared conversation context.
- **Async-Native Signal Handling**: Refactored the core process manager to use `asyncio.EventLoop.add_signal_handler`. This ensures immediate and reliable response to Ctrl+C (SIGINT) even during heavy I/O or network operations.
- **Emergency JSON Dumps**: Guaranteed export of partial data to `DB_EXPORTS/*.jsonl` upon interruption. The CLI now provides explicit feedback and the filesystem path of the dump.
- **Stateful Resume Engine**: Implemented a dual-sync model (Head/Tail) tracking synchronization boundaries per target. The system now skips already-synced history blocks and resumes instantly.

### Changed
- **Database Schema**: Significant upgrades to support normalization (`users`, `chats`, `message_target_links`).
- **Worker Logic**: Added granular shutdown checks to all export workers for immediate termination upon interrupt signals.
- **CLI UX**: Enhanced 24-bit ANSI gradient aesthetics and interactive sub-menu navigation.

### Fixed
- Resolved `NameError` in `process.py` by restoring missing `asyncio` imports.
- Fixed `AttributeError` in `Exporter` related to missing `should_stop` method in storage.
- Corrected database initialization logic to prevent missing table errors after full wipes.

## [3.5.0] - Previously
- Refactored project into modular `core/`, `services/`, `infrastructure/` layers.
- Implemented `TelethonClientWrapper` with advanced throttling and FloodWait protection.
- Added interactive terminal sub-menus with raw input support.
- Centralized logging into `LOGS/` directory.
