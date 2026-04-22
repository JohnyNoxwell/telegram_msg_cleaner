# 🧹 TG_MSG_MNGR: Advanced Telegram Suite

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="русский"></a>
## 🇷🇺 Русский

**TG_MSG_MNGR** — это мощная экосистема для управления вашим цифровым следом в Telegram. Переосмысленная в версии 4.0, утилита превратилась из простого скрипта в полноценное консольное Android-подобное приложение с фокусом на UX, скорость и надежность.

### 💎 Преимущества версии 4.0 (UX Revolution)

* 🎨 **Cyberpunk UI**: Полноцветная 24-битная ANSI градиентная шапка и премиальный дизайн интерфейса.
* ⚡ **Интерактивность**: Навигация в одно касание и поддержка клавиши **ESC** для оперативной отмены.
* 📊 **Terminal Feedback**: Реальное время отображения прогресса очистки и экспорта с наглядными счетчиками в консоли.
* 🏗️ **Модульная архитектура**: Сервисно-ориентированное ядро для максимальной стабильности.

* 📖 **Контекстное обучение**: Каждое подменю снабжено краткой справкой о том, как работает конкретный алгоритм.

### 🌟 Главные функции

* 🧹 **Глобальная очистка (`clean`)**
  Удаляет **только ваши** сообщения изо всех чатов. Поддерживает группы, каналы и (опционально) **личные переписки (PM)**. Включает белые списки и умный обход FloodWait.

  
* 📥 **Умный экспорт с контекстом (`export`)**
  Собирает сообщения цели вместе с «окном» беседы (реплики до и после), восстанавливая полную картину диалога.

* 🗄️ **SQLite Storage**
  Все данные превращаются в структурированную базу `messages.db`. Никакого дублирования, мгновенный доступ к миллионам записей.

* 💬 **Медиа-архив лички (`export-pm`)**
  Полный бэкап приватного чата: текст и все медиафайлы (фото, видео, документы), отсортированные по категориям.

* 📤 **Экспорт из БД (`db-export`)**
  Возможность выгрузить накопленные в SQLite данные в человекочитаемые форматы (JSON/Text).

---

### 📊 Подробный CLI Reference

Для продвинутых пользователей доступны команды напрямую:

*   **Экспорт сообщений (`export`)**
    *   Алиас: `tge --user-id ID`
    *   Полная команда: `tg export --user-id ID`
    *   Опции:
        *   `--chat-id ID`: Ограничить поиск конкретным чатом.
        *   `--context-window N`: Размер захвата сообщений вокруг цели (по умолчанию 3).
        *   `--depth N`: Глубина рекурсивного поиска связей (1-5, по умолчанию 3).
        *   `--flat`: Отключить сбор контекста (только сообщения цели).
        *   `--json`: Дублировать результат в JSON-файл.
        *   `--force-resync`: Игнорировать кэш и перекачать историю заново.

*   **Глобальная очистка (`clean`)**
    *   Алиас (Боевой): `tgd`
    *   Алиас (Тест): `tgr`
    *   Полная команда: `tg clean --apply` (для удаления) или `tg clean` (для теста).
    *   Опция `--yes`: Пропустить подтверждение удаления.

*   **Обновление базы (`update`)**
    *   Алиас: `tgu`
    *   Полная команда: `tg update`

*   **Экспорт из БД (`db-export`)**
    *   Команда: `tg db-export --user-id ID`

---

### 🚀 Быстрые Алиасы (Power User)

Если вы настроили алиасы через `tg-msg-manager setup`, вам доступны короткие команды:

*   `tgd` — **Live Deletion**: Мгновенный запуск очистки всех ваших сообщений (с подтверждением).
*   `tgr` — **Dry Run**: Тестовое сканирование сообщений без их удаления.
*   `tgu` — **Universal Update**: Автоматическое обновление всей накопленной базы по всем целям.

---

### 💻 Установка и быстрый старт

1. **Клонируйте репозиторий** и установите зависимости: `pip install .`
2. **Алиасы**: Выполните команду установки из основной папки:
   ```bash
   python3 -m tg_msg_manager.cli setup
   ```
   Это создаст короткую команду `tg` и быстрые алиасы (`tgd`, `tgr`, `tgu` и др.).
