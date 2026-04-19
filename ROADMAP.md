# 🗺️ Project Evolution Roadmap / Дорожная карта проекта

This document outlines the strategic path for transforming the Telegram Message Cleaner & Exporter into a professional-grade analysis system.

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="english"></a>
## 🇬🇧 English: System Architect’s Roadmap (AI-Targeted)

This section is optimized for future LLM agents to understand the system's technical requirements and architectural constraints.

### 🟢 Phase 1: Foundations & Reliability (COMPLETED)
*Status: 100% Complete*

### 1.1 Data Model Standardization
- [x] **Core Schema**: Defined essential fields (`msg_id`, `chat_id`, reactions, context).
- [x] **Schema Versioning**: Implementation of `schema_version` for future-proof storage.
- [x] **Nested Context**: Robust handling of replies and forwarded messages.

### 1.2 Storage Infrastructure (SQLite)
- [x] **Engine**: Implemented `SQLiteStorage` with WAL mode for performance.
- [x] **Deduplication**: Automatic conflict resolution via `INSERT OR REPLACE` on `(chat_id, msg_id)`.
- [x] **Smart Update 2.0 Engine**: Capability to query last known message indices across thousands of chats.

### 1.3 Scalable Logic
- [x] **Parallel Persistence**: Async loop saving to both Files and DB simultaneously.
- [x] **Identity Separation**: Namespace support for multiple accounts (`account_name`).
- [x] **Target Filtering**: Intelligent discovery of active export targets.

### 🟢 Phase 2: Logic & Execution Safety (COMPLETED)
*Status: 100% Complete*

- [x] **Deep Mode Formalization**: context fetching with sane defaults (window 3).
- [x] **Config Persistence**: per-target settings stored in SQLite.
- [x] **Smart Sync**: transitioned from file-scanning to DB state-tracking for updates.
- [x] **Force Resync**: capability to reset indexing and re-audit history.
- [x] **Default Safety**: explicitly defined priorities for CLI overrides.
- [x] **Data Disposal**: implemented `delete` command for full target purging (DB + Files).

### 🚀 Phase 3: Advanced Features & Analytics
**Goal**: Modularize the codebase and enable data-driven insights.

- **1. Module Decomposition**
    - [ ] Decouple into layers: `core` (API/Client), `services` (Action logic), `infrastructure` (Storage/Scheduler).
- **2. Data-Driven Analytics**
    - [ ] Implement Query Layer: Search by user patterns, keywords, and time clusters.
    - [ ] **Graph Modeling**: Build nodes (users) and edges (interactions/replies).
- **3. Quality & Observability**
    - [ ] Implement structured JSON logging for all system events.
    - [ ] Develop comprehensive test suite (Unit/Integration).

---

<a id="русский"></a>
## 🇷🇺 Русский: Дорожная карта (Для пользователя)

Данный раздел описывает этапы эволюции проекта от набора скриптов до полноценной аналитической системы.

### 🗺️ Этап 1: Фундамент и Надежность
**Цель**: Создать строгую структуру данных и перейти на профессиональное хранение.

1.  **Стандартизация данных**: Определение четких схем для сообщений, пользователей и логов. Введение контроля версий схемы.
2.  **Переход на Базу Данных**: Внедрение SQLite (и DuckDB в будущем) вместо текстовых файлов. Это обеспечит скорость поиска и исключит повреждение файлов.
3.  **Система защиты от дублей**: Умная проверка по ID сообщения и чата. Если сообщение было отредактировано в Telegram, инструмент обновит его в базе.
4.  **Безопасность конфигурации**: Валидация настроек при запуске, поддержка секретов через переменные окружения и поддержка нескольких аккаунтов.

### 🟢 Этап 2: Умная логика и Стабильность (ЗАВЕРШЕНО)
*Статус: Готово на 100%*

1.  **Глубокий анализ контекста**: Внедрен Gold Standard (окно 3) по умолчанию.
2.  **Память конфигураций**: Настройки для каждой цели теперь живут в базе данных.
3.  **Мгновенные обновления**: Переход на полностью автономный `update` через БД.
4.  **Флаг Force Resync**: Добавлена возможность полного пересмотра истории.
5.  **Команда Delete**: Реализована полная очистка данных пользователя (БД + файлы).

### 📊 Этап 3: Аналитика и Архитектура
**Цель**: Разделить код на независимые модули и добавить инструменты исследования данных.

1.  **Модульная структура**: Разделение кода на независимые части (Ядро, Сервисы, Хранилище). Это упростит добавление новых функций.
2.  **Граф взаимодействий**: Возможность визуализировать, кто с кем общается, строить связи между пользователями на основе ответов (replies).
3.  **Поиск и Отчетность**: Продвинутый поиск по ключевым словам и паттернам поведения во всем массиве собранных данных.
4.  **Полное покрытие тестами**: Гарантия того, что обновления не сломают старые функции.

---
*Roadmap created based on the evolution plan of April 2026.*
