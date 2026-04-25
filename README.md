# 🧹 TG_MSG_MNGR: Advanced Telegram Suite

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="русский"></a>
## 🇷🇺 Русский

**TG_MSG_MNGR** — это мощная экосистема для управления вашим цифровым следом в Telegram. Утилита представляет собой полноценное консольное приложение с интерактивным меню, фокусом на UX, скорость и надежность.

### 🚀 Быстрый старт

1. **Установка**:
   ```bash
   git clone https://github.com/JohnyNoxwell/tg-msg-manager.git
   cd tg-msg-manager
   pip install .
   ```

2. **Запуск интерактивного меню**:
   *   **Способ A (Самый быстрый)**: Из корня папки проекта:
       ```bash
       python3 run.py
       ```
   *   **Способ B (После настройки)**: Введите `tg` в любом месте терминала (см. раздел [Алиасы](#алиасы)).

3. **Навигация**: Используйте цифры **1-9** для выбора функций, **ESC** — для возврата назад, **0** — для выхода.

---

### 🌟 Основные функции (Интерактивное меню)

Все возможности доступны через удобный графический интерфейс в терминале:

* 🧹 **Глобальная очистка (`clean`)** — Удаляет **только ваши** сообщения из всех выбранных чатов. Поддерживает фильтры и безопасный режим (Dry Run).
* 📥 **Умный экспорт с контекстом (`export`)** — Собирает сообщения цели вместе с окружающим контекстом беседы, восстанавливая полную картину диалога.
* 💬 **Архив лички (`export-pm`)** — Текстовый бэкап приватного чата с подготовленной структурой папок под медиа.
* 🗄️ **SQLite База данных** — Все данные хранятся в структурированной базе `messages.db`. Это обеспечивает мгновенный поиск и отсутствие дубликатов.
* 📤 **Экспорт из БД** — Выгрузка накопленных данных из SQLite в человекочитаемые форматы (JSON/Text).

---

### 🛠️ Продвинутое использование (CLI)

Для автоматизации и опытных пользователей доступны прямые команды:

> ⚠️ **Примечание**: Прямые команды `python3 -m ...` необходимо запускать из корня проекта.

*   **Экспорт сообщений**: 
    `python3 -m tg_msg_manager.cli export --user-id 9439859384 --depth 3`
*   **Очистка (Боевой режим)**: 
    `python3 -m tg_msg_manager.cli clean --apply --yes`
*   **Обновление всех целей**: 
    `python3 -m tg_msg_manager.cli update`

<a id="алиасы"></a>
#### 🚀 Быстрые Алиасы (Power User)
Выполните `python3 run.py setup`, чтобы создать короткие команды:
*   `tg` — Запуск главного меню.
*   `tgd` — Мгновенная очистка всех ваших сообщений.
*   `tgu` — Автоматическое обновление всей базы.
*   `tge ID` — Быстрый экспорт конкретного пользователя.

---
---

<a id="english"></a>
## 🇬🇧 English

**TG_MSG_MNGR** is a high-performance ecosystem for managing your digital footprint on Telegram. The utility features a robust, "app-like" terminal interface focusing on UX, speed, and deterministic data integrity.

### 🚀 Quick Start

1. **Installation**:
   ```bash
   git clone https://github.com/JohnyNoxwell/tg-msg-manager.git
   cd tg-msg-manager
   pip install .
   ```

2. **Launch Interactive Menu**:
   *   **Method A (Fastest)**: From the project root:
       ```bash
       python3 run.py
       ```
   *   **Method B (After setup)**: Type `tg` anywhere in your terminal (see [Aliases](#aliases)).

3. **Navigation**: Use numbers **1-9** to select, **ESC** to go back/cancel, and **0** to exit.

---

### 🌟 Core Features (Interactive Menu)

All features are available through a premium terminal UI:

* 🧹 **Global Cleanup (`clean`)** — Removes **your own** messages from all selected chats. Supports whitelists and safe Dry Run mode.
* 📥 **Deep Context Export (`export`)** — Automatically retrieves target messages along with the "surrounding" conversation window.
* 💬 **PM Archive (`export-pm`)** — Text backup for private conversations with a prepared folder structure for media.
* 🗄️ **SQLite Storage** — All messages are stored in a structured `messages.db` for instant querying and zero duplicates.
* 📤 **Database Export** — Export collected SQLite records into human-readable JSON or Text formats.

---

### 🛠️ Advanced Usage (CLI)

Subcommands can be executed directly for automation:

> ⚠️ **Note**: Full `python3 -m ...` commands must be executed from the project root.

*   **Message Export**: 
    `python3 -m tg_msg_manager.cli export --user-id 9439859384 --depth 3`
*   **Global Cleanup (Apply)**: 
    `python3 -m tg_msg_manager.cli clean --apply --yes`
*   **Universal Update**: 
    `python3 -m tg_msg_manager.cli update`

<a id="aliases"></a>
#### 🚀 Power User Aliases
Run `python3 run.py setup` to register short commands:
*   `tg` — Launch the main menu.
*   `tgd` — Instantly scan and delete your messages.
*   `tgu` — Progressively update all tracked targets.
*   `tge ID` — Quick export for a specific user.