3. **Запуск**: Просто введите `tg` в терминале для входа в интерактивное меню.

> 💡 **Навигация в меню**: Используйте цифры **1-9** для выбора, **ESC** — назад/отмена, **0** — выход.

---
---

<a id="english"></a>
## 🇬🇧 English

**TG_MSG_MNGR** is a high-performance ecosystem for managing your digital footprint on Telegram. Reimagined in Version 4.0, the utility has evolved from a simple script into a robust, "app-like" terminal experience focusing on UX, speed, and deterministic data integrity.

### 💎 Version 4.0 Highlights (UX Revolution)

* 🎨 **Cyberpunk UI**: Vibrant 24-bit ANSI gradient banners and a premium interface design.
* ⚡ **Ultra-Responsive**: Single-key navigation and full **ESC** key support for instant cancellation.
* 📊 **Live Telemetry**: Real-time progress indicators and message counters for all cleanup and sync operations.
* 🏗️ **Service-Oriented Core**: Refactored modular architecture ensuring long-term stability and easier auditing.

* 📖 **In-App Guidance**: Every sub-menu features technical descriptions of how the specific engine works.

### 🌟 Core Features

* 🧹 **Global Cleanup (`clean`)**
  Removes **your own** messages from all chats. Supports groups, channels, and optionally **Private Dialogues (PM)**. Respects whitelists and handles FloodWait.

  
* 📥 **Deep Context Export (`export`)**
  Automatically retrieves target messages along with the "surrounding" conversation window, providing a complete picture of the dialogue.

* 🗄️ **SQLite Source of Truth**
  All messages are stored in a structured `messages.db`. Ensures zero duplicates and instant querying across millions of records.

* 💬 **Media Archive (`export-pm`)**
  Total backup for private conversations: text and **all media types** (photos, videos, voice notes), auto-sorted into categorized folders.

* 📤 **Database Export (`db-export`)**
  Native service to export collected SQLite records into human-readable formats (JSON/TXT).

---

### 📊 Detailed CLI Reference

For power users, subcommands can be executed directly:

*   **Message Export (`export`)**
    *   Alias: `tge --user-id ID`
    *   Full Command: `tg export --user-id ID`
    *   Options:
        *   `--chat-id ID`: Target a specific chat only.
        *   `--context-window N`: Number of neighbor messages to fetch (default: 3).
        *   `--depth N`: Recursion depth for context extraction (1-5, default: 3).
        *   `--flat`: Disable "Deep Mode" (fetch target messages only).
        *   `--json`: Simultaneously export to JSON file.
        *   `--force-resync`: Ignore sync markers and re-scan history.

*   **Global Cleanup (`clean`)**
    *   Alias (Apply): `tgd`
    *   Alias (Dry-run): `tgr`
    *   Full Command: `tg clean --apply` (to delete) or `tg clean` (to test).
    *   Option `--yes`: Skip the safety confirmation prompt.

*   **Smart Update (`update`)**
    *   Alias: `tgu`
    *   Full Command: `tg update`

*   **Database Export (`db-export`)**
    *   Command: `tg db-export --user-id ID`

---

### 🚀 Power User Aliases

After running `tg-msg-manager setup`, these shortcuts are available:

*   `tgd` — **Live Deletion**: Instantly scan and delete your messages from all chats.
*   `tgr` — **Dry Run**: Check what messages would be deleted without taking action.
*   `tgu` — **Universal Update**: Progressively update all tracked targets in the database.

---

### 💻 Installation & Quick Start

1. **Clone & Install**: Run `pip install .` in the root directory.
2. **Aliases**: Execute the setup command from the project folder:
   ```bash
   python3 -m tg_msg_manager.cli setup
   ```
   This registers the `tg` shortcut and all power-user aliases.
3. **Launch**: Simply type `tg` in your terminal to enter the premium interactive menu.

> 💡 **Menu Navigation**: Use numbers **1-9** to select, **ESC** to go back/cancel, and **0** to exit.

