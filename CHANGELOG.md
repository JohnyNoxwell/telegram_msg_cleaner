All notable changes to this project will be documented in this file in both English and Russian.
Все значимые изменения проекта фиксируются в этом файле на английском и русском языках.

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
