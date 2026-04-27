# 🧹 TG_MSG_MNGR: Advanced Telegram Suite

[🇷🇺 Русская версия](#русский) | [🇬🇧 English Version](#english)

---

<a id="русский"></a>
## 🇷🇺 Русский

**TG_MSG_MNGR** — это мощная экосистема для управления вашим цифровым следом в Telegram. Утилита представляет собой полноценное консольное приложение с интерактивным меню, фокусом на UX, скорость и надежность.

### Quick Reference

```bash
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --depth 3 --json
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --flat
python3 -m tg_msg_manager.cli db-export --user-id 123456789
python3 -m tg_msg_manager.cli export-pm --user-id 123456789
python3 -m tg_msg_manager.cli db-export --user-id 123456789 --json
python3 -m tg_msg_manager.cli update
```

### 🚀 Быстрый старт

1. **Установка**:
   ```bash
   git clone https://github.com/JohnyNoxwell/tg-msg-manager.git
   cd tg-msg-manager
   pip install .
   ```

2. **Запуск интерактивного меню**:
   *   **Способ A (Самый быстрый)**: Из интерактивного терминала, находясь в корне проекта:
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
* 📤 **Экспорт из БД** — Выгрузка накопленных данных из SQLite в JSON/Text. JSONL по умолчанию теперь компактный и ориентирован на анализ нейросетью.

---

### 🛠️ Продвинутое использование (CLI)

Для автоматизации и опытных пользователей доступны прямые команды:

> ⚠️ **Примечание**: Прямые команды `python3 -m ...` необходимо запускать из корня проекта.

*   **Экспорт сообщений**: 
    `python3 -m tg_msg_manager.cli export --user-id 123456789 --depth 3`
    `python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --depth 3 --json`
    `python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --flat`
    `--json` собирает итоговый JSONL-файл после синка; без `--json` итоговый файл будет TXT.
    По умолчанию Deep Mode использует `--depth 2`, если глубина явно не указана.
*   **Очистка (Боевой режим)**: 
    `python3 -m tg_msg_manager.cli clean --apply --yes`
*   **Обновление всех целей**: 
    `python3 -m tg_msg_manager.cli update`
    После прерванного большого экспорта `update` может некоторое время выглядеть "задумавшимся" до появления построчного прогресса: в этот момент сервис делает shared head prefetch для чата и готовит общий HEAD-срез для нескольких целей.
*   **Архив лички**:
    `python3 -m tg_msg_manager.cli export-pm --user-id 123456789`
*   **Экспорт из БД**:
    `python3 -m tg_msg_manager.cli db-export --user-id 123456789`
    `python3 -m tg_msg_manager.cli db-export --user-id 123456789 --json`
    Без `--json` команда пишет TXT; с `--json` — компактный AI-friendly JSONL.
*   **Полное удаление локальных данных**:
    `python3 -m tg_msg_manager.cli delete --user-id 123456789`
*   **Планировщик (macOS)**:
    `python3 -m tg_msg_manager.cli schedule`
*   **Установка алиасов**:
    `python3 -m tg_msg_manager.cli setup`

### ✅ Локальная проверка

```bash
pip install -e .[dev]
make lint
make format-check
make test
make verify
```

Минимальный smoke-check с текущей Telegram-сессией:

```bash
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --flat --limit 1
```

### Known Limitations

* `--limit` ограничивает обработку в рамках одного `sync_chat`; при экспорте пользователя по нескольким диалогам лимит применяется к каждому диалогу отдельно.
* `export-pm` пишет текстовый лог и медиа-структуру, но не восстанавливает Telegram-специфичные сущности как полноценный replay архива.
* Фоновая запись в SQLite остаётся чувствительной к очень большим deep-export проходам; основная оптимизация сейчас сделана на уровне пакетных сервисных вызовов.
* Планировщик `schedule` сейчас ориентирован на macOS `launchd`.
* `db-export --json` по умолчанию не включает полный `raw_payload`; если когда-нибудь понадобится полный Telethon-слепок, это потребует отдельного full-профиля экспорта.
* После прерванного `export/tge` команда `update/tgu` может иметь заметную подготовительную паузу перед первым видимым прогрессом, если системе нужно переиспользовать большой общий HEAD-срез чата.

<a id="алиасы"></a>
#### 🚀 Быстрые Алиасы (Power User)
Выполните `python3 run.py setup`, чтобы создать короткие команды:
*   `tg` — Запуск главного меню.
*   `tgr` — Репетиция очистки в dry-run.
*   `tgd` — Мгновенная очистка всех ваших сообщений.
*   `tgu` — Автоматическое обновление всей базы.
*   `tge ID` — Быстрый экспорт конкретного пользователя.
*   `tgpm ID` — Быстрый архив лички по user ID.

---
---

<a id="english"></a>
## 🇬🇧 English

**TG_MSG_MNGR** is a high-performance ecosystem for managing your digital footprint on Telegram. The utility features a robust, "app-like" terminal interface focusing on UX, speed, and deterministic data integrity.

### Quick Reference

```bash
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --depth 3 --json
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --flat
python3 -m tg_msg_manager.cli db-export --user-id 123456789
python3 -m tg_msg_manager.cli export-pm --user-id 123456789
python3 -m tg_msg_manager.cli db-export --user-id 123456789 --json
python3 -m tg_msg_manager.cli update
```

### 🚀 Quick Start

1. **Installation**:
   ```bash
   git clone https://github.com/JohnyNoxwell/tg-msg-manager.git
   cd tg-msg-manager
   pip install .
   ```

2. **Launch Interactive Menu**:
   *   **Method A (Fastest)**: From an interactive terminal in the project root:
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
* 📤 **Database Export** — Export collected SQLite records into JSON or Text. JSONL now defaults to a compact AI-friendly profile.

---

### 🛠️ Advanced Usage (CLI)

Subcommands can be executed directly for automation:

> ⚠️ **Note**: Full `python3 -m ...` commands must be executed from the project root.

*   **Message Export**: 
    `python3 -m tg_msg_manager.cli export --user-id 123456789 --depth 3`
    `python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --depth 3 --json`
    `python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --flat`
    `--json` writes a final JSONL snapshot after sync; without `--json`, the final export is TXT.
    Deep Mode defaults to `--depth 2` when no explicit depth is provided.
*   **Global Cleanup (Apply)**: 
    `python3 -m tg_msg_manager.cli clean --apply --yes`
*   **Universal Update**: 
    `python3 -m tg_msg_manager.cli update`
    After a large interrupted export, `update` may appear idle before per-target progress starts; during that phase the service is building a shared head prefetch slice for the chat.
*   **PM Archive**:
    `python3 -m tg_msg_manager.cli export-pm --user-id 123456789`
*   **DB Export**:
    `python3 -m tg_msg_manager.cli db-export --user-id 123456789`
    `python3 -m tg_msg_manager.cli db-export --user-id 123456789 --json`
    Without `--json`, the command writes TXT; with `--json`, it writes compact AI-friendly JSONL.
*   **Full Local Purge**:
    `python3 -m tg_msg_manager.cli delete --user-id 123456789`
*   **Scheduler (macOS)**:
    `python3 -m tg_msg_manager.cli schedule`
*   **Alias Setup**:
    `python3 -m tg_msg_manager.cli setup`

### ✅ Local Verification

```bash
pip install -e .[dev]
make lint
make format-check
make test
make verify
```

Minimal live smoke-check with the current Telegram session:

```bash
python3 -m tg_msg_manager.cli export --user-id 123456789 --chat-id 987654321 --flat --limit 1
```

### Known Limitations

* `--limit` caps work inside a single `sync_chat`; when exporting a user across multiple dialogs, the cap applies per dialog.
* `export-pm` produces a text-and-media archive, not a full Telegram-native replayable backup.
* SQLite background writing is still most sensitive during very large deep-export passes; the current optimization focus is batched service-level writes.
* The built-in `schedule` command currently targets macOS `launchd`.
* `db-export --json` no longer includes the full `raw_payload` by default; a future explicit full-export profile would be needed for raw Telethon dumps.
* After an interrupted `export/tge`, `update/tgu` may have a noticeable preparation pause before the first visible per-target progress if the service needs to rebuild a large shared chat-head slice.

<a id="aliases"></a>
#### 🚀 Power User Aliases
Run `python3 run.py setup` to register short commands:
*   `tg` — Launch the main menu.
*   `tgr` — Dry-run cleanup rehearsal.
*   `tgd` — Instantly scan and delete your messages.
*   `tgu` — Progressively update all tracked targets.
*   `tge ID` — Quick export for a specific user.
*   `tgpm ID` — Quick PM archive by user ID.
